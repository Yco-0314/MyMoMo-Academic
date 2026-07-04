"""Newman 2002 — SIR on networks via the bond-percolation mapping — a faithful
network-GENERATION + percolation reproduction.

Source: Newman, M. E. J. (2002) "Spread of epidemic disease on networks",
Phys. Rev. E 66:016128. doi:10.1103/PhysRevE.66.016128.

IMPORTANT (honesty, binds the FINDINGS): this is a network-GENERATION + BOND-
PERCOLATION model, NOT an agent-stepping ABM. There are no agents, no scheduler, no
ticks of SIR dynamics. Newman's central result is that the SIR epidemic on a
configuration-model network with a given degree distribution is *exactly isomorphic*
to bond percolation on that network, where each edge is independently OCCUPIED with
probability T (the transmissibility). The giant occupied cluster is the epidemic. We
build configuration-model graphs by stub-matching, occupy each edge with probability
T, and measure the largest occupied cluster with union-find. It is reproduced
faithfully as a network-science result; the lock-first + honest-verdict + L3-bundle
discipline still fully applies.

The three locked quantities (all from Newman 2002):

  * THRESHOLD (P1).  The epidemic threshold in the transmissibility is the closed form
        T_c = <k> / (<k^2> - <k>)
    where <k>, <k^2> are the first two moments of the REALIZED degree sequence. Below
    T_c the occupied clusters are all o(N) (no epidemic); at/above T_c a giant occupied
    cluster (the epidemic) emerges. Equivalently this is the bond-percolation threshold
    of the configuration model, p_c = 1/(g1'(1)) with g1 the excess-degree generating
    function — the same number. We measure T_c empirically two ways (susceptibility peak
    and giant-cluster onset) and compare to the formula computed from the realized
    degree moments.

  * HETEROGENEITY LOWERS IT (P2).  <k^2> is dominated by the tail, so a heavy-tailed
    (power-law) degree distribution at the SAME mean degree has a far larger <k^2> and
    hence a far SMALLER T_c than a homogeneous graph. A well-mixed SIR has no degree
    moments and cannot show this; it is the structural, discriminating prediction.

  * GENERATING-FUNCTION FINAL SIZE (P3).  Above threshold the fraction of the network
    in the giant occupied cluster (the epidemic size S) satisfies the self-consistent
    generating-function equations
        u = g1(1 - T + T*u),      S = 1 - g0(1 - T + T*u)
    where g0(x) = sum_k p_k x^k is the degree generating function and g1(x) =
    g0'(x)/g0'(1) is the excess-degree generating function. u is the probability that
    an edge does NOT lead to the giant cluster; iterate the u fixed point to
    convergence, then read S. We compare S(T) to the simulated giant-cluster fraction.

Built with NO agent platform (there is no agent dynamics): a stub-matching
configuration-model generator (deterministic given a seed), a union-find bond-
percolation routine, and the closed-form / generating-function calculators. Union-find
(not BFS-per-node) keeps a single percolation realization O(E * alpha(N)).
"""
from __future__ import annotations

import math
import random
import statistics
from typing import Any, Callable, Dict, List, Sequence, Tuple


# -- degree-sequence generators (configuration model inputs) ------------------

def poisson_degree_sequence(n: int, mean_k: float, *, rng: random.Random) -> List[int]:
    """A homogeneous degree sequence: n i.i.d. Poisson(mean_k) draws (the classic
    'homogeneous / Poisson' network of Newman 2002 — the configuration-model analogue
    of an Erdos-Renyi graph). Poisson has <k^2> - <k> = <k>^2, giving T_c ~= 1/<k>, the
    homogeneous baseline. Degrees are drawn, not tuned. Deterministic given ``rng``."""
    if n <= 0:
        raise ValueError("n must be positive")
    if mean_k < 0:
        raise ValueError("mean_k must be non-negative")
    seq = [_poisson_draw(mean_k, rng) for _ in range(n)]
    return seq


def powerlaw_degree_sequence(n: int, gamma: float, *, kmin: int = 1,
                             kmax: int, rng: random.Random) -> List[int]:
    """A heavy-tailed degree sequence: n i.i.d. draws from a discrete power law
    p_k ∝ k^(-gamma) on the integer support [kmin, kmax] (inclusive). The hard cutoff
    kmax keeps <k^2> finite and the stub-matching tractable at finite N; it is FIXED
    (a structural regularizer of the finite-N ensemble), NOT tuned to hit a threshold.
    Deterministic given ``rng``.

    We build the normalized pmf over [kmin, kmax] once and inverse-transform sample.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if kmin < 1:
        raise ValueError("kmin must be >= 1")
    if kmax < kmin:
        raise ValueError("kmax must be >= kmin")
    if gamma <= 1.0:
        raise ValueError("gamma must be > 1 for a normalizable tail")
    ks = list(range(kmin, kmax + 1))
    weights = [k ** (-gamma) for k in ks]
    total = sum(weights)
    # cumulative distribution for inverse-transform sampling
    cum: List[float] = []
    acc = 0.0
    for w in weights:
        acc += w / total
        cum.append(acc)
    cum[-1] = 1.0  # guard against float drift
    seq: List[int] = []
    for _ in range(n):
        r = rng.random()
        # binary search into cum
        lo, hi = 0, len(cum) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if r <= cum[mid]:
                hi = mid
            else:
                lo = mid + 1
        seq.append(ks[lo])
    return seq


def _poisson_draw(lam: float, rng: random.Random) -> int:
    """One Poisson(lam) draw (Knuth's multiplicative algorithm). Adequate for the
    modest means used here; deterministic given ``rng``."""
    if lam <= 0:
        return 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


def rescale_to_mean(seq: List[int], target_mean: float) -> List[int]:
    """(unused by the locked runs; kept for exploration) — no-op passthrough is avoided;
    this scales degrees multiplicatively toward a target mean and rounds. Not used to
    tune any locked number. Present only so a caller can align two ensembles' means if
    desired; the locked runs instead draw both ensembles and REPORT the realized means.
    """
    cur = statistics.fmean(seq) if seq else 0.0
    if cur <= 0:
        return seq
    factor = target_mean / cur
    return [max(0, int(round(k * factor))) for k in seq]


# -- degree moments + closed-form threshold -----------------------------------

def degree_moments(seq: Sequence[int]) -> Tuple[float, float]:
    """Return (<k>, <k^2>) of a degree sequence."""
    n = len(seq)
    if n == 0:
        return 0.0, 0.0
    s1 = sum(seq)
    s2 = sum(k * k for k in seq)
    return s1 / n, s2 / n


def critical_transmissibility(seq: Sequence[int]) -> float:
    """Newman 2002 closed-form epidemic threshold in the transmissibility,

        T_c = <k> / (<k^2> - <k>),

    computed from the REALIZED degree sequence's first two moments. Equal to the
    bond-percolation threshold p_c = 1/g1'(1) of the configuration model. Returns
    +inf if the denominator is non-positive (no percolating regime — e.g. a graph with
    no degree variance and <k> <= 1)."""
    mean_k, mean_k2 = degree_moments(seq)
    denom = mean_k2 - mean_k
    if denom <= 0.0:
        return float("inf")
    return mean_k / denom


# -- configuration-model graph (stub matching) --------------------------------

def build_configuration_edges(seq: List[int], *, rng: random.Random
                              ) -> List[Tuple[int, int]]:
    """Configuration-model edge list from a degree sequence by STUB MATCHING.

    Each node i contributes ``seq[i]`` stubs (half-edges); we shuffle the full stub
    list and pair adjacent stubs. Self-loops and multi-edges are simply removed (the
    standard 'erased configuration model'); at N>=1e4 with modest mean degree the
    erased fraction is tiny and does not move the moments materially. If the total stub
    count is odd, one random stub is dropped so the list pairs evenly. Deterministic
    given ``rng``. Returns a list of undirected edges (i, j) with i != j, de-duplicated.
    """
    stubs: List[int] = []
    for node, deg in enumerate(seq):
        stubs.extend([node] * deg)
    if len(stubs) % 2 == 1:
        # drop one random stub to make the count even
        j = rng.randrange(len(stubs))
        stubs[j], stubs[-1] = stubs[-1], stubs[j]
        stubs.pop()
    rng.shuffle(stubs)
    seen: set = set()
    edges: List[Tuple[int, int]] = []
    for a, b in zip(stubs[0::2], stubs[1::2]):
        if a == b:
            continue  # self-loop -> erase
        key = (a, b) if a < b else (b, a)
        if key in seen:
            continue  # multi-edge -> erase
        seen.add(key)
        edges.append(key)
    return edges


# -- union-find (disjoint set) ------------------------------------------------

class UnionFind:
    """Disjoint-set forest with path compression + union by size. Used to grow the
    occupied bond clusters in a single O(E * alpha(N)) pass — NOT a BFS-per-node."""

    __slots__ = ("parent", "size")

    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.size = [1] * n

    def find(self, x: int) -> int:
        root = x
        parent = self.parent
        while parent[root] != root:
            root = parent[root]
        # path compression
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]

    def largest_size(self) -> int:
        best = 0
        for i, p in enumerate(self.parent):
            if p == i and self.size[i] > best:
                best = self.size[i]
        return best


# -- bond percolation ---------------------------------------------------------

def percolate_once(n: int, edges: Sequence[Tuple[int, int]], T: float, *,
                   rng: random.Random) -> Tuple[int, int]:
    """Occupy each edge independently with probability T and grow the occupied clusters
    with union-find. Returns (largest_cluster_size, second_largest_cluster_size).

    The largest occupied cluster = the SIR epidemic (Newman's isomorphism); the second-
    largest is a susceptibility-style probe (it peaks near the percolation threshold).
    Deterministic given ``rng``.
    """
    if not 0.0 <= T <= 1.0:
        raise ValueError("T (transmissibility / edge-occupation) must be in [0, 1]")
    uf = UnionFind(n)
    for a, b in edges:
        if rng.random() < T:
            uf.union(a, b)
    # component-size histogram from the roots
    sizes: List[int] = []
    for i, p in enumerate(uf.parent):
        if p == i:
            sizes.append(uf.size[i])
    sizes.sort(reverse=True)
    largest = sizes[0] if sizes else 0
    second = sizes[1] if len(sizes) > 1 else 0
    return largest, second


# -- generating-function final size (P3) --------------------------------------

def degree_pmf(seq: Sequence[int]) -> Dict[int, float]:
    """Empirical degree pmf p_k of a degree sequence."""
    n = len(seq)
    counts: Dict[int, int] = {}
    for k in seq:
        counts[k] = counts.get(k, 0) + 1
    return {k: c / n for k, c in counts.items()}


def gf_final_size(seq: Sequence[int], T: float, *, tol: float = 1e-12,
                  max_iter: int = 100_000) -> float:
    """Newman-2002 generating-function epidemic final size S at transmissibility T.

    With the degree pmf p_k and generating functions
        g0(x) = sum_k p_k x^k,      g1(x) = g0'(x) / g0'(1),
    the probability u that an edge does NOT lead into the giant cluster solves the
    self-consistency
        u = g1( 1 - T + T*u ),
    reached by iterating u <- g1(1 - T + T*u) from u = 0 (converges UP to the surviving
    root). The epidemic size is then
        S = 1 - g0( 1 - T + T*u ).
    Returns 0 exactly at T = 0. Below threshold the iteration converges to u = 1 and
    S = 0 (no giant outbreak), as it should.
    """
    if not 0.0 <= T <= 1.0:
        raise ValueError("T must be in [0, 1]")
    if T == 0.0:
        return 0.0
    pmf = degree_pmf(seq)
    ks = sorted(pmf)
    mean_k = sum(k * pmf[k] for k in ks)
    if mean_k <= 0.0:
        return 0.0

    def g0(x: float) -> float:
        return sum(pmf[k] * (x ** k) for k in ks)

    def g1(x: float) -> float:
        # g0'(x)/g0'(1) = sum_k p_k k x^{k-1} / <k>
        num = sum(pmf[k] * k * (x ** (k - 1)) for k in ks if k >= 1)
        return num / mean_k

    u = 0.0
    for _ in range(max_iter):
        arg = 1.0 - T + T * u
        nxt = g1(arg)
        if abs(nxt - u) < tol:
            u = nxt
            break
        u = nxt
    arg = 1.0 - T + T * u
    S = 1.0 - g0(arg)
    return max(0.0, S)


# -- one realization + sweeps -------------------------------------------------

def build_graph(seq: List[int], *, seed: int) -> Dict[str, Any]:
    """Build one configuration-model graph from a degree sequence and return its edge
    list + realized moments + closed-form T_c. Deterministic given ``seed``."""
    rng = random.Random(seed)
    edges = build_configuration_edges(seq, rng=rng)
    mean_k, mean_k2 = degree_moments(seq)
    return {
        "n": len(seq),
        "edges": edges,
        "n_edges": len(edges),
        "mean_k": mean_k,
        "mean_k2": mean_k2,
        "T_c_formula": critical_transmissibility(seq),
    }


def percolation_sweep(seq: List[int], T_grid: Sequence[float], *,
                      n_graphs: int = 5, n_perc: int = 10, seed_base: int = 0
                      ) -> List[Dict[str, Any]]:
    """Sweep transmissibility T over a grid on a fixed degree sequence.

    For each T we build ``n_graphs`` configuration-model graphs (graph seed
    ``seed_base + g``) and run ``n_perc`` bond-percolation realizations on each
    (percolation seed derived from the graph seed and T index). We record the mean
    giant-cluster FRACTION (largest occupied cluster / N) and the mean SECOND-largest
    fraction (the susceptibility probe) at each T. Deterministic given ``seed_base``.
    Returns one summary dict per T.
    """
    n = len(seq)
    out: List[Dict[str, Any]] = []
    for ti, T in enumerate(T_grid):
        giant_fracs: List[float] = []
        second_fracs: List[float] = []
        for g in range(n_graphs):
            graph = build_graph(seq, seed=seed_base + g)
            edges = graph["edges"]
            for r in range(n_perc):
                # stable, distinct percolation seed per (graph, T, realization)
                pseed = (seed_base + g) * 1_000_003 + ti * 9973 + r
                rng = random.Random(pseed)
                largest, second = percolate_once(n, edges, T, rng=rng)
                giant_fracs.append(largest / n)
                second_fracs.append(second / n)
        out.append({
            "T": T,
            "n": n,
            "n_graphs": n_graphs,
            "n_perc": n_perc,
            "mean_giant_fraction": statistics.fmean(giant_fracs),
            "std_giant_fraction": statistics.pstdev(giant_fracs) if len(giant_fracs) > 1 else 0.0,
            "mean_second_fraction": statistics.fmean(second_fracs),
            "max_second_fraction": max(second_fracs) if second_fracs else 0.0,
            "gf_final_size": gf_final_size(seq, T),
        })
    return out


def empirical_threshold_from_sweep(sweep: List[Dict[str, Any]], *,
                                   giant_onset_frac: float = 0.01) -> Dict[str, Any]:
    """Estimate the empirical epidemic threshold two ways from a T-sweep.

      * SUSCEPTIBILITY peak: the T that maximizes the mean second-largest-cluster
        fraction (the standard percolation susceptibility probe peaks at the threshold).
      * GIANT ONSET: the smallest T whose mean giant fraction first exceeds a small
        floor ``giant_onset_frac`` (giant cluster becomes O(N)); we linearly interpolate
        between the last sub-floor and first super-floor grid points for a sharper
        estimate.

    Returns both estimates (and the grid points used).
    """
    if not sweep:
        return {"T_c_susceptibility": float("nan"), "T_c_giant_onset": float("nan")}
    # susceptibility peak
    peak = max(sweep, key=lambda row: row["mean_second_fraction"])
    T_susc = peak["T"]
    # giant onset with linear interpolation across the crossing
    T_onset = float("nan")
    prev = None
    for row in sweep:
        if row["mean_giant_fraction"] >= giant_onset_frac:
            if prev is None:
                T_onset = row["T"]
            else:
                # interpolate where the mean giant fraction crosses the floor
                t0, f0 = prev["T"], prev["mean_giant_fraction"]
                t1, f1 = row["T"], row["mean_giant_fraction"]
                if f1 > f0:
                    frac = (giant_onset_frac - f0) / (f1 - f0)
                    T_onset = t0 + frac * (t1 - t0)
                else:
                    T_onset = row["T"]
            break
        prev = row
    return {
        "T_c_susceptibility": T_susc,
        "T_c_giant_onset": T_onset,
        "giant_onset_frac_floor": giant_onset_frac,
    }
