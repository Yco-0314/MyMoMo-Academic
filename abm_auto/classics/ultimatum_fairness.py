"""Evolution of fairness in the ultimatum game (Nowak-Page-Sigmund 2000) — a
faithful agent-based reproduction.

Source: Nowak, M.A., Page, K.M. & Sigmund, K. (2000). "Fairness versus reason in the
ultimatum game." Science 289(5485):1773-1775. doi:10.1126/science.289.5485.1773.

The ultimatum game: a proposer is given a sum (normalised to 1) and offers a share to a
responder; the responder either accepts (proposer keeps 1-offer, responder gets the
offer) or rejects (both get nothing). Sub-game-perfect *rational* play is: offer the
smallest positive amount, and accept any positive amount — so a rational proposer keeps
almost everything. Humans instead offer near-fair splits and reject low offers. Nowak,
Page & Sigmund show that REPUTATION (a proposer's chance of knowing the responder's
acceptance threshold) is what tips an evolving population from the rational near-0 offer
toward fairness.

Model (the fixed rules, locked before running — see PREDICTIONS-locked.md):

  * A finite population of N ``PlayerAgent``s, each carrying a genotype (p, q) in [0,1]^2:
      - p = the offer it makes as PROPOSER (fraction of the pie it gives away);
      - q = the minimum offer it accepts as RESPONDER (its acceptance threshold).
    Init is FAIR: p and q are each drawn uniformly on [0,1] (mean 0.5), so the population
    starts neither selfish nor fair — any drift toward one is produced by selection.

  * Reputation weight w in [0,1] is the single treatment knob. In each proposer-responder
    encounter, with probability w the proposer KNOWS the responder's threshold q and
    best-responds (offers exactly q if that is worth doing, i.e. 1-q >= 0 which always
    holds, so it offers q and the deal goes through); with probability 1-w the proposer is
    anonymous and offers its own genotype p. w=0 is the anonymous one-shot game (a
    proposer can never see who it faces); w=1 is full reputation (the proposer always
    knows the responder). Only the OFFER channel uses reputation; acceptance is always by
    the responder's own q.

  * Payoff / fitness: every agent plays many encounters per generation, once as proposer
    against a random responder and once as responder against a random proposer (averaged
    over ``rounds_per_gen`` random partners for a smooth fitness estimate). An accepted
    offer x pays the proposer 1-x and the responder x; a rejected offer (x < responder's
    q) pays both 0. Fitness = accumulated payoff across all encounters this generation
    (shifted to be non-negative for proportional selection).

  * Reproduction = one generation of fitness-proportional replication with mutation
    (a Moran/replicator step at the population scale): the next generation's N genotypes
    are each drawn from a parent chosen with probability proportional to fitness, then
    mutated by a small Gaussian nudge on both p and q (clamped back into [0,1]). This is
    the canonical selection+mutation dynamic of evolutionary game theory; it is
    deterministic given a seed.

  * Outcome (LOCKED metrics) = the population-mean acceptance threshold q̄ and mean offer
    p̄ at steady state (mean over the last generations, averaged over seeds). The
    prediction is: w=0 collapses toward the rational near-0 offer (q̄ and p̄ small);
    w>=0.8 evolves fair offers (q̄, p̄ > 0.3); and q̄ rises monotonically with w.

The reputation channel is the ONLY thing that differs across treatments: N, the fair
uniform init, rounds_per_gen, mutation size, generation count, and the seed set are all
identical across the w-grid. No parameter is tuned to make fairness appear (batch lesson:
a falsified clause is reported as an honest MISS, not papered over).

Built on the neutral platform (``abm_auto._platform``): each player is a ``PlayerAgent``
carrying its (p, q) genotype and its generational fitness; the model owns the encounter
accounting, the fitness-proportional + mutation reproduction, and a ``DataCollector``
that records the population-mean (p̄, q̄) each generation — not a hand-rolled god-loop.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class PlayerAgent(Agent):
    """One player with a genotype (p, q) in [0,1]^2.

    ``p`` is the offer it makes as proposer; ``q`` is the minimum offer it accepts as
    responder. ``fitness`` accumulates this generation's payoff (reset each generation by
    the model). The genotype is the heritable unit: reproduction copies (p, q) from a
    fitness-selected parent and mutates it. The per-agent ``step`` is a no-op because the
    generational encounter + reproduction is a model-level synchronous update.
    """

    def __init__(self, agent_id: int, model: "UltimatumModel", *, p: float, q: float) -> None:
        super().__init__(agent_id, model)
        self.p = p
        self.q = q
        self.fitness = 0.0

    def step(self) -> None:  # pragma: no cover - the generation lives on the model
        """The generation (encounters + fitness-proportional reproduction) is a
        model-level synchronous update, not an autonomous single-agent step."""
        return None


# -- Model --------------------------------------------------------------------

class UltimatumModel(AgentModel):
    """Drives the evolutionary ultimatum game with a reputation channel.

    Construct with the population size N, the reputation weight ``w`` in [0,1], the number
    of random encounter partners per role per generation, the mutation size, and a seed.
    ``run(n_gens)`` iterates (encounters -> fitness -> fitness-proportional replication +
    mutation) and records the population-mean (p̄, q̄) each generation.
    """

    def __init__(self, n: int = 200, *, w: float = 0.0, rounds_per_gen: int = 10,
                 mutation: float = 0.02, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 1:
            raise ValueError(f"need n > 1 (got {n})")
        if not (0.0 <= w <= 1.0):
            raise ValueError(f"need 0 <= w <= 1 (got {w})")
        if rounds_per_gen <= 0:
            raise ValueError(f"need rounds_per_gen > 0 (got {rounds_per_gen})")
        if mutation < 0.0:
            raise ValueError(f"need mutation >= 0 (got {mutation})")
        self.seed_value = seed
        self.n = n
        self.w = float(w)
        self.rounds_per_gen = int(rounds_per_gen)
        self.mutation = float(mutation)

        # FAIR random init: p, q each uniform on [0,1] (population mean 0.5), so the start
        # is neither selfish nor fair. Any drift is produced by selection + reputation.
        self.agent_list: List[PlayerAgent] = []
        for i in range(n):
            p = self.rng.uniform(0.0, 1.0)
            q = self.rng.uniform(0.0, 1.0)
            agent = PlayerAgent(i, self, p=p, q=q)
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({
            "mean_p": lambda m: m.mean_offer(),
            "mean_q": lambda m: m.mean_threshold(),
        })

    # -- metrics --
    def mean_offer(self) -> float:
        """Population-mean proposer offer p̄ (a genotype average, independent of w)."""
        if self.n == 0:
            return 0.0
        return sum(a.p for a in self.agent_list) / self.n

    def mean_threshold(self) -> float:
        """Population-mean responder acceptance threshold q̄ (the primary locked metric)."""
        if self.n == 0:
            return 0.0
        return sum(a.q for a in self.agent_list) / self.n

    # -- one generation of payoffs --
    def _random_other(self, self_id: int) -> PlayerAgent:
        """A uniformly random agent != ``self_id`` (an encounter partner)."""
        rng = self.rng
        j = rng.randrange(self.n)
        while j == self_id:
            j = rng.randrange(self.n)
        return self.agent_list[j]

    def _offer_of(self, proposer: PlayerAgent, responder: PlayerAgent) -> float:
        """The offer a proposer makes to a given responder.

        With probability w the proposer KNOWS the responder's threshold q and
        best-responds — it offers exactly the responder's q (the minimum that still gets
        accepted, keeping 1-q for itself), which is always the payoff-maximising known
        response since keeping 1-q > 0 beats a rejected 0. With probability 1-w the
        proposer is anonymous and simply offers its own genotype p."""
        if self.w > 0.0 and self.rng.random() < self.w:
            return responder.q          # informed best-response: meet the threshold
        return proposer.p               # anonymous: offer own genotype

    def assign_fitness(self) -> None:
        """Reset fitness, then play ``rounds_per_gen`` encounters for each agent in EACH
        role (proposer against random responders, responder against random proposers) and
        accumulate payoff. An offer x is accepted iff x >= the responder's q, paying the
        proposer 1-x and the responder x; a rejected offer pays both 0."""
        for a in self.agent_list:
            a.fitness = 0.0
        rounds = self.rounds_per_gen
        for a in self.agent_list:
            # a acts as PROPOSER against random responders.
            for _ in range(rounds):
                responder = self._random_other(a.id)
                offer = self._offer_of(a, responder)
                if offer >= responder.q:
                    a.fitness += (1.0 - offer)        # proposer keeps the rest
                    responder.fitness += offer         # responder gets the offer
                # rejected -> both get 0 (no change)
            # a acts as RESPONDER against random proposers.
            for _ in range(rounds):
                proposer = self._random_other(a.id)
                offer = self._offer_of(proposer, a)
                if offer >= a.q:
                    proposer.fitness += (1.0 - offer)
                    a.fitness += offer

    # -- reproduction --
    def _select_parent(self, cumulative: Sequence[float], total: float) -> PlayerAgent:
        """Fitness-proportional (roulette) selection of one parent using a precomputed
        cumulative-fitness array. Falls back to a uniform pick when total fitness is 0
        (all-equal / degenerate generation)."""
        if total <= 0.0:
            return self.agent_list[self.rng.randrange(self.n)]
        r = self.rng.random() * total
        # linear scan (N is small); cumulative is non-decreasing so this finds the first
        # index whose cumulative fitness exceeds r.
        for i, c in enumerate(cumulative):
            if r < c:
                return self.agent_list[i]
        return self.agent_list[-1]

    @staticmethod
    def _clamp01(x: float) -> float:
        if x < 0.0:
            return 0.0
        if x > 1.0:
            return 1.0
        return x

    def reproduce(self) -> None:
        """One generation of fitness-proportional replication with Gaussian mutation.

        Build the next generation's N genotypes by drawing each from a parent selected
        with probability proportional to fitness, then nudging both p and q by an
        independent Gaussian of std ``mutation`` (clamped into [0,1]). Fitness is shifted
        so the minimum is 0 before proportional selection (payoffs are already >= 0 here,
        but the shift keeps selection well-defined for any payoff sign). The whole update
        is synchronous: all parents are read from the CURRENT generation, then committed."""
        fits = [a.fitness for a in self.agent_list]
        fmin = min(fits)
        shifted = [f - fmin for f in fits]          # non-negative selection weights
        total = sum(shifted)
        cumulative: List[float] = []
        running = 0.0
        for s in shifted:
            running += s
            cumulative.append(running)

        rng = self.rng
        mut = self.mutation
        new_pq: List[Tuple[float, float]] = []
        for _ in range(self.n):
            parent = self._select_parent(cumulative, total)
            np_ = self._clamp01(parent.p + rng.gauss(0.0, mut)) if mut > 0.0 else parent.p
            nq_ = self._clamp01(parent.q + rng.gauss(0.0, mut)) if mut > 0.0 else parent.q
            new_pq.append((np_, nq_))
        for a, (np_, nq_) in zip(self.agent_list, new_pq):
            a.p = np_
            a.q = nq_

    # -- tick --
    def step(self) -> None:
        """One generation: (1) play the encounters and accumulate fitness against the
        CURRENT population; (2) fitness-proportional replication + mutation to form the
        next generation (synchronous commit); (3) record (p̄, q̄) and advance t."""
        self.assign_fitness()
        self.reproduce()
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_gens: int = 500, *, measure_last: int = 100) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_gens`` generations; return the run summary.

        ``measure_last`` is the trailing window over which the steady-state (p̄, q̄) are
        averaged (the leading transient is discarded). Returns steady + final (p̄, q̄) and
        the full per-generation series of both.
        """
        if measure_last <= 0 or measure_last > n_gens + 1:
            raise ValueError(
                f"measure_last must be in [1, n_gens+1] (got {measure_last}, n_gens={n_gens})")
        self.reporter.collect(self)              # t=0 baseline (the fair init)
        for _ in range(n_gens):
            self.step()
        p_series = self.reporter.series("mean_p")
        q_series = self.reporter.series("mean_q")
        return {
            "n": self.n,
            "w": self.w,
            "rounds_per_gen": self.rounds_per_gen,
            "mutation": self.mutation,
            "seed": self.seed_value,
            "n_gens": n_gens,
            "measure_last": measure_last,
            "steady_p": tail_mean(p_series, window=measure_last),
            "steady_q": tail_mean(q_series, window=measure_last),
            "final_p": p_series[-1],
            "final_q": q_series[-1],
            "mean_p_series": p_series,
            "mean_q_series": q_series,
        }


# -- summary helpers ----------------------------------------------------------

def tail_mean(series: Sequence[float], *, window: int = 100) -> float:
    """Steady-state estimate = mean of the trailing ``window`` of a series (or the whole
    series if shorter). Averaging the tail smooths finite-N drift and discards the
    transient before measurement."""
    if not series:
        return 0.0
    tail = series[-window:] if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def run_single(n: int = 200, *, w: float = 0.0, rounds_per_gen: int = 10,
               mutation: float = 0.02, seed: int = 0, n_gens: int = 500,
               measure_last: int = 100) -> Dict[str, Any]:
    """One ultimatum-game run at a given (w, seed) and the fixed evolution parameters."""
    return UltimatumModel(n, w=w, rounds_per_gen=rounds_per_gen, mutation=mutation,
                          seed=seed).run(n_gens, measure_last=measure_last)


def run_many_seeds(n: int = 200, *, w: float = 0.0, rounds_per_gen: int = 10,
                   mutation: float = 0.02, n_seeds: int = 10, seed_base: int = 0,
                   n_gens: int = 500, measure_last: int = 100) -> Dict[str, Any]:
    """Run ``n_seeds`` ultimatum runs (seed ``seed_base + i``) at a fixed reputation
    weight ``w`` and summarise the steady-state mean offer p̄ and mean threshold q̄ across
    seeds (mean + spread).

    Returns the per-seed steady (p̄, q̄), their mean / std / min / max, and one
    representative trajectory (first seed) of both series for inspection. The w-grid is
    swept by calling this at each w with identical n, init, rounds, mutation, and seeds.
    """
    runs = [run_single(n, w=w, rounds_per_gen=rounds_per_gen, mutation=mutation,
                       seed=seed_base + i, n_gens=n_gens, measure_last=measure_last)
            for i in range(n_seeds)]
    per_seed_p = [rr["steady_p"] for rr in runs]
    per_seed_q = [rr["steady_q"] for rr in runs]
    per_seed_final_p = [rr["final_p"] for rr in runs]
    per_seed_final_q = [rr["final_q"] for rr in runs]
    mean_p = sum(per_seed_p) / n_seeds
    mean_q = sum(per_seed_q) / n_seeds
    var_p = sum((s - mean_p) ** 2 for s in per_seed_p) / n_seeds
    var_q = sum((s - mean_q) ** 2 for s in per_seed_q) / n_seeds
    return {
        "n": n, "w": w, "rounds_per_gen": rounds_per_gen, "mutation": mutation,
        "n_seeds": n_seeds, "seed_base": seed_base,
        "n_gens": n_gens, "measure_last": measure_last,
        "per_seed_steady_p": per_seed_p,
        "per_seed_steady_q": per_seed_q,
        "per_seed_final_p": per_seed_final_p,
        "per_seed_final_q": per_seed_final_q,
        "mean_steady_p": mean_p,
        "std_steady_p": var_p ** 0.5,
        "min_steady_p": min(per_seed_p),
        "max_steady_p": max(per_seed_p),
        "mean_steady_q": mean_q,
        "std_steady_q": var_q ** 0.5,
        "min_steady_q": min(per_seed_q),
        "max_steady_q": max(per_seed_q),
        # one representative trajectory (first seed) for plotting/inspection.
        "example_p_series": runs[0]["mean_p_series"],
        "example_q_series": runs[0]["mean_q_series"],
    }
