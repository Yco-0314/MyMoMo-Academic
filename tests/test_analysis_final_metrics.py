"""Tests for results_reader.final_metrics — the per-run final-step metric vector
shared by analyze_runs() and the memory-ingest phase (which previously diverged on
which CSV defines a run's metrics)."""
from __future__ import annotations

from abm_auto.analysis.results_reader import final_metrics


def _csv(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_picks_env_csv_and_takes_last_row(tmp_path):
    # The 'env' CSV is preferred; metadata cols (step) are excluded.
    _csv(tmp_path / "agents.csv", "step,x\n0,1\n1,2\n")
    _csv(tmp_path / "environment.csv", "step,infected,susceptible\n0,5,95\n1,8,92\n")
    out = final_metrics([tmp_path / "agents.csv", tmp_path / "environment.csv"])
    assert out == {"infected": 8.0, "susceptible": 92.0}


def test_excludes_identifier_columns(tmp_path):
    _csv(tmp_path / "env.csv", "step,id_scenario,id_run,value\n0,1,1,10\n1,1,1,20\n")
    assert final_metrics([tmp_path / "env.csv"]) == {"value": 20.0}


def test_empty_input_list(tmp_path):
    assert final_metrics([]) == {}


def test_header_only_csv_returns_empty(tmp_path):
    _csv(tmp_path / "env.csv", "step,value\n")
    assert final_metrics([tmp_path / "env.csv"]) == {}
