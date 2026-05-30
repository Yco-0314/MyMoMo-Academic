"""Local identifiability diagnostics — profile likelihood + Fisher info.

Two methods that complement `identifiability.identify_basins` (global,
K-restart clustering). All three together cover three identifiability
question scales:

  identify_basins      (global)  : are there multiple distinct optima?
  profile_likelihood   (per-param): around the MAP, is each param identified?
  fisher_info_eigen    (local)    : in joint param-space, which DIRECTIONS
                                    are flat?

Why three not one
-----------------
`identify_basins` finds MULTIPLE optima (multimodality). It can't tell
you about LOCAL identifiability around one optimum.

`profile_likelihood` fixes other params at MAP and sweeps ONE param ⟶
shows whether each param INDIVIDUALLY is identifiable. Misses
joint-space ridges (e.g., μ × α product matters, individual values
don't).

`fisher_info_eigen` does Hessian eigendecomposition at MAP — eigenvalues
near zero correspond to FLAT DIRECTIONS in joint param-space. Each
flat direction is a linear combination of parameters, so this catches
the joint-space ridges that single-param profile misses.

ADR-006 OQ#3 closed by all three together (today's Opinion Dynamics
35% err on μ is exactly the kind of identifiability ridge fisher_info
would diagnose as a flat eigenvector pointing along μ-α correlation).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from abm_auto.calibration.summary_stats import SummaryStats, full_trajectory


# Default grid size for profile sweep
DEFAULT_PROFILE_GRID = 15

# Default Fisher info finite-difference step as fraction of prior range
DEFAULT_FISHER_EPS_FRAC = 0.02

# Eigenvalue threshold below which a direction is considered "flat"
# (i.e. unidentifiable). Relative to the largest eigenvalue.
DEFAULT_FLAT_EIGEN_RATIO = 1e-3


# ─────────────────────────────────────────────────────────────────────────
# Profile likelihood
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class ProfilePoint:
    """One slice point: (param value, objective at that slice)."""
    param_value: float
    objective: float


@dataclass
class ParamProfile:
    """Profile of one parameter — objective sliced across prior range."""
    name: str
    points: list[ProfilePoint]
    map_value: float
    map_objective: float

    @property
    def min_objective(self) -> float:
        return min(p.objective for p in self.points)

    @property
    def max_objective(self) -> float:
        return max(p.objective for p in self.points)

    @property
    def curvature(self) -> float:
        """Spread of objectives across the slice — proxy for identifiability.

        Large curvature = sharp minimum at MAP = well-identified.
        Small curvature = flat profile = unidentifiable.
        Normalised by MAP objective so cross-param comparable.
        """
        if self.map_objective == 0:
            return float(self.max_objective - self.min_objective)
        return (self.max_objective - self.min_objective) / max(self.map_objective, 1e-9)


@dataclass
class ProfileResult:
    """Full profile-likelihood diagnostic across all parameters."""
    map_params: dict[str, float]
    per_param: dict[str, ParamProfile]

    def unidentifiable_params(self, threshold: float = 0.1) -> list[str]:
        """Names of params whose profile curvature is below threshold."""
        return [name for name, p in self.per_param.items() if p.curvature < threshold]

    def to_markdown(self) -> str:
        lines = ["## Profile likelihood (per-parameter identifiability)", ""]
        lines.append("| Parameter | MAP value | MAP objective | Min profile | Max profile | Curvature | Verdict |")
        lines.append("|---|---|---|---|---|---|---|")
        for name, prof in self.per_param.items():
            verdict = "FLAT" if prof.curvature < 0.1 else "identified"
            lines.append(
                f"| `{name}` | {prof.map_value:.4f} | {prof.map_objective:.2f} | "
                f"{prof.min_objective:.2f} | {prof.max_objective:.2f} | "
                f"{prof.curvature:.3f} | {verdict} |"
            )
        flat = self.unidentifiable_params()
        if flat:
            lines += [
                "",
                f"> **⚠ Flat profiles detected for: {flat}** — these parameters' MAP "
                "values are not individually identifiable from the observation. "
                "Reporting them as point estimates is misleading; consider posterior "
                "ranges or note the unidentifiability explicitly."
            ]
        return "\n".join(lines) + "\n"


def profile_likelihood(
    simulator,
    priors: dict[str, dict],
    map_params: dict[str, float],
    targets: list[str],
    obs_stats: np.ndarray,
    n_grid: int = DEFAULT_PROFILE_GRID,
    summary_fn: SummaryStats = full_trajectory,
) -> ProfileResult:
    """For each parameter, fix others at MAP and sweep across prior range.

    Returns objective profile per parameter — flat profile means that
    parameter individually doesn't affect fit quality (unidentifiable).

    Cost: n_params × n_grid simulator calls. For 3 params × 15-grid =
    45 extra sims (~11s at 250ms/sim).
    """
    profiles: dict[str, ParamProfile] = {}

    # MAP objective — baseline for all profiles
    map_sim = simulator.simulate(map_params, targets)
    if map_sim is None:
        map_obj = float("inf")
    else:
        map_obj = float(np.linalg.norm(map_sim - obs_stats))

    for name in priors:
        lo, hi = float(priors[name]["min"]), float(priors[name]["max"])
        grid = np.linspace(lo, hi, n_grid)
        points: list[ProfilePoint] = []
        for value in grid:
            params = dict(map_params)
            params[name] = float(value)
            sim = simulator.simulate(params, targets)
            if sim is None:
                continue
            obj = float(np.linalg.norm(sim - obs_stats))
            points.append(ProfilePoint(param_value=float(value), objective=obj))
        if not points:
            continue
        profiles[name] = ParamProfile(
            name=name,
            points=points,
            map_value=float(map_params[name]),
            map_objective=map_obj,
        )

    return ProfileResult(map_params=dict(map_params), per_param=profiles)


# ─────────────────────────────────────────────────────────────────────────
# Fisher information + eigendecomposition
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class FisherEigenResult:
    """Hessian eigendecomposition at MAP.

    Eigenvalues near zero → flat directions → unidentifiable combinations
    of parameters. Eigenvectors give the LINEAR COMBINATION of params
    that's unidentifiable (e.g. [+1 in μ, -1 in α] = the μ×α ridge).
    """
    param_names: list[str]
    map_params: dict[str, float]
    hessian: np.ndarray            # n_params × n_params
    eigenvalues: np.ndarray        # n_params, sorted descending
    eigenvectors: np.ndarray       # n_params × n_params, columns are directions

    def flat_directions(
        self, ratio_threshold: float = DEFAULT_FLAT_EIGEN_RATIO,
    ) -> list[tuple[float, dict[str, float]]]:
        """Return (eigenvalue, direction-as-dict) for flat eigenvectors.

        A direction is "flat" when its eigenvalue ÷ largest eigenvalue is
        below `ratio_threshold` (default 1e-3). Each direction is a
        normalised linear combination of parameters expressed as
        {param_name: coefficient}.
        """
        if len(self.eigenvalues) == 0:
            return []
        top = float(np.max(np.abs(self.eigenvalues)))
        if top == 0:
            return []
        flats: list[tuple[float, dict[str, float]]] = []
        for j, eig in enumerate(self.eigenvalues):
            if abs(eig) / top < ratio_threshold:
                vec = self.eigenvectors[:, j]
                direction = {n: float(vec[i]) for i, n in enumerate(self.param_names)}
                flats.append((float(eig), direction))
        return flats

    def to_markdown(self) -> str:
        lines = ["## Fisher information eigendecomposition (local identifiability)", ""]
        lines.append("Hessian of ||sim−obs||² at MAP, eigendecomposed. Small eigenvalues "
                     "correspond to flat directions in joint param-space — these are "
                     "parameter combinations that don't affect fit quality.")
        lines.append("")
        lines.append("| Rank | Eigenvalue | Direction (param: coefficient) |")
        lines.append("|---|---|---|")
        for j, eig in enumerate(self.eigenvalues):
            vec = self.eigenvectors[:, j]
            dir_str = ", ".join(
                f"{n}={vec[i]:+.3f}" for i, n in enumerate(self.param_names)
            )
            lines.append(f"| {j+1} | {eig:.4f} | {dir_str} |")
        flats = self.flat_directions()
        if flats:
            lines.append("")
            lines.append("> **⚠ Flat directions detected:**")
            for eig, direction in flats:
                dir_str = ", ".join(f"{n}={c:+.3f}" for n, c in direction.items())
                lines.append(f"> - eigenvalue {eig:.4f}: combination `{dir_str}`")
            lines.append(">")
            lines.append("> Each flat direction is a linear combination of params that "
                         "the data CAN'T constrain. Calibrator reports SOME point on this "
                         "ridge — don't trust individual param values along the flat direction.")
        return "\n".join(lines) + "\n"


def fisher_info_eigen(
    simulator,
    priors: dict[str, dict],
    map_params: dict[str, float],
    targets: list[str],
    obs_stats: np.ndarray,
    eps_frac: float = DEFAULT_FISHER_EPS_FRAC,
    summary_fn: SummaryStats = full_trajectory,
) -> Optional[FisherEigenResult]:
    """Numerical Hessian of ||sim−obs||² at MAP, eigendecomposed.

    Uses central differences for diagonal entries and cross differences
    for off-diagonal. Total simulator calls: 1 (centre) + 2N (diag) +
    4 × N×(N-1)/2 (off-diag) = 1 + 2N + 2N(N-1) = 1 + 2N² calls.

    For N=3 params → 1 + 18 = 19 calls (~5s at 250ms/sim).
    For N=5 params → 1 + 50 = 51 calls (~13s).

    Returns None if any required sim returns None (simulator failure).
    """
    param_names = list(priors.keys())
    N = len(param_names)
    if N == 0:
        return None

    # Step sizes per param (fraction of prior range)
    eps = np.array([
        eps_frac * (float(priors[n]["max"]) - float(priors[n]["min"]))
        for n in param_names
    ])

    def obj_at(params: dict[str, float]) -> Optional[float]:
        sim = simulator.simulate(params, targets)
        if sim is None:
            return None
        return float(np.linalg.norm(sim - obs_stats) ** 2)

    f0 = obj_at(map_params)
    if f0 is None:
        return None

    H = np.zeros((N, N))

    # Diagonal: ∂²f/∂θ_i² ≈ (f(θ+e_i) - 2f(θ) + f(θ-e_i)) / eps²
    f_plus = np.full(N, np.nan)
    f_minus = np.full(N, np.nan)
    for i, ni in enumerate(param_names):
        p_plus = dict(map_params); p_plus[ni] = map_params[ni] + eps[i]
        p_minus = dict(map_params); p_minus[ni] = map_params[ni] - eps[i]
        fp = obj_at(p_plus)
        fm = obj_at(p_minus)
        if fp is None or fm is None:
            return None
        f_plus[i] = fp
        f_minus[i] = fm
        H[i, i] = (fp - 2 * f0 + fm) / (eps[i] ** 2)

    # Off-diagonal: ∂²f/∂θ_i∂θ_j ≈
    #   (f(θ+e_i+e_j) - f(θ+e_i-e_j) - f(θ-e_i+e_j) + f(θ-e_i-e_j)) / (4*eps_i*eps_j)
    for i in range(N):
        for j in range(i + 1, N):
            ni, nj = param_names[i], param_names[j]
            def step(si: int, sj: int) -> Optional[float]:
                p = dict(map_params)
                p[ni] = map_params[ni] + si * eps[i]
                p[nj] = map_params[nj] + sj * eps[j]
                return obj_at(p)
            f_pp = step(+1, +1)
            f_pm = step(+1, -1)
            f_mp = step(-1, +1)
            f_mm = step(-1, -1)
            if None in (f_pp, f_pm, f_mp, f_mm):
                return None
            H[i, j] = (f_pp - f_pm - f_mp + f_mm) / (4 * eps[i] * eps[j])
            H[j, i] = H[i, j]

    # Eigendecomposition (symmetric Hessian)
    eigvals, eigvecs = np.linalg.eigh(H)
    # eigh returns ascending; flip to descending so rank 1 = largest
    order = np.argsort(-eigvals)
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]

    return FisherEigenResult(
        param_names=param_names,
        map_params=dict(map_params),
        hessian=H,
        eigenvalues=eigvals,
        eigenvectors=eigvecs,
    )


__all__ = [
    "ProfilePoint",
    "ParamProfile",
    "ProfileResult",
    "profile_likelihood",
    "FisherEigenResult",
    "fisher_info_eigen",
    "DEFAULT_PROFILE_GRID",
    "DEFAULT_FISHER_EPS_FRAC",
    "DEFAULT_FLAT_EIGEN_RATIO",
]
