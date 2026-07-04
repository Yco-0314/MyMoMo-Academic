"""Watts (2002) global cascades — a faithful agent-based reproduction.

Source: Watts, D.J. (2002) "A simple model of global cascades on random networks",
PNAS 99(9):5766-5771 (open: https://pmc.ncbi.nlm.nih.gov/articles/PMC122850/).

Rules (verified against the paper):
  * Erdos-Renyi random graph G(n, m) with mean degree z (we use ``gnm_random_graph``
    so z = 2m/n is controlled exactly).
  * Every node carries a uniform fixed threshold ``phi`` (default 0.18).
  * A node adopts state 1 iff the FRACTION of its neighbours already in state 1 is
    >= phi. Adoption is monotone (once active, stays active).
  * Degree-0 (isolated) nodes have no neighbours; we treat their active-fraction as
    0, so an isolated node NEVER activates unless it is itself the seed (Watts'
    convention: an isolated vertex cannot be triggered by neighbours).
  * One uniformly-random node is seeded active; the system runs DETERMINISTICALLY to
    a fixed point (a step with no new activations).

A *global cascade* is a final active set that spans a macroscopic fraction of the
graph. Watts shows the size distribution is bimodal (tiny local failures vs
system-spanning cascades), so a fixed cutoff cleanly separates the two modes; the
study uses final active fraction >= 0.10.

Built on the neutral platform (``abm_auto._platform``): each vertex is a
``CascadeAgent`` whose ``step`` applies the local threshold rule; the model drives an
``AgentSet`` scheduler and a ``DataCollector`` (the active-count series) — NOT a
hand-rolled god-loop. Given a seed the whole run is reproducible.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import networkx as nx

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class CascadeAgent(Agent):
    """One vertex. ``active`` is its binary state; ``threshold`` is phi (uniform).

    The local rule is computed against the state at the START of the tick
    (``_next_active`` is staged in ``step`` and committed by the model after every
    agent has stepped), so a tick is a synchronous update — order-independent and
    therefore deterministic regardless of scheduler order.
    """

    def __init__(self, agent_id: int, model: "CascadeModel", *, threshold: float) -> None:
        super().__init__(agent_id, model)
        self.threshold = threshold
        self.active = False
        self._next_active = False

    def neighbor_ids(self) -> List[int]:
        return self.model.neighbors[self.id]

    def active_fraction(self) -> float:
        """Fraction of neighbours currently in state 1. Degree-0 => 0.0 (the node
        cannot be triggered by neighbours it does not have)."""
        nbrs = self.neighbor_ids()
        if not nbrs:
            return 0.0
        agents = self.model.agent_by_id
        n_active = sum(1 for j in nbrs if agents[j].active)
        return n_active / len(nbrs)

    def step(self) -> None:
        """Stage the next state: already-active stays active (monotone); an inactive
        node becomes active iff its active-neighbour FRACTION >= phi."""
        if self.active:
            self._next_active = True
            return
        self._next_active = self.active_fraction() >= self.threshold


# -- Model --------------------------------------------------------------------

class CascadeModel(AgentModel):
    """Drives the threshold cascade on a fixed graph to a fixed point.

    Construct with a networkx graph, a uniform threshold, and the seed node. ``run``
    iterates synchronous threshold updates until no new activations occur, then
    returns a summary dict (final active fraction + size, and the active-count
    series via the DataCollector).
    """

    def __init__(self, graph: nx.Graph, *, phi: float = 0.18, seed_node: int = 0,
                 seed: int = 0, max_steps: Optional[int] = None) -> None:
        super().__init__(seed=seed, schedule="sequential")
        self.graph = graph
        self.phi = phi
        self.seed_node = seed_node
        self.n = graph.number_of_nodes()
        self.max_steps = max_steps if max_steps is not None else self.n + 2

        # Adjacency snapshot keyed by node id (stable, integer node labels).
        self.neighbors: Dict[int, List[int]] = {
            node: list(graph.neighbors(node)) for node in graph.nodes()
        }
        self.agent_by_id: Dict[int, CascadeAgent] = {}
        for node in graph.nodes():
            agent = CascadeAgent(node, self, threshold=phi)
            self.agent_by_id[node] = agent
            self.add_agent(agent)

        # Seed exactly one node active.
        self.agent_by_id[seed_node].active = True

        self.reporter = DataCollector({"active": lambda m: m.active_count()})

    # -- metrics --
    def active_count(self) -> int:
        return sum(1 for a in self.agent_by_id.values() if a.active)

    def active_fraction(self) -> float:
        return self.active_count() / self.n if self.n else 0.0

    # -- tick --
    def step(self) -> None:
        """One synchronous threshold update: every agent stages its next state, then
        the model commits all states at once and records the new active count."""
        self.agents.step()                       # each agent stages _next_active
        new_activations = 0
        for a in self.agent_by_id.values():
            if a._next_active and not a.active:
                new_activations += 1
            a.active = a._next_active
        self.t += 1
        self._new_activations = new_activations
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate to a fixed point; return the run summary."""
        self.reporter.collect(self)              # t=0 baseline (just the seed)
        self._new_activations = 0
        for _ in range(self.max_steps):
            self.step()
            if self._new_activations == 0:
                break
        final_size = self.active_count()
        return {
            "final_active_count": final_size,
            "final_active_fraction": final_size / self.n if self.n else 0.0,
            "n": self.n,
            "phi": self.phi,
            "seed_node": self.seed_node,
            "steps": self.t,
            "active_series": self.reporter.series("active"),
        }


# -- graph + sweep helpers ----------------------------------------------------

def build_er_graph(n: int, z: float, *, seed: int) -> nx.Graph:
    """Erdos-Renyi graph with n nodes and mean degree z, built with
    ``gnm_random_graph`` so z = 2m/n is controlled exactly. Nodes are 0..n-1."""
    m = int(round(z * n / 2.0))
    m = max(0, min(m, n * (n - 1) // 2))
    return nx.gnm_random_graph(n, m, seed=seed)


def run_single(graph: nx.Graph, *, phi: float = 0.18, seed_node: int = 0) -> Dict[str, Any]:
    """One cascade on a given graph from a given seed node."""
    return CascadeModel(graph, phi=phi, seed_node=seed_node).run()


def run_many_seeds(n: int, z: float, *, phi: float = 0.18, n_seeds: int = 100,
                   cascade_cutoff: float = 0.10, graph_seed_base: int = 0,
                   fresh_graph_per_seed: bool = True) -> Dict[str, Any]:
    """Run ``n_seeds`` cascades at mean degree z and summarise.

    Faithful to Watts' Monte-Carlo: each trial draws a fresh ER graph AND a fresh
    random seed node (this samples over both graph and seed-placement randomness, the
    standard ensemble). Deterministic: trial ``i`` uses graph seed ``graph_seed_base
    + i`` and seed node ``i % n`` (a spread of distinct seed nodes). Returns the
    global-cascade frequency (final active fraction >= cutoff) and the list of final
    sizes (for the size distribution).
    """
    sizes: List[float] = []
    n_cascades = 0
    for i in range(n_seeds):
        g_seed = graph_seed_base + i if fresh_graph_per_seed else graph_seed_base
        graph = build_er_graph(n, z, seed=g_seed)
        seed_node = i % n
        res = CascadeModel(graph, phi=phi, seed_node=seed_node).run()
        frac = res["final_active_fraction"]
        sizes.append(frac)
        if frac >= cascade_cutoff:
            n_cascades += 1
    return {
        "z": z,
        "n": n,
        "phi": phi,
        "n_seeds": n_seeds,
        "cascade_cutoff": cascade_cutoff,
        "cascade_frequency": n_cascades / n_seeds if n_seeds else 0.0,
        "n_cascades": n_cascades,
        "sizes": sizes,
    }


def vulnerable_degree_bound(phi: float) -> int:
    """Analytic vulnerable-vertex degree bound K = floor(1/phi): a vertex with degree
    k <= K flips on a single active neighbour (1/k >= phi). For phi=0.18, K=5."""
    return int(math.floor(1.0 / phi))


def size_histogram(sizes: Sequence[float], *, bins: int = 20) -> List[Dict[str, float]]:
    """Histogram of final active fractions in [0, 1] over ``bins`` equal buckets."""
    counts = [0] * bins
    for s in sizes:
        idx = min(bins - 1, int(s * bins))
        counts[idx] += 1
    width = 1.0 / bins
    return [{"lo": round(i * width, 4), "hi": round((i + 1) * width, 4), "count": counts[i]}
            for i in range(bins)]


def is_bimodal(sizes: Sequence[float], *, low_hi: float = 0.02, high_lo: float = 0.10,
               min_each: int = 1) -> Tuple[bool, Dict[str, int]]:
    """A coarse bimodality check matching Watts' separation: a small/local mode
    (final fraction <= ``low_hi``) AND a large/global mode (>= ``high_lo``), with the
    intermediate band sparse. Returns (bimodal, counts)."""
    low = sum(1 for s in sizes if s <= low_hi)
    high = sum(1 for s in sizes if s >= high_lo)
    mid = sum(1 for s in sizes if low_hi < s < high_lo)
    counts = {"low_mode": low, "mid_band": mid, "high_mode": high}
    bimodal = low >= min_each and high >= min_each and mid <= max(low, high)
    return bimodal, counts
