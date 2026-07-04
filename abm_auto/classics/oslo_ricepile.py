"""Oslo rice-pile model (Christensen et al. 1996) — a faithful self-organized-criticality
(SOC) reproduction.

Source: Christensen, K., Corral, A., Frette, V., Feder, J. & Jossang, T. (1996)
"Tracer Dispersion in a Self-Organized Critical System", Phys. Rev. Lett. 77:107-110.
doi:10.1103/PhysRevLett.77.107. (The "Oslo model" — the stochastic 1D rice-pile whose
avalanche-size exponent is tau ~ 1.55, distinct from the trivial deterministic 1D BTW pile.)

IMPORTANT (honesty, binds the FINDINGS): this is a CELLULAR AUTOMATON / SOC model, NOT an
agent-stepping ABM. There are no agents that perceive, decide and act, no scheduler over an
agent roster, no per-agent step. It is a stochastic slope-relaxation rule applied to a 1D
array of integer site heights until the pile is stable. This is disclosed exactly as the
btw_sandpile and ER/WS network reproductions disclose that they are not agent-based:
framing "CA (disclosed)". The lock-first + honest-verdict + L3-bundle discipline still
fully applies.

Rules (the canonical 1D Oslo model, verified against Christensen et al. 1996):
  * A line of L sites i = 0..L-1 with integer heights h[i]. The local slope is
        z[i] = h[i] - h[i+1],   with h[L] := 0  (open RIGHT boundary — grains leave there).
    The left boundary (i=0) is closed (a wall); site 0's slope is h[0] - h[1] as usual.
  * Each site carries a PER-SITE critical slope z_c[i] drawn uniformly at random in {1, 2}.
  * DRIVE: add one grain at the left site 0:  h[0] += 1  (so z[0] += 1).
  * RELAX (avalanche): while ANY site has z[i] > z_c[i], that site TOPPLES:
        h[i]   -= 1        (one grain moves downslope)
        h[i+1] += 1        (to the right neighbour; if i == L-1 the grain LEAVES the system)
    and AFTER each toppling the toppled site's z_c[i] is RE-DRAWN uniformly in {1, 2}.
    This stochastic re-drawn threshold is the whole point: it makes the 1D pile genuinely
    critical, whereas the deterministic 1D BTW pile (fixed z_c) is trivial / non-critical.
  * AVALANCHE SIZE s = the total number of individual topplings triggered by that one added
    grain (s = 0 if the grain caused no toppling).

The relaxation is done as a synchronous sweep here (find every currently-unstable site,
topple them all once, re-draw each toppled site's threshold, recompute slopes, repeat until
stable). Each pass counts the number of unstable sites as that pass's topplings; summed over
passes = s. Because a toppling only exchanges one grain between adjacent sites and the
re-draw of z_c is applied per toppling, the sweep reproduces the Oslo relaxation.

SOC: drive the empty pile grain-by-grain; after a transient (of order L^2 grains) it
self-organizes to a STATIONARY critical state in which avalanche sizes are power-law
distributed, P(s) ~ s^{-tau} with tau ~ 1.55 in 1D, with a cutoff that grows with L. We
discard a fixed transient of added grains, then record a fixed number of avalanche sizes at
stationarity. We support a grid of L in {32, 64, 128, 256}.

Determinism: the whole run is reproducible given an integer seed (a single
``numpy.random.default_rng(seed)`` seeds both the initial thresholds and every re-draw).
NumPy is used only to make the relaxation sweep fast (vectorized); the result is the
canonical stochastic-CA outcome for that seed.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
from scipy.optimize import brentq
from scipy.special import zeta

# The two allowed critical-slope values (the Oslo stochastic threshold set {1, 2}).
ZC_LOW = 1
ZC_HIGH = 2


# -- core CA: a single 1D Oslo pile --------------------------------------------

class OsloPile:
    """A 1D Oslo rice-pile of L sites with an open right boundary.

    ``h`` is an (L,) int array of site heights; ``zc`` is an (L,) int array of per-site
    critical slopes, each in {1, 2}, re-drawn on each toppling. ``slopes()`` returns the
    local slopes z[i] = h[i] - h[i+1] with h[L] treated as 0. ``drive_one`` adds a grain at
    site 0 and relaxes, returning the avalanche size (number of topplings).

    The relaxation sweep is synchronous (all currently-unstable sites topple once per pass,
    each re-drawing its threshold), repeated until stable.
    """

    def __init__(self, L: int, rng: np.random.Generator) -> None:
        if L <= 0:
            raise ValueError("L must be positive")
        self.L = int(L)
        self.rng = rng
        self.h = np.zeros(self.L, dtype=np.int64)
        # Initial per-site critical slopes drawn uniformly in {1, 2}.
        self.zc = self._draw_zc(self.L)

    def _draw_zc(self, n: int) -> np.ndarray:
        """Draw ``n`` critical slopes uniformly in {1, 2}."""
        return self.rng.integers(ZC_LOW, ZC_HIGH + 1, size=n).astype(np.int64)

    def slopes(self) -> np.ndarray:
        """Local slopes z[i] = h[i] - h[i+1], with the open right boundary h[L] := 0.

        z[i] for i < L-1 is h[i] - h[i+1]; z[L-1] = h[L-1] - 0 = h[L-1] (a grain toppled off
        the last site leaves the system, so its "downslope neighbour" is the ground at 0).
        """
        z = np.empty(self.L, dtype=np.int64)
        z[:-1] = self.h[:-1] - self.h[1:]
        z[-1] = self.h[-1]
        return z

    def relax(self) -> int:
        """Relax the pile until no site has z[i] > z_c[i]. Returns the total number of
        individual topplings performed (the avalanche size).

        Each pass: find all sites with slope over threshold, topple each once (move one grain
        from i to i+1; the grain at site L-1 leaves the system), and re-draw each toppled
        site's z_c uniformly in {1, 2}. Repeat until no site is over threshold.
        """
        h = self.h
        L = self.L
        total = 0
        while True:
            z = self.slopes()
            unstable = z > self.zc
            n_unstable = int(unstable.sum())
            if n_unstable == 0:
                return total
            total += n_unstable
            idx = np.nonzero(unstable)[0]
            # Each unstable site loses one grain to its right neighbour. A site at L-1 loses a
            # grain to the ground (open boundary): decrement it, but add nothing past the edge.
            h[idx] -= 1
            interior = idx[idx < L - 1]
            h[interior + 1] += 1
            # Re-draw the critical slope of every toppled site (the stochastic threshold).
            self.zc[idx] = self._draw_zc(idx.size)

    def drive_one(self) -> int:
        """Add one grain at the left site 0, relax, and return the avalanche size."""
        self.h[0] += 1
        return self.relax()

    def total_grains(self) -> int:
        return int(self.h.sum())

    def is_stable(self) -> bool:
        return not bool(np.any(self.slopes() > self.zc))


# -- drive loop -----------------------------------------------------------------

def drive(pile: OsloPile, n_grains: int, *, record: bool = True) -> List[int]:
    """Drive ``pile`` for ``n_grains`` added grains (each added at site 0, then relaxed).

    If ``record`` is True, returns the list of per-grain avalanche sizes (length
    ``n_grains``); if False, returns an empty list (used to burn through the transient
    cheaply without storing it).
    """
    if record:
        return [pile.drive_one() for _ in range(n_grains)]
    for _ in range(n_grains):
        pile.drive_one()
    return []


def run_single(L: int, *, transient: int, n_avalanches: int, seed: int) -> Dict[str, Any]:
    """Full SOC experiment: drive an empty L-site Oslo pile past a transient to the critical
    steady state, then record ``n_avalanches`` avalanche sizes.

    Returns a summary dict: the recorded sizes, the stationary mean height (of site 0, a
    natural scalar order parameter that plateaus at criticality), and config echoes.
    Deterministic given ``seed``.
    """
    rng = np.random.default_rng(seed)
    pile = OsloPile(L, rng)

    # Burn through the transient (do not store its avalanches). The transient to fill an
    # empty pile to the critical slope is of order L^2 grains.
    drive(pile, transient, record=False)

    # Record the steady-state avalanches.
    sizes = drive(pile, n_avalanches, record=True)

    arr = np.asarray(sizes, dtype=np.float64)
    nonzero = arr[arr >= 1]
    return {
        "L": L,
        "transient": transient,
        "n_avalanches": n_avalanches,
        "seed": seed,
        "sizes": sizes,
        "mean_size": float(arr.mean()) if arr.size else 0.0,
        "mean_nonzero_size": float(nonzero.mean()) if nonzero.size else 0.0,
        "n_nonzero": int(nonzero.size),
        "max_size": float(arr.max()) if arr.size else 0.0,
        "final_top_height": int(pile.h[0]),
    }


def run_L_grid(L_grid: Sequence[int], *, transient_factor: float, n_avalanches: int,
               seed: int) -> List[Dict[str, Any]]:
    """Run ``run_single`` for each L in ``L_grid``. The transient is scaled with L^2
    (``transient = ceil(transient_factor * L^2)``) because the fill time of an empty 1D
    pile to its critical slope grows like L^2. Deterministic given ``seed`` (each L uses the
    same base ``seed`` so the runs are independent-but-reproducible)."""
    out: List[Dict[str, Any]] = []
    for L in L_grid:
        transient = int(math.ceil(transient_factor * L * L))
        out.append(run_single(L, transient=transient, n_avalanches=n_avalanches, seed=seed))
    return out


# -- analysis (shared with the SOC toolkit: discrete-MLE tau + heavy-tail stats) -

def fit_tau(sizes: Sequence[int], *, kmin: int = 1,
            tau_bracket: Tuple[float, float] = (1.001, 6.0)) -> Dict[str, Any]:
    """Discrete power-law MLE for the avalanche-size tail exponent tau.

    Method (FIXED before the run; Clauset, Shalizi & Newman 2009, the EXACT discrete MLE for
    the discrete power law P(s) = s^{-tau} / zeta(tau, kmin), s = kmin, kmin+1, ...). Over
    all avalanches with size s >= kmin (zero-size avalanches, where the added grain triggered
    no toppling, are EXCLUDED — they are not part of the power-law tail), tau maximizes the
    log-likelihood

        L(tau) = -n*ln(zeta(tau, kmin)) - tau * sum_i ln(s_i),

    i.e. tau solves the score equation  -zeta'(tau, kmin)/zeta(tau, kmin) = mean_i ln(s_i)
    (zeta is the Hurwitz zeta). We solve it numerically (Brent root-find on the score),
    rather than the (kmin - 0.5) continuity-correction *approximation*, which is biased low at
    small kmin. ``kmin`` is fixed and is NOT tuned to hit a target exponent. The asymptotic
    standard error is sigma = (tau - 1) / sqrt(n). Returns tau, its standard error, the number
    of tail samples, and the kmin used.
    """
    arr = np.asarray(sizes, dtype=np.float64)
    tail = arr[arr >= kmin]
    n = int(tail.size)
    if n == 0:
        return {"tau": float("nan"), "stderr": float("nan"), "n_tail": 0, "kmin": kmin}
    mean_log = float(np.mean(np.log(tail)))

    h = 1e-6

    def score(tau: float) -> float:
        dln_zeta = (math.log(zeta(tau + h, kmin)) - math.log(zeta(tau - h, kmin))) / (2 * h)
        return -dln_zeta - mean_log

    lo, hi = tau_bracket
    try:
        tau = float(brentq(score, lo, hi, xtol=1e-8))
    except ValueError:
        denom = float(np.sum(np.log(tail / (kmin - 0.5)))) if kmin != 0.5 else float("nan")
        tau = 1.0 + n / denom if denom else float("nan")
    stderr = (tau - 1.0) / math.sqrt(n)
    return {"tau": tau, "stderr": stderr, "n_tail": n, "kmin": kmin}


def heavy_tail_stats(sizes: Sequence[int]) -> Dict[str, Any]:
    """Heavy-tail descriptors for P2: decades spanned by nonzero sizes, the max size, the
    median NONZERO size, and the max/median ratio. 'Decades spanned' = log10(max) -
    log10(min nonzero) over the nonzero avalanches."""
    arr = np.asarray(sizes, dtype=np.float64)
    nonzero = arr[arr >= 1]
    if nonzero.size == 0:
        return {"n_nonzero": 0, "max": 0.0, "min_nonzero": 0.0,
                "median_nonzero": 0.0, "decades": 0.0, "max_over_median": 0.0}
    smax = float(nonzero.max())
    smin = float(nonzero.min())
    median = float(np.median(nonzero))
    decades = math.log10(smax) - math.log10(smin) if smin > 0 else 0.0
    max_over_median = smax / median if median > 0 else float("inf")
    return {
        "n_nonzero": int(nonzero.size),
        "max": smax,
        "min_nonzero": smin,
        "median_nonzero": median,
        "decades": decades,
        "max_over_median": max_over_median,
    }


def size_histogram(sizes: Sequence[int], *, n_bins: int = 30) -> List[Dict[str, float]]:
    """Logarithmically-binned histogram of nonzero avalanche sizes (for reporting / the
    heavy-tail visual). Bins are geometric from 1 to max size; counts are raw (not
    density-normalized). Zero-size avalanches are reported separately by the caller."""
    arr = np.asarray(sizes, dtype=np.float64)
    nonzero = arr[arr >= 1]
    if nonzero.size == 0:
        return []
    smax = float(nonzero.max())
    if smax <= 1:
        return [{"lo": 1.0, "hi": 1.0, "count": int(nonzero.size)}]
    edges = np.unique(np.floor(np.geomspace(1.0, smax, n_bins + 1)).astype(np.int64))
    edges = edges.astype(np.float64)
    out: List[Dict[str, float]] = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if i == len(edges) - 2:
            count = int(np.sum((nonzero >= lo) & (nonzero <= hi)))
        else:
            count = int(np.sum((nonzero >= lo) & (nonzero < hi)))
        out.append({"lo": float(lo), "hi": float(hi), "count": count})
    return out
