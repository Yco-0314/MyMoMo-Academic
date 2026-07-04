"""Galam majority-rule opinion model — a faithful agent-based reproduction.

Source: Galam, S. (2002) "Minority opinion spreading in random geometry",
Eur. Phys. J. B 25:403-406 (and the broader Galam majority-rule family,
e.g. Galam 1986/2008). Open review: Galam, S. (2008) "Sociophysics: A review
of Galam models", Int. J. Mod. Phys. C 19(3):409-440.

Rules (verified against the Galam majority-rule model):

  * N agents, each an ``OpinionAgent`` holding a binary opinion in {0, 1}
    (1 = "up", 0 = "down"). The opinion lives ON the agent (agents persist;
    the local-majority rule reads/writes the opinions of agents within a group).
  * Initial up-fraction p0: each agent independently set to 1 with probability
    p0, else 0 (random, seeded).
  * One update step: randomly PARTITION the whole population into groups of a
    fixed size g (shuffle, then chunk). Each FULL group adopts its LOCAL
    MAJORITY: every member takes the majority opinion of that group. Then the
    grouping is dissolved and re-formed (reshuffled) on the next step.
  * Odd g (g=3): a strict majority always exists -- ties are impossible.
  * Even g (g=4): a 2-2 tie is broken toward a FIXED opinion (the "prejudice"
    / status-quo bias). Here the locked tie rule is **ties -> UP (1)**.
  * The leftover agents that do not fill a complete final group (N mod g of
    them) are left UNCHANGED this step (a partial group has no full local
    majority to apply); they are reshuffled into full groups on later steps.
  * The system is iterated until CONSENSUS (every agent 0, or every agent 1)
    or a step cap is reached. Outcome = which consensus vs p0.

Deterministic given a seed: a single seeded RNG chain on the model drives both
the initial opinion placement and every reshuffle, so the same seed reproduces
byte-identical output.

Built on the neutral platform (``abm_auto._platform``): each agent is an
autonomous ``OpinionAgent`` carrying its opinion; the ``GalamModel`` owns the
seeded RNG, the partition/local-majority rule, and a ``DataCollector`` for the
per-step up-fraction series -- NOT a hand-rolled god-loop.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class OpinionAgent(Agent):
    """One agent. ``opinion`` is its binary state in {0, 1}.

    The agent is a passive opinion-holder: the Galam local-majority rule (owned
    by the model) partitions agents into groups and writes the group majority
    onto each member. There is no per-agent ``step`` in the Galam dynamics (the
    unit of action is a group's majority vote, not an individual activation), so
    ``step`` is a no-op kept only to satisfy the platform contract.
    """

    def __init__(self, agent_id: int, model: "GalamModel", *, opinion: int) -> None:
        super().__init__(agent_id, model)
        self.opinion = opinion

    def step(self) -> None:  # pragma: no cover - Galam acts per-group, not per-agent
        pass


# -- group local-majority rule (pure function; hand-testable) -----------------

def group_majority(opinions: List[int], *, g: int, tie_break_up: bool) -> int:
    """The local-majority opinion of one group.

    ``opinions`` is the list of binary opinions of the group's members. Returns
    the majority opinion (1 or 0). For an even group a 2-2 (k=g/2) tie is broken
    toward UP iff ``tie_break_up`` (the fixed prejudice); for an odd group a
    strict majority always exists so ``tie_break_up`` is irrelevant.
    """
    ups = sum(opinions)
    downs = g - ups
    if ups > downs:
        return 1
    if downs > ups:
        return 0
    # ups == downs: only possible for even g (a tie). Locked rule: ties -> up.
    return 1 if tie_break_up else 0


# -- Model --------------------------------------------------------------------

class GalamModel(AgentModel):
    """Galam majority-rule dynamics on a well-mixed population of N agents.

    Construct with the population size N, the group size g, the initial
    up-fraction p0, the tie rule (ties -> up), and a seed. ``run`` drives
    reshuffle+local-majority steps until consensus (all-0 / all-1) or the step
    cap, then returns a summary dict (final up-fraction + which consensus + the
    per-step up-fraction series).
    """

    def __init__(self, *, N: int = 10001, g: int = 3, p0: float = 0.5,
                 tie_break_up: bool = True, seed: int = 0,
                 max_steps: int = 1000) -> None:
        super().__init__(seed=seed, schedule="sequential")
        self.seed = seed
        self.N = N
        self.g = g
        self.p0 = p0
        self.tie_break_up = tie_break_up
        self.max_steps = max_steps

        # Random initial placement (seeded): each agent 1 with prob p0, else 0.
        for agent_id in range(N):
            opinion = 1 if self.rng.random() < p0 else 0
            self.add_agent(OpinionAgent(agent_id, self, opinion=opinion))
        self._agents: List[OpinionAgent] = list(self.agents)

        self.reporter = DataCollector({"up_fraction": lambda m: m.up_fraction()})

    # -- metrics --
    def up_count(self) -> int:
        return sum(a.opinion for a in self._agents)

    def up_fraction(self) -> float:
        return self.up_count() / self.N if self.N else 0.0

    def consensus(self) -> Optional[int]:
        """1 if every agent is 1, 0 if every agent is 0, else None."""
        ups = self.up_count()
        if ups == self.N:
            return 1
        if ups == 0:
            return 0
        return None

    # -- one update step: reshuffle, partition into groups of g, local majority --
    def step(self) -> None:
        """One Galam step: shuffle the population, chunk into groups of g, set
        every member of each FULL group to that group's local majority; leftover
        agents (N mod g) are unchanged this step.

        Records the post-step up-fraction and stores the step's change count on
        ``self._step_changes`` so ``run`` can detect a fixed point."""
        agents = self._agents
        self.rng.shuffle(agents)
        g = self.g
        n_full = self.N // g          # number of complete groups
        changes = 0
        for gi in range(n_full):
            group = agents[gi * g:(gi + 1) * g]
            maj = group_majority([a.opinion for a in group], g=g,
                                 tie_break_up=self.tie_break_up)
            for a in group:
                if a.opinion != maj:
                    a.opinion = maj
                    changes += 1
        self._step_changes = changes
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate reshuffle+local-majority steps until consensus (all-0/all-1)
        or the step cap; return the run summary."""
        self.reporter.collect(self)              # t=0 baseline (initial placement)
        self._step_changes = 0
        reached = False
        for _ in range(self.max_steps):
            self.step()
            if self.consensus() is not None:
                reached = True
                break
        cons = self.consensus()
        return {
            "N": self.N,
            "g": self.g,
            "p0": self.p0,
            "tie_break_up": self.tie_break_up,
            "seed": self.seed,
            "steps": self.t,
            "consensus": cons,                   # 1, 0, or None (cap hit, no consensus)
            "consensus_reached": reached,
            "all_up": cons == 1,
            "all_down": cons == 0,
            "final_up_fraction": self.up_fraction(),
            "up_fraction_series": self.reporter.series("up_fraction"),
        }


# -- single / Monte-Carlo helpers ---------------------------------------------

def run_single(*, N: int = 10001, g: int = 3, p0: float = 0.5,
               tie_break_up: bool = True, seed: int = 0,
               max_steps: int = 1000) -> Dict[str, Any]:
    """One Galam run to consensus (or the step cap)."""
    return GalamModel(N=N, g=g, p0=p0, tie_break_up=tie_break_up, seed=seed,
                      max_steps=max_steps).run()


def is_monotone_toward_consensus(series: List[float], *, p0: float,
                                 tol: float = 1e-9) -> bool:
    """True iff the up-fraction trajectory moves monotonically AWAY from p0
    toward 0 or 1 (Galam P3: no interior stable fixed point).

    If the run ends up (final >= p0) the series must be non-decreasing; if it
    ends down (final < p0) it must be non-increasing. A flat run (no change) is
    vacuously monotone. ``tol`` absorbs floating point on the fractions.

    NOTE: this is a STRICT step-by-step test. Right ON the unstable fixed point
    p_c a finite-N trajectory can wobble by a few thousandths before committing,
    so this returns False there even though the flow still ends at 0/1. Use
    ``flows_away_from_interior`` for the substantive "no interior stable fixed
    point" claim (which is robust to that knife-edge wobble).
    """
    if len(series) < 2:
        return True
    final = series[-1]
    if final >= series[0]:
        return all(series[i + 1] >= series[i] - tol for i in range(len(series) - 1))
    return all(series[i + 1] <= series[i] + tol for i in range(len(series) - 1))


def flows_away_from_interior(series: List[float], *, eps: float = 1e-9) -> bool:
    """True iff the trajectory ENDS at a 0/1 consensus (no interior stable fixed
    point) -- the substantive Galam P3 claim.

    The flow has no interior attractor: every trajectory leaves the interior and
    settles at exactly 0 or 1. This is robust to small finite-N wobble right on
    the unstable fixed point p_c (which ``is_monotone_toward_consensus`` flags
    but which still flows away). A run that gets stuck at an interior value
    (final not within ``eps`` of 0 or 1) would FALSIFY the claim.
    """
    if not series:
        return False
    final = series[-1]
    return final <= eps or final >= 1.0 - eps


def run_many_seeds(*, N: int = 10001, g: int = 3, p0: float = 0.5,
                   tie_break_up: bool = True, n_seeds: int = 20,
                   seed_base: int = 0, max_steps: int = 1000) -> Dict[str, Any]:
    """Run ``n_seeds`` independent Galam runs at up-fraction p0 and summarise.

    Each trial uses seed ``seed_base + i`` (drives both the initial placement and
    every reshuffle). Returns per-seed results plus the locked-metric aggregates:
    P(all-UP) (fraction ending in the all-1 consensus), P(all-DOWN), the fraction
    reaching ANY consensus, and the fraction of trajectories that moved
    monotonically away from p0 (P3). Deterministic given (N, g, p0, tie rule,
    seed_base, max_steps).
    """
    results: List[Dict[str, Any]] = []
    for i in range(n_seeds):
        results.append(run_single(N=N, g=g, p0=p0, tie_break_up=tie_break_up,
                                  seed=seed_base + i, max_steps=max_steps))

    n = len(results)
    n_all_up = sum(1 for r in results if r["all_up"])
    n_all_down = sum(1 for r in results if r["all_down"])
    n_consensus = sum(1 for r in results if r["consensus_reached"])
    n_monotone = sum(1 for r in results
                     if is_monotone_toward_consensus(r["up_fraction_series"], p0=p0))
    n_flows_away = sum(1 for r in results
                       if flows_away_from_interior(r["up_fraction_series"]))
    final_fracs = [r["final_up_fraction"] for r in results]
    steps = [r["steps"] for r in results]

    return {
        "N": N,
        "g": g,
        "p0": p0,
        "tie_break_up": tie_break_up,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "max_steps": max_steps,
        "p_all_up": n_all_up / n if n else 0.0,
        "p_all_down": n_all_down / n if n else 0.0,
        "p_consensus": n_consensus / n if n else 0.0,
        "p_monotone": n_monotone / n if n else 0.0,
        "p_flows_away": n_flows_away / n if n else 0.0,
        "n_all_up": n_all_up,
        "n_all_down": n_all_down,
        "n_consensus": n_consensus,
        "n_monotone": n_monotone,
        "n_flows_away": n_flows_away,
        "mean_steps": sum(steps) / n if n else 0.0,
        "max_steps_used": max(steps) if steps else 0,
        "mean_final_up_fraction": sum(final_fracs) / n if n else 0.0,
        "per_seed": [
            {"seed": r["seed"], "consensus": r["consensus"],
             "consensus_reached": r["consensus_reached"], "all_up": r["all_up"],
             "all_down": r["all_down"], "final_up_fraction": r["final_up_fraction"],
             "steps": r["steps"]}
            for r in results
        ],
    }


def tipping_point(sweep: List[Dict[str, Any]], *, threshold: float = 0.5) -> Optional[float]:
    """Estimate the up-tipping point p_c from a p0 sweep: the smallest p0 at which
    P(all-UP) crosses ``threshold`` (>= half the seeds reach the all-UP consensus).

    ``sweep`` is a list of ``run_many_seeds`` summaries ordered by ascending p0.
    Returns the first p0 with p_all_up >= threshold, or None if none cross.
    """
    for row in sweep:
        if row["p_all_up"] >= threshold:
            return row["p0"]
    return None
