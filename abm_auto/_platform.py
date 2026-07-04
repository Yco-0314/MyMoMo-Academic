"""Neutral ABM platform layer — minimal Mesa-shaped floor abstractions (ADR-020).

Promoted out of ``abm_auto/gis/_platform.py`` so non-spatial ABM modules (coord/,
later closed extensions) can ride the same agent floor WITHOUT inheriting the optional GIS
deps (rasterio/pyproj) that importing ``abm_auto.gis`` would pull. The logic here
is moved verbatim from the GIS platform; only the names are neutral.

A new ABM subclasses ``Agent`` (override ``step``) + ``AgentModel`` (optionally
override ``step`` for a non-default tick order), instead of re-implementing agent
state, a scheduler, a collector, and a run loop by hand.

Mesa's *shape*, not its code — no Mesa dependency, only ``random`` + ``typing``.
Deterministic: one seeded RNG chain on the model.
"""
from __future__ import annotations

import random
from typing import Any, Callable, Dict, Iterable, List, Optional


# ── Agent ────────────────────────────────────────────────────────────────────

class Agent:
    """One agent. Subclass and override `step`. Carries an id and a back-reference
    to its model (for RNG, space, and neighbour lookup)."""

    def __init__(self, agent_id: int, model: "AgentModel") -> None:
        self.id = agent_id
        self.model = model

    def step(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError("subclasses override step()")


# ── AgentSet (scheduler) ─────────────────────────────────────────────────────

class AgentSet:
    """Ordered agent collection + scheduler strategy.

    Strategies: ``sequential`` (insertion order) and ``random_order`` (a seeded
    permutation per step). ``concurrent``/``staged`` are deferred (ADR-020 YAGNI:
    the existing 5 ABM modules all iterate sequentially).
    """

    _STRATEGIES = ("sequential", "random_order")

    def __init__(self, agents: Iterable["Agent"] = (), *, schedule: str = "sequential",
                 rng: Optional[random.Random] = None) -> None:
        if schedule not in self._STRATEGIES:
            raise ValueError(f"unknown schedule {schedule!r}; expected {self._STRATEGIES}")
        self._agents: List["Agent"] = list(agents)
        self.schedule = schedule
        self._rng = rng or random.Random(0)

    def add(self, agent: "Agent") -> None:
        self._agents.append(agent)

    def __iter__(self):
        return iter(self._agents)

    def __len__(self) -> int:
        return len(self._agents)

    def ordered(self) -> List["Agent"]:
        if self.schedule == "random_order":
            order = list(self._agents)
            self._rng.shuffle(order)
            return order
        return list(self._agents)

    def step(self) -> None:
        for agent in self.ordered():
            agent.step()

    def do(self, method_name: str, *args, **kwargs) -> None:
        """Run a named per-agent stage in the configured schedule order."""
        for agent in self.ordered():
            getattr(agent, method_name)(*args, **kwargs)


# ── DataCollector ────────────────────────────────────────────────────────────

class DataCollector:
    """Per-tick metric collection. `metrics` maps name -> callable(model) -> value."""

    def __init__(self, metrics: Dict[str, Callable[["AgentModel"], Any]]) -> None:
        self.metrics = dict(metrics)
        self.records: List[Dict[str, Any]] = []

    def collect(self, model: "AgentModel") -> None:
        self.records.append({name: fn(model) for name, fn in self.metrics.items()})

    def series(self, name: str) -> list:
        return [r[name] for r in self.records]

    @property
    def final(self) -> Dict[str, Any]:
        return dict(self.records[-1]) if self.records else {}


# ── RunReporter ──────────────────────────────────────────────────────────────

class RunReporter:
    """Turns a `DataCollector`'s collected series into a structured run report.

    The seam between per-tick collection and the run-level summary a production
    adapter returns. The report's ``steps`` block *is* the collected records, and
    any run-level peak (e.g. the busiest tick of a per-tick series) is derived
    from that collected data rather than tracked separately on the model.
    Run-level fields the collector cannot see (agent rosters, scalar counters)
    are passed through as ``extra``.
    """

    def __init__(self, collector: DataCollector) -> None:
        self.collector = collector

    def report(self, *, peaks: Optional[Dict[str, str]] = None,
               extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        records = self.collector.records
        out: Dict[str, Any] = {"steps": records}
        for out_name, series_name in (peaks or {}).items():
            out[out_name] = max(self.collector.series(series_name), default=0)
        if extra:
            out.update(extra)
        return out


# ── AgentModel ───────────────────────────────────────────────────────────────

class AgentModel:
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

    def add_agent(self, agent: "Agent") -> None:
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


# ── StagedAgentModel ─────────────────────────────────────────────────────────

class StagedAgentModel(AgentModel):
    """A model-specific multi-stage tick over a scheduled AgentSet.

    Subclasses name the per-agent `stages` and use hooks to prepare or update
    tick-level context. The platform owns the lifecycle shape and summary
    collection; subclasses own domain logic.
    """

    stages: tuple[str, ...] = ()

    def begin_step(self) -> None:
        pass

    def before_stage(self, stage: str) -> None:
        pass

    def after_stage(self, stage: str) -> None:
        pass

    def end_step(self) -> None:
        pass

    def step(self) -> None:
        self.begin_step()
        for stage in self.stages:
            self.before_stage(stage)
            self.agents.do(stage)
            self.after_stage(stage)
        self.end_step()
        if self.reporter is not None:
            self.reporter.collect(self)
        self.t += 1
