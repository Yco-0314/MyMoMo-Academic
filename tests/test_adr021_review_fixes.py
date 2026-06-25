"""Regression tests for the pre-push adversarial-review fixes (ADR-021 D1/D3/D4/D5).

Each test pins a confirmed bug the review caught so it cannot silently return.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd


# --- D3: benchmark_archetype is a construction-time ctx field ---------------

def test_benchmark_archetype_in_construction_time_fields():
    from abm_auto.pipeline.contract import CONSTRUCTION_TIME_FIELDS
    assert "benchmark_archetype" in CONSTRUCTION_TIME_FIELDS  # else contracts falsely flag it missing


# --- D1: backend values are coerced JSON-native (resume marker round-trips) --

def test_run_cell_coerces_numpy_to_jsonnative():
    import json
    from abm_auto.experiment import ExperimentSpec, _run_cell, register_backend

    @register_backend("_np_backend")
    def _b(params, seed):
        return {"metric": np.float64(3.5), "count": np.int64(7)}

    spec = ExperimentSpec(name="t", backend="_np_backend", sweep={"a": [1]})
    row = _run_cell(spec, {"params": {"a": 1}, "seed": 0})
    # values are python scalars, not numpy, not stringified
    assert type(row["metric"]) is float and row["metric"] == 3.5
    assert type(row["count"]) is int and row["count"] == 7
    # and the row round-trips through json without default=str stringification
    assert json.loads(json.dumps(row))["metric"] == 3.5


def test_marker_path_uses_full_sha256():
    from abm_auto.experiment import _marker_path
    from pathlib import Path
    p = _marker_path(Path("/tmp/x"), "some-cell-key")
    assert len(p.stem) == 64  # full sha256, not truncated to 16


# --- D5: _our_metrics never emits NaN (anti-fabrication) --------------------

def test_our_metrics_omits_empty_or_nan_columns(tmp_path):
    from abm_auto.pipeline.phases.benchmark_phase import _our_metrics
    results = tmp_path / "results" / "run_0"
    results.mkdir(parents=True)
    # a CSV whose 'peak_infected' column is all-NaN and 'final_infected' is real
    pd.DataFrame({"peak_infected": [np.nan, np.nan], "final_infected": [4.0, 9.0]}).to_csv(
        results / "out.csv", index=False)
    ctx = SimpleNamespace(workspace=SimpleNamespace(path=tmp_path))
    out = _our_metrics(ctx, ("peak_infected", "final_infected"))
    assert "peak_infected" not in out          # all-NaN -> omitted, never "nan"
    assert out["final_infected"] == 9.0        # real value kept
    assert all(np.isfinite(v) for v in out.values())


# --- D4: Critic._complete routes through BaseAgent.call_llm (retry path) ----

def test_critic_complete_uses_call_llm_not_raw_client(tmp_path, monkeypatch):
    from abm_auto.agents.critic import DesignCritic
    design = tmp_path / "DESIGN.md"
    design.write_text("beta = 0.3 chosen with no justification at all\n", encoding="utf-8")
    ctx = SimpleNamespace(workspace=SimpleNamespace(design_path=design, path=tmp_path))

    # client=None: if _complete called self.client.create it would AttributeError.
    critic = DesignCritic(client=None, workspace=None)
    calls = {}

    def fake_call_llm(system, user, max_tokens=8192, model=None):
        calls["used"] = True
        return '[{"code":"UNJUST","message":"beta unjustified","evidence":{"quote":"no justification at all"}}]'

    monkeypatch.setattr(critic, "call_llm", fake_call_llm)
    report = critic.run(ctx)                    # generate() -> _llm_candidates -> _complete -> call_llm
    assert calls.get("used") is True           # routed through the retry-wrapped call_llm
    assert not report.passed                    # the verified violation survived
    assert report.violations[0].evidence["quote"] in design.read_text(encoding="utf-8")
