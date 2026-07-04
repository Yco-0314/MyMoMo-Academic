"""Department coordination network + weighted global efficiency / CEI + ensemble
generator + treatment operators. Edge length = 1/weight (DOC A: l_ij = 1/w_ij),
so higher coordination frequency => shorter path => higher efficiency."""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import networkx as nx
import numpy as np

Edge = Tuple[str, str]


@dataclass
class CoordNetwork:
    nodes: List[str]
    edges: Dict[Edge, float]  # undirected; key order normalized on use

    def graph(self) -> nx.Graph:
        g = nx.Graph()
        g.add_nodes_from(self.nodes)
        for (u, v), w in self.edges.items():
            if w > 0:
                g.add_edge(u, v, length=1.0 / w, weight=w)
        return g


def global_efficiency(net: CoordNetwork) -> float:
    """Weighted global efficiency: mean of 1/d_ij over all ordered pairs,
    d_ij = shortest path using edge length 1/w (inf -> contributes 0)."""
    g = net.graph()
    n = len(net.nodes)
    if n < 2:
        return 0.0
    total = 0.0
    lengths = dict(nx.all_pairs_dijkstra_path_length(g, weight="length"))
    for i in net.nodes:
        di = lengths.get(i, {})
        for j in net.nodes:
            if i != j and j in di and di[j] > 0:
                total += 1.0 / di[j]
    return total / (n * (n - 1))


def cei(net: CoordNetwork, node: str) -> float:
    """Coordination Efficiency Index: relative drop in global efficiency when
    `node` is removed (Latora-Marchiori efficiency centrality).

    The node set is held FIXED and the node is *isolated* (its edges dropped),
    so the now-unreachable pairs contribute 0 and the denominator stays
    n*(n-1). This is the standard efficiency-centrality definition: it measures
    how much the network's reach degrades without this department, rather than
    re-normalising over a smaller graph (which can hide the loss)."""
    e0 = global_efficiency(net)
    if e0 == 0:
        return 0.0
    sub = CoordNetwork(nodes=list(net.nodes),
                       edges={e: w for e, w in net.edges.items() if node not in e})
    return (e0 - global_efficiency(sub)) / e0


_HUBS = ["省应急管理厅", "省水利厅", "省气象局"]
_DEPTS = _HUBS + [
    "省公安厅", "省交通运输厅", "省住房和城乡建设厅", "省农业农村厅", "省民政厅",
    "省商务厅", "省通信管理局", "省粮食和物资储备局", "国网电力公司", "铁路部门",
    "省红十字会", "消防救援队伍",
]


def required_pairs() -> List[Edge]:
    """The (lead, collaborator) department pairs the 9-task DAG needs to coordinate.

    Derived from `default_tasks()` (the single source of truth) so the set can
    never drift from the DAG. Every such pair MUST exist as an edge in any
    baseline so that the ORIGINAL network can complete all 9 tasks (0 failed) —
    failures must come from overload dynamics, not from missing coordination
    links. Lazy import breaks the _network<->_experiment cycle."""
    from abm_auto.coord._experiment import default_tasks
    pairs = set()
    for t in default_tasks():
        for c in t.collaborators:
            if t.lead != c:
                pairs.add(tuple(sorted((t.lead, c))))
    return sorted(pairs)


def representative_network(*, seed: int, n_extra_edges: int = 18,
                          required_low_weight: float = 0.34) -> CoordNetwork:
    """A representative department coordination network. GUARANTEES every required
    (lead, collaborator) pair of the 9-task DAG exists as an edge (so the ORIGINAL
    network completes all tasks — 0 failed).

    Kept genuinely IMPROVABLE: required coordination edges are added at WEAK weight
    (≈0.34–0.84 → info-delay 1/w ≈ 1.2–2.9 ticks, i.e. ABOVE the 1-tick floor), so
    a task's baseline coordination is slow and DOC A's global-efficiency edge-edit
    has real room to create a FASTER multi-hop route (a strong shortcut through a
    well-connected hub) that reduces that task's delay — or, by making tasks start
    sooner, increase concurrency and trigger the overload counterexample. The hub
    backbone is strong (high weight) precisely so added shortcuts can be fast.
    Weights are positive coordination-frequency proxies. Deterministic."""
    rng = np.random.default_rng(seed)
    nodes = list(_DEPTS)
    edges: Dict[Edge, float] = {}
    # strong hub backbone (high weight -> short hops -> good shortcut material)
    for u, v in itertools.combinations(_HUBS, 2):
        edges[(u, v)] = float(rng.integers(6, 11))
    # REQUIRED DAG coordination edges: present but deliberately WEAK, so coordination
    # is slow (delay > 1 tick) and the optimizer has room to route around them.
    for key in required_pairs():
        if key not in edges:
            edges[key] = required_low_weight + 0.5 * float(rng.integers(0, 2))  # ~0.34 or ~0.84
    # hub-biased extra (non-required) structure, moderate weight
    others = [d for d in nodes if d not in _HUBS]
    for _ in range(n_extra_edges):
        u = _HUBS[rng.integers(len(_HUBS))] if rng.random() < 0.6 else nodes[rng.integers(len(nodes))]
        v = others[rng.integers(len(others))]
        if u != v:
            key = tuple(sorted((u, v)))
            # don't overwrite a weak required edge with a strong one (keep it improvable)
            if key not in edges:
                edges[key] = float(rng.integers(2, 5))
    return CoordNetwork(nodes=nodes, edges=edges)


def _candidate_edges(net: CoordNetwork) -> List[Edge]:
    present = {tuple(sorted(e)) for e in net.edges}
    return [tuple(sorted((u, v))) for u, v in itertools.combinations(net.nodes, 2)
            if tuple(sorted((u, v))) not in present]


def optimize_edges(net: CoordNetwork, *, budget: int, protect: str,
                   new_weight: float = 4.0) -> Tuple[CoordNetwork, List[Edge]]:
    """DOC-A-style: greedily add up to `budget` edges that maximize weighted global
    efficiency, subject to the protected node's CEI not being weakened. Greedy
    (one edge per step picking the max marginal efficiency gain) — tractable and
    monotone-non-decreasing in static efficiency."""
    cur = CoordNetwork(nodes=list(net.nodes), edges=dict(net.edges))
    added: List[Edge] = []
    base_protect_cei = cei(net, protect)
    for _ in range(budget):
        best, best_e = None, global_efficiency(cur)
        for e in _candidate_edges(cur):
            trial = CoordNetwork(nodes=cur.nodes, edges={**cur.edges, e: new_weight})
            ge = global_efficiency(trial)
            if ge > best_e and cei(trial, protect) >= base_protect_cei - 1e-9:
                best, best_e = e, ge
        if best is None:
            break
        cur = CoordNetwork(nodes=cur.nodes, edges={**cur.edges, best: new_weight})
        added.append(best)
    return cur, added


def add_random_edges(net: CoordNetwork, *, budget: int, rng, new_weight: float = 4.0) -> CoordNetwork:
    cands = _candidate_edges(net)
    rng.shuffle(cands)
    chosen = cands[:budget]
    return CoordNetwork(nodes=list(net.nodes), edges={**net.edges, **{e: new_weight for e in chosen}})


def rewire_preserving_degree(net: CoordNetwork, *, rng, n_swaps: int = 20) -> CoordNetwork:
    """Degree-preserving rewire null: swaps edge endpoints while keeping each node's
    degree fixed, so any process effect cannot be attributed to degree changes.
    `nx.double_edge_swap` accepts an int seed; pass `rng.randint(...)` since the
    installed networkx (3.6.1) does not accept a `random.Random`."""
    g = net.graph()
    try:
        nx.double_edge_swap(g, nswap=n_swaps, max_tries=n_swaps * 20,
                            seed=rng.randint(0, 2 ** 31 - 1))
    except (nx.NetworkXError, nx.NetworkXAlgorithmError):
        pass
    edges = {tuple(sorted((u, v))): net.edges.get(tuple(sorted((u, v))), 4.0) for u, v in g.edges()}
    return CoordNetwork(nodes=list(net.nodes), edges=edges)
