"""Tests for the canonical metric-column seam (analysis-1).

trajectory_analyzer and statistics used to carry their own skip-lists that drifted
from results_reader.METADATA_COLS — notably they listed "scenario_id" while the
runtime emits "id_scenario", so identifier/coordinate columns leaked in as metrics.
Both now delegate to numeric_metrics(); this pins what it excludes.
"""
from __future__ import annotations

import pandas as pd

from abm_auto.analysis.results_reader import numeric_metrics, select_environment_csv


def test_numeric_metrics_excludes_identifiers_time_and_coordinates():
    df = pd.DataFrame({
        "id_scenario": [0, 0, 0],
        "id_run": [1, 1, 1],
        "run_num": [1, 1, 1],
        "period": [0, 1, 2],
        "step": [0, 1, 2],
        "t": [0, 1, 2],
        "x": [1.0, 2.0, 3.0],
        "y": [4.0, 5.0, 6.0],
        "infected": [3, 5, 8],
        "susceptible": [97, 95, 92],
    })
    # Identifiers (id_scenario/id_run/run_num), time (period/step/t) and spatial
    # coords (x/y) are metadata; only real metrics survive, in column order.
    assert numeric_metrics(df) == ["infected", "susceptible"]


def test_numeric_metrics_skips_non_numeric_columns():
    df = pd.DataFrame({"label": ["a", "b"], "value": [1.0, 2.0]})
    assert numeric_metrics(df) == ["value"]


def test_numeric_metrics_is_case_insensitive_on_metadata():
    df = pd.DataFrame({"ID_Scenario": [0, 1], "Period": [0, 1], "payoff": [1.0, 2.0]})
    assert numeric_metrics(df) == ["payoff"]


# ── select_environment_csv (analysis-2) ─────────────────────────────────────


def test_select_environment_csv_prefers_env_file(tmp_path):
    files = [tmp_path / "agent.csv", tmp_path / "environment.csv", tmp_path / "z.csv"]
    assert select_environment_csv(files).name == "environment.csv"


def test_select_environment_csv_falls_back_to_sorted_first(tmp_path):
    # No env file: deterministic — first by sorted name, regardless of input order.
    files = [tmp_path / "b.csv", tmp_path / "a.csv"]
    assert select_environment_csv(files).name == "a.csv"


def test_select_environment_csv_deterministic_when_multiple_env(tmp_path):
    files = [tmp_path / "env_b.csv", tmp_path / "env_a.csv"]
    assert select_environment_csv(files).name == "env_a.csv"


def test_select_environment_csv_empty_is_none():
    assert select_environment_csv([]) is None
