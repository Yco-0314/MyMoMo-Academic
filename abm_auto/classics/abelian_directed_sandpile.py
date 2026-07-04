"""Directed abelian sandpile (Dhar & Ramaswamy 1989) — a faithful, exactly-solvable SOC
reproduction.

Source: Dhar, D. & Ramaswamy, R. (1989), "Exactly solved model of self-organized critical
phenomena", Phys. Rev. Lett. 63:1659-1662. doi:10.1103/PhysRevLett.63.1659.

IMPORTANT (honesty, binds the FINDINGS): this is a CELLULAR AUTOMATON / SOC model, NOT an
agent-stepping ABM. **CA (disclosed).** There are no agents that perceive, decide and act,
no scheduler over an agent roster, no per-agent step. It is a deterministic directed
toppling rule applied to a grid of integer heights until the grid is stable. We disclose
this exactly as the BTW sandpile and the network-generation reproductions disclose that
they are not agent-based. The lock-first + honest-verdict + L3-bundle discipline still
fully applies.

The directed rule (verified against the paper). A lattice of H rows (y = 0 .. H-1) by W
columns (x = 0 .. W-1), PERIODIC in the transverse direction x and OPEN at the bottom row
(y = H-1). Each cell holds an integer height h[y, x]. A cell is UNSTABLE when h >= 2 (the
directed-model threshold is z_c = 2, its in-degree in the preferred down-diagonal subset).
When it topples:

    h[y,   x]                 -= 2
    h[y+1, x]                 += 1        (down-left  down-diagonal neighbour)
    h[y+1, (x + 1) mod W]     += 1        (down-right down-diagonal neighbour)

i.e. it sheds its 2 grains DOWNWARD to the two down-diagonal sites in the next row. Grains
NEVER move to smaller or equal y — this anisotropy (the "preferred DOWNSTREAM subset" of
neighbours) is exactly what makes the model directed and exactly solvable, in contrast to
the isotropic BTW pile (4 neighbours, no directional bias). Grains that topple OUT of the
bottom row (from y = H-1) are LOST (open bottom boundary / dissipation). The transverse
wrap (mod W) is a closed cylinder, so grains are lost only at the bottom.

Abelian relaxation. Because grains only ever move to strictly larger y, the relaxation can
be done row by row from the top down: once row y is stable, toppling any lower row can
never feed a grain back into row y, so row y stays stable forever. A single top-to-bottom
sweep in which every row is fully relaxed before the next row is touched therefore reaches
THE stable configuration, and the total number of topplings is independent of the order —
the abelian property. (We relax each row fully because a cell can topple more than once as
it keeps receiving grains from above.)

Drive. From an empty (or steady-state) pile, add ONE grain at a uniformly-random column in
the TOP row (y = 0) and relax downward. The AVALANCHE SIZE s = the total number of
individual topplings triggered by that one grain (s = 0 if it caused none). For each
avalanche we also record the SET of toppled sites and, from that set, its LONGITUDINAL
extent (max y - min y of toppled sites, along the drive) and its TRANSVERSE extent (span
in x, computed on the cylinder so a wrap-around cluster is measured correctly). We discard
a fixed transient of driving grains, then collect a fixed number of avalanches.

Determinism. The whole run is reproducible given an integer seed (a single
``numpy.random.default_rng(seed)`` draws every drive column). NumPy is used only to make
the directed toppling sweep fast (vectorized per row); the result is the canonical CA
outcome.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import brentq
from scipy.special import zeta

THRESHOLD = 2  # a cell topples at height >= 2 (directed model: in-degree of the down subset)


# =============================================================================
# core CA: a single directed sandpile grid
# =============================================================================

class DirectedSandpile:
    """An H x W directed abelian sandpile of integer heights.

    Transverse direction x is PERIODIC (a cylinder of circumference W); the bottom row
    (y = H-1) is OPEN (grains toppling off the bottom are lost). ``drop_one`` adds a grain
    at a top-row column and relaxes the pile downward, returning ``(size, toppled_sites)``
    where ``size`` is the number of topplings and ``toppled_sites`` is the set of (y, x)
    cells that toppled at least once.

    Relaxation is a single top-to-bottom sweep: each row is fully relaxed (repeatedly, as
    a cell can topple more than once) before moving to the next row. Because grains only
    move to larger y this reaches the canonical stable configuration; the toppling count is
    order-independent (abelian).
    """

    def __init__(self, H: int = 200, W: int = 200) -> None:
        if H <= 1:
            raise ValueError(f"need H > 1 (got {H})")
        if W <= 1:
            raise ValueError(f"need W > 1 (got {W})")
        self.H = int(H)
        self.W = int(W)
        self.heights = np.zeros((H, W), dtype=np.int64)

    def _relax(self) -> Tuple[int, set]:
        """Relax the whole pile with one top-to-bottom sweep. Returns the total number of
        topplings and the set of (y, x) cells that toppled at least once."""
        h = self.heights
        H, W = self.H, self.W
        total = 0
        toppled: set = set()
        for y in range(H):
            # Fully relax row y (it may need several passes because a cell can accumulate
            # grains from repeated topplings of its up-neighbours within the same row's feed;
            # but since feed to row y comes only from row y-1 which is already stable, one
            # pass suffices UNLESS a single cell holds >= 2*k grains — handle via a loop).
            row = h[y]
            while True:
                unstable = row >= THRESHOLD
                n_unstable = int(unstable.sum())
                if n_unstable == 0:
                    break
                total += n_unstable
                # number of times each unstable cell topples this pass: floor(h/2) would be
                # the abelian shortcut, but to record each toppling faithfully we shed the
                # canonical single unit (subtract THRESHOLD, distribute) per pass. Repeat.
                cols = np.nonzero(unstable)[0]
                for x in cols:
                    toppled.add((y, int(x)))
                # shed THRESHOLD grains from every unstable cell in this row
                row[unstable] -= THRESHOLD
                if y + 1 < H:
                    below = h[y + 1]
                    # down-left: same column x
                    below[unstable] += 1
                    # down-right: column (x+1) mod W
                    shifted = np.zeros(W, dtype=bool)
                    shifted[(cols + 1) % W] = True
                    # if two unstable cols map to the same (x+1) target only via distinct x,
                    # they are distinct targets unless W small; use add via bincount to be safe
                    below += np.bincount((cols + 1) % W, minlength=W).astype(np.int64)
                # grains from the bottom row (y == H-1) simply vanish (open boundary)
        return total, toppled

    def drop_one(self, col: int) -> Tuple[int, set]:
        """Add one grain at top-row column ``col``, relax, and return (size, toppled_sites)."""
        self.heights[0, col % self.W] += 1
        return self._relax()

    def mean_height(self) -> float:
        return float(self.heights.mean())

    def total_grains(self) -> int:
        return int(self.heights.sum())


# =============================================================================
# avalanche geometry
# =============================================================================

def longitudinal_extent(toppled: set) -> int:
    """Longitudinal (drive-direction) extent of an avalanche: max y - min y over its
    toppled sites. 0 for an empty or single-row avalanche."""
    if not toppled:
        return 0
    ys = [y for (y, _x) in toppled]
    return max(ys) - min(ys)


def transverse_extent(toppled: set, W: int) -> int:
    """Transverse (across-drive) extent of an avalanche on the PERIODIC cylinder of
    circumference W: the smallest arc (in columns) that contains all toppled x-coordinates.

    Because x wraps, the naive max(x) - min(x) over-counts a cluster that straddles the
    seam. We take the columns actually touched, sort them, and find the largest GAP between
    consecutive occupied columns (wrapping around); the transverse extent is W minus that
    largest gap (the complement arc), which is the tightest wrap-aware span. 0 for a
    single-column (or empty) avalanche."""
    if not toppled:
        return 0
    xs = sorted({x for (_y, x) in toppled})
    if len(xs) == 1:
        return 0
    # Largest gap (in column-steps) between consecutive occupied columns on the ring; the
    # tightest bounding arc is the complement, so its span (max-min analog) is W - max_gap.
    max_gap = 0
    for i in range(len(xs)):
        nxt = xs[(i + 1) % len(xs)]
        gap = (nxt - xs[i]) % W
        if gap > max_gap:
            max_gap = gap
    return W - max_gap


# =============================================================================
# drive loop
# =============================================================================

def drive(pile: DirectedSandpile, n_grains: int, rng: np.random.Generator,
          *, record: bool = True) -> Dict[str, List]:
    """Drive ``pile`` for ``n_grains`` added grains (each at a uniformly-random TOP-row
    column, using ``rng``). If ``record`` is True, returns per-grain avalanche ``sizes``,
    ``longitudinal`` extents and ``transverse`` extents; if False, returns empty lists
    (used to burn the transient cheaply)."""
    W = pile.W
    cols = rng.integers(0, W, size=n_grains)
    sizes: List[int] = []
    longs: List[int] = []
    transes: List[int] = []
    if record:
        for i in range(n_grains):
            s, toppled = pile.drop_one(int(cols[i]))
            sizes.append(s)
            longs.append(longitudinal_extent(toppled))
            transes.append(transverse_extent(toppled, W))
    else:
        for i in range(n_grains):
            pile.drop_one(int(cols[i]))
    return {"sizes": sizes, "longitudinal": longs, "transverse": transes}


def run_directed_sandpile(H: int = 200, W: int = 200, *, transient: int = 20_000,
                          n_avalanches: int = 12_000, seed: int = 0) -> Dict[str, Any]:
    """Full SOC experiment: drive an empty H x W directed pile past a transient to the
    steady state, then record ``n_avalanches`` avalanches (size + longitudinal/transverse
    extent each). Deterministic given ``seed``.

    Only NONZERO avalanches (grain triggered >= 1 toppling) contribute an extent; the raw
    per-grain ``sizes`` list includes zeros (a grain that landed without toppling) so the
    heavy-tail and MLE analyses see the true distribution."""
    rng = np.random.default_rng(seed)
    pile = DirectedSandpile(H, W)

    # Burn the transient (do not store its avalanches).
    drive(pile, transient, rng, record=False)

    # Record the steady-state avalanches.
    rec = drive(pile, n_avalanches, rng, record=True)
    return {
        "H": H, "W": W, "transient": transient, "n_avalanches": n_avalanches, "seed": seed,
        "sizes": rec["sizes"],
        "longitudinal": rec["longitudinal"],
        "transverse": rec["transverse"],
        "stationary_mean_height": pile.mean_height(),
    }


# =============================================================================
# analysis: discrete-MLE tail exponent, heavy-tail stats, anisotropy
# =============================================================================

def fit_tau(sizes: Sequence[int], *, kmin: int = 1,
            tau_bracket: Tuple[float, float] = (1.001, 6.0)) -> Dict[str, Any]:
    """Discrete power-law MLE for the avalanche-size tail exponent tau.

    Method (FIXED before the run; Clauset, Shalizi & Newman 2009, the EXACT discrete MLE
    for P(s) = s^{-tau} / zeta(tau, kmin), s = kmin, kmin+1, ...). Over all avalanches with
    size s >= kmin (zero-size avalanches are EXCLUDED — they are not part of the power-law
    tail), tau maximizes the log-likelihood

        L(tau) = -n*ln(zeta(tau, kmin)) - tau * sum_i ln(s_i),

    i.e. tau solves the score equation  -zeta'(tau, kmin)/zeta(tau, kmin) = mean_i ln(s_i)
    (Hurwitz zeta). We solve it numerically (Brent root-find on the score) rather than the
    (kmin - 0.5) continuity-correction approximation, which is biased at small kmin. ``kmin``
    is fixed at 1 and is NOT tuned to hit a target exponent. The asymptotic standard error
    is sigma = (tau - 1) / sqrt(n). Returns tau, its standard error, the tail-sample count,
    and kmin."""
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


def size_histogram(sizes: Sequence[int], *, n_bins: int = 30) -> List[Dict[str, float]]:
    """Logarithmically-binned histogram of nonzero avalanche sizes (for the heavy-tail
    visual). Bins geometric from 1 to max; counts raw. Zero-size avalanches reported
    separately by the caller."""
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


def heavy_tail_stats(sizes: Sequence[int]) -> Dict[str, Any]:
    """Heavy-tail descriptors (P3): decades spanned by nonzero sizes, the max, the median
    NONZERO size, and the max/median ratio. 'Decades spanned' = log10(max) - log10(min
    nonzero) over the nonzero avalanches."""
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


def anisotropy_stats(longitudinal: Sequence[int], transverse: Sequence[int],
                     sizes: Sequence[int]) -> Dict[str, Any]:
    """Directional-anisotropy descriptors (P2). Over the NONZERO avalanches (those that
    toppled at least one site), report the mean longitudinal extent, the mean transverse
    extent, and their ratio. Directed propagation => mean longitudinal >> mean transverse.

    Averaging over the nonzero avalanches (not all grains) is the faithful geometric
    observable: an avalanche that never toppled has no bounding box. We align the three
    lists by index and select the nonzero ones."""
    s = np.asarray(sizes, dtype=np.float64)
    lon = np.asarray(longitudinal, dtype=np.float64)
    tra = np.asarray(transverse, dtype=np.float64)
    mask = s >= 1
    n = int(mask.sum())
    if n == 0:
        return {"n_nonzero": 0, "mean_longitudinal": 0.0, "mean_transverse": 0.0,
                "aniso_ratio": float("nan"), "mean_longitudinal_all": 0.0,
                "mean_transverse_all": 0.0}
    lon_nz = lon[mask]
    tra_nz = tra[mask]
    mean_lon = float(lon_nz.mean())
    mean_tra = float(tra_nz.mean())
    ratio = mean_lon / mean_tra if mean_tra > 0 else float("inf")
    return {
        "n_nonzero": n,
        "mean_longitudinal": mean_lon,
        "mean_transverse": mean_tra,
        "aniso_ratio": ratio,
        "mean_longitudinal_all": float(lon.mean()),
        "mean_transverse_all": float(tra.mean()),
    }


def analyze(run: Dict[str, Any], *, kmin: int = 1) -> Dict[str, Any]:
    """Bundle the three locked analyses on a single run's recorded arrays."""
    tau = fit_tau(run["sizes"], kmin=kmin)
    heavy = heavy_tail_stats(run["sizes"])
    aniso = anisotropy_stats(run["longitudinal"], run["transverse"], run["sizes"])
    hist = size_histogram(run["sizes"])
    n_zero = int(np.sum(np.asarray(run["sizes"]) == 0))
    return {
        "tau": tau, "heavy_tail": heavy, "anisotropy": aniso, "histogram": hist,
        "n_zero": n_zero, "n_total": len(run["sizes"]),
        "stationary_mean_height": run["stationary_mean_height"],
    }
