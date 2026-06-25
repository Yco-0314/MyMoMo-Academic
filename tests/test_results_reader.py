"""Tests for the canonical metric-column filter (results_reader.numeric_metrics).

Pins the contract that pipeline/agents rely on to tell metrics from identifiers:
the runtime data collector emits id_scenario / id_run / period as core identifier
columns (see runtime/_data_collector._CORE_PROPERTIES_), so those must never be
treated as metrics. A local skip-list in the memory-ingest path used to miss them.
"""
from __future__ import annotations

import pandas as pd

from abm_auto.analysis.results_reader import METADATA_COLS, numeric_metrics


def test_metadata_cols_uses_canonical_id_naming():
    # The emitted identifier columns are id_scenario / id_run, not "scenario_id".
    assert {"id_scenario", "id_run"} <= METADATA_COLS
    assert "scenario_id" not in METADATA_COLS


def test_numeric_metrics_excludes_runtime_identifier_columns():
    df = pd.DataFrame({
        "id_scenario": [0, 0, 0],
        "id_run": [1, 1, 1],
        "period": [0, 1, 2],
        "infected": [5, 8, 12],
        "susceptible": [95, 92, 88],
    })
    assert numeric_metrics(df) == ["infected", "susceptible"]


def test_numeric_metrics_excludes_coordinates_and_keeps_real_metrics():
    df = pd.DataFrame({
        "id": [1, 2], "step": [0, 1], "x": [3.0, 4.0], "y": [5.0, 6.0],
        "energy": [10.0, 9.0],
    })
    assert numeric_metrics(df) == ["energy"]


def test_numeric_metrics_skips_non_numeric_columns():
    df = pd.DataFrame({"label": ["a", "b"], "value": [1.0, 2.0]})
    assert numeric_metrics(df) == ["value"]
