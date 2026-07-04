"""Moran process with selection (Moran 1958) — a faithful agent-based reproduction.

Source: Moran, P.A.P. (1958) "Random processes in genetics", Math. Proc. Camb. Phil.
Soc. 54(1):60-71. The Moran model is the canonical finite-population birth-death
process. A single mutant of relative fitness ``r`` introduced into a resident
population of size ``N`` (residents have fitness 1) fixes (reaches frequency 1) with
probability

        rho = (1 - 1/r) / (1 - 1/r**N)      (and rho = 1/N at r == 1).

Rules (the classic frequency-dependent Birth-Death process, verified against the source):
  * A well-mixed population of N ``IndividualAgent``s, each a pure type: MUTANT
    (fitness r) or RESIDENT (fitness 1). The population size N is CONSTANT.
  * Start with exactly ONE mutant.
  * Each elementary step (one Moran Birth-Death event):
      1. BIRTH: pick one individual to reproduce with probability proportional to its
         fitness. With m mutants, the reproducer is a mutant with probability
            r*m / (r*m + (N - m))                       [= fitness-weighted choice]
         and a resident otherwise.
      2. DEATH: pick one individual UNIFORMLY at random to die.
      3. REPLACEMENT: the offspring (same type as the reproducer) replaces the dead
         individual. (Population size stays N.)
    Because death is uniform and only the type COUNT changes the dynamics in a
    well-mixed model, the state collapses to the integer m = #mutants and the step is a
    biased random walk on m in {0, ..., N}.
  * Run until FIXATION: m == 0 (mutant lost) or m == N (mutant fixed).
  * Outcome of one run = whether the mutant fixed (m reached N). Over many independent
    runs (each a fresh single mutant, a different seed) the fixation FRACTION estimates
    the Moran fixation probability rho.

Why this is genuinely agent-based (no analytic rho is fed into the dynamics):
  Each individual is an agent holding its OWN discrete heritable type. The model draws a
  reproducer (fitness-weighted over the actual roster) and a dier (uniform over the
  actual roster), then mutates the dier's type to the reproducer's type. The analytic
  rho is computed ONLY as the comparison anchor (``analytic_fixation``); the agents
  never see it, and the measured fixation fraction is a pure Monte-Carlo estimate over
  N interacting individuals. Given a seed the whole run is reproducible (one seeded RNG
  chain on the model).

Built on the neutral platform (``abm_auto._platform``): each individual is an
``IndividualAgent`` carrying its discrete type; ``MoranModel`` owns the seeded RNG, the
birth-death step over the ``AgentSet`` roster, and the fixation stop rule.

NOTE (and a locked claim of this study): the large-N limit of the Moran rho is
1 - 1/r ~= s (the selection coefficient), NOT the Wright-Fisher diffusion result 2s.
We reproduce the EXACT Moran formula, not the WF approximation.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from abm_auto._platform import Agent, AgentModel

MUTANT = "M"
RESIDENT = "R"


# -- analytic anchor ----------------------------------------------------------

def analytic_fixation(r: float, N: int) -> float:
    """The exact Moran fixation probability of a single mutant of fitness ``r`` in a
    resident population of total size ``N``:

        rho = (1 - 1/r) / (1 - 1/r**N)        for r != 1
        rho = 1/N                             for r == 1 (neutral).

    This is the COMPARISON anchor — it is never fed into the agent dynamics."""
    if N <= 0:
        raise ValueError(f"N must be positive (got {N})")
    if r <= 0:
        raise ValueError(f"fitness r must be positive (got {r})")
    if r == 1.0:
        return 1.0 / N
    x = 1.0 / r
    return (1.0 - x) / (1.0 - x ** N)


# -- Agent --------------------------------------------------------------------

class IndividualAgent(Agent):
    """One individual in the population, carrying a discrete heritable ``type``
    (``MUTANT`` or ``RESIDENT``). The type is the only state; selection acts through the
    type's fitness (r for a mutant, 1 for a resident)."""

    def __init__(self, agent_id: int, model: "MoranModel", *, type_: str) -> None:
        super().__init__(agent_id, model)
        self.type = type_

    def is_mutant(self) -> bool:
        return self.type == MUTANT

    def fitness(self) -> float:
        return self.model.r if self.type == MUTANT else 1.0

    def step(self) -> None:  # pragma: no cover - birth-death lives on the model
        """The Moran event (pick a reproducer fitness-weighted, pick a dier uniformly,
        replace) is a model-level step over the whole roster, not an autonomous
        single-agent step, so the per-agent ``step`` is intentionally a no-op."""
        return None


# -- Model --------------------------------------------------------------------

class MoranModel(AgentModel):
    """Drives the Moran Birth-Death process with selection.

    Construct with N, the mutant fitness r, and a seed. Exactly one individual starts as
    a mutant (the rest residents). ``run`` iterates birth-death events until fixation
    (m == 0 or m == N) and returns a summary dict (whether the mutant fixed, the number
    of events, and the final mutant count).
    """

    def __init__(self, n: int = 100, *, r: float = 1.0, seed: int = 0,
                 mutant_index: int = 0, max_events: Optional[int] = None) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 1:
            raise ValueError(f"N must be > 1 (got {n})")
        if r <= 0:
            raise ValueError(f"fitness r must be positive (got {r})")
        if not (0 <= mutant_index < n):
            raise ValueError(f"mutant_index {mutant_index} out of range [0, {n})")
        self.seed_value = seed
        self.n = n
        self.r = r
        # Safety cap on event count: the process fixes a.s., but a finite cap keeps a
        # run bounded. Default is generous (scales with N) and is NOT a tuning knob —
        # fixation is essentially always reached well within it.
        self.max_events = max_events if max_events is not None else 2000 * n * n

        # Seed the population: exactly ONE mutant (at mutant_index), the rest residents.
        # Which specific individual is the mutant is irrelevant in a well-mixed model;
        # only the count m matters. Deterministic placement keeps init seed-independent.
        self.agent_list: List[IndividualAgent] = []
        for i in range(n):
            type_ = MUTANT if i == mutant_index else RESIDENT
            agent = IndividualAgent(i, self, type_=type_)
            self.agent_list.append(agent)
            self.add_agent(agent)

    # -- metrics --
    def n_mutants(self) -> int:
        return sum(1 for a in self.agent_list if a.is_mutant())

    def mutant_fraction(self) -> float:
        return self.n_mutants() / self.n if self.n else 0.0

    def is_fixed(self) -> bool:
        """Absorbing state reached: all-mutant or all-resident."""
        m = self.n_mutants()
        return m == 0 or m == self.n

    # -- one Moran Birth-Death event --
    def birth_death_step(self) -> None:
        """One elementary Moran event:

          BIRTH: pick a reproducer with probability proportional to fitness. Total
            fitness is r*m + (N - m); a uniform draw on [0, total) selects the
            reproducer by accumulating per-agent fitness over the roster.
          DEATH: pick a dier UNIFORMLY at random over the roster.
          REPLACEMENT: the dier adopts the reproducer's type.

        Reads only the actual agent roster (their types/fitnesses) — no analytic rho,
        no global-fraction oracle beyond the literal fitness sum it must normalise by."""
        total_fitness = sum(a.fitness() for a in self.agent_list)
        # BIRTH: fitness-weighted reproducer.
        threshold = self.rng.random() * total_fitness
        cum = 0.0
        reproducer = self.agent_list[-1]
        for a in self.agent_list:
            cum += a.fitness()
            if threshold < cum:
                reproducer = a
                break
        # DEATH: uniform dier.
        dier = self.agent_list[self.rng.randrange(self.n)]
        # REPLACEMENT: offspring (reproducer's type) overwrites the dier.
        dier.type = reproducer.type

    # -- run to fixation --
    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate birth-death events until fixation (m == 0 or m == N) or the safety
        cap; return the run summary (fixed?, #events, final mutant count)."""
        events = 0
        while not self.is_fixed() and events < self.max_events:
            self.birth_death_step()
            events += 1
        self.t = events
        m_final = self.n_mutants()
        return {
            "n": self.n,
            "r": self.r,
            "seed": self.seed_value,
            "events": events,
            "final_mutants": m_final,
            "fixed": m_final == self.n,
            "absorbed": self.is_fixed(),
            "analytic_fixation": analytic_fixation(self.r, self.n),
        }


# -- run drivers --------------------------------------------------------------

def run_single(n: int = 100, *, r: float = 1.0, seed: int = 0,
               mutant_index: int = 0, max_events: Optional[int] = None) -> Dict[str, Any]:
    """One Moran run (a fresh single mutant) at a given seed; runs to fixation."""
    return MoranModel(n, r=r, seed=seed, mutant_index=mutant_index,
                      max_events=max_events).run()


def fixation_fraction(n: int = 100, *, r: float = 1.0, n_runs: int = 2000,
                      seed_base: int = 0,
                      max_events: Optional[int] = None) -> Dict[str, Any]:
    """Run ``n_runs`` independent Moran runs (seed ``seed_base + i``; each a fresh single
    mutant) at fixed (N, r) and estimate the fixation probability = fraction of runs in
    which the mutant fixed.

    Returns the measured fixation fraction, its binomial standard error
    sqrt(p(1-p)/n_runs), the count of fixations, the analytic Moran rho, the
    measured-minus-analytic error, and per-run event counts (mean) for context.

    NOTE: the mutant always starts at the SAME index (0); since the model is well-mixed
    the start position is irrelevant (only the count m matters), so different runs differ
    ONLY by their seed — exactly the "different seed per run" the locked protocol asks
    for. Determinism is preserved (seed -> identical run)."""
    fixations = 0
    n_absorbed = 0
    events_list: List[int] = []
    for i in range(n_runs):
        res = run_single(n, r=r, seed=seed_base + i, mutant_index=0,
                         max_events=max_events)
        if res["fixed"]:
            fixations += 1
        if res["absorbed"]:
            n_absorbed += 1
        events_list.append(res["events"])
    p = fixations / n_runs if n_runs else 0.0
    se = (p * (1.0 - p) / n_runs) ** 0.5 if n_runs else 0.0
    rho = analytic_fixation(r, n)
    return {
        "n": n,
        "r": r,
        "n_runs": n_runs,
        "seed_base": seed_base,
        "fixations": fixations,
        "measured_fixation": p,
        "binomial_se": se,
        "analytic_fixation": rho,
        "error": p - rho,
        "abs_error": abs(p - rho),
        "n_absorbed": n_absorbed,
        "all_absorbed": n_absorbed == n_runs,
        "mean_events": sum(events_list) / n_runs if n_runs else 0.0,
        "max_events_observed": max(events_list) if events_list else 0,
    }
