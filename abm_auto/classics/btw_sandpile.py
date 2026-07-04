"""Bak-Tang-Wiesenfeld sandpile (1987) — a faithful self-organized-criticality (SOC)
reproduction.

Source: Bak, P., Tang, C. & Wiesenfeld, K. (1987) "Self-organized criticality: An
explanation of the 1/f noise", Phys. Rev. Lett. 59:381-384.
doi:10.1103/PhysRevLett.59.381.

IMPORTANT (honesty, binds the FINDINGS): this is a CELLULAR AUTOMATON / SOC model, NOT
an agent-stepping ABM. There are no agents that perceive, decide and act, no scheduler
over an agent roster, no per-agent step. It is a deterministic toppling rule applied to a
grid of integer heights until the grid is stable. We disclose this exactly as the ER/WS
network-generation reproductions disclose that they are not agent-based. The lock-first +
honest-verdict + L3-bundle discipline still fully applies.

Rules (the canonical 2D BTW abelian sandpile, verified against the paper):
  * An L x L grid of integer "heights" (number of grains on each cell). L=50 here.
  * DRIVE: add one grain at a uniformly random cell.
  * TOPPLE (relaxation): while ANY cell has height >= 4, every unstable cell topples:
        cell      -= 4
        each of its 4 von-Neumann neighbours (up/down/left/right) += 1
    Grains that would leave the grid boundary are LOST (open boundary / dissipation).
    Toppling continues until no cell has height >= 4 (the avalanche has relaxed). The
    rule is "abelian": the final stable configuration and the total number of topplings
    are independent of the order in which unstable cells are toppled, so a synchronous
    sweep (topple all currently-unstable cells at once, repeat) gives the canonical
    avalanche size.
  * AVALANCHE SIZE s = the total number of individual topplings triggered by that one
    added grain (s = 0 if the added grain caused no toppling).

SOC: drive the grid from empty; after a transient it self-organizes to a STATIONARY
CRITICAL state with mean height ~ 2.1, in which avalanche sizes are POWER-LAW
distributed, P(s) ~ s^{-tau} with tau ~ 1.2 in 2D. We discard a fixed transient of added
grains, then record a fixed number of avalanche sizes.

Determinism: the whole run is reproducible given an integer seed (a single
``numpy.random.default_rng(seed)`` draws every drop location). NumPy is used only to make
the toppling sweep fast (vectorized); the result is bit-for-bit the canonical CA outcome.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import brentq
from scipy.special import zeta

THRESHOLD = 4  # a cell topples at height >= 4 (canonical 2D BTW)


# -- core CA: a single grid -----------------------------------------------------

class Sandpile:
    """An L x L BTW sandpile grid of integer heights with an open boundary.

    ``heights`` is an (L, L) int array. ``drop_one`` adds a grain at a given cell and
    relaxes the grid, returning the avalanche size (number of topplings). The toppling
    sweep is synchronous (all currently-unstable cells topple together) and repeated
    until stable; because the BTW rule is abelian this yields the canonical avalanche
    size regardless of order.
    """

    def __init__(self, L: int = 50) -> None:
        if L <= 0:
            raise ValueError("L must be positive")
        self.L = L
        self.heights = np.zeros((L, L), dtype=np.int64)

    def topple_until_stable(self) -> int:
        """Relax the grid until no cell has height >= THRESHOLD. Returns the total
        number of individual topplings performed (the avalanche size).

        Each sweep: find all unstable cells, subtract THRESHOLD from each, and add 1 to
        each von-Neumann neighbour (grains leaving the boundary are dropped because we
        only add into in-bounds slices). Repeat until no cell is unstable. The number of
        topplings in a sweep = number of unstable cells; summed over sweeps = s.
        """
        h = self.heights
        total = 0
        while True:
            unstable = h >= THRESHOLD
            n_unstable = int(unstable.sum())
            if n_unstable == 0:
                return total
            total += n_unstable
            # Remove THRESHOLD grains from every unstable cell.
            h[unstable] -= THRESHOLD
            # Distribute one grain to each von-Neumann neighbour. Slicing keeps the
            # boundary open: a grain pushed past an edge is simply not added anywhere.
            # up neighbour gets a grain from the cell below it, etc.
            h[:-1, :] += unstable[1:, :]    # grain moves up   (from row i to row i-1)
            h[1:, :]  += unstable[:-1, :]   # grain moves down (from row i to row i+1)
            h[:, :-1] += unstable[:, 1:]    # grain moves left
            h[:, 1:]  += unstable[:, :-1]   # grain moves right

    def drop_one(self, row: int, col: int) -> int:
        """Add one grain at (row, col), relax, and return the avalanche size."""
        self.heights[row, col] += 1
        return self.topple_until_stable()

    def mean_height(self) -> float:
        """Current mean height (average grains per cell)."""
        return float(self.heights.mean())

    def total_grains(self) -> int:
        return int(self.heights.sum())


# -- drive loop -----------------------------------------------------------------

def drive(pile: Sandpile, n_grains: int, rng: np.random.Generator,
          *, record: bool = True) -> List[int]:
    """Drive ``pile`` for ``n_grains`` added grains using ``rng`` for drop locations.

    Each grain is dropped at a uniformly random cell, then the grid is relaxed. If
    ``record`` is True, returns the list of per-grain avalanche sizes (length
    ``n_grains``); if False, returns an empty list (used to burn through the transient
    cheaply without storing it).
    """
    L = pile.L
    sizes: List[int] = []
    # Draw all drop coordinates up front (one deterministic RNG stream).
    rows = rng.integers(0, L, size=n_grains)
    cols = rng.integers(0, L, size=n_grains)
    if record:
        for i in range(n_grains):
            sizes.append(pile.drop_one(int(rows[i]), int(cols[i])))
    else:
        for i in range(n_grains):
            pile.drop_one(int(rows[i]), int(cols[i]))
    return sizes


def avalanche(pile: Sandpile, row: int, col: int) -> int:
    """Drop one grain at (row, col) and return the avalanche size. Thin wrapper around
    ``Sandpile.drop_one`` for the public helper surface required by the spec."""
    return pile.drop_one(row, col)


def run_sandpile(L: int = 50, *, transient: int = 100_000, n_avalanches: int = 200_000,
                 seed: int = 0, mean_height_samples: int = 2_000) -> Dict[str, Any]:
    """Full SOC experiment: drive an empty L x L grid past a transient to the critical
    steady state, then record ``n_avalanches`` avalanche sizes.

    Returns a summary dict: the recorded sizes, the stationary mean height (sampled over
    the recording phase, so it is the steady-state value not the transient ramp), and
    config echoes. Deterministic given ``seed``.
    """
    rng = np.random.default_rng(seed)
    pile = Sandpile(L)

    # Burn through the transient (do not store its avalanches).
    drive(pile, transient, rng, record=False)

    # Record the steady-state avalanches; sample mean height periodically so the
    # reported mean is the STATIONARY value, not contaminated by the transient ramp.
    sizes: List[int] = []
    mh_samples: List[float] = []
    sample_every = max(1, n_avalanches // mean_height_samples)
    rows = rng.integers(0, L, size=n_avalanches)
    cols = rng.integers(0, L, size=n_avalanches)
    for i in range(n_avalanches):
        sizes.append(pile.drop_one(int(rows[i]), int(cols[i])))
        if i % sample_every == 0:
            mh_samples.append(pile.mean_height())

    return {
        "L": L,
        "transient": transient,
        "n_avalanches": n_avalanches,
        "seed": seed,
        "sizes": sizes,
        "stationary_mean_height": float(np.mean(mh_samples)) if mh_samples else pile.mean_height(),
        "mean_height_samples": mh_samples,
        "final_mean_height": pile.mean_height(),
    }


# -- analysis -------------------------------------------------------------------

def mean_height(pile: Sandpile) -> float:
    """Mean height of a pile (module-level helper required by the spec)."""
    return pile.mean_height()


def fit_tau(sizes: Sequence[int], *, kmin: int = 1,
            tau_bracket: Tuple[float, float] = (1.001, 6.0)) -> Dict[str, Any]:
    """Discrete power-law MLE for the avalanche-size tail exponent tau.

    Method (FIXED before the run; Clauset, Shalizi & Newman 2009, the EXACT discrete MLE
    for the discrete power law P(s) = s^{-tau} / zeta(tau, kmin), s = kmin, kmin+1, ...).
    Over all avalanches with size s >= kmin (zero-size avalanches, where the added grain
    triggered no toppling, are EXCLUDED — they are not part of the power-law tail), tau
    maximizes the log-likelihood

        L(tau) = -n*ln(zeta(tau, kmin)) - tau * sum_i ln(s_i),

    i.e. tau solves the score equation  -zeta'(tau, kmin)/zeta(tau, kmin) = mean_i ln(s_i)
    (zeta is the Hurwitz zeta). We solve it numerically (Brent root-find on the score),
    rather than the (kmin - 0.5) continuity-correction *approximation* tau = 1 + n /
    sum ln(s/(kmin-0.5)) — that approximation is only accurate for kmin >~ 6 and is biased
    LOW at the small kmin we lock here, so it is deliberately NOT used. ``kmin`` is fixed
    at 1 and is NOT tuned to hit a target exponent. The asymptotic standard error is
    sigma = (tau - 1) / sqrt(n). Returns tau, its standard error, the number of tail
    samples, and the kmin used.
    """
    arr = np.asarray(sizes, dtype=np.float64)
    tail = arr[arr >= kmin]
    n = int(tail.size)
    if n == 0:
        return {"tau": float("nan"), "stderr": float("nan"), "n_tail": 0, "kmin": kmin}
    mean_log = float(np.mean(np.log(tail)))

    # Score: d/dtau of -(1/n)*lnL = -zeta'(tau,kmin)/zeta(tau,kmin) - mean(ln s). Root = MLE.
    h = 1e-6

    def score(tau: float) -> float:
        dln_zeta = (math.log(zeta(tau + h, kmin)) - math.log(zeta(tau - h, kmin))) / (2 * h)
        return -dln_zeta - mean_log

    lo, hi = tau_bracket
    try:
        tau = float(brentq(score, lo, hi, xtol=1e-8))
    except ValueError:
        # No sign change in the bracket (degenerate data); fall back to the closed-form
        # continuity-corrected approximation so the caller still gets a finite estimate.
        denom = float(np.sum(np.log(tail / (kmin - 0.5)))) if kmin != 0.5 else float("nan")
        tau = 1.0 + n / denom if denom else float("nan")
    stderr = (tau - 1.0) / math.sqrt(n)
    return {"tau": tau, "stderr": stderr, "n_tail": n, "kmin": kmin}


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
        # half-open [lo, hi) except the last bin which includes the max.
        if i == len(edges) - 2:
            count = int(np.sum((nonzero >= lo) & (nonzero <= hi)))
        else:
            count = int(np.sum((nonzero >= lo) & (nonzero < hi)))
        out.append({"lo": float(lo), "hi": float(hi), "count": count})
    return out


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
