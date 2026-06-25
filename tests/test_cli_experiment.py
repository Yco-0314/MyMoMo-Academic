"""Test for ADR-021 D1 — the `abm-auto experiment` CLI subcommand."""
from __future__ import annotations

import json

import pandas as pd
from typer.testing import CliRunner

from abm_auto.cli import app

runner = CliRunner()


def _spec_file(tmp_path, **over):
    data = {"name": "cli_t", "backend": "_demo", "sweep": {"a": [1, 2]}, "n_iter": 2}
    data.update(over)
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_experiment_cli_writes_csv(tmp_path, monkeypatch):
    monkeypatch.setattr("abm_auto.config.WORKSPACE_DIR", tmp_path)  # don't pollute repo workspace/
    sp = _spec_file(tmp_path)
    out = tmp_path / "results.csv"
    result = runner.invoke(app, ["experiment", str(sp), "--out", str(out)])
    assert result.exit_code == 0, result.output
    df = pd.read_csv(out)
    assert len(df) == 4  # 2 tuples × 2 seeds
    assert {"a", "seed", "value"}.issubset(df.columns)


def test_experiment_cli_prints_to_stdout(tmp_path, monkeypatch):
    monkeypatch.setattr("abm_auto.config.WORKSPACE_DIR", tmp_path)
    sp = _spec_file(tmp_path, sweep={"a": [1]}, n_iter=1)
    result = runner.invoke(app, ["experiment", str(sp)])
    assert result.exit_code == 0, result.output
    assert "value" in result.output  # the _demo backend's metric column header
