"""Axelrod (1986) Norms / Metanorms game — a faithful evolutionary agent-based model.

Source: Axelrod, R. (1986) "An Evolutionary Approach to Norms", American Political
Science Review 80(4):1095-1111. doi:10.2307/1960858. Axelrod asks how a NORM (a
behaviour that is punished when violated) can become established in a population, and
shows that a plain norm tends to collapse, while a METANORM ("you must punish those who
do not punish") can sustain enforcement.

This is the genuine agent-based model from the paper: a small population of ``N`` player
agents, each carrying two heritable 3-bit strategy genes, evolved over generations by
Axelrod's own selection rule. No replicator ODE; each agent holds its OWN genes and its
OWN realised payoff, and selection reads only the population's payoff mean and standard
deviation.

Strategy genes (heritable, integer, range {0..7}; 3 bits each, as in Axelrod 1986):
  * boldness    B — the agent defects iff its normalised boldness b = B/7 exceeds the
    (known) chance S of being seen this opportunity. A bold agent defects even when
    likely to be observed.
  * vengefulness V — when the agent SEES a defection, it punishes with probability equal
    to its normalised vengefulness v = V/7.

One ROUND (one defection opportunity for every agent), following Axelrod's structure:
  1. For each agent in turn, draw the known see-probability S ~ U(0,1) for THIS act
     (common to all potential observers of that act — Axelrod uses a schedule of S
     values; an i.i.d. U(0,1) draw per opportunity is the simple faithful choice and is
     documented here as the exact rule).
  2. The agent DEFECTS iff b = B/7 > S (bold enough to risk being seen). A defection
     yields the defector the temptation payoff T = +3 and inflicts the hurt H = −1 on
     each OTHER agent in the population.
  3. Every OTHER agent independently SEES the defection with probability S. Each seer
     punishes with probability v = V/7; a punishment costs the DEFECTOR the enforcement
     penalty E = −9 and costs the PUNISHER the enforcement cost P = −2.
  4. METANORM variant only: a seer who saw the defection but did NOT punish is itself a
     norm violator. Each such non-punisher can be seen by every OTHER agent (again with
     probability S); each meta-seer meta-punishes with probability equal to ITS own v,
     costing the non-punisher E' = −9 and the meta-punisher P' = −2. This is the single
     difference between the two arms.

A GENERATION = ``rounds_per_gen`` such rounds, with payoffs accumulated. Then the
EVOLUTIONARY UPDATE, exactly Axelrod's rule: compute the population mean μ and standard
deviation σ of the accumulated payoff. An agent whose payoff ≥ μ + σ reproduces TWICE
(an extra copy), one whose payoff ≤ μ − σ dies (no copy), and everyone else reproduces
ONCE — then the new population is truncated / topped up to exactly N. Offspring inherit
the parent's genes with a small per-BIT mutation (each of the 3+3 bits flips with
probability ``mut_rate``), keeping every gene in {0..7}. Run ~100 generations over ≥20
seeds.

The two arms (no-metanorm vs metanorm) are FAIR: identical N, payoff constants
(T,H,E,P), rounds per generation, generations, mutation rate, initial gene distribution
and seeds. They differ ONLY in whether the metanorm meta-punishment step (4) is applied.
No parameter is tuned to make the norm establish (the locked claims are COMPARATIVE).

Outcome metric (LOCKED): the population-mean vengefulness V (and boldness B) on the
0..7 scale, averaged over the final generations and over seeds.

Built on the neutral platform (``abm_auto._platform``): each player is a ``PlayerAgent``
carrying its (B, V) genes and realised payoff; ``NormsModel`` owns the rounds, the
payoff accounting (including the optional metanorm step), Axelrod's selection +
mutation, and a ``DataCollector`` recording the per-generation mean B and V.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector

# Gene resolution: 3 bits -> integer levels 0..7 (Axelrod 1986).
GENE_BITS = 3
GENE_MAX = (1 << GENE_BITS) - 1            # 7

# Payoff constants (Axelrod 1986, Table; fixed before running — not tuned).
TEMPTATION = 3.0                            # T: defector's gain from defecting
HURT = 1.0                                  # H: harm to each other agent from a defection
ENFORCE_PENALTY = 9.0                       # E: cost to a punished defector
ENFORCE_COST = 2.0                          # P: cost to a punisher
META_PENALTY = 9.0                          # E': cost to a punished non-punisher (metanorm)
META_COST = 2.0                             # P': cost to a meta-punisher (metanorm)


# -- Agent --------------------------------------------------------------------

class PlayerAgent(Agent):
    """One player carrying two heritable genes and a realised payoff.

    ``B`` (boldness) and ``V`` (vengefulness) are integers in {0..7}. ``b`` and ``v`` are
    the normalised values B/7, V/7 ∈ [0,1] used in the defect / punish probabilities.
    ``payoff`` is the fitness accumulated over the current generation's rounds (reset at
    the start of each generation). The evolutionary update lives on the model (selection
    reads the population's payoff distribution), so the per-agent ``step`` is a no-op."""

    def __init__(self, agent_id: int, model: "NormsModel", *, B: int, V: int) -> None:
        super().__init__(agent_id, model)
        if not (0 <= B <= GENE_MAX) or not (0 <= V <= GENE_MAX):
            raise ValueError(f"genes must be in {{0..{GENE_MAX}}} (got B={B}, V={V})")
        self.B = int(B)
        self.V = int(V)
        self.payoff = 0.0

    @property
    def b(self) -> float:
        """Normalised boldness B/7 ∈ [0,1] (the defect threshold)."""
        return self.B / GENE_MAX

    @property
    def v(self) -> float:
        """Normalised vengefulness V/7 ∈ [0,1] (the punish probability)."""
        return self.V / GENE_MAX

    def step(self) -> None:  # pragma: no cover - generation logic lives on the model
        """The generation (rounds of defect/punish + Axelrod selection) is a model-level
        tick over the whole population, not an autonomous single-agent step, so this is a
        no-op."""
        return None


# -- Model --------------------------------------------------------------------

class NormsModel(AgentModel):
    """Drives Axelrod (1986) norms-game evolutionary dynamics.

    Construct with N, the metanorm flag, the per-generation round count, the mutation
    rate, the number of generations, and a seed. ``metanorms=True`` adds ONLY the
    meta-punishment of non-punishers (step 4); every other rule and constant is shared
    with the no-metanorm arm. ``run`` iterates the generations and records the
    population-mean B and V each generation.
    """

    def __init__(self, n: int = 20, *, metanorms: bool = False,
                 rounds_per_gen: int = 4, mut_rate: float = 0.01,
                 n_generations: int = 100, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 1:
            raise ValueError(f"need n > 1 (got {n})")
        if rounds_per_gen <= 0:
            raise ValueError(f"need rounds_per_gen > 0 (got {rounds_per_gen})")
        if not (0.0 <= mut_rate <= 1.0):
            raise ValueError(f"need 0 <= mut_rate <= 1 (got {mut_rate})")
        if n_generations < 0:
            raise ValueError(f"need n_generations >= 0 (got {n_generations})")
        self.seed_value = seed
        self.n = n
        self.metanorms = bool(metanorms)
        self.rounds_per_gen = rounds_per_gen
        self.mut_rate = mut_rate
        self.n_generations = n_generations

        # Constants (mirrored onto the instance so a test can read them; FIXED).
        self.T = TEMPTATION
        self.H = HURT
        self.E = ENFORCE_PENALTY
        self.P = ENFORCE_COST
        self.E_meta = META_PENALTY
        self.P_meta = META_COST

        # Initial population: genes drawn uniformly over {0..7} (a fair, un-rigged
        # start; the same seed gives the same draw, so the two arms start identical).
        self.agent_list: List[PlayerAgent] = []
        for i in range(n):
            B = self.rng.randint(0, GENE_MAX)
            V = self.rng.randint(0, GENE_MAX)
            agent = PlayerAgent(i, self, B=B, V=V)
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({
            "mean_B": lambda m: m.mean_boldness(),
            "mean_V": lambda m: m.mean_vengefulness(),
        })

    # -- metrics (population-mean genes on the 0..7 scale) --
    def mean_boldness(self) -> float:
        return sum(a.B for a in self.agent_list) / self.n if self.n else 0.0

    def mean_vengefulness(self) -> float:
        return sum(a.V for a in self.agent_list) / self.n if self.n else 0.0

    # -- one round of payoffs (the only place the metanorm flag matters) --
    def play_round(self) -> None:
        """One defection opportunity per agent, applying the norms game (and the
        metanorm meta-punishment iff ``self.metanorms``). Payoffs ACCUMULATE onto each
        agent (caller resets them at the start of a generation).

        For each agent ``actor`` in turn:
          * draw the known see-probability S ~ U(0,1) for this act;
          * the actor DEFECTS iff its b = B/7 > S;
          * on a defection the actor gains T and every OTHER agent loses H;
          * every other agent sees it with prob S; each seer punishes with prob v,
            costing the defector E and the punisher P;
          * (metanorm) each seer who did NOT punish is itself seen by every other agent
            with prob S, and each meta-seer meta-punishes with prob (its own) v, costing
            the non-punisher E' and the meta-punisher P'.
        """
        rng = self.rng
        agents = self.agent_list
        for actor in agents:
            S = rng.random()                       # known chance of being seen this act
            if actor.b <= S:
                continue                            # not bold enough -> no defection
            # --- a defection happens ---
            actor.payoff += self.T
            others = [a for a in agents if a is not actor]
            for o in others:
                o.payoff -= self.H                  # everyone else is hurt

            # who SAW this defection (independent prob S each), and who punished
            seers: List[PlayerAgent] = []
            punishers: List[PlayerAgent] = []
            for o in others:
                if rng.random() < S:                # o saw the defection
                    seers.append(o)
                    if rng.random() < o.v:          # o punishes with prob v
                        actor.payoff -= self.E      # defector penalised
                        o.payoff -= self.P          # punisher pays the enforcement cost
                        punishers.append(o)

            if not self.metanorms:
                continue
            # --- METANORM: a seer who did NOT punish is itself a violator ---
            non_punishers = [o for o in seers if o not in punishers]
            for nonp in non_punishers:
                # every OTHER agent (besides the non-punisher) can see + meta-punish
                meta_others = [a for a in agents if a is not nonp]
                for mp in meta_others:
                    if rng.random() < S:            # mp saw the non-punishment
                        if rng.random() < mp.v:     # mp meta-punishes with prob v
                            nonp.payoff -= self.E_meta   # non-punisher penalised
                            mp.payoff -= self.P_meta     # meta-punisher pays the cost

    # -- Axelrod's selection + mutation --
    def _mutate_gene(self, value: int) -> int:
        """Flip each of the ``GENE_BITS`` bits of an integer gene independently with
        probability ``mut_rate``; the result stays in {0..7} by construction."""
        out = value
        for bit in range(GENE_BITS):
            if self.rng.random() < self.mut_rate:
                out ^= (1 << bit)
        return out

    def reproduce(self) -> None:
        """Axelrod's selection: agents 1 std ABOVE the mean payoff reproduce twice,
        agents 1 std BELOW die, the rest reproduce once. The resulting pool is truncated
        or topped up (by repeating from the front of the pool) to exactly N. Offspring
        inherit the parent's genes with a small per-bit mutation.

        Reads only the population's payoff mean and standard deviation — no analytic
        fitness, no external oracle. Deterministic given the RNG draw sequence."""
        agents = self.agent_list
        n = self.n
        payoffs = [a.payoff for a in agents]
        mean = sum(payoffs) / n
        var = sum((p - mean) ** 2 for p in payoffs) / n
        std = var ** 0.5

        # Number of offspring per parent: 2 if >= mean+std, 0 if <= mean-std, else 1.
        pool: List[Tuple[int, int]] = []           # (B, V) genotypes of survivors' kids
        for a in agents:
            if std > 0.0 and a.payoff >= mean + std:
                copies = 2
            elif std > 0.0 and a.payoff <= mean - std:
                copies = 0
            else:
                copies = 1
            for _ in range(copies):
                pool.append((a.B, a.V))

        # Degenerate guard: if everyone died (can't happen with std>0 truncation, but
        # std==0 makes everyone "1 copy"), fall back to copying the current genotypes.
        if not pool:
            pool = [(a.B, a.V) for a in agents]

        # Truncate / top up to exactly N. Top-up cycles deterministically through the
        # pool (offspring 0, 1, 2, ... reused in order) — a fair fill that does not bias
        # toward any single survivor.
        base = len(pool)
        i = 0
        while len(pool) < n:
            pool.append(pool[i % base])
            i += 1
        genotypes = pool[:n]

        # Build the next generation in place (reuse the agent objects / ids), applying
        # the per-bit mutation to each inherited gene.
        for a, (B, V) in zip(agents, genotypes):
            a.B = self._mutate_gene(B)
            a.V = self._mutate_gene(V)
            a.payoff = 0.0

    # -- tick (one generation) --
    def step(self) -> None:
        """One generation: reset payoffs, play ``rounds_per_gen`` rounds (accumulating
        payoffs), then apply Axelrod's selection + mutation. Record the new
        population-mean B and V."""
        for a in self.agent_list:
            a.payoff = 0.0
        for _ in range(self.rounds_per_gen):
            self.play_round()
        self.reproduce()
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_generations: Optional[int] = None) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate ``n_generations`` generations (default ``self.n_generations``); return
        a run summary with the full per-generation mean-B and mean-V series (generation 0
        baseline + each generation) and the final-window means."""
        gens = self.n_generations if n_generations is None else n_generations
        if gens < 0:
            raise ValueError(f"n_generations must be >= 0 (got {gens})")
        self.reporter.collect(self)                # generation-0 baseline (initial draw)
        for _ in range(gens):
            self.step()
        B_series = self.reporter.series("mean_B")
        V_series = self.reporter.series("mean_V")
        return {
            "n": self.n,
            "metanorms": self.metanorms,
            "rounds_per_gen": self.rounds_per_gen,
            "mut_rate": self.mut_rate,
            "n_generations": gens,
            "seed": self.seed_value,
            "params": {"T": self.T, "H": self.H, "E": self.E, "P": self.P,
                       "E_meta": self.E_meta, "P_meta": self.P_meta},
            "mean_B_series": B_series,
            "mean_V_series": V_series,
            "final_mean_B": B_series[-1],
            "final_mean_V": V_series[-1],
        }


# -- summary helpers ----------------------------------------------------------

def tail_mean(series: Sequence[float], *, window: int = 20) -> float:
    """Final-state estimate = mean of the trailing ``window`` of a series (or the whole
    series if shorter). Averaging the tail smooths the finite-population generation jitter
    around the stationary level."""
    if not series:
        return 0.0
    tail = series[-window:] if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def run_single(*, metanorms: bool = False, n: int = 20, rounds_per_gen: int = 4,
               mut_rate: float = 0.01, n_generations: int = 100, seed: int = 0,
               measure_last: int = 20) -> Dict[str, Any]:
    """One norms-game run at a given (metanorm, seed) and the fixed parameters. Adds the
    trailing-window final-mean B and V (the locked outcome metric)."""
    res = NormsModel(n=n, metanorms=metanorms, rounds_per_gen=rounds_per_gen,
                     mut_rate=mut_rate, n_generations=n_generations, seed=seed).run()
    res["measure_last"] = measure_last
    res["window_mean_B"] = tail_mean(res["mean_B_series"], window=measure_last)
    res["window_mean_V"] = tail_mean(res["mean_V_series"], window=measure_last)
    return res


def run_many_seeds(*, metanorms: bool = False, n: int = 20, rounds_per_gen: int = 4,
                   mut_rate: float = 0.01, n_generations: int = 100,
                   n_seeds: int = 20, seed_base: int = 0,
                   measure_last: int = 20) -> Dict[str, Any]:
    """Run ``n_seeds`` norms-game runs (seed ``seed_base + i``) for ONE arm at fixed
    parameters; summarise the trailing-window final mean vengefulness V and boldness B
    across seeds (mean + spread).

    The two arms call this with identical params and seeds, differing ONLY in
    ``metanorms``. Returns the per-seed final-window B and V, their seed means / spreads,
    the count of seeds whose final V is below the P1 collapse bar, and one representative
    trajectory (first seed) of both series.
    """
    runs = [run_single(metanorms=metanorms, n=n, rounds_per_gen=rounds_per_gen,
                       mut_rate=mut_rate, n_generations=n_generations,
                       seed=seed_base + i, measure_last=measure_last)
            for i in range(n_seeds)]
    per_seed_V = [r["window_mean_V"] for r in runs]
    per_seed_B = [r["window_mean_B"] for r in runs]
    per_seed_final_V = [r["final_mean_V"] for r in runs]
    per_seed_final_B = [r["final_mean_B"] for r in runs]
    mean_V = sum(per_seed_V) / n_seeds
    mean_B = sum(per_seed_B) / n_seeds
    var_V = sum((s - mean_V) ** 2 for s in per_seed_V) / n_seeds
    var_B = sum((s - mean_B) ** 2 for s in per_seed_B) / n_seeds
    return {
        "metanorms": metanorms,
        "n": n,
        "rounds_per_gen": rounds_per_gen,
        "mut_rate": mut_rate,
        "n_generations": n_generations,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "measure_last": measure_last,
        "per_seed_window_V": per_seed_V,
        "per_seed_window_B": per_seed_B,
        "per_seed_final_V": per_seed_final_V,
        "per_seed_final_B": per_seed_final_B,
        "mean_window_V": mean_V,
        "std_window_V": var_V ** 0.5,
        "min_window_V": min(per_seed_V),
        "max_window_V": max(per_seed_V),
        "mean_window_B": mean_B,
        "std_window_B": var_B ** 0.5,
        "min_window_B": min(per_seed_B),
        "max_window_B": max(per_seed_B),
        # one representative trajectory (first seed) for plotting / inspection.
        "example_B_series": runs[0]["mean_B_series"],
        "example_V_series": runs[0]["mean_V_series"],
    }
