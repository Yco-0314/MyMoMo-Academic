"""Cont-Bouchaud percolation market (Cont & Bouchaud 2000) — a faithful
network-GENERATION + trading reproduction.

Source: Cont, R. & Bouchaud, J.-P. (2000). "Herd behavior and aggregate
fluctuations in financial markets." Macroeconomic Dynamics 4:170-196.
doi:10.1017/S1365100500015029.

IMPORTANT (honesty, binds the FINDINGS): this is a network-GENERATION
(percolation) + trading model. The GENERATION half is an Erdos-Renyi random
graph whose connected clusters are the traders; the TRADING half is the
per-step activation of clusters into a signed aggregate return. There is no
per-agent scheduler stepping autonomous state — the aggregate return is a
sum over clusters. It is reproduced faithfully; the lock-first + honest-verdict
+ L3-bundle discipline fully applies.

The model (Cont-Bouchaud 2000):

  * N agents are the nodes of an Erdos-Renyi random graph G(N, p) with connection
    probability p = c/N (so the mean degree is c). Two agents linked (directly or
    transitively) belong to the same CLUSTER; a cluster is a connected component of
    the graph and acts as a SINGLE trader (herd) — all its members trade together.

  * At each trading step, each cluster is INDEPENDENTLY active with probability a.
    An active cluster of size s either BUYS (+1 per member) or SELLS (-1 per member)
    with equal probability (a fair coin, one coin per cluster). Inactive clusters do
    nothing. The aggregate excess demand / return that step is

        r = sum over ACTIVE clusters of ( sign * cluster_size ),   sign in {+1, -1}.

  * At the PERCOLATION THRESHOLD c = 1 the cluster-size distribution is a power law
    (critical percolation), so a handful of macroscopic clusters can dominate a step:
    aggregating their signed sizes yields FAT-TAILED (excess-kurtosis) returns — the
    stylized fact of real markets. Away from criticality (c << 1, all clusters tiny)
    or at high activity a (many independent clusters active, central-limit averaging),
    the return distribution is near-Gaussian. Small activity a at c = 1 is the herding
    regime that produces the fat tail.

Design (efficiency): we build ONE Erdos-Renyi graph per seed and find its connected
components ONCE with union-find (a single O(E * alpha(N)) pass, NOT a BFS per node);
the component SIZES are then a fixed multiset for that graph. Each trading step only
re-draws the per-cluster activity (Bernoulli(a)) and sign (fair coin) and sums the
signed active sizes — O(#clusters) per step. Collecting >=1e4-1e5 return samples over
a large N graph is therefore fast. Returns are STANDARDIZED (subtract mean, divide by
std) before all tail / kurtosis statistics, exactly as the lock requires.

The near-Gaussian CONTROL is the SAME machinery with only the regime changed
(large activity a, or c << 1 well below threshold); nothing else — N, seeds, sample
count, the standardization, the statistics — differs. That isolates "the percolation
clustering at criticality is what makes the tail fat".
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Sequence, Tuple


# -- union-find (disjoint set) ------------------------------------------------

class UnionFind:
    """Disjoint-set forest with path compression + union by size. Grows the connected
    components of the Erdos-Renyi graph in a single O(E * alpha(N)) pass — NOT a
    BFS-per-node."""

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


# -- Erdos-Renyi graph -> cluster sizes ---------------------------------------

def cluster_sizes(n: int, c: float, *, rng: random.Random) -> List[int]:
    """Connected-component (cluster) SIZES of an Erdos-Renyi graph G(N, p=c/N).

    Each of the N(N-1)/2 possible edges is present independently with probability
    p = c / N (mean degree c). We draw the edges and union their endpoints, then read
    the component sizes off the union-find roots. Deterministic given ``rng``.

    Efficiency: rather than testing all N(N-1)/2 pairs (O(N^2)), we sample the number
    of edges m ~ Binomial(N(N-1)/2, p) and then draw m distinct endpoint pairs — the
    expected m = c*N/2 is O(N) at c = O(1), so building the graph is O(N). This is the
    exact G(N, p) ensemble (each pair present independently w.p. p) realized by first
    drawing the edge COUNT and then a uniform edge SET of that size.
    """
    if n <= 0:
        raise ValueError(f"need n > 0 (got {n})")
    if c < 0:
        raise ValueError(f"need c >= 0 (got {c})")
    max_edges = n * (n - 1) // 2
    p = c / n if n > 0 else 0.0
    if p >= 1.0:
        m = max_edges
    else:
        # Number of present edges ~ Binomial(max_edges, p). rng-driven, deterministic.
        m = _binomial(max_edges, p, rng)
    uf = UnionFind(n)
    drawn = 0
    seen: set = set()
    # Draw m distinct unordered pairs uniformly. At c = O(1), m ~ c*N/2 << max_edges,
    # so rejection of the rare repeat is cheap; union only distinct pairs.
    while drawn < m:
        a = rng.randrange(n)
        b = rng.randrange(n)
        if a == b:
            continue
        key = (a, b) if a < b else (b, a)
        if key in seen:
            continue
        seen.add(key)
        uf.union(a, b)
        drawn += 1
    # component sizes from the roots
    sizes: List[int] = []
    for i in range(n):
        if uf.parent[i] == i:
            sizes.append(uf.size[i])
    return sizes


def _binomial(trials: int, p: float, rng: random.Random) -> int:
    """One Binomial(trials, p) draw. Uses a normal approximation for large trials*p
    (fast, adequate for the edge COUNT of a large sparse graph where trials ~ N^2/2
    but the mean m = trials*p ~ c*N/2 is O(N)), and exact Bernoulli summation only for
    tiny cases. Deterministic given ``rng``.

    The normal approximation is used ONLY to pick how many edges to draw; the graph
    ensemble itself (a uniform random edge set of that size) is exact. At N >= 1e4 the
    relative error of the count is O(1/sqrt(m)) and does not move c = 2m/N off its
    target materially (we also report the realized c)."""
    if trials <= 0 or p <= 0.0:
        return 0
    if p >= 1.0:
        return trials
    mean = trials * p
    if trials <= 1000:
        # exact
        return sum(1 for _ in range(trials) if rng.random() < p)
    var = trials * p * (1.0 - p)
    val = int(round(rng.gauss(mean, math.sqrt(var))))
    return max(0, min(trials, val))


# -- return sampling (the trading half) ---------------------------------------

def sample_returns(sizes: Sequence[int], a: float, n_steps: int, *,
                   rng: random.Random) -> List[float]:
    """Draw ``n_steps`` aggregate returns from a FIXED cluster-size multiset.

    Each step: each cluster is active with probability ``a`` (independent Bernoulli),
    and each ACTIVE cluster contributes ``+size`` or ``-size`` with equal probability
    (a fair coin per active cluster). The step's return is the sum of those signed
    active sizes. Deterministic given ``rng``.
    """
    if not 0.0 <= a <= 1.0:
        raise ValueError(f"activity a must be in [0, 1] (got {a})")
    if n_steps <= 0:
        raise ValueError(f"n_steps must be positive (got {n_steps})")
    sizes = list(sizes)
    returns: List[float] = []
    for _ in range(n_steps):
        r = 0
        for s in sizes:
            if rng.random() < a:
                r += s if rng.random() < 0.5 else -s
        returns.append(float(r))
    return returns


# -- standardization + tail / kurtosis statistics -----------------------------

def standardize(returns: Sequence[float]) -> List[float]:
    """Subtract the mean and divide by the (population) standard deviation. Returns a
    list of zeros if the std is zero (a degenerate all-equal series)."""
    n = len(returns)
    if n == 0:
        return []
    mean = sum(returns) / n
    var = sum((x - mean) ** 2 for x in returns) / n
    std = math.sqrt(var)
    if std == 0.0:
        return [0.0] * n
    return [(x - mean) / std for x in returns]


def excess_kurtosis(returns: Sequence[float]) -> float:
    """Excess kurtosis (fourth standardized moment minus 3) of a sample. 0 for a
    Gaussian; > 0 for a fat-tailed (leptokurtic) distribution. Computed on the raw
    values (it is scale-invariant, so standardizing first does not change it). Returns
    0.0 for a degenerate zero-variance sample."""
    n = len(returns)
    if n == 0:
        return 0.0
    mean = sum(returns) / n
    m2 = sum((x - mean) ** 2 for x in returns) / n
    if m2 == 0.0:
        return 0.0
    m4 = sum((x - mean) ** 4 for x in returns) / n
    return m4 / (m2 * m2) - 3.0


def tail_prob(std_returns: Sequence[float], k: float) -> float:
    """Empirical P(|r| > k) for STANDARDIZED returns (units of sigma). k is in sigma."""
    n = len(std_returns)
    if n == 0:
        return 0.0
    return sum(1 for x in std_returns if abs(x) > k) / n


def gaussian_tail_prob(k: float) -> float:
    """P(|Z| > k) for a standard normal Z = 2 * (1 - Phi(k)) = erfc(k / sqrt(2))."""
    return math.erfc(k / math.sqrt(2.0))


def tail_exponent(std_returns: Sequence[float], *, q_lo: float = 0.90,
                  q_hi: float = 0.999) -> float:
    """Estimate a power-law tail exponent alpha of the return magnitudes via a
    Hill-style log-log fit of the empirical complementary CDF over an upper quantile
    band.

    We take |r| for the standardized returns, sort them, and over the magnitudes lying
    between the ``q_lo`` and ``q_hi`` quantiles fit  log P(|r| > x) ~ -alpha * log x  by
    ordinary least squares; alpha is the negated slope. This is a coarse but robust
    tail-index estimate (a straight line on a log-log CCDF plot). Returns NaN if fewer
    than a handful of tail points are available."""
    n = len(std_returns)
    if n == 0:
        return float("nan")
    mags = sorted(abs(x) for x in std_returns)
    lo_i = int(q_lo * n)
    hi_i = int(q_hi * n)
    hi_i = min(hi_i, n - 1)
    if hi_i - lo_i < 5:
        return float("nan")
    xs: List[float] = []
    ys: List[float] = []
    for i in range(lo_i, hi_i + 1):
        x = mags[i]
        if x <= 0.0:
            continue
        # empirical CCDF at this magnitude: fraction of sample with |r| > x = (n-1-i)/n
        ccdf = (n - 1 - i) / n
        if ccdf <= 0.0:
            continue
        xs.append(math.log(x))
        ys.append(math.log(ccdf))
    if len(xs) < 5:
        return float("nan")
    # OLS slope of ys on xs
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0.0:
        return float("nan")
    slope = sxy / sxx
    return -slope   # alpha = -slope of log-CCDF vs log-magnitude


# -- one regime (graph + return sampling + statistics) ------------------------

def run_regime(n: int, c: float, a: float, *, n_steps: int, seed: int) -> Dict[str, Any]:
    """One regime: build one ER graph at connectivity c (seed), find its clusters, draw
    ``n_steps`` aggregate returns at activity a, standardize, and compute the locked
    statistics (excess kurtosis, tail probabilities at 3 and 5 sigma, tail exponent).

    Deterministic given ``seed``: the graph and the return draws share one seeded RNG
    chain (graph first, then trading), so a re-run reproduces every number.
    """
    rng = random.Random(seed)
    sizes = cluster_sizes(n, c, rng=rng)
    returns = sample_returns(sizes, a, n_steps, rng=rng)
    std = standardize(returns)
    n_clusters = len(sizes)
    largest = max(sizes) if sizes else 0
    # The realized mean degree is not recoverable from the cluster sizes alone; we
    # report the target c and the largest-cluster fraction (the percolation order
    # parameter) instead.
    return {
        "n": n,
        "c": c,
        "a": a,
        "n_steps": n_steps,
        "seed": seed,
        "n_clusters": n_clusters,
        "largest_cluster": largest,
        "largest_cluster_fraction": largest / n if n else 0.0,
        "mean_cluster_size": (sum(sizes) / n_clusters) if n_clusters else 0.0,
        "excess_kurtosis": excess_kurtosis(returns),
        "p_gt_3sigma": tail_prob(std, 3.0),
        "p_gt_5sigma": tail_prob(std, 5.0),
        "tail_exponent": tail_exponent(std),
        "return_std": (sum((x - (sum(returns) / len(returns))) ** 2 for x in returns)
                       / len(returns)) ** 0.5 if returns else 0.0,
    }


def run_many_seeds(n: int, c: float, a: float, *, n_steps: int, n_seeds: int,
                   seed_base: int = 0) -> Dict[str, Any]:
    """Run ``n_seeds`` independent regimes (graph seed ``seed_base + i``) at (c, a) and
    POOL their standardized returns for the tail statistics, while reporting the excess
    kurtosis both pooled and per-seed (mean + spread across seeds).

    Pooling many seeds' returns gives a large sample for the heavy-tail probabilities
    (P(|r|>3sigma), P(|r|>5sigma)) without any single graph dominating; the per-seed
    kurtosis spread shows the fat tail is a robust property of the ensemble, not one
    lucky graph. Deterministic given ``seed_base``.
    """
    per_seed: List[Dict[str, Any]] = []
    pooled_std: List[float] = []
    for i in range(n_seeds):
        seed = seed_base + i
        rng = random.Random(seed)
        sizes = cluster_sizes(n, c, rng=rng)
        returns = sample_returns(sizes, a, n_steps, rng=rng)
        std = standardize(returns)
        pooled_std.extend(std)
        per_seed.append({
            "seed": seed,
            "n_clusters": len(sizes),
            "largest_cluster": max(sizes) if sizes else 0,
            "largest_cluster_fraction": (max(sizes) / n) if (sizes and n) else 0.0,
            "excess_kurtosis": excess_kurtosis(returns),
            "p_gt_3sigma": tail_prob(std, 3.0),
            "p_gt_5sigma": tail_prob(std, 5.0),
            "return_std": (sum((x - (sum(returns) / len(returns))) ** 2 for x in returns)
                           / len(returns)) ** 0.5 if returns else 0.0,
        })
    kurts = [ps["excess_kurtosis"] for ps in per_seed]
    mean_kurt = sum(kurts) / len(kurts) if kurts else 0.0
    var_kurt = (sum((k - mean_kurt) ** 2 for k in kurts) / len(kurts)) if kurts else 0.0
    large_fracs = [ps["largest_cluster_fraction"] for ps in per_seed]
    return {
        "n": n, "c": c, "a": a, "n_steps": n_steps,
        "n_seeds": n_seeds, "seed_base": seed_base,
        "total_samples": len(pooled_std),
        # excess kurtosis
        "mean_excess_kurtosis": mean_kurt,
        "std_excess_kurtosis": var_kurt ** 0.5,
        "min_excess_kurtosis": min(kurts) if kurts else 0.0,
        "max_excess_kurtosis": max(kurts) if kurts else 0.0,
        "per_seed_excess_kurtosis": kurts,
        # pooled tail statistics
        "pooled_excess_kurtosis": excess_kurtosis(pooled_std),
        "pooled_p_gt_3sigma": tail_prob(pooled_std, 3.0),
        "pooled_p_gt_5sigma": tail_prob(pooled_std, 5.0),
        "pooled_tail_exponent": tail_exponent(pooled_std),
        # percolation order parameter
        "mean_largest_cluster_fraction": sum(large_fracs) / len(large_fracs) if large_fracs else 0.0,
        "mean_n_clusters": sum(ps["n_clusters"] for ps in per_seed) / len(per_seed) if per_seed else 0.0,
        "per_seed": per_seed,
    }


def activity_sweep(n: int, c: float, a_grid: Sequence[float], *, n_steps: int,
                   n_seeds: int, seed_base: int = 0) -> List[Dict[str, Any]]:
    """Sweep the activity ``a`` over a grid at fixed connectivity c, returning one
    ``run_many_seeds`` summary per a. Used for the P3 activity-driven crossover: excess
    kurtosis should decrease monotonically as a rises (herding -> Gaussian)."""
    return [run_many_seeds(n, c, a, n_steps=n_steps, n_seeds=n_seeds,
                           seed_base=seed_base) for a in a_grid]
