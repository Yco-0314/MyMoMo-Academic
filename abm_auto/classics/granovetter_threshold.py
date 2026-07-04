"""Granovetter (1978) threshold model — a faithful agent-based reproduction.

Source: Granovetter, M. (1978) "Threshold Models of Collective Behavior",
AJS 83(6):1420-1443.

Rules (verified against the paper, fully-mixed riot formulation):
  * N agents, FULLY MIXED — each agent reads the GLOBAL count of agents currently
    acting (no spatial/network structure; everyone observes everyone).
  * Agent ``i`` has an integer threshold ``threshold``. It acts iff the number of
    agents currently acting is ``>= threshold``. Acting is monotone (once an agent
    acts, it stays acting).
  * People with lower thresholds act first, possibly cascading: a round counts the
    current actors, then lets EVERY agent whose threshold <= that count act; repeat
    until a round adds no new actor (a fixed point).
  * Deterministic: NO RNG. The equilibrium and the per-round series depend only on
    the threshold multiset.

Granovetter's headline (the riot example): a tiny change to ONE agent's threshold —
mean-invariant — can swing the equilibrium from "everyone acts" to "almost nobody
acts." Collective behavior is a property of the threshold DISTRIBUTION, not its mean.

Built on the neutral platform (``abm_auto._platform``): each agent is a
``ThresholdAgent`` whose ``step`` applies the global-count rule; the model drives an
``AgentSet`` scheduler and a ``DataCollector`` (the active-count series) -- NOT a
hand-rolled god-loop.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from abm_auto._platform import Agent, AgentModel, AgentSet, DataCollector


# -- Agent --------------------------------------------------------------------

class ThresholdAgent(Agent):
    """One agent in the fully-mixed crowd.

    ``threshold`` is the integer count of others-already-acting at or above which
    this agent joins. ``acting`` is its binary state. The decision reads the model's
    GLOBAL active count at the START of the round (staged into ``_next_acting`` and
    committed by the model after every agent has stepped), so a round is a
    synchronous update -- order-independent and therefore deterministic regardless
    of scheduler order.
    """

    def __init__(self, agent_id: int, model: "ThresholdModel", *, threshold: int) -> None:
        super().__init__(agent_id, model)
        self.threshold = int(threshold)
        self.acting = False
        self._next_acting = False

    def step(self) -> None:
        """Stage the next state: an agent already acting stays acting (monotone); an
        inactive agent joins iff the GLOBAL active count this round is >= its
        threshold. The count is read from the model (the fully-mixed signal)."""
        if self.acting:
            self._next_acting = True
            return
        self._next_acting = self.model.active_count() >= self.threshold


# -- Model --------------------------------------------------------------------

class ThresholdModel(AgentModel):
    """Drives the fully-mixed threshold cascade to a fixed point.

    Construct with a sequence of integer thresholds (one agent each). ``run``
    iterates synchronous rounds -- count actors, let everyone whose threshold <=
    count act -- until a round adds no new actor, then returns a summary dict:
    the equilibrium active count, the per-round active-count series, and the mean
    threshold (the mean-invariant the P3 claim turns on).
    """

    def __init__(self, thresholds: Sequence[int], *, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        self.thresholds: List[int] = [int(t) for t in thresholds]
        self.n = len(self.thresholds)
        # Lower thresholds act first: a stable sort by threshold makes the
        # sequential scheduler march low->high within a round. (The synchronous
        # commit makes the equilibrium order-independent regardless; sorting only
        # makes the per-agent staging order faithful to "lower thresholds first".)
        self.agents = AgentSet([], schedule="sequential", rng=self.rng)
        self.agent_list: List[ThresholdAgent] = []
        for aid, thr in enumerate(sorted(self.thresholds)):
            agent = ThresholdAgent(aid, self, threshold=thr)
            self.agent_list.append(agent)
            self.add_agent(agent)
        self.reporter = DataCollector({"active": lambda m: m.active_count()})
        self._new_actors = 0

    # -- metrics --
    def active_count(self) -> int:
        return sum(1 for a in self.agent_list if a.acting)

    def mean_threshold(self) -> float:
        return sum(self.thresholds) / self.n if self.n else 0.0

    # -- round --
    def step(self) -> None:  # type: ignore[override]
        """One synchronous round: every agent stages its next state against the
        active count at the start of the round, then the model commits all states
        at once and records the new active count."""
        self.agents.step()                       # each agent stages _next_acting
        new_actors = 0
        for a in self.agent_list:
            if a._next_acting and not a.acting:
                new_actors += 1
            a.acting = a._next_acting
        self.t += 1
        self._new_actors = new_actors
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate rounds to a fixed point; return the run summary.

        ``max_rounds = n + 1`` is a hard safety bound: at most one new actor can
        join per round in the slowest cascade, so the fixed point is reached in <= n
        rounds. The series' first entry is the t=0 baseline (count before any round)."""
        self.reporter.collect(self)              # t=0 baseline (no one acting yet)
        max_rounds = self.n + 1
        for _ in range(max_rounds):
            self.step()
            if self._new_actors == 0:
                break
        equilibrium = self.active_count()
        return {
            "equilibrium": equilibrium,
            "n": self.n,
            "mean_threshold": self.mean_threshold(),
            "rounds": self.t,
            "active_series": self.reporter.series("active"),
        }


# -- distribution helpers (the two locked distributions) ----------------------

def uniform_thresholds(n: int = 100) -> List[int]:
    """The uniform distribution {0, 1, 2, ..., n-1} -- one agent at each integer
    threshold. For n=100 this is Granovetter's instigator-plus-uniform crowd."""
    return list(range(n))


def perturbed_thresholds(n: int = 100) -> List[int]:
    """The single-agent perturbation of ``uniform_thresholds``: remove the lone
    threshold-1 agent and add a SECOND agent at threshold 2. The multiset becomes
    {0, 2, 2, 3, 4, ..., n-1} -- a gap at 1, same size n. Mean-invariant to ~0.02%
    (the sum rises by exactly 1). This is the locked perturbation; do not alter it."""
    base = list(range(n))
    base.remove(1)        # drop the lone threshold-1 agent
    base.append(2)        # add a second threshold-2 agent
    return sorted(base)


def run_distribution(thresholds: Sequence[int]) -> Dict[str, Any]:
    """Run one threshold multiset to equilibrium and return its summary."""
    return ThresholdModel(thresholds).run()
