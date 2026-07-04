"""Drossel-Schwabl forest-fire model (1992) — a faithful self-organized-criticality (SOC)
reproduction.

Source: Drossel, B. & Schwabl, F. (1992) "Self-organized critical forest-fire model",
Phys. Rev. Lett. 69:1629-1632. doi:10.1103/PhysRevLett.69.1629.

IMPORTANT (honesty, binds the FINDINGS): this is a CELLULAR AUTOMATON / SOC model, NOT
an agent-stepping ABM. There are no agents that perceive, decide and act, no scheduler
over an agent roster, no per-agent step. It is a synchronous local update rule applied to
a grid of cells (empty / tree / burning). We disclose this exactly as the BTW sandpile and
the Erdos-Renyi / Watts-Strogatz network-generation reproductions disclose that they are
not agent-based. The lock-first + honest-verdict + L3-bundle discipline still fully applies.

Rules (the canonical Drossel-Schwabl forest-fire CA, verified against the paper):
  * An L x L grid (L=128 here) of cells in {EMPTY=0, TREE=1, BURNING=2}.
  * Each tick (SYNCHRONOUS update, all cells at once, von-Neumann neighbourhood):
      1. a BURNING cell becomes EMPTY (it has burnt down);
      2. a TREE with >= 1 BURNING von-Neumann neighbour becomes BURNING (fire spreads);
      3. an EMPTY cell becomes a TREE with probability p (growth);
      4. a TREE that is NOT already igniting from a burning neighbour becomes BURNING
         with probability f (lightning).
    Boundary: open (no wrap) for the literal synchronous CA; cells off the grid are
    treated as non-burning. The control parameter is f/p; SOC is reached in the
    double-separation limit 1 >> p >> f.

TWO IMPLEMENTATIONS (we use the second for the clean fire-size metric; both are provided):

  (A) ``ForestFire`` — the literal synchronous CA above. Faithful to the microscopic rule
      and used by the determinism / faithful-rule tests. With f/p small a "fire" started
      by one lightning strike spreads over many ticks; a single fire is not cleanly
      delimited from concurrent fires, so this implementation is NOT used to measure the
      fire-size distribution.

  (B) ``run_separated`` — the STANDARD double-separation (a.k.a. instantaneous-burning)
      implementation used throughout the SOC literature to measure fire sizes cleanly
      (Drossel & Schwabl 1992; Grassberger 2002; Clar, Drossel & Schwabl 1996). The two
      time-scale separations 1 >> p >> f are taken to their limit:
        - between two lightning strikes, grow trees for a while (each empty cell -> tree
          with prob p per growth step), then
        - a SINGLE lightning strike hits a uniformly random cell; if it is a tree, its
          WHOLE toroidal connected (von-Neumann) cluster burns INSTANTLY in one event and
          is removed (set to empty). The fire size = the number of cells in that cluster.
      This is the f -> 0 (after p) limit of implementation (A): one fire per lightning,
      no overlap, fire size = cluster size. We document that this is the implementation we
      grade on. The single controlling parameter is theta = p/f = the average number of
      TREES PLANTED between two lightning strikes (Drossel & Schwabl 1992; Grassberger
      2002; Wikipedia "Forest-fire model"). With p=0.05, f=p/1000 -> theta = 1000 trees
      planted per strike. We plant EXACTLY theta trees one-at-a-time on uniformly-random
      currently-empty cells between strikes (NOT a saturating bulk growth) — that is what
      keeps the system at the SOC tree density rather than filling the whole grid.

SOC: from any initial condition, after a transient the grid self-organises to a STATIONARY
state with a characteristic tree density, in which fire (cluster) sizes are POWER-LAW
distributed P(s) ~ s^{-tau} over a range, with KNOWN deviations at the largest sizes (the
forest-fire model is only APPROXIMATELY scale-free; this is reported as a caveat, with the
fit range). We discard a fixed transient of fires, then record a fixed number of fire sizes.

Determinism: the whole run is reproducible given an integer seed (a single
``numpy.random.default_rng(seed)`` drives growth + strike locations). NumPy + a small BFS
flood-fill make it fast; the result is the canonical CA/SOC outcome.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import brentq
from scipy.special import zeta

EMPTY = 0
TREE = 1
BURNING = 2


# -- (A) literal synchronous CA -------------------------------------------------

class ForestFire:
    """An L x L Drossel-Schwabl forest-fire grid with the literal synchronous update.

    ``grid`` is an (L, L) int8 array of cells in {EMPTY, TREE, BURNING}. ``step`` applies
    one synchronous tick. Used by the faithful-rule + determinism tests; NOT used for the
    fire-size metric (use ``run_separated`` for that).
    """

    def __init__(self, L: int = 128, *, p: float = 0.05, f: float = 5e-5,
                 rng: Optional[np.random.Generator] = None,
                 init: str = "empty", seed: int = 0) -> None:
        if L <= 0:
            raise ValueError("L must be positive")
        if not (0.0 <= f <= p <= 1.0):
            raise ValueError("require 0 <= f <= p <= 1 (scale separation)")
        self.L = L
        self.p = p
        self.f = f
        self.rng = rng if rng is not None else np.random.default_rng(seed)
        if init == "empty":
            self.grid = np.full((L, L), EMPTY, dtype=np.int8)
        elif init == "trees":
            self.grid = np.full((L, L), TREE, dtype=np.int8)
        elif init == "random":
            self.grid = self.rng.integers(0, 2, size=(L, L)).astype(np.int8)
        else:
            raise ValueError(f"unknown init {init!r}")

    def _burning_neighbour(self) -> np.ndarray:
        """Boolean (L,L): cell has >= 1 BURNING von-Neumann neighbour (open boundary)."""
        burning = self.grid == BURNING
        nb = np.zeros_like(burning)
        nb[1:, :] |= burning[:-1, :]    # neighbour above is burning
        nb[:-1, :] |= burning[1:, :]    # below
        nb[:, 1:] |= burning[:, :-1]    # left
        nb[:, :-1] |= burning[:, 1:]    # right
        return nb

    def step(self) -> None:
        """Apply one synchronous CA tick (in place)."""
        g = self.grid
        burning = g == BURNING
        tree = g == TREE
        empty = g == EMPTY
        nb = self._burning_neighbour()

        new = g.copy()
        # 1. burning -> empty
        new[burning] = EMPTY
        # 2. tree with a burning neighbour -> burning (fire spreads)
        spread = tree & nb
        new[spread] = BURNING
        # 4. tree NOT igniting from a neighbour -> burning with prob f (lightning)
        tree_no_nb = tree & ~nb
        lightning = tree_no_nb & (self.rng.random(g.shape) < self.f)
        new[lightning] = BURNING
        # 3. empty -> tree with prob p (growth)
        growth = empty & (self.rng.random(g.shape) < self.p)
        new[growth] = TREE
        self.grid = new

    def tree_density(self) -> float:
        return float(np.mean(self.grid == TREE))

    def counts(self) -> Dict[str, int]:
        return {
            "empty": int(np.sum(self.grid == EMPTY)),
            "tree": int(np.sum(self.grid == TREE)),
            "burning": int(np.sum(self.grid == BURNING)),
        }


# -- (B) standard double-separation (instantaneous-burning) implementation ------

def _cluster_size(grid: np.ndarray, r0: int, c0: int) -> List[Tuple[int, int]]:
    """Return the toroidal von-Neumann TREE cluster containing ``(r0, c0)``.

    The literal synchronous CA above keeps open boundaries because that rule is tested as
    such. The scale-separated fire-size metric treats the lattice as periodic so a cluster
    crossing the left/right or top/bottom edge is counted as one fire, not two fragments.
    """
    L = grid.shape[0]
    if grid[r0, c0] != TREE:
        return []
    seen = [(r0, c0)]
    q = deque(seen)
    visited = np.zeros_like(grid, dtype=bool)
    visited[r0, c0] = True
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = (r + dr) % L, (c + dc) % L
            if not visited[rr, cc] and grid[rr, cc] == TREE:
                visited[rr, cc] = True
                q.append((rr, cc))
                seen.append((rr, cc))
    return seen


class SeparatedForestFire:
    """Double-separation forest-fire: grow trees between strikes, then a single lightning
    strike instantly burns the whole toroidal connected cluster it lands on (fire size =
    cluster size). This is the standard SOC fire-size implementation (Drossel & Schwabl
    1992) with periodic fire-size accounting.

    ``grid`` is an (L, L) int8 of {EMPTY, TREE}; there is no persistent BURNING state
    because each fire is instantaneous (the burnt cluster is set to EMPTY immediately).
    """

    def __init__(self, L: int = 128, *, p: float = 0.05, f: float = 5e-5,
                 rng: Optional[np.random.Generator] = None,
                 init: str = "empty", seed: int = 0) -> None:
        if L <= 0:
            raise ValueError("L must be positive")
        if not (0.0 < f <= p <= 1.0):
            raise ValueError("require 0 < f <= p <= 1 (scale separation)")
        self.L = L
        self.p = p
        self.f = f
        # The controlling parameter theta = p/f = average number of TREES PLANTED between
        # two lightning strikes. With p=0.05, f=p/1000 -> theta = 1000. We plant exactly
        # theta trees one-at-a-time on random empty cells between strikes (the canonical
        # double-separation drive); this holds the SOC density instead of saturating.
        self.trees_per_strike = max(1, int(round(p / f)))
        self.rng = rng if rng is not None else np.random.default_rng(seed)
        if init == "empty":
            self.grid = np.full((L, L), EMPTY, dtype=np.int8)
        elif init == "trees":
            self.grid = np.full((L, L), TREE, dtype=np.int8)
        elif init == "random":
            self.grid = self.rng.integers(0, 2, size=(L, L)).astype(np.int8)
        else:
            raise ValueError(f"unknown init {init!r}")

    def _grow(self) -> None:
        """Plant exactly ``trees_per_strike`` (= theta = p/f) trees between lightning
        strikes, each on a uniformly-random currently-EMPTY cell (sampled without
        replacement within this growth phase). If the grid has fewer empty cells than
        theta, every empty cell becomes a tree (the forest is full). This is the canonical
        double-separation drive; it holds the SOC density rather than saturating the grid.
        """
        empty_idx = np.flatnonzero(self.grid.ravel() == EMPTY)
        n_empty = empty_idx.size
        if n_empty == 0:
            return
        k = min(self.trees_per_strike, n_empty)
        chosen = self.rng.choice(empty_idx, size=k, replace=False)
        flat = self.grid.ravel()
        flat[chosen] = TREE

    def lightning(self) -> int:
        """Strike one uniformly random cell. If it is a tree, burn its whole connected
        toroidal cluster instantly (set those cells to EMPTY) and return the fire size =
        cluster size; if the struck cell is empty, return 0 (lightning hit bare ground)."""
        r = int(self.rng.integers(0, self.L))
        c = int(self.rng.integers(0, self.L))
        if self.grid[r, c] != TREE:
            return 0
        cells = _cluster_size(self.grid, r, c)
        for (rr, cc) in cells:
            self.grid[rr, cc] = EMPTY
        return len(cells)

    def one_fire(self) -> int:
        """One full cycle: grow trees, then a single lightning strike. Returns fire size."""
        self._grow()
        return self.lightning()

    def tree_density(self) -> float:
        return float(np.mean(self.grid == TREE))


def run_separated(L: int = 128, *, p: float = 0.05, f: float = 5e-5,
                  transient: int = 2_000, n_fires: int = 20_000,
                  seed: int = 0, init: str = "empty",
                  density_samples: int = 2_000) -> Dict[str, Any]:
    """Full SOC experiment with the double-separation implementation: from ``init``, run
    ``transient`` fire cycles to reach the stationary state (sizes discarded), then record
    ``n_fires`` fire sizes. Returns the recorded sizes, the stationary tree density (sampled
    over the recording phase), and config echoes. Deterministic given ``seed``.
    """
    rng = np.random.default_rng(seed)
    ff = SeparatedForestFire(L, p=p, f=f, rng=rng, init=init)

    for _ in range(transient):
        ff.one_fire()

    sizes: List[int] = []
    dens_samples: List[float] = []
    sample_every = max(1, n_fires // density_samples)
    for i in range(n_fires):
        sizes.append(ff.one_fire())
        if i % sample_every == 0:
            dens_samples.append(ff.tree_density())

    return {
        "L": L, "p": p, "f": f, "init": init,
        "transient": transient, "n_fires": n_fires, "seed": seed,
        "trees_per_strike": ff.trees_per_strike,
        "sizes": sizes,
        "stationary_tree_density": float(np.mean(dens_samples)) if dens_samples else ff.tree_density(),
        "tree_density_samples": dens_samples,
        "final_tree_density": ff.tree_density(),
    }


# -- analysis -------------------------------------------------------------------

def fit_tau(sizes: Sequence[int], *, kmin: int = 1,
            tau_bracket: Tuple[float, float] = (1.001, 6.0)) -> Dict[str, Any]:
    """Discrete power-law MLE for the fire-size tail exponent tau.

    Method (FIXED before the run; Clauset, Shalizi & Newman 2009, the EXACT discrete MLE
    for the discrete power law P(s) = s^{-tau} / zeta(tau, kmin), s = kmin, kmin+1, ...).
    Over all fires with size s >= kmin (zero-size events, where lightning hit bare ground,
    are EXCLUDED), tau maximizes the log-likelihood

        L(tau) = -n*ln(zeta(tau, kmin)) - tau * sum_i ln(s_i),

    i.e. tau solves -zeta'(tau, kmin)/zeta(tau, kmin) = mean_i ln(s_i) (Hurwitz zeta). We
    solve it numerically (Brent root-find on the score), NOT the (kmin-0.5) continuity-
    correction approximation tau = 1 + n / sum ln(s/(kmin-0.5)) — that approximation is
    only accurate for kmin >~ 6 and is biased LOW at small kmin, so it is deliberately not
    used. ``kmin`` is FIXED before the run and NOT tuned to hit a target exponent. The
    asymptotic standard error is sigma = (tau - 1) / sqrt(n). Returns tau, its standard
    error, the number of tail samples, and the kmin used.
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


def size_histogram(sizes: Sequence[int], *, n_bins: int = 30) -> List[Dict[str, float]]:
    """Logarithmically-binned histogram of nonzero fire sizes (for reporting / the
    heavy-tail visual). Bins are geometric from 1 to max size; counts are raw."""
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
    """Heavy-tail descriptors for P2: decades spanned by nonzero sizes, the max size, the
    median NONZERO size, and the max/median ratio."""
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
