"""Keller-Segel chemotaxis / slime-mold aggregation (1970) — a faithful grid-PDE reproduction.

Source: Keller, E. F. & Segel, L. A. (1970) "Initiation of slime mold aggregation viewed
as an instability", J. Theor. Biol. 26(3):399-415. doi:10.1016/0022-5193(70)90092-5.

IMPORTANT (honesty, binds the FINDINGS): this is a two-field chemotaxis PARTIAL-
DIFFERENTIAL-EQUATION integrated on a grid — a CELLULAR / grid-PDE model, NOT an agent-
stepping ABM. There are no agents that perceive, decide and act; no scheduler over an
agent roster; no per-agent step. It is a single synchronous update (explicit Euler with a
conservative flux discretization) applied to every grid cell of the two fields at once. We
disclose this exactly as the game_of_life / forest_fire / gray_scott reproductions disclose
they are cellular automata. The lock-first + honest-verdict + L3-bundle discipline still
applies in full.

The model (Keller & Segel 1970), two fields on a 2D PERIODIC (toroidal) grid — the cell
density rho and the chemoattractant concentration c:

    d rho/dt = D_rho * lap(rho)  -  chi * div( rho * grad(c) )
    d c  /dt = D_c   * lap(c)    +  a * rho  -  b * c

Cells DIFFUSE (D_rho) and, crucially, CLIMB the gradient of the attractant THEY THEMSELVES
secrete (the -chi*div(rho*grad c) chemotaxis flux, an advection of cells UP the c-gradient).
The attractant diffuses (D_c), is produced by cells at rate a*rho, and decays at rate b*c.
This positive feedback — cells make the signal, the signal pulls cells together, denser
clumps make more signal — is the Keller-Segel instability: above a threshold in the
chemotactic sensitivity, a uniform lawn of cells spontaneously collapses into dense peaks
(aggregation centres); below it, diffusion wins and the lawn stays uniform.

The dimensionless sensitivity S (the bifurcation parameter). Keller & Segel's linear
stability analysis of the uniform state rho=rho0, c=a*rho0/b shows the uniform state is
unstable exactly when the chemotactic drift overwhelms cell diffusion. The natural
dimensionless group is

    S  =  chi * a * rho0 / (D_rho * b)

(chemotactic pull per cell-diffusion, using the quasi-steady attractant response c' =
(a/b)*rho' to a density perturbation). S is what we DIAL; for a target S we back out
chi = S * D_rho * b / (a * rho0) with a, b, D_rho, D_c, rho0 all FIXED. S >> 1 is strongly
super-critical (aggregation), S << 1 is sub-critical (uniform). This is the single knob the
locked predictions sweep; nothing else is tuned.

Small random IC: rho = rho0 * (1 + eps * white noise), c at its uniform equilibrium
a*rho0/b, with a matching tiny perturbation. The noise seeds every Fourier mode so the
fastest-growing (long-wavelength) mode can emerge; it is the only randomness and is
deterministic given ``seed``.

CRITICAL NUMERICS (locked; a numerical blow-up is NOT physical aggregation):
  * The chemotaxis advection chi*div(rho*grad c) is discretised CONSERVATIVELY with an
    UPWIND flux at cell faces: the drift velocity on a face is chi*(gradient of c across
    that face), and the advected density on the face is taken from the UPWIND cell (the
    cell the flux flows out of). The divergence of these face fluxes updates rho. Upwinding
    keeps rho non-negative and the total mass exactly conserved (the flux leaving one cell
    is the flux entering its neighbour), so a growing max(rho) is genuine mass PILING UP,
    not a numerical oscillation exploding.
  * Diffusion uses the standard 5-point periodic Laplacian.
  * Explicit forward Euler with dt kept small enough for BOTH the diffusive limit
    dt < dx^2/(4*max(D_rho,D_c)) AND the advective (CFL) limit dt < dx / max|drift|. The
    constructor guards the diffusive limit; the runner uses a small dt and enough steps
    (~1e4-5e4) to reach the aggregated state.

Metrics (the locked grading quantities; all deterministic given seed):
  * ``peak_ratio`` = max(rho)/rho0 — how tall the tallest peak is vs the uniform mean.
  * ``cv`` = std(rho)/mean(rho) — the coefficient of variation of the density field; ~eps
    at t=0 (flat lawn + noise), large once mass has piled into peaks.
  * ``low_q_amplitude`` — the magnitude of the leading low-wavenumber Fourier mode of rho
    (mean over the smallest non-zero |k| shell). Its EARLY growth (positive slope) is the
    long-wavelength instability signature of the Keller-Segel linear analysis.

NumPy holds the two fields and does the vectorised Laplacian (np.roll), the upwind
chemotactic flux + divergence, and the FFT-free low-q mode; the result is the deterministic
Keller-Segel orbit for a given (S, seed).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Fixed physical / numerical constants (locked; PREDICTIONS-locked.md). None of these is
# tuned per-regime — only the dimensionless sensitivity S is dialled.
D_RHO = 1.0          # cell (random-motility) diffusion
D_C = 1.0            # attractant diffusion
A = 1.0             # attractant production rate per unit cell density
B = 1.0             # attractant decay rate
RHO0 = 1.0           # uniform mean cell density
DOMAIN_SIDE = 20.0   # physical side length of the (square, periodic) domain
GRID_N = 96          # cells per side (in [64,128] per the lock)


# -- the 5-point periodic Laplacian ------------------------------------------------

def laplacian(field: np.ndarray, dx: float) -> np.ndarray:
    """5-point discrete Laplacian of ``field`` on a PERIODIC (toroidal) grid.

    lap(f)_{ij} = (f_{i+1,j} + f_{i-1,j} + f_{i,j+1} + f_{i,j-1} - 4 f_{ij}) / dx^2.
    Implemented with np.roll (which wraps the edges, giving the periodic stencil exactly).
    """
    return (
        np.roll(field, 1, axis=0)
        + np.roll(field, -1, axis=0)
        + np.roll(field, 1, axis=1)
        + np.roll(field, -1, axis=1)
        - 4.0 * field
    ) / (dx * dx)


# -- the conservative upwind chemotactic flux divergence ---------------------------

def chemotaxis_divergence(rho: np.ndarray, c: np.ndarray, chi: float, dx: float) -> np.ndarray:
    """div( chi * rho * grad(c) ) on a PERIODIC grid, via a CONSERVATIVE UPWIND flux.

    This is the numerically delicate term. We build the advective flux on the cell FACES,
    upwinding the advected density, and take the discrete divergence of those face fluxes.
    Because each interior/periodic face contributes with opposite sign to its two cells, the
    total sum of the returned divergence is exactly zero — mass is conserved to machine
    precision, and there is no oscillatory instability of the advection term (upwinding is
    the flux-limited / stable discretization the lock requires).

    Face convention (axis 0 = rows, "x"; axis 1 = cols, "y"):
      * The face BETWEEN cell (i,j) and (i+1,j) carries a drift velocity
            u = chi * (c[i+1,j] - c[i,j]) / dx                       (up the c-gradient)
        and an upwind density  rho_face = rho[i,j] if u >= 0 else rho[i+1,j]
        (take the density from the cell the flux flows OUT of). The face flux is
            F_x[i,j] = u * rho_face.
      * The divergence contribution to rho[i,j] is (F into i,j  -  F out of i,j)/dx summed
        over both axes:  ( F_x[i-1,j] - F_x[i,j] + F_y[i,j-1] - F_y[i,j] ) / dx.

    Returns  div(chi*rho*grad c)  so that the density update is  d rho = ... - this term.
    """
    # --- axis 0 (rows) faces: face f[i] sits between cell i and cell i+1 ---
    u_x = chi * (np.roll(c, -1, axis=0) - c) / dx          # drift on the i|i+1 face
    rho_up_x = np.where(u_x >= 0.0, rho, np.roll(rho, -1, axis=0))
    flux_x = u_x * rho_up_x                                 # F_x[i,j] on face i|i+1

    # --- axis 1 (cols) faces ---
    u_y = chi * (np.roll(c, -1, axis=1) - c) / dx
    rho_up_y = np.where(u_y >= 0.0, rho, np.roll(rho, -1, axis=1))
    flux_y = u_y * rho_up_y                                 # F_y[i,j] on face j|j+1

    # discrete divergence: (flux entering from the "left" face) - (flux leaving the "right"
    # face), per axis, all /dx. np.roll(flux, 1) brings F[i-1,j] to position (i,j).
    div = (
        (np.roll(flux_x, 1, axis=0) - flux_x)
        + (np.roll(flux_y, 1, axis=1) - flux_y)
    ) / dx
    # 'div' as built equals -(divergence of the flux). The chemotaxis term in the PDE is
    # -chi*div(rho grad c); the density update adds exactly this 'div'. Return it as the
    # term to ADD to d rho (i.e. already the -div of the outward flux).
    return div


# -- low-q Fourier amplitude (long-wavelength mode) --------------------------------

def low_q_amplitude(field: np.ndarray) -> float:
    """Magnitude of the leading low-wavenumber Fourier mode of ``field`` (mean over the
    smallest non-zero |k| shell), on the periodic grid.

    The DC (k=0) component is the conserved mean and is excluded. The smallest non-zero
    |k| corresponds to the LONGEST wavelength that fits the box — exactly the mode the
    Keller-Segel linear stability analysis predicts grows first when S is super-critical.
    Growth of this amplitude early in the run is the long-wavelength instability signature.
    """
    n = field.shape[0]
    fk = np.fft.fft2(field - field.mean())
    # radial wavenumber index of each Fourier component (integer cycles per box, with wrap).
    kx = np.fft.fftfreq(n) * n
    ky = np.fft.fftfreq(n) * n
    KX, KY = np.meshgrid(kx, ky, indexing="ij")
    kmag = np.sqrt(KX * KX + KY * KY)
    # the smallest non-zero |k| shell is |k| == 1 (one full wave across the box).
    shell = np.isclose(kmag, 1.0)
    if not shell.any():
        return 0.0
    return float(np.mean(np.abs(fk[shell])) / (n * n))


# -- Model ------------------------------------------------------------------------

class KellerSegelModel:
    """Keller-Segel chemotaxis (1970) on an L x L periodic grid.

    Construct with the dimensionless sensitivity ``S`` (the bifurcation knob; chi is
    derived from it and the FIXED a, b, D_rho, rho0), plus the grid size, domain side, the
    fixed rates, time step, noise amplitude and seed. ``step`` performs one explicit-Euler
    update of both fields with the conservative upwind chemotactic flux; ``run`` integrates
    a fixed number of steps and records the peak ratio, CV, and low-q amplitude at
    intervals. Deterministic given ``seed``.

    This is a grid PDE (disclosed), not an agent model, so there is no AgentSet / scheduler;
    the "tick" is the synchronous field update.
    """

    def __init__(self, *, S: float, n: int = GRID_N, side: float = DOMAIN_SIDE,
                 D_rho: float = D_RHO, D_c: float = D_C, a: float = A, b: float = B,
                 rho0: float = RHO0, dt: float = 2e-3, noise: float = 0.01,
                 seed: int = 0) -> None:
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if side <= 0:
            raise ValueError(f"need side > 0 (got {side})")
        if D_rho <= 0 or D_c <= 0:
            raise ValueError(f"need D_rho>0, D_c>0 (got D_rho={D_rho}, D_c={D_c})")
        if a <= 0 or b <= 0:
            raise ValueError(f"need a>0, b>0 (got a={a}, b={b})")
        if rho0 <= 0:
            raise ValueError(f"need rho0 > 0 (got rho0={rho0})")
        if S < 0:
            raise ValueError(f"need S >= 0 (got {S})")
        if dt <= 0:
            raise ValueError(f"need dt > 0 (got {dt})")
        if noise < 0:
            raise ValueError(f"need noise >= 0 (got {noise})")
        self.S = float(S)
        self.n = int(n)
        self.side = float(side)
        self.D_rho = float(D_rho)
        self.D_c = float(D_c)
        self.a = float(a)
        self.b = float(b)
        self.rho0 = float(rho0)
        self.dt = float(dt)
        self.dx = self.side / self.n
        self.noise = float(noise)
        self.seed = int(seed)
        self.t = 0

        # Derive the chemotactic sensitivity chi from the dimensionless S (the only knob):
        #   S = chi * a * rho0 / (D_rho * b)   =>   chi = S * D_rho * b / (a * rho0).
        self.chi = self.S * self.D_rho * self.b / (self.a * self.rho0)

        # Stability guard: explicit-Euler DIFFUSION needs dt < dx^2/(4*max(D_rho,D_c)).
        # (The advective CFL limit dt < dx/max|drift| is regime-dependent; the runner keeps
        # dt small and the density stays finite/non-negative under the upwind flux, so a
        # finite peak is physical piling-up, not a blow-up.)
        self.diffusion_dt_limit = self.dx * self.dx / (4.0 * max(self.D_rho, self.D_c))
        if self.dt >= self.diffusion_dt_limit:
            raise ValueError(
                f"dt={self.dt} violates the diffusion stability limit "
                f"dx^2/(4*max(D_rho,D_c))={self.diffusion_dt_limit:.4g}")

        self._rng = np.random.default_rng(seed)
        self.rho, self.c = self._initial_condition()
        self.initial_cv = self.coefficient_of_variation()

    def _initial_condition(self) -> Tuple[np.ndarray, np.ndarray]:
        """Small random IC around the uniform state: rho = rho0*(1 + noise*white), and c at
        its uniform equilibrium c* = a*rho0/b with the matching tiny perturbation
        (a/b)*(rho-rho0). Deterministic given ``seed``. Density is clipped to stay >= 0."""
        pert = self.noise * self._rng.standard_normal((self.n, self.n))
        rho = self.rho0 * (1.0 + pert)
        np.clip(rho, 0.0, None, out=rho)
        c_eq = self.a * self.rho0 / self.b
        c = c_eq + (self.a / self.b) * (rho - self.rho0)
        return rho, c

    # -- one synchronous explicit-Euler update of both fields --
    def step(self) -> None:
        """Advance both fields one time step (forward Euler) off one shared snapshot.

        rho: diffusion (5-point Laplacian) MINUS the chemotactic flux divergence
        (conservative upwind). c: diffusion + production a*rho - decay b*c. The chemotaxis
        term is the ``chemotaxis_divergence`` helper, which returns -div(chi*rho*grad c)
        already, so it is ADDED to d rho."""
        rho, c = self.rho, self.c
        lap_rho = laplacian(rho, self.dx)
        lap_c = laplacian(c, self.dx)
        chemo = chemotaxis_divergence(rho, c, self.chi, self.dx)   # = -div(chi*rho*grad c)
        d_rho = self.D_rho * lap_rho + chemo
        d_c = self.D_c * lap_c + self.a * rho - self.b * c
        new_rho = rho + self.dt * d_rho
        # Upwinding keeps rho >= 0 analytically; clip guards only floating-point undershoot.
        np.clip(new_rho, 0.0, None, out=new_rho)
        self.rho = new_rho
        self.c = c + self.dt * d_c
        self.t += 1

    # -- metrics --
    def peak_ratio(self) -> float:
        """max(rho)/rho0 — height of the tallest density peak relative to the uniform mean.
        ~1 for a flat lawn; grows well above 1 as mass piles into aggregation centres."""
        return float(np.max(self.rho) / self.rho0)

    def coefficient_of_variation(self) -> float:
        """std(rho)/mean(rho) — spatial coefficient of variation of the density field. ~the
        noise amplitude at t=0 (flat lawn), large once the field has clumped into peaks."""
        m = float(np.mean(self.rho))
        if m <= 0.0:
            return 0.0
        return float(np.std(self.rho) / m)

    def low_q(self) -> float:
        """Amplitude of the leading (longest-wavelength) Fourier mode of the density field —
        the long-wavelength instability observable."""
        return low_q_amplitude(self.rho)

    def total_mass(self) -> float:
        """Sum of rho over the grid (times cell area) — conserved by the diffusion + the
        conservative chemotactic flux (up to the tiny non-negativity clip)."""
        return float(np.sum(self.rho) * self.dx * self.dx)

    def max_drift_cfl(self) -> float:
        """Current advective CFL number dt*max|drift|/dx (drift = chi*|grad c|). < 1 means
        the explicit advection step is within its stability limit this step."""
        gx = (np.roll(self.c, -1, axis=0) - self.c) / self.dx
        gy = (np.roll(self.c, -1, axis=1) - self.c) / self.dx
        max_grad = float(np.max(np.sqrt(gx * gx + gy * gy)))
        return self.chi * max_grad * self.dt / self.dx

    # -- run --
    def run(self, n_steps: int = 20000, *, record_every: int = 500) -> Dict[str, Any]:
        """Integrate ``n_steps`` explicit-Euler steps, recording the peak ratio, CV, and
        low-q amplitude every ``record_every`` steps (and at t=0 and the final step).

        Returns the final field metrics, the initial CV (t=0 noise level), the EARLY low-q
        slope (growth over the first recorded interval — the instability sign check), the
        peak advective CFL seen (numerical-health diagnostic), the mass drift (conservation
        check), and the recorded series. Deterministic given the construction seed."""
        if n_steps < 0:
            raise ValueError(f"need n_steps >= 0 (got {n_steps})")
        if record_every <= 0:
            raise ValueError(f"need record_every > 0 (got {record_every})")
        step_series: List[int] = []
        peak_series: List[float] = []
        cv_series: List[float] = []
        lowq_series: List[float] = []
        cfl_series: List[float] = []
        mass0 = self.total_mass()

        def record() -> None:
            step_series.append(self.t)
            peak_series.append(self.peak_ratio())
            cv_series.append(self.coefficient_of_variation())
            lowq_series.append(self.low_q())
            cfl_series.append(self.max_drift_cfl())

        record()  # t=0 baseline
        for i in range(n_steps):
            self.step()
            if (i + 1) % record_every == 0 or (i + 1) == n_steps:
                record()

        # EARLY low-q slope: growth of the low-q amplitude over the first recorded interval
        # (t=0 -> first record). Positive => the long-wavelength mode is growing (unstable).
        if len(lowq_series) >= 2 and lowq_series[0] > 0.0:
            early_lowq_growth = (lowq_series[1] - lowq_series[0]) / lowq_series[0]
        else:
            early_lowq_growth = 0.0

        mass_final = self.total_mass()
        return {
            "S": self.S, "chi": self.chi, "n": self.n, "side": self.side,
            "D_rho": self.D_rho, "D_c": self.D_c, "a": self.a, "b": self.b,
            "rho0": self.rho0, "dt": self.dt, "dx": self.dx, "noise": self.noise,
            "seed": self.seed, "n_steps": n_steps, "record_every": record_every,
            "initial_cv": self.initial_cv,
            "final_peak_ratio": self.peak_ratio(),
            "final_cv": self.coefficient_of_variation(),
            "cv_growth_factor": (self.coefficient_of_variation() / self.initial_cv
                                 if self.initial_cv > 0 else 0.0),
            "final_low_q": self.low_q(),
            "early_low_q_growth": early_lowq_growth,
            "max_cfl": max(cfl_series) if cfl_series else 0.0,
            "mass_rel_drift": abs(mass_final - mass0) / mass0 if mass0 > 0 else 0.0,
            "step_series": step_series,
            "peak_series": peak_series,
            "cv_series": cv_series,
            "low_q_series": lowq_series,
            "cfl_series": cfl_series,
        }


# -- run helpers ------------------------------------------------------------------

def run_single(S: float, *, n: int = GRID_N, side: float = DOMAIN_SIDE, D_rho: float = D_RHO,
               D_c: float = D_C, a: float = A, b: float = B, rho0: float = RHO0,
               dt: float = 2e-3, noise: float = 0.01, seed: int = 0, n_steps: int = 20000,
               record_every: int = 500) -> Dict[str, Any]:
    """One Keller-Segel run at a given sensitivity S and the fixed numerics; returns the run
    summary (final density metrics + the early low-q growth + series)."""
    return KellerSegelModel(
        S=S, n=n, side=side, D_rho=D_rho, D_c=D_c, a=a, b=b, rho0=rho0, dt=dt,
        noise=noise, seed=seed).run(n_steps, record_every=record_every)


def run_many_seeds(S: float, *, n: int = GRID_N, side: float = DOMAIN_SIDE,
                   D_rho: float = D_RHO, D_c: float = D_C, a: float = A, b: float = B,
                   rho0: float = RHO0, dt: float = 2e-3, noise: float = 0.01,
                   n_seeds: int = 5, seed_base: int = 0, n_steps: int = 20000,
                   record_every: int = 500) -> Dict[str, Any]:
    """Run ``n_seeds`` Keller-Segel runs (seed ``seed_base + i``) at fixed parameters and a
    given sensitivity S, and summarise the aggregation observables across seeds.

    Returns per-seed final peak ratio, final CV, CV growth factor, and early low-q growth,
    their means / spreads, the fraction of seeds whose early low-q mode grows, plus one
    representative trajectory (first seed) and the worst-case numerical-health diagnostics
    (peak CFL, mass drift) across seeds.
    """
    runs = [run_single(S, n=n, side=side, D_rho=D_rho, D_c=D_c, a=a, b=b, rho0=rho0,
                       dt=dt, noise=noise, seed=seed_base + i, n_steps=n_steps,
                       record_every=record_every)
            for i in range(n_seeds)]
    peak = [r["final_peak_ratio"] for r in runs]
    cv = [r["final_cv"] for r in runs]
    cv_growth = [r["cv_growth_factor"] for r in runs]
    lowq_growth = [r["early_low_q_growth"] for r in runs]
    init_cv = [r["initial_cv"] for r in runs]

    def mean(xs: List[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    def std(xs: List[float]) -> float:
        if not xs:
            return 0.0
        m = mean(xs)
        return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5

    return {
        "S": S, "chi": runs[0]["chi"], "n": n, "side": side,
        "D_rho": D_rho, "D_c": D_c, "a": a, "b": b, "rho0": rho0,
        "dt": dt, "noise": noise, "n_seeds": n_seeds, "seed_base": seed_base,
        "n_steps": n_steps, "record_every": record_every,
        "per_seed_peak_ratio": peak,
        "per_seed_final_cv": cv,
        "per_seed_cv_growth_factor": cv_growth,
        "per_seed_early_low_q_growth": lowq_growth,
        "per_seed_initial_cv": init_cv,
        "mean_peak_ratio": mean(peak), "min_peak_ratio": min(peak), "max_peak_ratio": max(peak),
        "std_peak_ratio": std(peak),
        "mean_final_cv": mean(cv), "min_final_cv": min(cv), "max_final_cv": max(cv),
        "mean_cv_growth_factor": mean(cv_growth), "min_cv_growth_factor": min(cv_growth),
        "mean_initial_cv": mean(init_cv),
        "mean_early_low_q_growth": mean(lowq_growth),
        "n_seeds_low_q_grows": sum(1 for g in lowq_growth if g > 0.0),
        "frac_low_q_grows": sum(1 for g in lowq_growth if g > 0.0) / len(lowq_growth),
        # worst-case numerical health across seeds (a blow-up would show here).
        "max_cfl_over_seeds": max(r["max_cfl"] for r in runs),
        "max_mass_rel_drift_over_seeds": max(r["mass_rel_drift"] for r in runs),
        # one representative trajectory (first seed) for plotting/inspection.
        "example_step_series": runs[0]["step_series"],
        "example_peak_series": runs[0]["peak_series"],
        "example_cv_series": runs[0]["cv_series"],
        "example_low_q_series": runs[0]["low_q_series"],
    }
