"""Barabasi-Albert (1999) preferential attachment - a mildly agent-based reproduction.

Source: Barabasi, A.-L. & Albert, R. (1999) "Emergence of scaling in random
networks", Science 286:509-512. The growing network with preferential attachment
yields a scale-free degree distribution P(k) ~ k^{-gamma} with gamma ~= 3,
independent of m.

Honest framing (binds the FINDINGS): this is MILDLY agent-based. The network is
GROWN one node at a time; each tick a new ``NodeAgent`` arrives and makes a
preferential-attachment DECISION - it samples m existing targets with probability
proportional to their current degree (degree-weighted sampling WITHOUT replacement).
That arrival decision is the agent step on the neutral platform. It is not a
population of agents stepping repeatedly (unlike SIS / Voter); the outcome is the
emergent structure, not agent trajectories.

Built on ``abm_auto._platform``: each arriving node is a ``NodeAgent`` whose ``step``
performs the attachment choice; ``BAModel`` drives the ``AgentSet`` scheduler. The
RNG chain is the single seeded ``model.rng`` (deterministic given the seed).

Fit method (FIXED before running, NOT tuned to hit 3):
  * Graded metric = tail exponent ``gamma`` from the discrete (integer) power-law
    MLE of Clauset, Shalizi & Newman (2009), with ``kmin`` fixed on theoretical
    grounds to ``m + 1`` (the first degree strictly above the minimum-degree spike
    at k = m, which every node trivially has from its m birth-edges). The estimator:
        gamma = 1 + n_tail * [ sum_i ln( k_i / (kmin - 0.5) ) ]^{-1}
    over all nodes with degree k_i >= kmin.
  * A log-log CCDF linear-regression slope is also computed as a documented
    SECONDARY cross-check (gamma_ccdf = 1 - slope of log10 P(K>=k) vs log10 k over
    k >= kmin), never the graded number.
``kmin`` and binning are NOT swept to move gamma toward 3.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

from abm_auto._platform import Agent, AgentModel


# -- Agent --------------------------------------------------------------------

class NodeAgent(Agent):
    """One arriving node. Its ``step`` is the preferential-attachment decision: pick
    m distinct existing targets with probability proportional to current degree
    (degree-weighted sampling WITHOUT replacement), then attach to each.

    The agent reads/writes the model's degree bookkeeping. Sampling uses the model's
    single seeded RNG so the whole grown network is reproducible.
    """

    def __init__(self, agent_id: int, model: "BAModel", *, m: int) -> None:
        super().__init__(agent_id, model)
        self.m = m

    def choose_targets(self) -> List[int]:
        """Degree-weighted sampling WITHOUT replacement of m existing nodes.

        Implements preferential attachment explicitly: each existing node is chosen
        with probability proportional to its CURRENT degree. Sampling without
        replacement (a node cannot be picked twice -> no multi-edges) is done by m
        sequential weighted draws that exclude already-picked targets. The weight of
        an excluded node is removed from the running total. Deterministic given the
        model RNG.
        """
        model = self.model
        existing = model.node_ids          # ids that already exist (0..id-1)
        degree = model.degree
        # Running total degree over the candidate set.
        total = model.total_degree
        chosen: List[int] = []
        chosen_set: set[int] = set()
        m = min(self.m, len(existing))     # cannot attach to more nodes than exist
        for _ in range(m):
            avail_total = total
            # Subtract the degree of already-chosen nodes from the live total.
            for c in chosen:
                avail_total -= degree[c]
            # Weighted draw over not-yet-chosen existing nodes.
            r = model.rng.random() * avail_total
            cum = 0.0
            pick = existing[-1]
            for node in existing:
                if node in chosen_set:
                    continue
                cum += degree[node]
                if r < cum:
                    pick = node
                    break
            chosen.append(pick)
            chosen_set.add(pick)
        return chosen

    def step(self) -> None:
        targets = self.choose_targets()
        self.model.attach(self.id, targets)


# -- Model --------------------------------------------------------------------

class BAModel(AgentModel):
    """Grows a Barabasi-Albert network to N nodes with parameter m.

    Starts from a small connected seed (a clique/cycle of ``m + 1`` nodes so every
    node begins with degree >= m and the first preferential draw is well defined).
    Each tick one ``NodeAgent`` arrives and attaches m degree-weighted edges. The
    degree sequence at N nodes is the outcome.

    Degree bookkeeping (``degree`` dict + ``total_degree`` scalar + adjacency) is
    maintained incrementally so each arrival is O(existing) for the weighted draw -
    no per-tick rescan of the whole graph.
    """

    def __init__(self, *, n: int, m: int, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if m < 1:
            raise ValueError("m must be >= 1")
        if n <= m:
            raise ValueError("n must be > m")
        self.target_n = n
        self.m = m
        self.degree: Dict[int, int] = {}
        self.adjacency: Dict[int, set] = {}
        self.node_ids: List[int] = []
        self.total_degree = 0
        self._seed_network()

    # -- construction --
    def _seed_network(self) -> None:
        """Seed = a connected clique on ``m + 1`` nodes (ids 0..m). Each seed node
        therefore starts with degree m, so the first arrival's degree-weighted draw
        is well defined and the seed contributes no zero-degree nodes."""
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
            if t in self.adjacency[new_id]:
                continue  # defensive: no multi-edges
            self.adjacency[new_id].add(t)
            self.adjacency[t].add(new_id)
            self.degree[new_id] += 1
            self.degree[t] += 1
            self.total_degree += 2

    def grow(self) -> None:
        """Add nodes one at a time until ``target_n`` exist. Each new node is a
        ``NodeAgent`` that steps once (its attachment decision) at arrival."""
        while len(self.node_ids) < self.target_n:
            new_id = len(self.node_ids)
            self._register_node(new_id)
            agent = NodeAgent(new_id, self, m=self.m)
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


# -- fit methods --------------------------------------------------------------

def discrete_powerlaw_mle(degrees: List[int], *, kmin: int) -> Tuple[float, int]:
    """Clauset-Shalizi-Newman (2009) discrete power-law MLE for the tail exponent.

        gamma = 1 + n_tail * [ sum_i ln( k_i / (kmin - 0.5) ) ]^{-1}

    over all degrees k_i >= kmin. Returns (gamma, n_tail). The 0.5 continuity
    correction is the standard discrete-MLE approximation (CSN eq. 3.5). ``kmin`` is
    fixed by the caller; it is NOT optimised here.
    """
    tail = [k for k in degrees if k >= kmin]
    n_tail = len(tail)
    if n_tail == 0:
        return float("nan"), 0
    s = sum(math.log(k / (kmin - 0.5)) for k in tail)
    if s <= 0:
        return float("nan"), n_tail
    gamma = 1.0 + n_tail / s
    return gamma, n_tail


def ccdf_loglog_slope(degrees: List[int], *, kmin: int) -> Tuple[float, int]:
    """Secondary cross-check: gamma from the log-log CCDF linear fit.

    Computes the empirical CCDF P(K >= k) over distinct degree values k >= kmin,
    regresses log10(CCDF) on log10(k) (ordinary least squares), and returns
    (gamma_ccdf, n_points) with gamma_ccdf = 1 - slope (CCDF exponent is gamma-1).
    Documented secondary metric only; never the graded number.
    """
    tail = sorted(k for k in degrees if k >= kmin)
    n = len(tail)
    if n < 2:
        return float("nan"), n
    # distinct degree -> CCDF (fraction of tail with degree >= that value)
    distinct = sorted(set(tail))
    xs: List[float] = []
    ys: List[float] = []
    for k in distinct:
        ccdf = sum(1 for t in tail if t >= k) / n
        if ccdf > 0 and k > 0:
            xs.append(math.log10(k))
            ys.append(math.log10(ccdf))
    if len(xs) < 2:
        return float("nan"), len(xs)
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    if den == 0:
        return float("nan"), len(xs)
    slope = num / den
    gamma_ccdf = 1.0 - slope
    return gamma_ccdf, len(xs)


def degree_histogram(degrees: List[int]) -> List[Dict[str, int]]:
    """Plain integer-degree histogram: [{degree, count}, ...] sorted by degree."""
    counts: Dict[int, int] = {}
    for k in degrees:
        counts[k] = counts.get(k, 0) + 1
    return [{"degree": k, "count": counts[k]} for k in sorted(counts)]


# -- ER comparison (P3) -------------------------------------------------------

def er_max_degree(n: int, mean_degree: float, *, seed: int) -> Dict[str, Any]:
    """Build an Erdos-Renyi G(n, p) graph at the given mean degree and return its
    max degree (and mean degree achieved). Used to contrast hub formation: BA grows
    hubs (heavy tail) while ER degrees are Poisson-concentrated around the mean.

    Uses the same kind of degree bookkeeping (no networkx dependency) with a seeded
    RNG so it is deterministic. p = mean_degree / (n - 1).
    """
    import random as _random
    rng = _random.Random(seed)
    p = mean_degree / (n - 1)
    degree = [0] * n
    # Sparse regime: iterate candidate pairs with Bernoulli(p). For n=10k and
    # p~3e-4 this is ~5e7 pair checks; acceptable and exact. We use a fast
    # geometric-skip sampler to avoid the O(n^2) inner loop.
    edges = 0
    # Geometric-skipping Erdos-Renyi sampler (Batagelj-Brandes 2005): generate edge
    # indices in the upper-triangular enumeration with geometric gaps.
    if p <= 0:
        achieved = 0.0
        return {"n": n, "p": p, "mean_degree_target": mean_degree,
                "mean_degree_achieved": achieved, "max_degree": 0, "edges": 0}
    log1mp = math.log(1.0 - p)
    v = 1
    w = -1
    while v < n:
        r = rng.random()
        w = w + 1 + int(math.floor(math.log(1.0 - r) / log1mp))
        while w >= v and v < n:
            w = w - v
            v = v + 1
        if v < n:
            degree[v] += 1
            degree[w] += 1
            edges += 1
    achieved = 2.0 * edges / n
    return {
        "n": n, "p": p, "mean_degree_target": mean_degree,
        "mean_degree_achieved": achieved,
        "max_degree": max(degree) if degree else 0,
        "edges": edges,
    }


# -- driver -------------------------------------------------------------------

def run_ba(*, n: int, m: int, seed: int) -> Dict[str, Any]:
    """Grow one BA network and return its degree sequence + summary stats."""
    model = BAModel(n=n, m=m, seed=seed)
    model.grow()
    degrees = model.degree_sequence()
    return {
        "n": len(model.node_ids),
        "m": m,
        "seed": seed,
        "degrees": degrees,
        "max_degree": model.max_degree(),
        "mean_degree": model.mean_degree(),
        "min_degree": min(degrees),
    }


def fit_gamma(degrees: List[int], *, m: int) -> Dict[str, Any]:
    """Apply the FIXED fit: discrete MLE with kmin = m + 1 (graded), plus the
    documented CCDF cross-check at the same kmin."""
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
