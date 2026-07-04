"""GIS-ABM platform layer — GIS-named view of the neutral ABM floor (ADR-020).

The generic core (agent, scheduler, collector, reporter, model, staged model) now
lives in the dep-light neutral module ``abm_auto._platform`` so non-spatial ABM
modules (coord/, later closed extensions) can ride the same agent floor without inheriting the
optional GIS deps. This module re-exports that core under the historical GIS names
so existing gis code/tests are untouched, and KEEPS the GIS reference adapter
(``ContagionAgent``/``ContagionModel``/``contagion_gate``/``_IsolatedContagionModel``,
GIS adapter #1) defined on top of those aliases.

# ponytail: kept GIS-name aliases in gis/_platform.py so existing gis
# code/tests are untouched; upgrade path = rename gis subclasses to the neutral names.

Mesa's *shape*, not its code — no Mesa dependency. Deterministic: one seeded RNG
chain on the model.
"""
from __future__ import annotations

from abm_auto._platform import (
    Agent as GISAgent,
    AgentSet,
    DataCollector,
    RunReporter,
    AgentModel as GISModel,
    StagedAgentModel as StagedGISModel,
)

__all__ = [
    "GISAgent", "AgentSet", "DataCollector", "RunReporter", "GISModel",
    "StagedGISModel", "ContagionAgent", "ContagionModel", "contagion_gate",
]


# ── Reference model (adapter #1): line contagion on the platform ─────────────

class ContagionAgent(GISAgent):
    """S/I agent on a line. A susceptible agent catches the infection from any
    infected line-neighbour with probability `beta` (model RNG)."""

    def __init__(self, agent_id: int, model: "ContagionModel", infected: bool = False) -> None:
        super().__init__(agent_id, model)
        self.infected = infected

    def step(self) -> None:
        if self.infected:
            return
        m = self.model
        for nid in (self.id - 1, self.id + 1):
            if 0 <= nid < len(m.agents_by_id) and m.agents_by_id[nid].infected:
                if m.rng.random() < m.beta:
                    self.infected = True
                    return


class ContagionModel(GISModel):
    """A line of `n` agents; agent 0 starts infected. Demonstrates the platform
    floor end to end. Deterministic for a given seed."""

    def __init__(self, n: int = 20, beta: float = 0.5, seed: int = 0,
                 connected: bool = True, schedule: str = "sequential") -> None:
        super().__init__(seed=seed, schedule=schedule)
        self.beta = beta
        self.agents_by_id: List[ContagionAgent] = []
        for i in range(n):
            a = ContagionAgent(i, self, infected=(i == 0))
            self.agents_by_id.append(a)
            self.add_agent(a)
        if not connected:
            # isolate everyone: no agent sees a neighbour (override lookup width)
            self._connected = False
        else:
            self._connected = True
        self.reporter = DataCollector({"infected": lambda m: m.infected_count()})

    def infected_count(self) -> int:
        return sum(1 for a in self.agents_by_id if a.infected)


def contagion_gate(n: int = 20, beta: float = 0.5, seed: int = 0):
    """More steps -> the infection spreads: infected is monotone non-decreasing
    and ends strictly above the seed (1). Fails on an isolated population."""
    connected = ContagionModel(n=n, beta=beta, seed=seed, connected=True)
    series = [r["infected"] for r in connected.run(n)]
    if any(series[i] > series[i + 1] for i in range(len(series) - 1)):
        return False, f"infected not monotone: {series}"
    if series[-1] <= series[0]:
        return False, f"infection did not spread: {series}"

    isolated = _IsolatedContagionModel(n=n, beta=beta, seed=seed)
    iso_series = [r["infected"] for r in isolated.run(n)]
    if iso_series[-1] != iso_series[0]:
        return False, f"isolated population spread (impossible): {iso_series}"

    return True, (f"contagion spreads {series[0]} -> {series[-1]} over {n} steps; "
                  f"isolated stays {iso_series[0]}")


class _IsolatedContagionModel(ContagionModel):
    """No-neighbour control: every agent's neighbour lookup finds nobody."""

    class _Loner(ContagionAgent):
        def step(self) -> None:   # never catches: no reachable neighbours
            return

    def __init__(self, n: int = 20, beta: float = 0.5, seed: int = 0) -> None:
        GISModel.__init__(self, seed=seed)
        self.beta = beta
        self.agents_by_id = []
        for i in range(n):
            a = self._Loner(i, self, infected=(i == 0))
            self.agents_by_id.append(a)
            self.add_agent(a)
        self.reporter = DataCollector({"infected": lambda m: m.infected_count()})
