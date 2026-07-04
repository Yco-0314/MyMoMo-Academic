"""Independent Cascade + Influence Maximization — a faithful reproduction.

Sources (the locked claim):
  * Goldenberg, J., Libai, B. & Muller, E. (2001) "Talk of the network: A complex
    systems look at the underlying process of word-of-mouth", Marketing Letters
    12(3):211-223 — the Independent Cascade (IC) diffusion process.
  * Kempe, D., Kleinberg, J. & Tardos, E. (2003) "Maximizing the spread of influence
    through a social network", KDD '03:137-146, doi:10.1145/956750.956769 — IC as a
    submodular influence function and the 1-1/e greedy guarantee for influence
    maximization.

The Independent Cascade rule (verified against KKT 2003, section 2.2):
  * A directed graph, each edge (u -> w) carrying an activation probability p_uw.
  * Some seed set S starts active. In the discrete step right AFTER a node u first
    becomes active, u gets exactly ONE independent chance to activate each still-inactive
    out-neighbour w, succeeding with probability p_uw. This attempt is single-shot: if it
    fails, u never tries w again (memoryless per directed edge).
  * The process runs synchronously — every node that became active on step t makes its
    attempts on step t+1 — until a step passes with no new activations (quiescence).
  * The influence spread sigma(S) is the EXPECTED number of active nodes at the end; it is
    estimated by Monte-Carlo (averaging the final active count over many independent
    cascade realizations).

This is a HYBRID reproduction (disclosed): the per-node activation state is genuine
agent state on ``abm_auto._platform`` (a ``CascadeNode`` whose ``step`` fires its
out-edges), the cascade is an edge-probability stochastic process (not a node-threshold
rule — that is what distinguishes IC from watts-cascade / granovetter / complex-contagion),
and influence maximization adds a combinatorial-optimization gate (greedy / CELF / brute
force) on top of the simulator.

Key equivalence used for the "live-edge" analysis (KKT 2003, Claim 2.3): one IC
realization is equivalent to first flipping every edge independently (keep edge u->w with
prob p_uw) to get a random "live-edge" subgraph, then taking the set reachable from S.
This is why sigma is a coverage function and hence monotone + SUBMODULAR, and why greedy
attains a 1-1/e approximation. We use the direct forward-simulation form for the model and
the live-edge form only where it makes a Monte-Carlo estimator cheaper.
"""
from __future__ import annotations

import random
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import networkx as nx

from abm_auto._platform import Agent, AgentModel, DataCollector


# ── Agent ────────────────────────────────────────────────────────────────────

class CascadeNode(Agent):
    """One vertex of the diffusion graph. ``active`` is its binary state.

    A node is a *frontier* node exactly for the one step after it first becomes
    active: on that step it gets a single independent attempt to activate each
    still-inactive out-neighbour (probability p on that directed edge). The attempt
    is staged into the model's ``_newly_active`` set and committed synchronously by
    the model after every frontier node has fired, so within a step activations do
    not chain (a node activated this step only fires on the NEXT step). This makes a
    step order-independent given the model RNG.
    """

    def __init__(self, agent_id: int, model: "ICModel") -> None:
        super().__init__(agent_id, model)
        self.active = False
        self.is_frontier = False   # True only on the step this node fires its out-edges

    def step(self) -> None:
        """If this node is on the current frontier, make one single-shot attempt on
        each inactive out-neighbour with the edge probability."""
        if not self.is_frontier:
            return
        model = self.model
        p = model.p
        rng = model.rng
        active = model.active_flags
        staged = model._staged_activations
        for w in model.out_neighbors[self.id]:
            if active[w] or staged[w]:
                continue
            # single-shot: one Bernoulli(p) per directed edge (this step only).
            if rng.random() < p:
                staged[w] = True
                model._newly_active.append(w)


# ── Model ────────────────────────────────────────────────────────────────────

class ICModel(AgentModel):
    """Drives ONE Independent-Cascade realization on a fixed directed graph.

    Construct with a directed graph, a uniform edge probability ``p``, a seed set,
    and an integer ``seed`` for the RNG. ``run`` iterates synchronous frontier steps
    to quiescence and returns a summary (final active count/fraction + the
    active-count series via the DataCollector).

    Uniform-p only in the model (the locked study uses a single p); the live-edge
    estimator below supports per-edge probabilities but the forward simulator is
    driven at one p, matching the lock.
    """

    def __init__(self, graph: nx.DiGraph, *, p: float, seed_set: Sequence[int],
                 seed: int = 0, max_steps: Optional[int] = None) -> None:
        super().__init__(seed=seed, schedule="sequential")
        self.graph = graph
        self.p = p
        self.seed_set = list(seed_set)
        self.n = graph.number_of_nodes()
        self.max_steps = max_steps if max_steps is not None else self.n + 2

        # Out-adjacency snapshot keyed by node id (stable integer labels 0..n-1).
        self.out_neighbors: Dict[int, List[int]] = {
            node: list(graph.successors(node)) for node in graph.nodes()
        }
        # Flat activation flags (fast membership; avoids per-node object scans).
        self.active_flags: Dict[int, bool] = {node: False for node in graph.nodes()}
        self._staged_activations: Dict[int, bool] = {node: False for node in graph.nodes()}

        self.node_by_id: Dict[int, CascadeNode] = {}
        for node in graph.nodes():
            agent = CascadeNode(node, self)
            self.node_by_id[node] = agent
            self.add_agent(agent)

        # Seed: activate the seed set and make them the initial frontier.
        self._newly_active: List[int] = []
        for s in self.seed_set:
            if not self.active_flags[s]:
                self.active_flags[s] = True
                self.node_by_id[s].active = True
                self.node_by_id[s].is_frontier = True

        self.reporter = DataCollector({"active": lambda m: m.active_count()})

    # -- metrics --
    def active_count(self) -> int:
        return sum(1 for v in self.active_flags.values() if v)

    def active_fraction(self) -> float:
        return self.active_count() / self.n if self.n else 0.0

    # -- tick --
    def step(self) -> None:
        """One synchronous frontier step: every current frontier node fires its
        out-edges (staging activations), then the model commits the newly-activated
        set as the next frontier and clears the old frontier."""
        self._newly_active = []
        self.agents.step()                       # frontier nodes stage activations

        # Old frontier retires; newly-active become active + the next frontier.
        for node in self.node_by_id.values():
            node.is_frontier = False
        for w in self._newly_active:
            self.active_flags[w] = True
            node = self.node_by_id[w]
            node.active = True
            node.is_frontier = True
        # Reset the staging flags for the nodes we just committed (already active now).
        for w in self._newly_active:
            self._staged_activations[w] = False

        self.t += 1
        self._new_activations = len(self._newly_active)
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate synchronous frontier steps until a step adds no new node."""
        self.reporter.collect(self)              # t=0 baseline (just the seed set)
        self._new_activations = 0
        for _ in range(self.max_steps):
            self.step()
            if self._new_activations == 0:
                break
        final = self.active_count()
        return {
            "final_active_count": final,
            "final_active_fraction": final / self.n if self.n else 0.0,
            "n": self.n,
            "p": self.p,
            "seed_set": list(self.seed_set),
            "steps": self.t,
            "active_series": self.reporter.series("active"),
        }


# ── graph builders ───────────────────────────────────────────────────────────

def build_directed_er(n: int, z: float, *, seed: int) -> nx.DiGraph:
    """Directed Erdos-Renyi G(n, mean out-degree z): each ordered pair (u, w), u != w,
    gets a directed edge u->w independently with probability z/(n-1), so the expected
    out-degree (and in-degree) is z. On this family the IC control parameter is
    lambda = p * z (an active node has ~z out-neighbours, each activated w.p. p).

    Uses ``nx.fast_gnp_random_graph(directed=True)`` for an exact per-arc Bernoulli
    draw; nodes are 0..n-1.
    """
    if n <= 1:
        g = nx.DiGraph()
        g.add_nodes_from(range(n))
        return g
    prob = z / (n - 1)
    prob = max(0.0, min(1.0, prob))
    return nx.fast_gnp_random_graph(n, prob, seed=seed, directed=True)


# ── Monte-Carlo influence spread sigma(S) ─────────────────────────────────────

def influence_spread(graph: nx.DiGraph, seed_set: Sequence[int], *, p: float,
                     n_sims: int, rng: Optional[random.Random] = None,
                     base_seed: Optional[int] = None) -> float:
    """Monte-Carlo estimate of sigma(S) = E[ final active count ] under IC with uniform
    edge probability p, averaged over ``n_sims`` independent forward-simulation
    realizations. Uses a fast BFS-frontier simulation (equivalent to ``ICModel.run``'s
    process but without per-agent object overhead, so many sims are affordable).

    Variance reduction via a shared LIVE-EDGE WORLD (common random numbers). When
    ``base_seed`` is given, realization ``i`` is a fixed live-edge subgraph: EACH directed
    edge is independently declared "live" with probability p using a coin keyed to
    ``(base_seed, i, edge_index)`` — the coin depends on the EDGE, not on the traversal
    order or on the seed set. sigma(S) for that realization is then just the number of
    nodes reachable from S in the live subgraph. Because reachability in a fixed graph is
    a coverage function (KKT 2003 Claim 2.3), it is EXACTLY monotone + submodular per
    realization, so the average over the SAME ``n_sims`` live worlds is a pure,
    order-independent function of S. This is what makes CELF exactly equal to naive greedy
    and makes empirical submodularity hold sharply rather than being blurred by each set
    seeing a different edge world.

    (Contrast: a BFS that flips coins as it traverses gives a coin to edge (u,w) at a
    position that depends on which set's BFS reaches u first, so the same edge would get
    different coins for different sets — that blurs submodularity. Keying the coin to the
    edge index fixes the world.)

    If ``base_seed`` is None, the passed ``rng`` stream is consumed directly (each call
    advances it), giving independent-across-calls sampling (used only where per-call
    independence is wanted, e.g. quick determinism checks).
    """
    if not seed_set:
        return 0.0
    succ = {node: list(graph.successors(node)) for node in graph.nodes()}
    seed_list = list(seed_set)

    # BFS-coin path (base_seed None): flips coins on traversal — independent per call.
    if base_seed is None:
        total = 0
        for _ in range(n_sims):
            active: Set[int] = set(seed_list)
            frontier = list(seed_list)
            while frontier:
                new_frontier: List[int] = []
                for u in frontier:
                    for w in succ[u]:
                        if w not in active and rng.random() < p:
                            active.add(w)
                            new_frontier.append(w)
                frontier = new_frontier
            total += len(active)
        return total / n_sims

    # Live-edge world path (CRN): fix each realization's live subgraph by an edge-keyed
    # coin, then count reachability from S. Edge order is stable (sorted) so edge_index
    # is identical across every seed set for a given (base_seed, realization).
    edges = sorted(graph.edges())
    total = 0
    for i in range(n_sims):
        r = random.Random(base_seed * 1_000_003 + i * 2_654_435_761)
        live: Dict[int, List[int]] = {node: [] for node in graph.nodes()}
        for (u, w) in edges:
            if r.random() < p:
                live[u].append(w)
        active = set(seed_list)
        frontier = list(seed_list)
        while frontier:
            new_frontier = []
            for u in frontier:
                for w in live[u]:
                    if w not in active:
                        active.add(w)
                        new_frontier.append(w)
            frontier = new_frontier
        total += len(active)
    return total / n_sims


def influence_spread_batch(graph: nx.DiGraph, seed_sets: Sequence[Sequence[int]], *,
                           p: float, n_sims: int, base_seed: int) -> List[float]:
    """Estimate sigma(S) for SEVERAL seed sets on the SAME shared live-edge worlds.

    For each of ``n_sims`` realizations, the live subgraph is built exactly ONCE (edge
    coins keyed to ``(base_seed, realization, edge_index)``) and reachability is then
    computed for every seed set against that single world. Because all seed sets see the
    identical world, the per-realization submodularity/monotonicity relationships between
    them are EXACT (no cross-set MC noise) — this is the estimator used for the
    submodularity gate and greedy-vs-opt, and it is far cheaper than rebuilding the world
    per set (one O(E) build amortized over all sets). Returns sigma estimates aligned
    with ``seed_sets``.
    """
    edges = sorted(graph.edges())
    nodes = list(graph.nodes())
    totals = [0 for _ in seed_sets]
    for i in range(n_sims):
        r = random.Random(base_seed * 1_000_003 + i * 2_654_435_761)
        live: Dict[int, List[int]] = {node: [] for node in nodes}
        rr = r.random
        for (u, w) in edges:
            if rr() < p:
                live[u].append(w)
        for j, sset in enumerate(seed_sets):
            active = set(sset)
            frontier = list(sset)
            while frontier:
                new_frontier = []
                for u in frontier:
                    for w in live[u]:
                        if w not in active:
                            active.add(w)
                            new_frontier.append(w)
                frontier = new_frontier
            totals[j] += len(active)
    return [t / n_sims for t in totals]


def _reachable_size_liveedge(succ: Dict[int, List[int]], seed_set: Sequence[int],
                             p: float, rng: random.Random) -> Set[int]:
    """One live-edge realization: BFS from the seed set where each traversed edge is
    kept independently with probability p. Returns the reached set. (KKT 2003 Claim
    2.3: this is distributionally identical to one IC realization.)"""
    active: Set[int] = set(seed_set)
    frontier = list(seed_set)
    while frontier:
        new_frontier: List[int] = []
        for u in frontier:
            for w in succ[u]:
                if w not in active and rng.random() < p:
                    active.add(w)
                    new_frontier.append(w)
        frontier = new_frontier
    return active


# ── Percolation sweep (P1) ────────────────────────────────────────────────────

def single_seed_reach_sweep(n: int, lambdas: Sequence[float], *, z: float,
                            n_graphs: int, seed_base: int = 0) -> List[Dict[str, Any]]:
    """For each target lambda = p*z, build ``n_graphs`` fresh directed G(n, z) graphs,
    run ONE IC cascade from a single random seed on each (p = lambda / z), and record
    the mean final reached fraction. This is the percolation-transition sweep (P1):
    the mean reached fraction jumps from ~0 (sub-critical) to a macroscopic fraction
    (super-critical) as lambda crosses ~1.

    Deterministic: graph ``i`` at each lambda uses seed ``seed_base + i``, and the
    cascade RNG is seeded from the same index.
    """
    out: List[Dict[str, Any]] = []
    for lam in lambdas:
        p = lam / z
        fracs: List[float] = []
        for i in range(n_graphs):
            g = build_directed_er(n, z, seed=seed_base + i)
            seed_node = (seed_base + i) % n
            rng = random.Random(1_000_000 + seed_base + i)
            reached = _reachable_size_liveedge(
                {node: list(g.successors(node)) for node in g.nodes()},
                [seed_node], p, rng)
            fracs.append(len(reached) / n if n else 0.0)
        mean_frac = sum(fracs) / len(fracs) if fracs else 0.0
        out.append({"lambda": lam, "p": p, "z": z, "n": n,
                    "n_graphs": n_graphs, "mean_reached_fraction": mean_frac,
                    "reached_fractions": fracs})
    return out


def find_transition_crossing(sweep: Sequence[Dict[str, Any]], *,
                             crossing_fraction: float = 0.10) -> Optional[float]:
    """Estimate the lambda at which the mean reached fraction first crosses
    ``crossing_fraction`` (linear interpolation between the bracketing sweep points).
    Returns None if it never crosses within the swept range."""
    pts = sorted(sweep, key=lambda r: r["lambda"])
    for a, b in zip(pts, pts[1:]):
        fa, fb = a["mean_reached_fraction"], b["mean_reached_fraction"]
        if fa < crossing_fraction <= fb:
            la, lb = a["lambda"], b["lambda"]
            if fb == fa:
                return la
            return la + (crossing_fraction - fa) * (lb - la) / (fb - fa)
    return None


# ── Submodularity gate (P2) ───────────────────────────────────────────────────

def submodularity_test(graph: nx.DiGraph, *, p: float, n_pairs: int, n_sims: int,
                       max_set_size: int = 10, rng: Optional[random.Random] = None,
                       base_seed: int = 20259) -> Dict[str, Any]:
    """Test the discriminating property: influence spread is SUBMODULAR — for nested
    seed sets A subset of B and a vertex v not in B, the MARGINAL gain of adding v is
    larger for the smaller set (diminishing returns):

        sigma(A + v) - sigma(A)  >=  sigma(B + v) - sigma(B).

    Draws ``n_pairs`` random nested pairs (A, B, v): pick a random 1..max_set_size
    subset B, take A as a random proper subset of B, and v a random non-member.
    Estimates each sigma by ``n_sims`` Monte-Carlo cascades (shared per-quantity RNG
    stream, independent across the four quantities of a pair). Records the fraction of
    pairs for which submodularity holds (allowing a tiny MC tolerance).

    Returns the holding fraction, the count, and per-pair marginal gains.
    """
    rng = rng or random.Random(0)
    nodes = list(graph.nodes())
    n = len(nodes)
    tol = 1e-9
    n_hold = 0
    records: List[Dict[str, Any]] = []
    for _ in range(n_pairs):
        # Random nested pair A subset B, v not in B.
        size_b = rng.randint(2, max(2, min(max_set_size, n - 1)))
        B = rng.sample(nodes, size_b)
        size_a = rng.randint(1, size_b - 1)
        A = rng.sample(B, size_a)
        remaining = [x for x in nodes if x not in B]
        if not remaining:
            continue
        v = rng.choice(remaining)

        A_set, B_set = list(A), list(B)
        Av = A_set + [v]
        Bv = B_set + [v]

        # Common random numbers: all four sigmas of THIS pair are estimated on the SAME
        # per-pair live-edge worlds (one world-build per realization, shared across the
        # four sets), so the marginal-gain comparison is apples-to-apples and the
        # per-realization submodularity inequality is exact (not MC-blurred).
        pair_seed = base_seed + len(records)
        sig_A, sig_Av, sig_B, sig_Bv = influence_spread_batch(
            graph, [A_set, Av, B_set, Bv], p=p, n_sims=n_sims, base_seed=pair_seed)

        gain_A = sig_Av - sig_A
        gain_B = sig_Bv - sig_B
        holds = gain_A + tol >= gain_B
        n_hold += 1 if holds else 0
        records.append({
            "size_A": len(A_set), "size_B": len(B_set),
            "gain_A": gain_A, "gain_B": gain_B, "holds": holds,
            "diff": gain_A - gain_B,
        })
    n_eval = len(records)
    return {
        "n_pairs": n_eval,
        "n_hold": n_hold,
        "hold_fraction": n_hold / n_eval if n_eval else 0.0,
        "n_sims": n_sims,
        "p": p,
        "records": records,
    }


# ── Influence maximization: greedy / CELF / OPT (P3) ──────────────────────────

def greedy_seed_set(graph: nx.DiGraph, k: int, *, p: float, n_sims: int,
                    rng: Optional[random.Random] = None, base_seed: int = 777,
                    use_celf: bool = True) -> Tuple[List[int], float, int]:
    """Greedy influence maximization (KKT 2003): start from the empty set and add, at
    each of k rounds, the vertex with the largest MARGINAL influence gain, estimating
    sigma by Monte-Carlo.

    All sigma estimates share ONE common-random-number stream (``base_seed``), so every
    candidate set is scored on the same ``n_sims`` random worlds. This makes sigma an
    order-independent function of the set, which in turn makes the two facts below exact
    rather than MC-approximate.

    With ``use_celf=True`` this uses the CELF lazy-evaluation optimization
    (Leskovec et al. 2007): keep a max-priority queue of upper-bound marginal gains;
    only re-evaluate the top candidate's gain, and if it stays on top it is exact by
    submodularity. Under shared CRN worlds CELF returns the SAME seed set as naive
    greedy (it is exact, just far fewer sigma evaluations) — verified equal in the tests.

    ``rng`` is accepted for API symmetry but ignored when ``base_seed`` drives the CRN
    estimator. Returns (seed_set, sigma(seed_set) estimate, number of sigma evaluations).
    """
    nodes = list(graph.nodes())
    selected: List[int] = []
    n_evals = 0

    def sigma(sset: List[int]) -> float:
        return influence_spread(graph, sset, p=p, n_sims=n_sims, base_seed=base_seed)

    if not use_celf:
        cur_sigma = 0.0
        for _ in range(k):
            best_v, best_gain, best_sigma = None, -1.0, cur_sigma
            for v in nodes:
                if v in selected:
                    continue
                sig = sigma(selected + [v])
                n_evals += 1
                gain = sig - cur_sigma
                if gain > best_gain:
                    best_v, best_gain, best_sigma = v, gain, sig
            if best_v is None:
                break
            selected.append(best_v)
            cur_sigma = best_sigma
        return selected, cur_sigma, n_evals

    # CELF lazy greedy (exact under shared CRN worlds).
    # Round 1: evaluate every singleton gain. Ties broken by node id so naive greedy
    # (which scans nodes in order and keeps the FIRST max) and CELF agree exactly.
    heap: List[Tuple[float, int, int]] = []   # (-gain, node, last_updated_round)
    for v in nodes:
        sig = sigma([v])
        n_evals += 1
        heap.append((-sig, v, 0))
    heap.sort()                               # by (-gain, node): best gain, lowest id first
    top = heap.pop(0)
    selected.append(top[1])
    cur_sigma = -top[0]
    round_idx = 1

    while len(selected) < k and heap:
        # Re-evaluate the current top-of-heap lazily until it is up-to-date and still on
        # top; then by submodularity it is the exact best marginal gain.
        while True:
            neg_gain, v, last_round = heap[0]
            if last_round == round_idx:
                break
            new_gain = sigma(selected + [v]) - cur_sigma
            n_evals += 1
            heap[0] = (-new_gain, v, round_idx)
            heap.sort()
        neg_gain, v, _ = heap.pop(0)
        selected.append(v)
        cur_sigma += -neg_gain
        round_idx += 1

    final_sigma = sigma(selected)
    n_evals += 1
    return selected, final_sigma, n_evals


def brute_force_opt(graph: nx.DiGraph, k: int, *, p: float, n_sims: int,
                    rng: Optional[random.Random] = None, base_seed: int = 777
                    ) -> Tuple[List[int], float]:
    """Exact OPT for influence maximization by exhaustively evaluating every k-subset
    of the vertex set (feasible only for small n and k). Every subset is scored on the
    same CRN worlds as ``greedy_seed_set`` (share ``base_seed``) so greedy-vs-OPT is a
    fair apples-to-apples comparison. Use only on small instances (n <= ~200, k <= 3)."""
    from itertools import combinations
    nodes = list(graph.nodes())
    best_set: List[int] = []
    best_sigma = -1.0
    for combo in combinations(nodes, k):
        sig = influence_spread(graph, list(combo), p=p, n_sims=n_sims, base_seed=base_seed)
        if sig > best_sigma:
            best_sigma = sig
            best_set = list(combo)
    return best_set, best_sigma


def random_seed_set(graph: nx.DiGraph, k: int, *, p: float, n_sims: int,
                    rng: random.Random, base_seed: int = 777) -> Tuple[List[int], float]:
    """A random k-vertex baseline (the control greedy must beat). The k vertices are
    drawn from ``rng``; the resulting set is scored on the same CRN worlds as greedy."""
    nodes = list(graph.nodes())
    chosen = rng.sample(nodes, min(k, len(nodes)))
    sig = influence_spread(graph, chosen, p=p, n_sims=n_sims, base_seed=base_seed)
    return chosen, sig
