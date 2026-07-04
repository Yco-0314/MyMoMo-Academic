"""Erdos-Renyi giant component — a faithful network-GENERATION reproduction.

Source: Erdos, P. & Renyi, A. (1960) "On the evolution of random graphs",
Publ. Math. Inst. Hungar. Acad. Sci. 5:17-61.

IMPORTANT (honesty, binds the FINDINGS): this is a network-GENERATION model, NOT an
agent-stepping ABM. There are no agents, no scheduler, no ticks. We draw a random
graph G(n, p) and measure a static structural property (the largest connected
component). It is reproduced faithfully as a network-science result; the lock-first +
honest-verdict + L3-bundle discipline still fully applies.

Rules (the classic ER ensemble):
  * G(n, p): n vertices, each of the n(n-1)/2 possible edges present independently
    with probability p. Mean degree z = p(n - 1). We build with networkx
    ``gnm_random_graph`` (the G(n, m) model with m = round(z*n/2)) so the mean degree
    z = 2m/n is controlled EXACTLY rather than in expectation — the two ensembles are
    asymptotically equivalent and gnm removes one source of seed-to-seed degree noise.
  * Outcome = fraction of nodes in the largest connected component.
  * Theoretical giant fraction S solves the self-consistency S = 1 - exp(-z * S),
    iterated to convergence (the surviving root; S = 0 below z = 1).
  * Deterministic given a seed.
"""
from __future__ import annotations

import math
import statistics
from typing import Any, Dict, List

import networkx as nx


# -- graph construction + measurement -----------------------------------------

def edges_for_mean_degree(n: int, z: float) -> int:
    """Number of edges m giving mean degree z exactly (z = 2m/n), clamped to the
    [0, n(n-1)/2] feasible range."""
    if n <= 0:
        return 0
    m = int(round(z * n / 2.0))
    return max(0, min(m, n * (n - 1) // 2))


def build_graph(n: int, z: float, *, seed: int) -> nx.Graph:
    """Erdos-Renyi graph with n nodes and mean degree z.

    Uses ``gnm_random_graph`` so the realised mean degree z = 2m/n is exact (no
    seed-to-seed fluctuation in the edge count). Nodes are 0..n-1. Deterministic
    given ``seed``.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if z < 0:
        raise ValueError("z (mean degree) must be non-negative")
    m = edges_for_mean_degree(n, z)
    return nx.gnm_random_graph(n, m, seed=seed)


def largest_component_fraction(graph: nx.Graph) -> float:
    """Fraction of nodes in the largest connected component (0 for an empty graph)."""
    n = graph.number_of_nodes()
    if n == 0:
        return 0.0
    if graph.number_of_edges() == 0:
        return 1.0 / n  # every node isolated; the "largest" component is a single node
    largest = max(len(c) for c in nx.connected_components(graph))
    return largest / n


def theoretical_S(z: float, *, tol: float = 1e-12, max_iter: int = 100_000) -> float:
    """Theoretical giant-component fraction S, the surviving root of the
    self-consistency S = 1 - exp(-z * S).

    For z <= 1 the only root in [0, 1] is S = 0 (no giant component). For z > 1 a
    second root in (0, 1) exists and is the giant fraction; we reach it by fixed-point
    iteration S <- 1 - exp(-z*S) starting from S = 1 (which converges DOWN to the
    surviving root, never to the unstable S = 0). Iterated to convergence.
    """
    if z <= 1.0:
        return 0.0
    s = 1.0
    for _ in range(max_iter):
        nxt = 1.0 - math.exp(-z * s)
        if abs(nxt - s) < tol:
            return nxt
        s = nxt
    return s


# -- sweep helpers ------------------------------------------------------------

def run_many_seeds(n: int, z: float, *, n_seeds: int = 10,
                   seed_base: int = 0) -> Dict[str, Any]:
    """Draw ``n_seeds`` ER graphs at mean degree z and summarise the largest-component
    fraction (mean + variance + per-seed list). Deterministic: trial ``i`` uses graph
    seed ``seed_base + i``.
    """
    fractions: List[float] = []
    for i in range(n_seeds):
        graph = build_graph(n, z, seed=seed_base + i)
        fractions.append(largest_component_fraction(graph))
    mean = statistics.fmean(fractions) if fractions else 0.0
    variance = statistics.pvariance(fractions) if len(fractions) > 1 else 0.0
    return {
        "z": z,
        "n": n,
        "n_seeds": n_seeds,
        "m_edges": edges_for_mean_degree(n, z),
        "fractions": fractions,
        "mean_fraction": mean,
        "variance": variance,
        "stdev": math.sqrt(variance),
        "min_fraction": min(fractions) if fractions else 0.0,
        "max_fraction": max(fractions) if fractions else 0.0,
        "theoretical_S": theoretical_S(z),
    }


def sweep(n: int, z_grid: List[float], *, n_seeds: int = 10,
          seed_base: int = 0) -> List[Dict[str, Any]]:
    """Run the full z-grid; one summary dict per z."""
    return [run_many_seeds(n, z, n_seeds=n_seeds, seed_base=seed_base) for z in z_grid]
