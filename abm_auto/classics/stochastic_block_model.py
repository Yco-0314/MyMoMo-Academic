"""Two-block stochastic block model and Bethe-Hessian detectability test.

This module reproduces the Decelle-Krzakala-Moore-Zdeborova detectability setup:
two equal planted groups, average degree c, within/between rates c_in/N and c_out/N,
and a spectral detector that does not receive the planted labels.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List

import networkx as nx
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import eigsh


@dataclass(frozen=True)
class GraphSample:
    adjacency: sp.csr_matrix
    labels: List[int]
    mean_degree: float
    n_edges: int


def detectability_threshold_epsilon(*, c: float) -> float:
    if c <= 0:
        raise ValueError("c must be positive")
    root = math.sqrt(c)
    return (root - 1.0) / (root + 1.0)


def sbm_cin_cout(*, c: float, epsilon: float) -> tuple[float, float]:
    if c <= 0:
        raise ValueError("c must be positive")
    if epsilon < 0:
        raise ValueError("epsilon must be non-negative")
    cin = 2.0 * c / (1.0 + epsilon)
    cout = epsilon * cin
    return cin, cout


def _to_csr(graph: nx.Graph, n: int) -> sp.csr_matrix:
    return nx.to_scipy_sparse_array(graph, nodelist=list(range(n)), format="csr", dtype=float)


def generate_sbm(*, n: int, c: float, epsilon: float, seed: int) -> GraphSample:
    if n <= 1 or n % 2 != 0:
        raise ValueError("n must be an even integer > 1")
    cin, cout = sbm_cin_cout(c=c, epsilon=epsilon)
    sizes = [n // 2, n // 2]
    probs = [[cin / n, cout / n], [cout / n, cin / n]]
    graph = nx.stochastic_block_model(sizes, probs, seed=seed, sparse=True)
    adjacency = _to_csr(graph, n)
    n_edges = graph.number_of_edges()
    labels = [0] * (n // 2) + [1] * (n // 2)
    return GraphSample(
        adjacency=adjacency,
        labels=labels,
        mean_degree=2.0 * n_edges / n,
        n_edges=n_edges,
    )


def generate_matched_er(*, n: int, mean_degree: float, seed: int) -> GraphSample:
    if n <= 1:
        raise ValueError("n must be > 1")
    p = mean_degree / max(1, n - 1)
    graph = nx.fast_gnp_random_graph(n, p, seed=seed)
    adjacency = _to_csr(graph, n)
    n_edges = graph.number_of_edges()
    return GraphSample(
        adjacency=adjacency,
        labels=[0] * (n // 2) + [1] * (n - n // 2),
        mean_degree=2.0 * n_edges / n,
        n_edges=n_edges,
    )


def bethe_hessian_detect(adjacency: sp.csr_matrix, *, average_degree: float) -> List[int]:
    """Return a balanced two-way partition from the Bethe-Hessian informative vector.

    H(r) = (r^2 - 1)I - rA + D, with r=sqrt(c). The lowest algebraic eigenvector is
    thresholded at its median so the returned partition is balanced and label-free.
    """
    n = adjacency.shape[0]
    if n == 0:
        return []
    r = math.sqrt(max(average_degree, 1.000001))
    degrees = np.asarray(adjacency.sum(axis=1)).ravel()
    hessian = sp.diags((r * r - 1.0) + degrees, format="csr") - (r * adjacency)
    k = 2 if n > 2 else 1
    v0 = np.linspace(-1.0, 1.0, n)
    vals, vecs = eigsh(
        hessian, k=k, which="SA", tol=1e-3, maxiter=max(500, 5 * n), v0=v0
    )
    order = np.argsort(vals)
    negative = [idx for idx in order if vals[idx] < 0.0]
    # In sparse graphs the most negative vector is often localized. For the
    # assortative two-block signal the second negative vector is the informative
    # community direction when it exists.
    chosen = negative[1] if len(negative) >= 2 else order[0]
    vector = vecs[:, chosen]
    median = float(np.median(vector))
    labels = [1 if x >= median else 0 for x in vector]
    return labels


def overlap_score(truth: List[int], predicted: List[int]) -> float:
    if len(truth) != len(predicted):
        raise ValueError("truth and predicted must have the same length")
    if not truth:
        return 0.0
    acc = sum(1 for a, b in zip(truth, predicted) if a == b) / len(truth)
    best = max(acc, 1.0 - acc)
    return max(0.0, 2.0 * best - 1.0)


def run_sbm_detection(*, n: int, c: float, epsilon: float, seed: int) -> Dict[str, Any]:
    sample = generate_sbm(n=n, c=c, epsilon=epsilon, seed=seed)
    predicted = bethe_hessian_detect(sample.adjacency, average_degree=sample.mean_degree)
    return {
        "n": n,
        "c": c,
        "epsilon": epsilon,
        "seed": seed,
        "mean_degree": sample.mean_degree,
        "n_edges": sample.n_edges,
        "overlap": overlap_score(sample.labels, predicted),
    }
