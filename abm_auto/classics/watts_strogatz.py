"""Watts & Strogatz (1998) small-world networks — a faithful NETWORK-GENERATION
reproduction (NOT an agent-stepping ABM).

Source: Watts, D.J. & Strogatz, S.H. (1998) "Collective dynamics of 'small-world'
networks", Nature 393:440-442. doi:10.1038/30918.

Honesty note (binds the FINDINGS): this is a network-GENERATION model, not an
agent-based model. There are no agents stepping on the neutral platform here; the
contribution is a faithful structural reproduction of the Watts-Strogatz small-world
result under the same lock-first + honest-verdict + L3-bundle discipline as the
agent-based reproductions.

Construction (verified against the paper):
  * Start from a ring lattice on ``n`` nodes where every node is joined to its ``k``
    nearest neighbours (k/2 on each side); k is even. For n=1000, k=10.
  * Rewire: with probability ``p`` each edge of the ring is rewired — one endpoint is
    moved to a uniformly-chosen node, forbidding self-loops and duplicate edges. p=0 is
    the pristine lattice; p=1 is (essentially) a random graph. This is exactly
    networkx ``watts_strogatz_graph(n, k, p, seed)``, which implements the WS rewiring
    rule; we use it as the canonical reference generator.

Outcomes (the LOCKED grading metrics):
  * L(p) = characteristic path length = average shortest-path length on the LARGEST
    connected component (rewiring can disconnect the graph, so we measure the giant
    component, the standard WS convention).
  * C(p) = clustering coefficient = networkx average clustering (transitivity-style
    local clustering averaged over nodes).
  Each is normalised to the p=0 lattice values L0, C0 → L(p)/L0 and C(p)/C0.

Determinism: every quantity is a pure function of (n, k, p, seed). The runner averages
over a FIXED set of seeds and reports variance.
"""
from __future__ import annotations

from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Sequence

import networkx as nx


# -- graph construction -------------------------------------------------------

def build_ws_graph(n: int, k: int, p: float, *, seed: int) -> nx.Graph:
    """Watts-Strogatz small-world graph: ring lattice (n nodes, degree k) with each
    edge rewired with probability p. Pure function of (n, k, p, seed).

    p=0 returns the pristine ring lattice; p=1 is essentially a random graph. Uses
    networkx ``watts_strogatz_graph`` (the canonical WS rewiring rule)."""
    if k % 2 != 0:
        raise ValueError(f"k must be even (k/2 neighbours per side); got k={k}")
    return nx.watts_strogatz_graph(n, k, p, seed=seed)


# -- structural metrics -------------------------------------------------------

def giant_component(graph: nx.Graph) -> nx.Graph:
    """Return the subgraph induced by the largest connected component."""
    if graph.number_of_nodes() == 0:
        return graph
    nodes = max(nx.connected_components(graph), key=len)
    return graph.subgraph(nodes).copy()


def characteristic_path_length(graph: nx.Graph) -> float:
    """L = average shortest-path length on the LARGEST connected component.

    Rewiring can (rarely, at small p) disconnect a node; the WS convention measures L on
    the giant component so L stays finite. For a connected graph this is exactly
    networkx ``average_shortest_path_length``."""
    if graph.number_of_nodes() <= 1:
        return 0.0
    if nx.is_connected(graph):
        return nx.average_shortest_path_length(graph)
    gc = giant_component(graph)
    if gc.number_of_nodes() <= 1:
        return 0.0
    return nx.average_shortest_path_length(gc)


def clustering_coefficient(graph: nx.Graph) -> float:
    """C = average local clustering coefficient over all nodes (networkx
    ``average_clustering``)."""
    if graph.number_of_nodes() == 0:
        return 0.0
    return nx.average_clustering(graph)


def metrics_for(n: int, k: int, p: float, *, seed: int) -> Dict[str, float]:
    """Build the WS graph for (n, k, p, seed) and return its raw L and C plus the
    giant-component size (so the runner can report disconnection)."""
    g = build_ws_graph(n, k, p, seed=seed)
    gc = giant_component(g)
    return {
        "p": p,
        "seed": seed,
        "L": characteristic_path_length(g),
        "C": clustering_coefficient(g),
        "giant_fraction": gc.number_of_nodes() / n if n else 0.0,
    }


# -- seed-averaged sweep ------------------------------------------------------

def run_many_seeds(n: int, k: int, p: float, *, seeds: Sequence[int]) -> Dict[str, Any]:
    """Build the WS graph for each seed at rewiring probability p and average L and C.

    Deterministic: each seed produces a fixed graph. Returns mean + population stdev of
    L and C over the seeds, plus the per-seed raw values (for results.json)."""
    per_seed: List[Dict[str, float]] = [metrics_for(n, k, p, seed=s) for s in seeds]
    Ls = [r["L"] for r in per_seed]
    Cs = [r["C"] for r in per_seed]
    giants = [r["giant_fraction"] for r in per_seed]
    return {
        "p": p,
        "n": n,
        "k": k,
        "seeds": list(seeds),
        "L_mean": mean(Ls),
        "L_std": pstdev(Ls) if len(Ls) > 1 else 0.0,
        "C_mean": mean(Cs),
        "C_std": pstdev(Cs) if len(Cs) > 1 else 0.0,
        "giant_fraction_mean": mean(giants),
        "per_seed": per_seed,
    }


def sweep(n: int, k: int, p_grid: Sequence[float], *, seeds: Sequence[int]) -> List[Dict[str, Any]]:
    """Run the full p-grid; one seed-averaged summary dict per p (ascending p order as
    given)."""
    return [run_many_seeds(n, k, p, seeds=seeds) for p in p_grid]


def normalize_to_lattice(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach L/L0 and C/C0 to each row, normalised to the p=0 lattice values L0, C0.

    L0, C0 are taken from the row whose p == 0.0 (must be present; it is the lattice
    baseline the WS curves are normalised against)."""
    base = next((r for r in rows if r["p"] == 0.0), None)
    if base is None:
        raise ValueError("p-grid must contain p=0.0 (the lattice baseline L0, C0)")
    L0 = base["L_mean"]
    C0 = base["C_mean"]
    out: List[Dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        row["L0"] = L0
        row["C0"] = C0
        row["L_over_L0"] = (r["L_mean"] / L0) if L0 else 0.0
        row["C_over_C0"] = (r["C_mean"] / C0) if C0 else 0.0
        out.append(row)
    return out


def first_p_below_half(rows: Sequence[Dict[str, Any]], key: str) -> Optional[float]:
    """The smallest p (in grid order) at which the normalised ratio ``key``
    (``'L_over_L0'`` or ``'C_over_C0'``) first drops below 0.5. None if it never does.

    Rows are assumed in ascending p order."""
    for r in rows:
        if r[key] < 0.5:
            return r["p"]
    return None
