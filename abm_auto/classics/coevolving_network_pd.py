"""Coevolving-network Prisoner's Dilemma (Santos, Pacheco & Lenaerts 2006) — a
faithful agent-based reproduction.

Source: Santos, F.C., Pacheco, J.M. & Lenaerts, T. (2006), "Cooperation prevails
when individuals adjust their social ties", PLoS Comput Biol 2(10):e140.
doi:10.1371/journal.pcbi.0020140.

The novelty of this model — versus a STATIC spatial/network PD (e.g. Nowak-May's
fixed lattice) — is that the CONTACT NETWORK itself co-evolves with the strategies:
a cooperator being exploited by a defecting partner can react by breaking that tie
and rewiring it to someone else. Strategy dynamics (who cooperates) and structural
dynamics (who is linked to whom) are entangled at a controllable timescale ratio W.

Model (verified against the paper):
  * N agents on a HOMOGENEOUS random graph — every node starts with the SAME degree
    z (a random regular graph). The number of edges (= N*z/2) is CONSERVED for the
    whole run: rewiring only ever MOVES the endpoint of an existing edge, never
    creates or destroys one, so the average degree is exactly z at every moment
    (individual degrees fluctuate as ties are redirected).
  * One-shot PD played by every agent against ALL its current neighbours. In the
    b/c-scaled payoffs used in the paper: R (mutual cooperation), P (mutual
    defection), T (temptation, defect vs a cooperator), S (sucker, cooperate vs a
    defector). The hard reproduction point is T=2, R=1, P=0, S=-1  (⇒ b/c = 2). An
    agent's fitness is the SUM of its payoffs over all its neighbours.
  * Selection strength β enters a Fermi (pairwise-comparison) update: agent A picks a
    random neighbour B and copies B's strategy with probability
        p = 1 / (1 + exp(-β * (fitness_B - fitness_A))).
    (β small ⇒ weak selection; β→∞ ⇒ deterministic imitate-the-better.)
  * Timescale ratio W entangles the two dynamics. Each ELEMENTARY step is, with
    probability 1/(1+W), a STRATEGY update (the Fermi step above), and otherwise
    (probability W/(1+W)) a STRUCTURAL update:
        pick a directed active link A→B where A is a COOPERATOR and B is a DEFECTOR
        (A is "dissatisfied": it is being exploited). A wants to sever the tie. A
        rewires its end of the (A,B) edge away from B toward a NEW partner: with the
        paper's convention the winner of the A/B comparison keeps the tie's other
        endpoint. Here the dissatisfied cooperator A redirects the link to a
        uniformly random node C (C != A, not already A's neighbour), so the edge
        count and A's own degree are preserved; B loses one neighbour and C gains
        one. If A wins/loses is resolved by the same Fermi rule so the more
        successful strategist tends to keep/attract ties. W = 0 is the STATIC-graph
        control (structure never changes — only strategies evolve on the frozen
        homogeneous random graph).

  A generation = N elementary steps (each agent updated once on average). The run
  proceeds to a steady state; the graded observable is the steady-state fraction of
  cooperators, averaged over the trailing window and over independent realizations.

STATIC-GRAPH CONTROL (W=0): the exact same model with the structural update turned
off — the homogeneous random graph is frozen and only strategies evolve under the
Fermi rule. This is the fair "no rewiring" control and is precisely the arm the
locked P1 grades (at b/c=2 the static homogeneous graph cannot sustain cooperation).

Built on the neutral platform (``abm_auto._platform``): each node is a ``PDNode``
carrying its own C/D strategy; ``CoevolvingNetworkPD`` owns the adjacency (an array
of neighbour ``set``s for O(1) membership / rewiring), the two entangled micro-rules,
and a ``DataCollector`` recording the per-generation cooperator fraction. Payoff
accumulation is done once per generation over the adjacency (O(N*z)); the elementary
strategy/structural steps read those cached fitnesses.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector

COOPERATE = "C"
DEFECT = "D"


# -- Agent --------------------------------------------------------------------

class PDNode(Agent):
    """One network node: a pure cooperator (C) or defector (D).

    The two micro-rules (Fermi strategy imitation, cooperator-rewires-from-defector)
    are driven at the model level over the shared adjacency, so the per-agent ``step``
    is intentionally a no-op — this is an elementary-step (not a synchronous-tick)
    dynamics and there is no autonomous single-agent update."""

    def __init__(self, agent_id: int, model: "CoevolvingNetworkPD", *,
                 strategy: str) -> None:
        super().__init__(agent_id, model)
        self.strategy = strategy

    def step(self) -> None:  # pragma: no cover - dynamics live on the model
        return None


# -- Model --------------------------------------------------------------------

class CoevolvingNetworkPD(AgentModel):
    """Santos-Pacheco-Lenaerts (2006) coevolving-network PD.

    Construct with N, degree z, the PD payoffs (T, R, P, S), the selection strength
    β, the timescale ratio W, the initial cooperator fraction, and a seed. ``run``
    advances elementary steps (N per generation) to a steady state and records the
    per-generation cooperator fraction. ``W = 0`` freezes the graph (static control)."""

    def __init__(self, n: int = 1000, *, z: int = 30,
                 T: float = 2.0, R: float = 1.0, P: float = 0.0, S: float = -1.0,
                 beta: float = 0.005, W: float = 2.0,
                 init_coop_fraction: float = 0.5, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if z <= 0 or z >= n:
            raise ValueError(f"need 0 < z < n (got z={z}, n={n})")
        if (n * z) % 2 != 0:
            raise ValueError(f"n*z must be even for a z-regular graph (got n={n}, z={z})")
        if W < 0:
            raise ValueError(f"need W >= 0 (got {W})")
        if beta < 0:
            raise ValueError(f"need beta >= 0 (got {beta})")
        if not (0.0 <= init_coop_fraction <= 1.0):
            raise ValueError(f"need 0 <= init_coop_fraction <= 1 (got {init_coop_fraction})")

        self.seed_value = seed
        self.n = n
        self.z = z
        self.T = float(T)
        self.R = float(R)
        self.P = float(P)
        self.S = float(S)
        self.beta = float(beta)
        self.W = float(W)
        self.init_coop_fraction = float(init_coop_fraction)
        # Probability that an elementary step is a STRUCTURAL update (else strategy).
        self.p_structural = self.W / (1.0 + self.W)

        # Homogeneous random graph: every node degree z, edges conserved thereafter.
        # adj[i] is the set of i's current neighbours (O(1) membership + rewire).
        self.adj: List[set] = self._build_regular_graph(n, z)
        self.n_edges = sum(len(s) for s in self.adj) // 2

        # Random initial C/D placement (RNG use #1; the graph draw is RNG use #0).
        self.nodes: List[PDNode] = []
        for i in range(n):
            strat = COOPERATE if self.rng.random() < self.init_coop_fraction else DEFECT
            node = PDNode(i, self, strategy=strat)
            self.nodes.append(node)
            self.add_agent(node)
        # strategy[i] mirrors nodes[i].strategy as a fast bool array (True == C).
        self.is_coop: List[bool] = [nd.strategy == COOPERATE for nd in self.nodes]
        # cached per-node fitness (sum of PD payoffs over neighbours), refreshed each gen.
        self.fitness: List[float] = [0.0] * n

        self.reporter = DataCollector({"coop_fraction": lambda m: m.cooperator_fraction()})

    # -- graph construction ---------------------------------------------------
    def _build_regular_graph(self, n: int, z: int) -> List[set]:
        """A random z-regular graph on n nodes via the pairing (configuration) model
        with edge-swap REPAIR of self-loops / multi-edges. Every node ends with degree
        exactly z and there are n*z/2 distinct edges. Deterministic given the seed.

        Rather than restart the whole draw on the first collision (which almost never
        completes for large n*z), we lay down all n*z/2 stub-pairs — allowing a few
        self-loops / doubled edges — then repair each defect with a degree-preserving
        edge swap: for a bad edge (a,b), find a clean edge (c,d) such that swapping to
        (a,c)+(b,d) removes the defect without creating a new one. Edge swaps conserve
        every node's degree, so the result is still exactly z-regular and simple."""
        rng = self.rng
        for _attempt in range(50):
            edges = self._pairing_edges(n, z, rng)
            adj = self._repair_to_simple(edges, n, z, rng)
            if adj is not None:
                return adj
        raise RuntimeError(
            f"failed to draw a simple z-regular graph (n={n}, z={z}) in 50 attempts")

    @staticmethod
    def _pairing_edges(n: int, z: int, rng) -> List[Tuple[int, int]]:
        """Configuration-model stub pairing: n*z/2 random pairs (may contain a few
        self-loops / repeated pairs, repaired afterward)."""
        stubs: List[int] = []
        for node in range(n):
            stubs.extend([node] * z)
        rng.shuffle(stubs)
        return [(stubs[k], stubs[k + 1]) for k in range(0, len(stubs), 2)]

    @staticmethod
    def _repair_to_simple(edges, n: int, z: int, rng) -> Optional[List[set]]:
        """Repair a stub-paired multigraph into a simple z-regular graph by
        degree-preserving edge swaps. Returns the adjacency, or None if repair got
        stuck (caller retries with a fresh pairing).

        Maintains ``present`` (a set of undirected-edge keys) and a queue of defect
        indices incrementally, so each repair is near-O(1) amortised rather than a
        full O(E) rescan (important at E = n*z/2 ~ 1.5e4)."""
        def key(a, b):
            return (a, b) if a <= b else (b, a)

        edge_list = list(edges)
        present: Dict[Tuple[int, int], int] = {}   # edge key -> count
        defects: List[int] = []
        for idx, (a, b) in enumerate(edge_list):
            if a == b:
                defects.append(idx)
                continue
            k = key(a, b)
            cnt = present.get(k, 0)
            if cnt >= 1:
                defects.append(idx)     # this occurrence is a duplicate -> defect
            present[k] = cnt + 1

        budget = 100 * (len(edge_list) + 1)
        while defects and budget > 0:
            budget -= 1
            bad_index = defects[-1]
            a, b = edge_list[bad_index]
            # is this still a defect? (a prior swap may have cleaned it)
            k_ab = key(a, b)
            if a != b and present.get(k_ab, 0) <= 1:
                defects.pop()
                continue
            # find a random clean edge (c,d) to swap: (a,b)+(c,d)->(a,c)+(b,d).
            fixed = False
            for _try in range(200):
                j = rng.randrange(len(edge_list))
                if j == bad_index:
                    continue
                c, d = edge_list[j]
                if c == d:
                    continue          # don't swap against another self-loop
                if a == c or b == d:
                    continue          # would make a self-loop
                new1 = key(a, c)
                new2 = key(b, d)
                if new1 == new2:
                    continue
                # neither new edge may already exist (excluding the two we remove).
                if present.get(new1, 0) > 0 or present.get(new2, 0) > 0:
                    continue
                # commit the swap: update present-counts and edge_list.
                present[k_ab] = present.get(k_ab, 0) - 1
                kcd = key(c, d)
                present[kcd] = present.get(kcd, 0) - 1
                present[new1] = present.get(new1, 0) + 1
                present[new2] = present.get(new2, 0) + 1
                edge_list[bad_index] = (a, c)
                edge_list[j] = (b, d)
                defects.pop()
                fixed = True
                break
            if not fixed:
                return None
        if defects:
            return None
        adj: List[set] = [set() for _ in range(n)]
        for a, b in edge_list:
            adj[a].add(b)
            adj[b].add(a)
        if all(len(s) == z for s in adj):
            return adj
        return None

    # -- metrics --------------------------------------------------------------
    def cooperator_count(self) -> int:
        return sum(1 for c in self.is_coop if c)

    def cooperator_fraction(self) -> float:
        return self.cooperator_count() / self.n if self.n else 0.0

    def mean_degree(self) -> float:
        return (2.0 * self.n_edges) / self.n if self.n else 0.0

    # -- payoffs --------------------------------------------------------------
    def _pair_payoff(self, i_is_coop: bool, j_is_coop: bool) -> float:
        """Payoff to player i (with strategy i_is_coop) in one PD game against j."""
        if i_is_coop:
            return self.R if j_is_coop else self.S
        return self.T if j_is_coop else self.P

    def compute_fitnesses(self) -> None:
        """Refresh every node's fitness = SUM of PD payoffs over its current
        neighbours (the SPL accumulated-payoff convention). O(N*z) over the
        adjacency; called once per generation before that generation's elementary
        steps read the cached values."""
        R, S, T, P = self.R, self.S, self.T, self.P
        is_coop = self.is_coop
        fit = self.fitness
        for i in range(self.n):
            neigh = self.adj[i]
            if not neigh:
                fit[i] = 0.0
                continue
            n_coop = 0
            for j in neigh:
                if is_coop[j]:
                    n_coop += 1
            deg = len(neigh)
            n_def = deg - n_coop
            if is_coop[i]:
                fit[i] = R * n_coop + S * n_def
            else:
                fit[i] = T * n_coop + P * n_def

    # -- Fermi rule -----------------------------------------------------------
    def fermi_prob(self, fitness_focal: float, fitness_other: float) -> float:
        """Fermi (pairwise-comparison) probability that the focal player copies the
        OTHER player: p = 1 / (1 + exp(-β (fitness_other - fitness_focal))). Guarded
        against overflow for large |Δ|."""
        delta = self.beta * (fitness_other - fitness_focal)
        if delta >= 0:
            # p = 1/(1+e^{-delta}); for large delta -> 1
            if delta > 700:
                return 1.0
            return 1.0 / (1.0 + math.exp(-delta))
        else:
            if delta < -700:
                return 0.0
            e = math.exp(delta)
            return e / (1.0 + e)

    # -- elementary steps -----------------------------------------------------
    def strategy_step(self) -> None:
        """One STRATEGY elementary step: pick a random agent A with >=1 neighbour and
        a random neighbour B; A copies B's strategy with the Fermi probability
        p = 1/(1+exp(-β(fit_B - fit_A))). Fitnesses are the cached per-generation
        values."""
        rng = self.rng
        a = rng.randrange(self.n)
        neigh_a = self.adj[a]
        if not neigh_a:
            return
        b = _random_from_set(neigh_a, rng)
        if self.is_coop[a] == self.is_coop[b]:
            return  # nothing to copy (same strategy)
        p = self.fermi_prob(self.fitness[a], self.fitness[b])
        if rng.random() < p:
            self.is_coop[a] = self.is_coop[b]
            self.nodes[a].strategy = self.nodes[b].strategy

    def structural_step(self) -> None:
        """One STRUCTURAL elementary step (only fires when W > 0): find an ACTIVE link
        A→B with A a cooperator and B a defector (A is being exploited). The
        dissatisfied A wants to redirect its end of the (A,B) tie. The paper resolves
        who keeps the contested endpoint by the same Fermi comparison; here, with
        probability p = Fermi(fit_A, fit_B) the *defector B's* strategy is the more
        successful and A fails to escape (keeps the tie), otherwise A rewires the
        (A,B) edge to a fresh uniformly-random node C (C != A, not already adjacent).
        Rewiring MOVES one edge endpoint: edge count and A's degree are conserved; B
        loses a neighbour and C gains one."""
        rng = self.rng
        # sample a dissatisfied cooperator A that currently has a defecting neighbour.
        a = rng.randrange(self.n)
        if not self.is_coop[a]:
            return  # only cooperators are dissatisfied (being exploited)
        neigh_a = self.adj[a]
        if not neigh_a:
            return
        # collect A's defecting neighbours (the exploiters A would like to drop)
        defectors = [j for j in neigh_a if not self.is_coop[j]]
        if not defectors:
            return  # A has no defecting partner this step -> no structural change
        b = defectors[rng.randrange(len(defectors))]
        # Fermi: with prob p the defector B is "more fit" and A stays tied to B;
        # otherwise A escapes and rewires the (A,B) edge to a new partner C.
        p_stay = self.fermi_prob(self.fitness[a], self.fitness[b])
        if rng.random() < p_stay:
            return  # A fails to sever (the exploiter prevails this step)
        c = self._pick_new_partner(a)
        if c is None:
            return  # no valid rewiring target (A already saturated) -> keep the tie
        # move A's endpoint of the (A,B) edge from B to C (edge count conserved).
        self.adj[a].discard(b)
        self.adj[b].discard(a)
        self.adj[a].add(c)
        self.adj[c].add(a)

    def _pick_new_partner(self, a: int) -> Optional[int]:
        """A uniformly random node C to receive A's redirected tie: C != A and not
        already A's neighbour. Returns None if A is adjacent to everyone else."""
        rng = self.rng
        neigh_a = self.adj[a]
        # A can link to at most n-1 others; if already saturated, no target exists.
        if len(neigh_a) >= self.n - 1:
            return None
        for _ in range(64):
            c = rng.randrange(self.n)
            if c != a and c not in neigh_a:
                return c
        # dense fallback: enumerate the valid targets and pick one.
        candidates = [c for c in range(self.n) if c != a and c not in neigh_a]
        if not candidates:
            return None
        return candidates[rng.randrange(len(candidates))]

    def elementary_step(self) -> None:
        """One elementary step: STRUCTURAL with probability W/(1+W) (only when W>0),
        else a STRATEGY update. When W=0 every step is a strategy update (the static
        graph)."""
        if self.p_structural > 0.0 and self.rng.random() < self.p_structural:
            self.structural_step()
        else:
            self.strategy_step()

    # -- generation tick ------------------------------------------------------
    def step(self) -> None:
        """One generation = N elementary steps. Fitnesses are refreshed from the
        current graph + strategies ONCE at the start of the generation (the SPL
        accumulated-payoff snapshot); the N elementary steps then read those cached
        fitnesses. Records the cooperator fraction and advances t."""
        self.compute_fitnesses()
        for _ in range(self.n):
            self.elementary_step()
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_generations: int = 2000, *, measure_last: int = 200,
            absorb_check: bool = True) -> Dict[str, Any]:  # type: ignore[override]
        """Advance ``n_generations`` generations; return the run summary.

        ``measure_last`` is the trailing window over which the steady-state cooperator
        fraction is averaged. If ``absorb_check`` is set the run stops early once the
        population is ABSORBED (all-C or all-D): under the Fermi rule an all-one-strategy
        state is invariant for the strategy dynamics, so continuing wastes work. The
        final recorded value is then held for the remainder of the (un-run) generations
        when computing the steady tail, so early-stop and full-run give the same tail
        mean."""
        if measure_last <= 0 or measure_last > n_generations + 1:
            raise ValueError(
                f"measure_last must be in [1, n_generations+1] "
                f"(got {measure_last}, n_generations={n_generations})")
        self.reporter.collect(self)  # t=0 baseline (initial random placement)
        gens_run = 0
        absorbed = False
        for _ in range(n_generations):
            self.step()
            gens_run += 1
            if absorb_check:
                frac = self.cooperator_fraction()
                # Absorbed iff every node shares one strategy AND (for W>0) no active
                # link remains to rewire — i.e. the dynamics can no longer change
                # anything. All-C or all-D freezes the strategy dynamics; with a single
                # strategy there are no C-D active links, so structure freezes too.
                if frac <= 0.0 or frac >= 1.0:
                    absorbed = True
                    break
        series = list(self.reporter.series("coop_fraction"))
        # If the run ABSORBED early (all-C or all-D is a fixed point that never moves
        # again), the true steady state IS that absorbed value. Pad the recorded series
        # out to the full horizon with the absorbed value so the trailing-window steady
        # estimate reflects the fixed point, not the descent transient that preceded it.
        # (This is a correctness fix for the steady observable, NOT tuning: an absorbed
        # all-D run has steady cooperation 0, which is what P1/P3 measure.)
        if absorbed:
            full_len = n_generations + 1  # t=0 baseline + n_generations
            series = series + [series[-1]] * (full_len - len(series))
        return {
            "n": self.n,
            "z": self.z,
            "T": self.T, "R": self.R, "P": self.P, "S": self.S,
            "b_over_c": (self.T / self.R) if self.R else None,
            "beta": self.beta,
            "W": self.W,
            "p_structural": self.p_structural,
            "init_coop_fraction": self.init_coop_fraction,
            "seed": self.seed_value,
            "n_generations": n_generations,
            "generations_run": gens_run,
            "measure_last": measure_last,
            "n_edges": self.n_edges,
            "mean_degree": self.mean_degree(),
            "steady_coop_fraction": tail_mean(series, window=measure_last),
            "final_coop_fraction": series[-1],
            "coop_series": series,
        }


# -- summary helpers ----------------------------------------------------------

def _random_from_set(s: set, rng) -> int:
    """Uniformly pick one element from a non-empty set (sets are unordered; we
    materialise once — the neighbour sets are small, ~z elements)."""
    return rng.choice(tuple(s))


def tail_mean(series: Sequence[float], *, window: int = 200) -> float:
    """Steady-state estimate = mean of the trailing ``window`` of a series (or the
    whole series if shorter). Averaging the tail smooths finite-N jitter and discards
    the transient before measurement. An absorbed run (which stops early) has its final
    value dominate the tail, which is correct: the population no longer moves."""
    if not series:
        return 0.0
    tail = series[-window:] if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def run_single(n: int = 1000, *, z: int = 30, T: float = 2.0, R: float = 1.0,
               P: float = 0.0, S: float = -1.0, beta: float = 0.005, W: float = 2.0,
               init_coop_fraction: float = 0.5, seed: int = 0,
               n_generations: int = 2000, measure_last: int = 200) -> Dict[str, Any]:
    """One coevolving-network PD run at a given (W, seed) and the fixed PD parameters."""
    return CoevolvingNetworkPD(
        n, z=z, T=T, R=R, P=P, S=S, beta=beta, W=W,
        init_coop_fraction=init_coop_fraction, seed=seed).run(
        n_generations, measure_last=measure_last)


def run_many_seeds(n: int = 1000, *, z: int = 30, T: float = 2.0, R: float = 1.0,
                   P: float = 0.0, S: float = -1.0, beta: float = 0.005, W: float = 2.0,
                   init_coop_fraction: float = 0.5, n_seeds: int = 20, seed_base: int = 0,
                   n_generations: int = 2000, measure_last: int = 200) -> Dict[str, Any]:
    """Run ``n_seeds`` independent realizations (seed ``seed_base + i``) at a fixed W and
    the fixed PD parameters, and summarise the steady-state cooperator fraction across
    realizations (mean + spread).

    Returns per-seed steady + final cooperator fractions, their mean / std / min / max,
    the mean number of generations actually run (early-stop on absorption), and one
    representative cooperator-fraction trajectory (first seed) for inspection."""
    runs = [run_single(n, z=z, T=T, R=R, P=P, S=S, beta=beta, W=W,
                        init_coop_fraction=init_coop_fraction, seed=seed_base + i,
                        n_generations=n_generations, measure_last=measure_last)
            for i in range(n_seeds)]
    per_seed_steady = [rr["steady_coop_fraction"] for rr in runs]
    per_seed_final = [rr["final_coop_fraction"] for rr in runs]
    per_seed_gens = [rr["generations_run"] for rr in runs]
    mean_steady = sum(per_seed_steady) / n_seeds
    var_steady = sum((s - mean_steady) ** 2 for s in per_seed_steady) / n_seeds
    return {
        "n": n, "z": z, "T": T, "R": R, "P": P, "S": S,
        "b_over_c": (T / R) if R else None,
        "beta": beta, "W": W,
        "init_coop_fraction": init_coop_fraction,
        "n_seeds": n_seeds, "seed_base": seed_base,
        "n_generations": n_generations, "measure_last": measure_last,
        "per_seed_steady_coop": per_seed_steady,
        "per_seed_final_coop": per_seed_final,
        "per_seed_generations_run": per_seed_gens,
        "mean_steady_coop": mean_steady,
        "var_steady_coop": var_steady,
        "std_steady_coop": var_steady ** 0.5,
        "min_steady_coop": min(per_seed_steady),
        "max_steady_coop": max(per_seed_steady),
        "mean_generations_run": sum(per_seed_gens) / n_seeds,
        "example_coop_series": runs[0]["coop_series"],
    }
