"""
ABM Auto Runtime — Topology adapters for Network construction.

A **Topology** is a pure callable that constructs a graph on n nodes given a
seeded RNG, decoupled from how the graph is stored or traversed:

    Topology = Callable[[int, random.Random], "networkx.Graph"]

This module ships five built-in adapters covering the topologies LLM-generated
research models actually use. The most important is `netlogo_spatially_clustered`
— it replicates NetLogo's `setup-spatially-clustered-network` algorithm
bit-for-bit (iterative random-node → nearest-non-neighbor linking, no per-node
degree cap, terminating at n*avg_degree/2 total edges), enabling faithful
reproduction of BEHAVE 2025-style benchmarks.

Determinism contract: every adapter must consume randomness ONLY from its `rng`
argument. Calls to the global `random` module break the seam's reproducibility
guarantee.
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    import networkx as nx

Topology = Callable[[int, random.Random], "nx.Graph"]


def melodie_named(name: str, **params) -> Topology:
    """Wrap any networkx generator as a Topology.

    Escape hatch: anything networkx ships works through here. The wrapper
    converts our `random.Random` to the int seed networkx expects, ensuring
    determinism flows through.

    Example::

        topology = melodie_named("random_geometric_graph", radius=0.113)
    """
    def build(n: int, rng: random.Random) -> "nx.Graph":
        import networkx as nx
        kwargs = dict(params)
        if "seed" not in kwargs:
            kwargs["seed"] = rng.randrange(2**32)
        return getattr(nx, name)(n, **kwargs)
    return build


def netlogo_spatially_clustered(avg_degree: int) -> Topology:
    """NetLogo `setup-spatially-clustered-network`, faithful port.

    Algorithm (from NetLogo Models Library, Virus on a Network)::

        target_edges = n * avg_degree / 2
        while edge_count < target_edges:
            node = random_turtle()                       # pick random EACH iteration
            choice = nearest_non_neighbor(node)          # by 2D Euclidean distance
            if choice exists: link(node, choice)

    Key fidelity points vs naive implementations:
      - Node is re-picked at random every iteration (NOT iterated in order).
      - No per-node degree cap — a node can accumulate >>avg_degree edges if
        repeatedly picked. This produces a high-variance degree distribution
        characteristic of NetLogo's algorithm.
      - Loop terminates on total-edge count, not on per-node degree.

    Positions are sampled uniformly in [0,1]^2 from `rng`.
    """
    def build(n: int, rng: random.Random) -> "nx.Graph":
        import networkx as nx
        positions = [(rng.random(), rng.random()) for _ in range(n)]
        G = nx.Graph()
        G.add_nodes_from(range(n))
        target = (avg_degree * n) // 2
        while G.number_of_edges() < target:
            node = rng.randrange(n)
            non_neighbors = [
                m for m in range(n)
                if m != node and not G.has_edge(node, m)
            ]
            if not non_neighbors:
                continue
            nx_, ny_ = positions[node]
            nearest = min(
                non_neighbors,
                key=lambda m: (positions[m][0] - nx_) ** 2 + (positions[m][1] - ny_) ** 2,
            )
            G.add_edge(node, nearest)
        return G
    return build


def watts_strogatz(k: int, p: float) -> Topology:
    """Small-world graph: each node connected to k neighbors, then rewired with prob p."""
    return melodie_named("watts_strogatz_graph", k=k, p=p)


def erdos_renyi(p: float) -> Topology:
    """Random graph: each possible edge present with independent probability p."""
    return melodie_named("erdos_renyi_graph", p=p)


def barabasi_albert(m: int) -> Topology:
    """Scale-free graph by preferential attachment, m edges added per new node."""
    return melodie_named("barabasi_albert_graph", m=m)


__all__ = [
    "Topology",
    "melodie_named",
    "netlogo_spatially_clustered",
    "watts_strogatz",
    "erdos_renyi",
    "barabasi_albert",
]
