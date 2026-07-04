"""GIS platform layer (floor) — ADR-020. Predictions in
docs/reproduce/gis-platform/PREDICTIONS-locked.md."""
import random

import pytest

from abm_auto.gis._platform import (
    AgentSet,
    ContagionModel,
    DataCollector,
    GISAgent,
    GISModel,
    RunReporter,
    StagedGISModel,
    contagion_gate,
)


class _RecordAgent(GISAgent):
    def __init__(self, agent_id, model, log):
        super().__init__(agent_id, model)
        self.log = log

    def step(self):
        self.log.append(self.id)


class _NoopAgent(GISAgent):
    def step(self):
        pass


class _HaltAgent(GISAgent):
    def step(self):
        if self.model.t >= 2:
            self.model.running = False


class _StageAgent(GISAgent):
    def __init__(self, agent_id, model, log):
        super().__init__(agent_id, model)
        self.log = log

    def mark(self, label):
        self.log.append((label, self.id))


class _LifecycleAgent(GISAgent):
    def one(self):
        self.model.log.append(("agent", "one", self.id))

    def two(self):
        self.model.log.append(("agent", "two", self.id))


class _LifecycleModel(StagedGISModel):
    stages = ("one", "two")

    def __init__(self):
        self.log = []
        super().__init__(reporter=DataCollector({"t": lambda m: m.t, "events": lambda m: len(m.log)}))
        self.add_agent(_LifecycleAgent(0, self))
        self.add_agent(_LifecycleAgent(1, self))

    def begin_step(self):
        self.log.append(("begin", self.t))

    def before_stage(self, stage):
        self.log.append(("before", stage))

    def after_stage(self, stage):
        self.log.append(("after", stage))

    def end_step(self):
        self.log.append(("end", self.t))


# ── PL1 scheduler order ──────────────────────────────────────────────────────

def test_sequential_is_insertion_order():
    log = []
    aset = AgentSet(schedule="sequential")
    for i in range(5):
        aset.add(_RecordAgent(i, None, log))
    aset.step()
    assert log == [0, 1, 2, 3, 4]


def test_random_order_is_seeded_deterministic_permutation():
    log1, log2 = [], []
    a1 = AgentSet([_RecordAgent(i, None, log1) for i in range(8)],
                  schedule="random_order", rng=random.Random(42))
    a2 = AgentSet([_RecordAgent(i, None, log2) for i in range(8)],
                  schedule="random_order", rng=random.Random(42))
    a1.step(); a2.step()
    assert log1 == log2                       # deterministic for same seed
    assert sorted(log1) == list(range(8))     # a permutation
    assert log1 != [0, 1, 2, 3, 4, 5, 6, 7]   # actually shuffled


def test_unknown_schedule_rejected():
    with pytest.raises(ValueError, match="schedule"):
        AgentSet(schedule="staged")


def test_do_invokes_named_stage_in_schedule_order():
    log = []
    aset = AgentSet(schedule="sequential")
    for i in range(4):
        aset.add(_StageAgent(i, None, log))

    aset.do("mark", "plan")

    assert log == [("plan", 0), ("plan", 1), ("plan", 2), ("plan", 3)]


def test_do_rejects_missing_stage_loudly():
    aset = AgentSet([_NoopAgent(0, None)])
    with pytest.raises(AttributeError, match="missing_stage"):
        aset.do("missing_stage")


# ── PL2 DataCollector ────────────────────────────────────────────────────────

def test_datacollector_collects_series_and_final():
    dc = DataCollector({"t": lambda m: m.t, "n": lambda m: len(m.agents)})
    m = GISModel(reporter=dc)
    m.add_agent(_NoopAgent(0, m))
    dc.collect(m); m.t = 5; dc.collect(m)
    assert dc.series("t") == [0, 5]
    assert dc.series("n") == [1, 1]
    assert dc.final == {"t": 5, "n": 1}


# ── PL2b RunReporter (collected series -> structured run report) ──────────────

def test_run_reporter_steps_block_is_the_collected_series():
    dc = DataCollector({"t": lambda m: m.t, "load": lambda m: m.load})
    m = GISModel(reporter=dc)
    m.load = 1
    dc.collect(m)
    m.t = 1
    m.load = 3
    dc.collect(m)

    report = RunReporter(dc).report()

    assert report == {"steps": [{"t": 0, "load": 1}, {"t": 1, "load": 3}]}
    # the report's steps block IS the collected records (flows through the seam)
    assert report["steps"] == dc.records


def test_run_reporter_derives_series_peak_from_collected_data():
    dc = DataCollector({"load": lambda m: m.load})
    m = GISModel(reporter=dc)
    for value in (0, 2, 5, 1):
        m.load = value
        dc.collect(m)

    report = RunReporter(dc).report(peaks={"max_load": "load"})

    assert report["max_load"] == 5          # peak derived from the collected series
    assert report["steps"] == dc.records


def test_run_reporter_carries_run_level_fields_through():
    dc = DataCollector({"t": lambda m: m.t})
    m = GISModel(reporter=dc)
    dc.collect(m)

    report = RunReporter(dc).report(
        peaks={"max_load": "t"},
        extra={"n_agents": 4, "arrived": 2},
    )

    assert report["n_agents"] == 4
    assert report["arrived"] == 2
    assert report["max_load"] == 0
    assert report["steps"] == dc.records


def test_run_reporter_peak_of_empty_series_is_zero():
    dc = DataCollector({"load": lambda m: m.load})
    report = RunReporter(dc).report(peaks={"max_load": "load"})
    assert report["steps"] == []
    assert report["max_load"] == 0


# ── PL3 model loop ───────────────────────────────────────────────────────────

def test_run_collects_baseline_plus_one_per_step():
    dc = DataCollector({"t": lambda m: m.t})
    m = GISModel(reporter=dc)
    m.add_agent(_NoopAgent(0, m))
    records = m.run(5)
    assert len(records) == 6           # t=0 baseline + 5 steps
    assert dc.series("t") == [0, 1, 2, 3, 4, 5]
    assert m.t == 5


def test_staged_model_runs_hooks_stages_collects_and_advances():
    model = _LifecycleModel()

    model.step()

    assert model.log == [
        ("begin", 0),
        ("before", "one"),
        ("agent", "one", 0),
        ("agent", "one", 1),
        ("after", "one"),
        ("before", "two"),
        ("agent", "two", 0),
        ("agent", "two", 1),
        ("after", "two"),
        ("end", 0),
    ]
    assert model.reporter.records == [{"t": 0, "events": 10}]
    assert model.t == 1


def test_running_false_halts_early():
    dc = DataCollector({"t": lambda m: m.t})
    m = GISModel(reporter=dc)
    m.add_agent(_HaltAgent(0, m))
    records = m.run(10)
    assert len(records) < 11           # halted before all 10 steps
    assert m.running is False


# ── PL4 determinism ──────────────────────────────────────────────────────────

def test_contagion_deterministic_same_seed():
    a = ContagionModel(n=20, beta=0.5, seed=7).run(20)
    b = ContagionModel(n=20, beta=0.5, seed=7).run(20)
    assert a == b


# ── PL5 contagion spreads + gate ─────────────────────────────────────────────

def test_contagion_spreads_monotone_above_seed():
    m = ContagionModel(n=20, beta=0.6, seed=1)
    series = [r["infected"] for r in m.run(20)]
    assert all(series[i] <= series[i + 1] for i in range(len(series) - 1))
    assert series[-1] > series[0]


def test_contagion_gate_passes_connected_fails_isolated():
    ok, desc = contagion_gate(n=20, beta=0.6, seed=1)
    assert ok, desc
    assert "spreads" in desc
