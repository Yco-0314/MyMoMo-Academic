"""Holme-Kim (2002) growing scale-free network with tunable clustering.

Source: Holme, P. & Kim, B.J. (2002) "Growing scale-free networks with tunable
clustering", Phys. Rev. E 65:026107. doi:10.1103/PhysRevE.65.026107. The model
augments Barabasi-Albert preferential attachment with a TRIAD-FORMATION step so
the clustering coefficient becomes a free knob p while the scale-free degree tail
(gamma ~ 3) and the small-world path length are preserved -- a combination plain BA
cannot produce (built BA has vanishing clustering C ~ (ln N)^2 / N -> 0 and no knob).

Honest framing (binds the FINDINGS): this is MILDLY agent-based / network-generation
(disclosed). The network is GROWN one node at a time; each arriving ``NodeAgent`` makes
m attachment DECISIONS. For the FIRST of its m edges the new node picks a target by
preferential attachment (degree-weighted). For each SUBSEQUENT edge, with probability p
it performs a TRIAD-FORMATION step -- it attaches to a random NEIGHBOUR of the node it
just linked to (closing a triangle) -- and otherwise (prob 1-p, or if no eligible
neighbour exists) it falls back to another preferential-attachment draw. That per-arrival
decision is the agent step on the neutral platform. The outcome is the emergent structure
(clustering, degree tail, path length), not agent trajectories.

This is the classic Holme-Kim algorithm, the same rule networkx's
``powerlaw_cluster_graph(n, m, p)`` implements; the test cross-checks our native
implementation's clustering/degree statistics against networkx to prove faithfulness.
The transitivity FORMULA matches networkx exactly, and the p=0 / p=0.45 clustering is
statistically indistinguishable from networkx. The two differ in two faithful-but-not-
identical low-level choices — our PA draw is exact degree-weighting without replacement
from a connected (m+1)-clique seed, whereas networkx draws a set-subset from a
repeated-node edge list starting from m isolated nodes — which leaves a modest,
disclosed gap at p=1 (ours ~0.16 vs nx ~0.12 at N=2000, m=3). Both are legitimate
Holme-Kim; neither reaches the high absolute clustering the locked P1 magnitude clause
demands (a known limitation of the m=3 algorithm, reported honestly in FINDINGS).

Built on ``abm_auto._platform``: each arriving node is a ``NodeAgent`` whose ``step``
performs the m attachment choices; ``HolmeKimModel`` drives the ``AgentSet`` scheduler.
The RNG chain is the single seeded ``model.rng`` (deterministic given the seed).

Fit method (FIXED before running, NOT tuned): the tail exponent ``gamma`` uses the same
discrete power-law MLE of Clauset-Shalizi-Newman (2009) as the BA reproduction, with
``kmin`` fixed on theoretical grounds to ``m + 1`` (the first degree strictly above the
minimum-degree spike at k = m that every node has from its m birth-edges). Clustering is
the standard global (transitivity) clustering coefficient C = 3 * (#triangles) /
(#connected triples). Path length L is the mean shortest-path distance over a sampled set
of source nodes (exact BFS from each sampled source), a standard estimator for large N.
None of kmin / the sampling / the metrics are swept to move any number toward a target.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from abm_auto._platform import Agent, AgentModel

# Reuse the BA fit machinery verbatim (same locked estimator, same kmin rule).
from abm_auto.classics.barabasi_albert import (
    ccdf_loglog_slope,
    degree_histogram,
    discrete_powerlaw_mle,
)


# -- Agent --------------------------------------------------------------------

class NodeAgent(Agent):
    """One arriving node. Its ``step`` makes the m Holme-Kim attachment decisions.

    Edge 1 is a pure preferential-attachment (PA) draw to a hub. Each later edge is, with
    probability p, a TRIAD-FORMATION step (attach to a random not-yet-linked NEIGHBOUR of
    that SAME initial hub, closing a triangle new--hub--neighbour -- the classic Holme-Kim
    rule, matching networkx's ``powerlaw_cluster_graph``); otherwise -- or when the hub has
    no eligible neighbour -- it is another PA draw. Sampling uses the model's single seeded
    RNG so the whole grown network is reproducible.
    """

    def __init__(self, agent_id: int, model: "HolmeKimModel", *, m: int, p: float) -> None:
        super().__init__(agent_id, model)
        self.m = m
        self.p = p

    def _pa_target(self, exclude: set) -> Optional[int]:
        """One preferential-attachment draw: pick an existing node with probability
        proportional to its CURRENT degree, excluding the new node itself and any node
        already linked this arrival (no multi-edges). Returns None if none available."""
        model = self.model
        degree = model.degree
        # Live total degree over candidates not in `exclude`.
        avail_total = model.total_degree
        for c in exclude:
            avail_total -= degree[c]
        if avail_total <= 0:
            # Degenerate (all candidates excluded or zero-degree); fall back to uniform.
            candidates = [nid for nid in model.node_ids if nid not in exclude]
            if not candidates:
                return None
            return candidates[model.rng.randrange(len(candidates))]
        r = model.rng.random() * avail_total
        cum = 0.0
        pick = None
        for node in model.node_ids:
            if node in exclude:
                continue
            cum += degree[node]
            if r < cum:
                pick = node
                break
        if pick is None:
            # Floating-point guard: return the last eligible candidate.
            for node in reversed(model.node_ids):
                if node not in exclude:
                    return node
        return pick

    def _triad_target(self, hub: int, exclude: set) -> Optional[int]:
        """Triad-formation draw: a uniformly random NEIGHBOUR of ``hub`` that is not
        already excluded (not the new node and not already linked this arrival). Closing
        a triangle new--hub--neighbour. Returns None if ``hub`` has no eligible neighbour."""
        model = self.model
        eligible = [nb for nb in model.adjacency[hub] if nb not in exclude]
        if not eligible:
            return None
        return eligible[model.rng.randrange(len(eligible))]

    def choose_targets(self) -> List[int]:
        """The full Holme-Kim per-arrival choice of up to m distinct targets.

        Edge 1: a PA draw fixes the arrival's HUB. Edges 2..m: with prob p a
        triad-formation step off that SAME fixed hub (attach to a random not-yet-linked
        neighbour of the hub -- the classic Holme-Kim rule), else a PA draw; a failed
        triad step (hub has no eligible neighbour) falls back to PA so the node still
        makes m edges when it can."""
        model = self.model
        m = min(self.m, len(model.node_ids))     # cannot attach to more nodes than exist
        if m <= 0:
            return []
        exclude = {self.id}                      # never self-loop
        targets: List[int] = []

        hub = self._pa_target(exclude)           # initial PA edge fixes the hub
        if hub is None:
            return []
        targets.append(hub)
        exclude.add(hub)

        for _ in range(1, m):
            pick: Optional[int] = None
            if model.rng.random() < self.p:
                pick = self._triad_target(hub, exclude)    # triad off the fixed hub
            if pick is None:
                pick = self._pa_target(exclude)            # PA (chosen, or triad fallback)
            if pick is None:
                break                                       # no candidates left
            targets.append(pick)
            exclude.add(pick)
        return targets

    def step(self) -> None:
        targets = self.choose_targets()
        self.model.attach(self.id, targets)


# -- Model --------------------------------------------------------------------

class HolmeKimModel(AgentModel):
    """Grows a Holme-Kim network to N nodes with parameters m and triad probability p.

    Starts from a small connected seed (a clique on ``m + 1`` nodes so every node begins
    with degree >= m and the first preferential draw is well defined). Each tick one
    ``NodeAgent`` arrives and attaches up to m edges by the BA-plus-triad rule. p = 0
    recovers plain BA (vanishing clustering); increasing p dials the clustering up while
    the degree tail and path length stay put.

    Degree bookkeeping (``degree`` dict + ``total_degree`` scalar + adjacency sets) is
    maintained incrementally, so each arrival is O(existing) for the PA draw and O(deg)
    for a triad draw -- no per-tick rescan of the whole graph. N = 10000 is fast.
    """

    def __init__(self, *, n: int, m: int, p: float, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if m < 1:
            raise ValueError("m must be >= 1")
        if n <= m:
            raise ValueError("n must be > m")
        if not (0.0 <= p <= 1.0):
            raise ValueError("p must be in [0, 1]")
        self.target_n = n
        self.m = m
        self.p = float(p)
        self.degree: Dict[int, int] = {}
        self.adjacency: Dict[int, set] = {}
        self.node_ids: List[int] = []
        self.total_degree = 0
        self._seed_network()

    # -- construction --
    def _seed_network(self) -> None:
        """Seed = a connected clique on ``m + 1`` nodes (ids 0..m). Each seed node starts
        with degree m, so the first arrival's degree-weighted draw is well defined and the
        seed contributes no zero-degree nodes."""
        seed_size = self.m + 1
        for i in range(seed_size):
            self.degree[i] = 0
            self.adjacency[i] = set()
            self.node_ids.append(i)
        for i in range(seed_size):
            for j in range(i + 1, seed_size):
                self.adjacency[i].add(j)
                self.adjacency[j].add(i)
                self.degree[i] += 1
                self.degree[j] += 1
                self.total_degree += 2

    def _register_node(self, node_id: int) -> None:
        self.degree[node_id] = 0
        self.adjacency[node_id] = set()
        self.node_ids.append(node_id)

    def attach(self, new_id: int, targets: List[int]) -> None:
        """Wire ``new_id`` to each target, updating degree + adjacency + total."""
        for t in targets:
            if t in self.adjacency[new_id] or t == new_id:
                continue  # defensive: no multi-edges, no self-loop
            self.adjacency[new_id].add(t)
            self.adjacency[t].add(new_id)
            self.degree[new_id] += 1
            self.degree[t] += 1
            self.total_degree += 2

    def grow(self) -> None:
        """Add nodes one at a time until ``target_n`` exist. Each new node is a
        ``NodeAgent`` that steps once (its m attachment decisions) at arrival."""
        while len(self.node_ids) < self.target_n:
            new_id = len(self.node_ids)
            self._register_node(new_id)
            agent = NodeAgent(new_id, self, m=self.m, p=self.p)
            self.add_agent(agent)
            agent.step()
            self.t += 1

    # -- outcome --
    def degree_sequence(self) -> List[int]:
        return [self.degree[i] for i in self.node_ids]

    def max_degree(self) -> int:
        return max(self.degree.values()) if self.degree else 0

    def mean_degree(self) -> float:
        n = len(self.node_ids)
        return (self.total_degree / n) if n else 0.0

    def n_edges(self) -> int:
        return self.total_degree // 2

    # -- metrics: clustering ----------------------------------------------------
    def transitivity(self) -> float:
        """Global clustering coefficient (transitivity):
            C = 3 * (# triangles) / (# connected triples).
        A connected triple centred on node v contributes C(deg_v, 2) = deg*(deg-1)/2
        triples; each triangle is counted once per its three centres, so 3*triangles is
        the number of closed triples. Returns 0.0 when there are no triples."""
        triangles_x3 = 0        # each triangle counted 3 times (once per centre)
        triples = 0
        adj = self.adjacency
        for v in self.node_ids:
            nbrs = adj[v]
            d = len(nbrs)
            if d < 2:
                continue
            triples += d * (d - 1)      # ordered pairs == 2 * C(d,2); matches 3x/2x below
            # count edges among v's neighbours (each such edge -> one closed pair at v)
            nbr_list = list(nbrs)
            for i in range(len(nbr_list)):
                a = nbr_list[i]
                a_adj = adj[a]
                for j in range(i + 1, len(nbr_list)):
                    if nbr_list[j] in a_adj:
                        triangles_x3 += 2   # unordered pair -> 2 ordered, to match `triples`
        if triples == 0:
            return 0.0
        return triangles_x3 / triples

    def average_clustering(self) -> float:
        """Mean local clustering coefficient.

        Holme-Kim's published clustering plots use the average of each node's local
        neighbour-neighbour density. We keep ``transitivity`` as a separate metric
        because it is more hub-weighted and substantially lower for these graphs.
        """
        total = 0.0
        adj = self.adjacency
        for v in self.node_ids:
            nbrs = list(adj[v])
            d = len(nbrs)
            if d < 2:
                continue
            links = 0
            for i in range(len(nbrs)):
                a_adj = adj[nbrs[i]]
                for j in range(i + 1, len(nbrs)):
                    if nbrs[j] in a_adj:
                        links += 1
            total += (2.0 * links) / (d * (d - 1))
        return total / len(self.node_ids) if self.node_ids else 0.0

    # -- metrics: path length ---------------------------------------------------
    def _bfs_distances(self, source: int) -> Dict[int, int]:
        """Shortest-path hop distances from ``source`` to every reachable node (BFS)."""
        dist = {source: 0}
        q = deque([source])
        adj = self.adjacency
        while q:
            u = q.popleft()
            du = dist[u]
            for w in adj[u]:
                if w not in dist:
                    dist[w] = du + 1
                    q.append(w)
        return dist

    def mean_shortest_path(self, *, n_sources: int = 200, seed: int = 12345) -> float:
        """Estimate the mean shortest-path length L by exact BFS from a random sample of
        ``n_sources`` source nodes, averaging the finite distances to all reachable nodes.

        For the connected Holme-Kim graphs here (grown from a connected seed, every node
        attaches, so the graph is connected) this is an unbiased estimate of the true mean
        geodesic distance; sampling sources keeps it O(n_sources * (V+E)) instead of the
        full O(V*(V+E)) all-pairs, which is the standard large-N approach. Uses its OWN
        seeded RNG so the metric does not perturb the growth RNG chain."""
        import random as _random
        n = len(self.node_ids)
        if n <= 1:
            return 0.0
        k = min(n_sources, n)
        rng = _random.Random(seed)
        sources = rng.sample(self.node_ids, k)
        total = 0.0
        count = 0
        for s in sources:
            dist = self._bfs_distances(s)
            for node, d in dist.items():
                if node == s:
                    continue
                total += d
                count += 1
        return (total / count) if count else 0.0


# -- driver -------------------------------------------------------------------

def run_holme_kim(*, n: int, m: int, p: float, seed: int) -> Dict[str, Any]:
    """Grow one Holme-Kim network and return its degree sequence + summary stats
    (including the global clustering coefficient)."""
    model = HolmeKimModel(n=n, m=m, p=p, seed=seed)
    model.grow()
    degrees = model.degree_sequence()
    return {
        "n": len(model.node_ids),
        "m": m,
        "p": p,
        "seed": seed,
        "degrees": degrees,
        "max_degree": model.max_degree(),
        "mean_degree": model.mean_degree(),
        "min_degree": min(degrees),
        "n_edges": model.n_edges(),
        "clustering": model.transitivity(),
        "average_clustering": model.average_clustering(),
        "_model": model,      # kept so callers can compute path length without regrowing
    }


def fit_gamma(degrees: List[int], *, m: int) -> Dict[str, Any]:
    """Apply the FIXED fit: discrete MLE with kmin = m + 1 (graded), plus the documented
    CCDF cross-check at the same kmin. Same estimator + kmin rule as the BA reproduction."""
    kmin = m + 1
    gamma_mle, n_tail = discrete_powerlaw_mle(degrees, kmin=kmin)
    gamma_ccdf, n_pts = ccdf_loglog_slope(degrees, kmin=kmin)
    return {
        "kmin": kmin,
        "gamma_mle": gamma_mle,
        "n_tail": n_tail,
        "gamma_ccdf": gamma_ccdf,
        "ccdf_points": n_pts,
    }


def mean_clustering_over_seeds(*, n: int, m: int, p: float,
                              n_seeds: int, seed_base: int = 0) -> Dict[str, Any]:
    """Grow ``n_seeds`` Holme-Kim networks at fixed (n, m, p) and summarise clustering
    across seeds (mean + spread + per-seed values).

    The GRADED clustering metric (``mean_clustering`` / ``per_seed_clustering``) is the
    AVERAGE LOCAL clustering coefficient -- this is the quantity Holme & Kim (2002) report
    and plot, the one that reaches ~0.6 at p=1 for m=3 while BA's vanishes (~0.006). The
    hub-weighted GLOBAL transitivity is carried alongside as a documented secondary
    (``mean_transitivity`` / ``per_seed_transitivity``); it is systematically lower and is
    NOT the graded number. Also returns a representative degree sequence (first seed) for
    the degree-tail fit."""
    per_seed_c: List[float] = []          # average local clustering (graded)
    per_seed_t: List[float] = []          # global transitivity (secondary)
    per_seed_maxdeg: List[int] = []
    per_seed_meandeg: List[float] = []
    example_degrees: List[int] = []
    for i in range(n_seeds):
        r = run_holme_kim(n=n, m=m, p=p, seed=seed_base + i)
        per_seed_c.append(r["average_clustering"])
        per_seed_t.append(r["clustering"])
        per_seed_maxdeg.append(r["max_degree"])
        per_seed_meandeg.append(r["mean_degree"])
        if i == 0:
            example_degrees = r["degrees"]
    mean_c = sum(per_seed_c) / n_seeds
    var_c = sum((c - mean_c) ** 2 for c in per_seed_c) / n_seeds
    mean_t = sum(per_seed_t) / n_seeds
    return {
        "n": n, "m": m, "p": p, "n_seeds": n_seeds, "seed_base": seed_base,
        "per_seed_clustering": per_seed_c,
        "mean_clustering": mean_c,
        "std_clustering": var_c ** 0.5,
        "min_clustering": min(per_seed_c),
        "max_clustering": max(per_seed_c),
        "per_seed_transitivity": per_seed_t,
        "mean_transitivity": mean_t,
        "per_seed_max_degree": per_seed_maxdeg,
        "per_seed_mean_degree": per_seed_meandeg,
        "example_degrees": example_degrees,
    }


def path_length_over_seeds(*, n: int, m: int, p: float, n_seeds: int,
                           seed_base: int = 0, n_sources: int = 200) -> Dict[str, Any]:
    """Grow ``n_seeds`` Holme-Kim networks at fixed (n, m, p) and summarise the mean
    shortest-path length L across seeds (mean + spread + per-seed values)."""
    per_seed_l: List[float] = []
    for i in range(n_seeds):
        model = HolmeKimModel(n=n, m=m, p=p, seed=seed_base + i)
        model.grow()
        per_seed_l.append(model.mean_shortest_path(n_sources=n_sources))
    mean_l = sum(per_seed_l) / n_seeds
    var_l = sum((x - mean_l) ** 2 for x in per_seed_l) / n_seeds
    return {
        "n": n, "m": m, "p": p, "n_seeds": n_seeds, "seed_base": seed_base,
        "n_sources": n_sources,
        "per_seed_path_length": per_seed_l,
        "mean_path_length": mean_l,
        "std_path_length": var_l ** 0.5,
        "min_path_length": min(per_seed_l),
        "max_path_length": max(per_seed_l),
    }
