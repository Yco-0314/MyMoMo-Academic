"""Tests for ADR-021 D5 — BenchmarkPhase wiring (no LLM, fake adapters)."""
from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from abm_auto.agents.benchmark_adapter import BenchmarkAdapter
from abm_auto.pipeline.phases.benchmark_phase import BenchmarkPhase, _our_metrics


class _FakeAdapter(BenchmarkAdapter):
    def __init__(self, name, available, metrics):
        self.name = name
        self._available = available
        self._metrics = metrics

    def is_available(self):
        return self._available

    def run(self, spec):
        return dict(self._metrics)


def _ctx(tmp_path, archetype=None):
    return SimpleNamespace(
        workspace=SimpleNamespace(path=tmp_path),
        seed=0,
        benchmark_archetype=archetype,
        comparison_text=None,
    )


def test_should_run_off_by_default(tmp_path):
    assert BenchmarkPhase().should_run(_ctx(tmp_path, archetype=None)) is False


def test_should_run_when_archetype_set(tmp_path):
    assert BenchmarkPhase().should_run(_ctx(tmp_path, archetype="sir_network")) is True


def test_run_populates_comparison_text_with_table(tmp_path):
    ctx = _ctx(tmp_path, archetype="sir_network")
    adapters = [
        _FakeAdapter("mesa", True, {"peak_infected": 42.0, "final_infected": 3.0}),
        _FakeAdapter("netlogo", False, {}),  # unavailable → honest mark
    ]
    BenchmarkPhase(adapters=adapters).run(ctx)
    assert "Cross-tool baselines" in ctx.comparison_text
    assert "mesa" in ctx.comparison_text and "42" in ctx.comparison_text
    assert "_tool unavailable_" in ctx.comparison_text  # netlogo honestly marked


def test_run_appends_to_existing_comparison_text(tmp_path):
    ctx = _ctx(tmp_path, archetype="sir_network")
    ctx.comparison_text = "## CSV baseline\nexisting content"
    BenchmarkPhase(adapters=[_FakeAdapter("mesa", True, {"peak_infected": 1.0})]).run(ctx)
    assert ctx.comparison_text.startswith("## CSV baseline")  # preserved
    assert "Cross-tool baselines" in ctx.comparison_text     # appended


def test_our_metrics_reads_results_best_effort(tmp_path):
    run_dir = tmp_path / "results" / "run_1"
    run_dir.mkdir(parents=True)
    pd.DataFrame({"infected": [1, 5, 9, 2]}).to_csv(run_dir / "out.csv", index=False)
    out = _our_metrics(_ctx(tmp_path), ("peak_infected", "final_infected"))
    assert out["peak_infected"] == 9.0   # peak_ → max
    assert out["final_infected"] == 2.0  # final_ → last row


def test_our_metrics_missing_column_omitted(tmp_path):
    run_dir = tmp_path / "results" / "run_1"
    run_dir.mkdir(parents=True)
    pd.DataFrame({"unrelated": [1, 2]}).to_csv(run_dir / "out.csv", index=False)
    assert _our_metrics(_ctx(tmp_path), ("peak_infected",)) == {}  # never fabricated
