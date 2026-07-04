"""TASEP with open boundaries (Derrida, Evans, Hakim & Pasquier 1993) — a faithful
boundary-driven-transport reproduction.

Source: Derrida, B., Evans, M.R., Hakim, V. & Pasquier, V. (1993) "Exact solution of a
1D asymmetric exclusion model using a matrix formulation", J. Phys. A: Math. Gen.
26:1493-1517. doi:10.1088/0305-4470/26/7/011.

IMPORTANT (honesty, binds the FINDINGS): this is a CELLULAR-AUTOMATON / interacting-
particle-system model, framing **CA (disclosed)**, NOT an agent-stepping ABM. There are
no agents that perceive, decide and act, no scheduler over an agent roster, no per-agent
step. It is a stochastic hopping-exclusion rule applied to a 1D lattice of binary
occupations under random-sequential update. We disclose this exactly as the BTW sandpile
and the ER/WS network-generation reproductions disclose that they are not agent-based. The
lock-first + honest-verdict + L3-bundle discipline still fully applies.

Rules (the totally asymmetric simple exclusion process, TASEP, on an OPEN chain; verified
against the paper's model definition):

  * A 1D chain of ``L`` sites, ``occ[0..L-1]`` each 0 (empty) or 1 (occupied). Particles
    move only to the RIGHT (totally asymmetric), one particle per site (hard-core
    exclusion), so the maximum hop velocity is 1 site.
  * RANDOM-SEQUENTIAL update. One "sweep" = ``L`` elementary update attempts. Each attempt
    picks ONE of ``L`` candidate moves UNIFORMLY at random and applies it with its rate:
        - move -1  (LEFT boundary inject): if ``occ[0] == 0``, set ``occ[0] = 1`` with
          probability ``alpha``.
        - move i in {0 .. L-2} (BULK bond i -> i+1): if ``occ[i] == 1 and occ[i+1] == 0``,
          hop (``occ[i] = 0``, ``occ[i+1] = 1``) with probability 1 (bulk hop rate 1).
        - move L-1 (RIGHT boundary extract): if ``occ[L-1] == 1``, set ``occ[L-1] = 0``
          with probability ``beta``.
    So there are exactly ``L`` candidate moves (one left inject, ``L-1`` bulk bonds, one
    right extract), matching ``L`` attempts per sweep — one attempt per site's worth of
    update, the standard random-sequential normalisation.

Steady state / measurement (FIXED before the run):
  * Warm up for a fixed number of sweeps (``warmup``) from the empty chain, then measure
    over a long window (``measure`` sweeps).
  * CURRENT J = time-averaged number of successful hops across ONE fixed central bond, per
    sweep. During measurement we count, each attempt, whether the chosen move was the
    central bond ``c = L//2`` AND it actually hopped; J = (successful central-bond hops) /
    (number of sweeps). Because each attempt selects a specific bond with probability 1/L
    and a sweep is L attempts, this equals the per-bond hopping rate per unit time in the
    standard random-sequential clock, so J is directly comparable to the mean-field
    current alpha(1-alpha), beta(1-beta), 1/4.
  * BULK DENSITY rho = mean occupancy of the central third of the chain, time-averaged over
    the measurement window (sampled once per sweep). The central third avoids the boundary
    layers so the reported rho is the bulk plateau, per the lock's gate_design_check.
  * DENSITY PROFILE = per-site time-averaged occupancy over the measurement window (used
    for the coexistence-line shock / linear-profile check P3).

Phase diagram (exactly known, the analytic targets the lock grades against):
  * Maximal-current phase (alpha > 1/2 AND beta > 1/2): J = 1/4, rho = 1/2, independent of
    alpha, beta.
  * Low-density phase (alpha < 1/2 AND alpha < beta): J = alpha(1-alpha), rho = alpha.
  * High-density phase (beta < 1/2 AND beta < alpha): J = beta(1-beta), rho = 1 - beta.
  * Coexistence line (alpha = beta < 1/2): a shock (domain wall) between a low-density
    region (rho ~ alpha near the left) and a high-density region (rho ~ 1 - beta near the
    right); the time-averaged profile is roughly LINEAR because the wall diffuses freely.

Determinism: the whole run is reproducible given an integer seed (a single
``numpy.random.default_rng(seed)`` draws every move choice and every rate acceptance).
NumPy vectorises one sweep's L attempts, but the update stays strictly sequential within a
sweep by resolving conflicts one attempt at a time on the vectorised draw so that the
binary occupations and the counted hops are the canonical random-sequential outcome.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

# Move-code conventions used across the module.
LEFT_INJECT = -1  # candidate move that injects at site 0 with rate alpha
# bulk bond i in {0 .. L-2} hops occ[i] -> occ[i+1] with rate 1
# RIGHT_EXTRACT is encoded as move == L-1 (extract at site L-1 with rate beta)


# -- core CA: the open TASEP chain ---------------------------------------------

class TASEP:
    """A 1D open TASEP chain of ``L`` binary-occupancy sites.

    ``occ`` is a length-``L`` int array of 0/1. ``sweep`` performs ``L`` random-sequential
    update attempts and returns the number of successful hops across the fixed central
    bond during that sweep (used for the current). The update is strictly sequential
    within a sweep (each attempt sees the occupations left by the previous attempt), which
    is the canonical random-sequential TASEP dynamics.
    """

    def __init__(self, L: int = 200, alpha: float = 0.5, beta: float = 0.5,
                 seed: int = 0) -> None:
        if L < 3:
            raise ValueError("L must be >= 3 (need a left site, a bulk, and a right site)")
        if not (0.0 <= alpha <= 1.0):
            raise ValueError("alpha (injection rate) must be in [0, 1]")
        if not (0.0 <= beta <= 1.0):
            raise ValueError("beta (extraction rate) must be in [0, 1]")
        self.L = int(L)
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.rng = np.random.default_rng(seed)
        self.occ = np.zeros(self.L, dtype=np.int64)
        # Fixed central bond c -> c+1 whose crossings define the current.
        self.central_bond = self.L // 2

    def _apply_move(self, move: int, u: float) -> int:
        """Apply one candidate ``move`` with a pre-drawn uniform ``u`` in [0, 1).

        Returns 1 iff this move was a successful hop across the central bond, else 0. The
        rate acceptance uses ``u`` (u < rate accepts) so the RNG stream is deterministic.
        """
        occ = self.occ
        L = self.L
        if move == LEFT_INJECT:                       # inject at site 0 with rate alpha
            if occ[0] == 0 and u < self.alpha:
                occ[0] = 1
            return 0
        if move == L - 1:                             # extract at site L-1 with rate beta
            if occ[L - 1] == 1 and u < self.beta:
                occ[L - 1] = 0
            return 0
        # bulk bond move in {0 .. L-2}: hop occ[move] -> occ[move+1] with rate 1
        i = move
        if occ[i] == 1 and occ[i + 1] == 0:
            occ[i] = 0
            occ[i + 1] = 1
            return 1 if i == self.central_bond else 0
        return 0

    def sweep(self) -> int:
        """One sweep = ``L`` random-sequential attempts. Returns the number of successful
        central-bond hops in this sweep.

        There are exactly ``L + 1`` candidate moves: the LEFT inject (1), the bulk bonds
        ``0 .. L-2`` (``L - 1`` of them, each hopping site i -> i+1), and the RIGHT extract
        (1). Each attempt draws ONE candidate uniformly from these ``L + 1`` and applies it
        with its rate. We draw index in ``{0 .. L}`` and map: index 0 -> LEFT_INJECT
        (code -1); index in ``1 .. L-1`` -> bulk bond ``index - 1`` (codes ``0 .. L-2``);
        index ``L`` -> RIGHT extract (code ``L-1``). The moves and their rate-acceptance
        uniforms are drawn vectorised for speed, then applied strictly in sequence so the
        dynamics is the canonical random-sequential TASEP (conflicts are resolved by the
        current occupation, one attempt at a time).
        """
        L = self.L
        # index in {0 .. L} selects one of the L+1 candidate moves uniformly.
        choices = self.rng.integers(0, L + 1, size=L)
        uniforms = self.rng.random(size=L)
        central_hops = 0
        for k in range(L):
            idx = int(choices[k])
            if idx == 0:
                move = LEFT_INJECT            # inject at site 0
            elif idx == L:
                move = L - 1                  # extract at site L-1
            else:
                move = idx - 1                # bulk bond in {0 .. L-2}
            central_hops += self._apply_move(move, float(uniforms[k]))
        return central_hops

    def density_profile(self) -> np.ndarray:
        """Current per-site occupancy (a copy, as float)."""
        return self.occ.astype(np.float64).copy()

    def bulk_density(self) -> float:
        """Mean occupancy of the central third of the chain (avoids boundary layers)."""
        lo = self.L // 3
        hi = 2 * self.L // 3
        return float(self.occ[lo:hi].mean())


# -- steady-state experiment ---------------------------------------------------

def run_tasep(L: int = 200, alpha: float = 0.5, beta: float = 0.5, *,
              warmup: int = 2000, measure: int = 8000, seed: int = 0) -> Dict[str, Any]:
    """Run one open-TASEP steady-state experiment and return current + density summaries.

    Warm up ``warmup`` sweeps from the empty chain (discarded), then measure over
    ``measure`` sweeps. Returns:
      * ``current``: successful central-bond hops per sweep, averaged over the window.
      * ``bulk_density``: time-averaged central-third occupancy.
      * ``density_profile``: per-site time-averaged occupancy (length L).
      * config echoes for provenance.
    Deterministic given ``seed``.
    """
    if warmup < 0 or measure <= 0:
        raise ValueError("warmup must be >= 0 and measure must be > 0")
    m = TASEP(L=L, alpha=alpha, beta=beta, seed=seed)

    for _ in range(warmup):
        m.sweep()

    total_central_hops = 0
    profile_sum = np.zeros(L, dtype=np.float64)
    bulk_sum = 0.0
    lo, hi = L // 3, 2 * L // 3
    for _ in range(measure):
        total_central_hops += m.sweep()
        profile_sum += m.occ            # sampled once per sweep (post-sweep occupancy)
        bulk_sum += float(m.occ[lo:hi].mean())

    current = total_central_hops / measure
    profile = profile_sum / measure
    bulk_density = bulk_sum / measure
    return {
        "L": L,
        "alpha": float(alpha),
        "beta": float(beta),
        "warmup": warmup,
        "measure": measure,
        "seed": seed,
        "current": float(current),
        "bulk_density": float(bulk_density),
        "density_profile": profile.tolist(),
    }


def run_many_seeds(L: int, alpha: float, beta: float, *, warmup: int, measure: int,
                   n_seeds: int, seed_base: int = 0) -> Dict[str, Any]:
    """Run the open-TASEP experiment over ``n_seeds`` seeds and average the observables.

    Returns per-seed and mean current / bulk density, plus the seed-averaged density
    profile (length L). Deterministic given ``seed_base`` (seeds are
    ``seed_base .. seed_base + n_seeds - 1``).
    """
    if n_seeds <= 0:
        raise ValueError("n_seeds must be > 0")
    currents: List[float] = []
    densities: List[float] = []
    profile_acc = np.zeros(L, dtype=np.float64)
    for s in range(n_seeds):
        res = run_tasep(L, alpha, beta, warmup=warmup, measure=measure,
                        seed=seed_base + s)
        currents.append(res["current"])
        densities.append(res["bulk_density"])
        profile_acc += np.asarray(res["density_profile"], dtype=np.float64)
    profile = (profile_acc / n_seeds)
    return {
        "L": L,
        "alpha": float(alpha),
        "beta": float(beta),
        "warmup": warmup,
        "measure": measure,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "per_seed_current": currents,
        "per_seed_bulk_density": densities,
        "mean_current": float(np.mean(currents)),
        "std_current": float(np.std(currents)),
        "mean_bulk_density": float(np.mean(densities)),
        "std_bulk_density": float(np.std(densities)),
        "mean_density_profile": profile.tolist(),
    }


# -- analysis helpers ----------------------------------------------------------

def mean_field_current(alpha: float, beta: float) -> float:
    """Analytic mean-field steady-state current of the open TASEP (the phase-diagram
    target the lock grades against).

    Low-density phase (alpha < 1/2, alpha < beta): J = alpha(1 - alpha).
    High-density phase (beta < 1/2, beta < alpha): J = beta(1 - beta).
    Maximal-current phase (alpha >= 1/2 and beta >= 1/2): J = 1/4.
    On the coexistence line alpha = beta < 1/2 the two low/high expressions coincide.
    """
    if alpha < 0.5 and alpha <= beta:
        return alpha * (1.0 - alpha)
    if beta < 0.5 and beta < alpha:
        return beta * (1.0 - beta)
    return 0.25


def mean_field_density(alpha: float, beta: float) -> float:
    """Analytic mean-field bulk density of the open TASEP.

    Low-density: rho = alpha. High-density: rho = 1 - beta. Maximal-current: rho = 1/2.
    On the coexistence line the bulk value is ill-defined (a shock separates alpha and
    1-beta); this returns the low-density branch there for reference only.
    """
    if alpha < 0.5 and alpha <= beta:
        return alpha
    if beta < 0.5 and beta < alpha:
        return 1.0 - beta
    return 0.5


def profile_linearity(profile: Any, *, frac: float = 1.0 / 3.0) -> Dict[str, float]:
    """Quantify how LINEAR the bulk part of a density profile is (used for the P3 shock
    check on the coexistence line).

    The interior (dropping the first/last ``frac`` of sites to avoid boundary layers) is
    fit to a straight line by least squares; returns the fit slope (per site), the fitted
    endpoints, and the R^2 of the linear fit. A freely diffusing domain wall gives a
    time-averaged profile that rises ~linearly across the chain (high R^2, positive slope),
    which is the coexistence-line signature.
    """
    prof = np.asarray(profile, dtype=np.float64)
    n = prof.size
    lo = int(n * frac)
    hi = int(n * (1.0 - frac))
    if hi - lo < 3:
        lo, hi = 0, n
    x = np.arange(lo, hi, dtype=np.float64)
    y = prof[lo:hi]
    slope, intercept = np.polyfit(x, y, 1)
    yhat = slope * x + intercept
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "left_value": float(slope * lo + intercept),
        "right_value": float(slope * (hi - 1) + intercept),
        "r2": float(r2),
        "lo": lo,
        "hi": hi,
    }
