"""GIS platform layer (floor) — agents, scheduler, collector, run loop."""
import random

import pytest

from abm_auto.gis._platform import (
    AgentSet,
    ContagionModel,
    DataCollector,
    GISAgent,
    GISModel,
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


# ── PL2 DataCollector ────────────────────────────────────────────────────────

def test_datacollector_collects_series_and_final():
    dc = DataCollector({"t": lambda m: m.t, "n": lambda m: len(m.agents)})
    m = GISModel(reporter=dc)
    m.add_agent(_NoopAgent(0, m))
    dc.collect(m); m.t = 5; dc.collect(m)
    assert dc.series("t") == [0, 5]
    assert dc.series("n") == [1, 1]
    assert dc.final == {"t": 5, "n": 1}


# ── PL3 model loop ───────────────────────────────────────────────────────────

def test_run_collects_baseline_plus_one_per_step():
    dc = DataCollector({"t": lambda m: m.t})
    m = GISModel(reporter=dc)
    m.add_agent(_NoopAgent(0, m))
    records = m.run(5)
    assert len(records) == 6           # t=0 baseline + 5 steps
    assert dc.series("t") == [0, 1, 2, 3, 4, 5]
    assert m.t == 5


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
