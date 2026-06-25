"""GIS-ABM platform layer — minimal Mesa-shaped floor abstractions.

Ends the "5 hand-written step loops" duplication (one per ABM module). A new GIS
ABM subclasses `GISAgent` (override `step`) + `GISModel` (optionally override
`step` for a non-default tick order), instead of re-implementing agent state, a
scheduler, a collector, and a run loop by hand.

Mesa's *shape*, not its code — no Mesa dependency. Deterministic: one seeded RNG
chain on the model.
"""
from __future__ import annotations

import random
from typing import Any, Callable, Dict, Iterable, List, Optional


# ── GISAgent ─────────────────────────────────────────────────────────────────

class GISAgent:
    """One agent. Subclass and override `step`. Carries an id and a back-reference
    to its model (for RNG, space, and neighbour lookup)."""

    def __init__(self, agent_id: int, model: "GISModel") -> None:
        self.id = agent_id
        self.model = model

    def step(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError("subclasses override step()")


# ── AgentSet (scheduler) ─────────────────────────────────────────────────────

class AgentSet:
    """Ordered agent collection + scheduler strategy.

    Strategies: ``sequential`` (insertion order) and ``random_order`` (a seeded
    permutation per step). ``concurrent``/``staged`` are deferred (YAGNI:
    the existing 5 ABM modules all iterate sequentially).
    """

    _STRATEGIES = ("sequential", "random_order")

    def __init__(self, agents: Iterable[GISAgent] = (), *, schedule: str = "sequential",
                 rng: Optional[random.Random] = None) -> None:
        if schedule not in self._STRATEGIES:
            raise ValueError(f"unknown schedule {schedule!r}; expected {self._STRATEGIES}")
        self._agents: List[GISAgent] = list(agents)
        self.schedule = schedule
        self._rng = rng or random.Random(0)

    def add(self, agent: GISAgent) -> None:
        self._agents.append(agent)

    def __iter__(self):
        return iter(self._agents)

    def __len__(self) -> int:
        return len(self._agents)

    def ordered(self) -> List[GISAgent]:
        if self.schedule == "random_order":
            order = list(self._agents)
            self._rng.shuffle(order)
            return order
        return list(self._agents)

    def step(self) -> None:
        for agent in self.ordered():
            agent.step()


# ── DataCollector ────────────────────────────────────────────────────────────

class DataCollector:
    """Per-tick metric collection. `metrics` maps name -> callable(model) -> value."""

    def __init__(self, metrics: Dict[str, Callable[["GISModel"], Any]]) -> None:
        self.metrics = dict(metrics)
        self.records: List[Dict[str, Any]] = []

    def collect(self, model: "GISModel") -> None:
        self.records.append({name: fn(model) for name, fn in self.metrics.items()})

    def series(self, name: str) -> list:
        return [r[name] for r in self.records]

    @property
    def final(self) -> Dict[str, Any]:
        return dict(self.records[-1]) if self.records else {}


# ── GISModel ─────────────────────────────────────────────────────────────────

class GISModel:
    """Glue: space + seeded RNG + an AgentSet + an optional DataCollector + tick.

    Default `step` runs the schedule, advances `t`, and collects. Subclasses
    override `step` for a non-default tick order (e.g. flood-first-then-agents).
    """

    def __init__(self, *, space: Any = None, seed: int = 0,
                 schedule: str = "sequential",
                 reporter: Optional[DataCollector] = None) -> None:
        self.space = space
        self.rng = random.Random(seed)
        self.t = 0
        self.running = True
        self.agents = AgentSet([], schedule=schedule, rng=self.rng)
        self.reporter = reporter

    def add_agent(self, agent: GISAgent) -> None:
        self.agents.add(agent)

    def step(self) -> None:
        self.agents.step()
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_steps: int) -> Optional[List[Dict[str, Any]]]:
        if self.reporter is not None:
            self.reporter.collect(self)          # t=0 baseline
        for _ in range(n_steps):
            if not self.running:
                break
            self.step()
        return self.reporter.records if self.reporter is not None else None


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
