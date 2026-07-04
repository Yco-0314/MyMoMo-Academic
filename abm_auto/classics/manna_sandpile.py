"""Manna stochastic sandpile (Manna 1991) — a faithful self-organized-criticality (SOC)
reproduction.

Source: Manna, S. S. (1991) "Two-state model of self-organized criticality",
J. Phys. A: Math. Gen. 24:L363-L369. doi:10.1088/0305-4470/24/7/009. (The stochastic
sandpile whose 2D avalanche-size exponent is tau ~ 1.27 — the prototype of the "Manna"
universality class, distinct from the deterministic BTW class.)

IMPORTANT (honesty, binds the FINDINGS): this is a CELLULAR AUTOMATON / SOC model, NOT an
agent-stepping ABM. There are no agents that perceive, decide and act, no scheduler over an
agent roster, no per-agent step. It is a STOCHASTIC toppling rule applied to a grid of
integer heights until the grid is stable. We disclose this exactly as the btw_sandpile and
oslo_ricepile reproductions do: framing "CA (disclosed)". The lock-first + honest-verdict +
L3-bundle discipline still fully applies.

Rules (the canonical 2D Manna stochastic sandpile, verified against Manna 1991):
  * An L x L grid of integer "heights" (grains per cell). L = 64 here.
  * DRIVE: add one grain at a uniformly random cell.
  * TOPPLE (relaxation): a cell is CRITICAL when its height >= 2. A critical cell topples:
        cell -= 2
    and the TWO removed grains are EACH sent to an INDEPENDENTLY, uniformly randomly chosen
    nearest neighbour (4-neighbourhood: up/down/left/right). The two grains are drawn
    independently, so both may land on the SAME neighbour or on two DIFFERENT ones. This
    random two-grain redistribution is the whole point — it is what separates the Manna
    model (stochastic) from the deterministic BTW rule (fixed 4 neighbours, threshold 4).
    Grains sent off the lattice edge are LOST (open boundary / dissipation). Relaxation
    continues until NO cell is critical (the avalanche has stabilised).
  * AVALANCHE SIZE s = the total number of individual topplings triggered by that one added
    grain (s = 0 if the added grain caused no toppling).

The relaxation is done as a synchronous sweep: find every currently-critical cell, topple
them all at once (each loses 2 grains and scatters 2 grains to independently-random
neighbours), then repeat until no cell is critical. Each sweep counts the number of
critical cells as that sweep's topplings; summed over sweeps = s. Unlike the deterministic
BTW rule the Manna dynamics is stochastic, so the avalanche size for a given added grain
depends on the RNG stream; but the whole run is reproducible given an integer seed.

SOC: drive the grid from empty; after a transient (of order L^2 grains) it self-organizes
to a STATIONARY CRITICAL state with a finite mean occupancy (grains per cell) and
POWER-LAW-distributed avalanche sizes, P(s) ~ s^{-tau} with tau ~ 1.27 in 2D. We discard a
fixed transient of added grains, then record a fixed number of avalanche sizes at
stationarity.

Determinism: the whole run is reproducible given an integer seed — a single
``numpy.random.default_rng(seed)`` draws every drop location AND every grain-scatter
direction. NumPy is used only to make the toppling sweep fast (vectorized); the result is
the canonical stochastic-CA outcome for that seed.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
from scipy.optimize import brentq
from scipy.special import zeta

CRITICAL = 2  # a cell topples when its height >= CRITICAL (the Manna two-state threshold)

# The 4 von-Neumann neighbour directions, encoded as (drow, dcol). The scatter of a grain
# picks one of these 4 uniformly and independently per grain.
_DIRS = np.array([(-1, 0), (1, 0), (0, -1), (0, 1)], dtype=np.int64)  # up, down, left, right


# -- core CA: a single grid -----------------------------------------------------

class MannaSandpile:
    """An L x L Manna stochastic sandpile grid of integer heights with an open boundary.

    ``heights`` is an (L, L) int array. ``drop_one`` adds a grain at a given cell and
    relaxes the grid, returning the avalanche size (number of topplings). The toppling
    sweep is synchronous (all currently-critical cells topple together): each critical cell
    loses 2 grains and scatters those 2 grains to two INDEPENDENTLY-random von-Neumann
    neighbours (grains leaving the edge are lost). Repeated until no cell is critical.

    The RNG (``self.rng``) drives BOTH the scatter directions here and (in the drive loop)
    the drop locations, so a single seed reproduces the whole run bit-for-bit.
    """

    def __init__(self, L: int = 64, *, seed: int = 0) -> None:
        if L <= 0:
            raise ValueError("L must be positive")
        self.L = L
        self.rng = np.random.default_rng(seed)
        self.heights = np.zeros((L, L), dtype=np.int64)

    def topple_until_stable(self) -> int:
        """Relax the grid until no cell has height >= CRITICAL. Returns the total number of
        individual topplings performed (the avalanche size).

        Each sweep:
          1. find all critical cells (height >= 2);
          2. remove 2 grains from each critical cell;
          3. for EACH critical cell scatter 2 grains, each to an INDEPENDENTLY uniformly
             chosen von-Neumann neighbour (the two grains are drawn separately, so they may
             coincide). Grains scattered off the lattice edge are dropped (open boundary).
        Repeat until no cell is critical. The number of topplings in a sweep = number of
        critical cells; summed over sweeps = s.
        """
        h = self.heights
        L = self.L
        total = 0
        while True:
            crit_r, crit_c = np.nonzero(h >= CRITICAL)
            n_crit = crit_r.size
            if n_crit == 0:
                return total
            total += n_crit

            # Remove 2 grains from each critical cell.
            h[crit_r, crit_c] -= 2

            # Scatter 2 grains PER critical cell, each grain to an independently-random
            # von-Neumann neighbour. Stack the two grains: 2*n_crit source cells, each with
            # its own independent direction draw.
            src_r = np.concatenate((crit_r, crit_r))
            src_c = np.concatenate((crit_c, crit_c))
            dir_idx = self.rng.integers(0, 4, size=src_r.size)
            dr = _DIRS[dir_idx, 0]
            dc = _DIRS[dir_idx, 1]
            dst_r = src_r + dr
            dst_c = src_c + dc

            # Drop grains that left the lattice (open boundary): keep only in-bounds targets.
            inb = (dst_r >= 0) & (dst_r < L) & (dst_c >= 0) & (dst_c < L)
            dst_flat = dst_r[inb] * L + dst_c[inb]
            # Accumulate: several grains may land on the same cell in the same sweep, so use
            # bincount (np.add.at is correct but slower) on the flattened index.
            add = np.bincount(dst_flat, minlength=L * L)
            h += add.reshape(L, L)

    def drop_one(self, row: int, col: int) -> int:
        """Add one grain at (row, col), relax, and return the avalanche size."""
        self.heights[row, col] += 1
        return self.topple_until_stable()

    def mean_occupancy(self) -> float:
        """Current mean occupancy (average grains per cell)."""
        return float(self.heights.mean())

    def total_grains(self) -> int:
        return int(self.heights.sum())


# -- drive loop -----------------------------------------------------------------

def drive(pile: MannaSandpile, n_grains: int, *, record: bool = True) -> List[int]:
    """Drive ``pile`` for ``n_grains`` added grains, drawing drop locations from the pile's
    own RNG (so the scatter draws and the drop draws share one deterministic stream).

    Each grain is dropped at a uniformly random cell, then the grid is relaxed. If
    ``record`` is True, returns the list of per-grain avalanche sizes (length ``n_grains``);
    if False, returns an empty list (used to burn through the transient without storing it).
    """
    L = pile.L
    sizes: List[int] = []
    if record:
        for _ in range(n_grains):
            r = int(pile.rng.integers(0, L))
            c = int(pile.rng.integers(0, L))
            sizes.append(pile.drop_one(r, c))
    else:
        for _ in range(n_grains):
            r = int(pile.rng.integers(0, L))
            c = int(pile.rng.integers(0, L))
            pile.drop_one(r, c)
    return sizes


def avalanche(pile: MannaSandpile, row: int, col: int) -> int:
    """Drop one grain at (row, col) and return the avalanche size. Thin wrapper around
    ``MannaSandpile.drop_one`` for the public helper surface."""
    return pile.drop_one(row, col)


def run_manna(L: int = 64, *, transient: int = 100_000, n_avalanches: int = 200_000,
              seed: int = 0, occupancy_samples: int = 2_000) -> Dict[str, Any]:
    """Full SOC experiment: drive an empty L x L grid past a transient to the stationary
    critical state, then record ``n_avalanches`` avalanche sizes.

    Returns a summary dict: the recorded sizes, the stationary mean occupancy (sampled over
    the recording phase, so it is the steady-state value not the transient ramp), and config
    echoes. Deterministic given ``seed``.
    """
    pile = MannaSandpile(L, seed=seed)

    # Burn through the transient (do not store its avalanches).
    drive(pile, transient, record=False)

    # Record the steady-state avalanches; sample the occupancy periodically so the reported
    # mean is the STATIONARY value, not contaminated by the transient ramp.
    sizes: List[int] = []
    occ_samples: List[float] = []
    sample_every = max(1, n_avalanches // occupancy_samples)
    for i in range(n_avalanches):
        r = int(pile.rng.integers(0, L))
        c = int(pile.rng.integers(0, L))
        sizes.append(pile.drop_one(r, c))
        if i % sample_every == 0:
            occ_samples.append(pile.mean_occupancy())

    return {
        "L": L,
        "transient": transient,
        "n_avalanches": n_avalanches,
        "seed": seed,
        "sizes": sizes,
        "stationary_mean_occupancy": (
            float(np.mean(occ_samples)) if occ_samples else pile.mean_occupancy()),
        "occupancy_samples": occ_samples,
        "final_mean_occupancy": pile.mean_occupancy(),
    }


# -- analysis -------------------------------------------------------------------

def mean_occupancy(pile: MannaSandpile) -> float:
    """Mean occupancy of a pile (module-level helper)."""
    return pile.mean_occupancy()


def fit_tau(sizes: Sequence[int], *, s_min: int = 1,
            tau_bracket: Tuple[float, float] = (1.001, 6.0)) -> Dict[str, Any]:
    """Discrete power-law MLE for the avalanche-size tail exponent tau, with a lower cutoff
    ``s_min`` over the scaling region.

    Method (FIXED before the run; Clauset, Shalizi & Newman 2009 — the EXACT discrete MLE
    for the discrete power law P(s) = s^{-tau} / zeta(tau, s_min), s = s_min, s_min+1, ...).
    Over all avalanches with size s >= s_min (zero-size avalanches, where the added grain
    triggered no toppling, are EXCLUDED — they are not part of the power-law tail), tau
    maximizes the log-likelihood

        L(tau) = -n*ln(zeta(tau, s_min)) - tau * sum_i ln(s_i),

    i.e. tau solves the score equation  -zeta'(tau, s_min)/zeta(tau, s_min) = mean_i ln(s_i)
    (zeta is the Hurwitz zeta). We solve it numerically (Brent root-find on the score),
    rather than the (s_min - 0.5) continuity-correction *approximation* tau = 1 + n /
    sum ln(s/(s_min-0.5)) — that approximation is only accurate for s_min >~ 6 and is biased
    LOW at small s_min, so it is deliberately NOT used. The asymptotic standard error is
    sigma = (tau - 1) / sqrt(n). Returns tau, its standard error, the number of tail
    samples, and the s_min used.
    """
    arr = np.asarray(sizes, dtype=np.float64)
    tail = arr[arr >= s_min]
    n = int(tail.size)
    if n == 0:
        return {"tau": float("nan"), "stderr": float("nan"), "n_tail": 0, "s_min": s_min}
    mean_log = float(np.mean(np.log(tail)))

    # Score: d/dtau of -(1/n)*lnL = -zeta'(tau,s_min)/zeta(tau,s_min) - mean(ln s). Root=MLE.
    hh = 1e-6

    def score(tau: float) -> float:
        dln_zeta = (math.log(zeta(tau + hh, s_min)) - math.log(zeta(tau - hh, s_min))) / (2 * hh)
        return -dln_zeta - mean_log

    lo, hi = tau_bracket
    try:
        tau = float(brentq(score, lo, hi, xtol=1e-8))
    except ValueError:
        # No sign change in the bracket (degenerate data); fall back to the closed-form
        # continuity-corrected approximation so the caller still gets a finite estimate.
        denom = float(np.sum(np.log(tail / (s_min - 0.5)))) if s_min != 0.5 else float("nan")
        tau = 1.0 + n / denom if denom else float("nan")
    stderr = (tau - 1.0) / math.sqrt(n) if n > 0 else float("nan")
    return {"tau": tau, "stderr": stderr, "n_tail": n, "s_min": s_min}


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
