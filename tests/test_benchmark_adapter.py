"""Tests for ADR-021 D5 — the cross-tool BenchmarkAdapter seam.

mesa + NetLogo are not installed here, so their real-run paths are skipped; the
seam, the skip handling, the trajectory reduction, and the render are fully tested.
"""
from __future__ import annotations

import pandas as pd
import pytest

from abm_auto.agents.benchmark_adapter import (
    BenchmarkAdapter,
    BenchmarkSpec,
    MesaBaseline,
    NetLogoBaseline,
    _reduce_trajectory,
    render_comparison_table,
    run_benchmarks,
)


class _FakeAdapter(BenchmarkAdapter):
    def __init__(self, name, available, metrics):
        self.name = name
        self._available = available
        self._metrics = metrics

    def is_available(self):
        return self._available

    def run(self, spec):
        return dict(self._metrics)


# --- 1. seam + run_benchmarks skip handling ------------------------------

def test_run_benchmarks_aggregates_and_skips_unavailable():
    spec = BenchmarkSpec(archetype="sir_network", metrics=("peak_infected",))
    adapters = [
        _FakeAdapter("toolA", True, {"peak_infected": 12.0}),
        _FakeAdapter("toolB", False, {"peak_infected": 99.0}),  # unavailable → skipped
    ]
    out = run_benchmarks(spec, adapters)
    assert out["toolA"] == {"peak_infected": 12.0}
    assert out["toolB"] == {"_unavailable": True}  # recorded, never the fabricated 99


def test_benchmark_spec_rejects_unknown_key():
    with pytest.raises(Exception):
        BenchmarkSpec(archetype="x", bogus=1)


# --- 3. NetLogoBaseline reduction + clean skip ---------------------------

def test_reduce_trajectory_takes_final_tick_mean():
    summary = pd.DataFrame(
        {"[step]": [0, 1, 2], "peak_infected_mean": [1.0, 5.0, 9.0], "peak_infected_std": [0, 1, 2]}
    )
    assert _reduce_trajectory(summary, ("peak_infected",)) == {"peak_infected": 9.0}


def test_reduce_trajectory_empty_is_empty():
    assert _reduce_trajectory(pd.DataFrame(), ("x",)) == {}


def test_netlogo_unavailable_without_model_path():
    # no .nlogo model path → cleanly unavailable, not an error
    assert NetLogoBaseline(model_path=None).is_available() is False


# --- 4. render comparison table ------------------------------------------

def test_render_table_shows_ours_and_unavailable():
    our = {"peak_infected": 10.0}
    results = {"mesa": {"peak_infected": 11.0}, "netlogo": {"_unavailable": True}}
    table = render_comparison_table(our, results)
    assert "| Metric | ours | mesa | netlogo |" in table
    assert "peak_infected" in table
    assert "10" in table and "11" in table
    assert "_tool unavailable_" in table  # netlogo column honestly marked


def test_render_all_unavailable_states_so_without_fabricating():
    table = render_comparison_table(
        {"peak_infected": 10.0}, {"mesa": {"_unavailable": True}}
    )
    assert "_tool unavailable_" in table


# --- 2. MesaBaseline real run (skipped unless mesa installed) -------------

def test_mesa_baseline_real_run_is_deterministic():
    pytest.importorskip("mesa")  # only with abm-auto[benchmarks]
    spec = BenchmarkSpec(
        archetype="sir_network",
        params={"beta": 0.3, "gamma": 0.1, "n_agents": 60, "k": 4},
        n_ticks=20, seed=7, metrics=("peak_infected", "final_infected"),
    )
    a = MesaBaseline()
    assert a.is_available() is True
    r1 = a.run(spec)
    r2 = a.run(spec)
    assert r1 == r2  # seeded → deterministic
    assert r1["peak_infected"] >= 1  # a real spreading run


def test_mesa_unavailable_is_clean():
    # whatever the environment, is_available() returns a bool and never raises
    assert isinstance(MesaBaseline().is_available(), bool)
