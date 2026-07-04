"""BehaviorSpace manifest bridge tests.

These tests package existing NetLogo fixtures as audit manifests. They do not
run NetLogo headless and do not require NetLogo to be installed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from abm_auto.verification.netlogo_behaviorspace import (
    build_behaviorspace_manifest,
    extract_behaviorspace_experiments,
    find_behaviorspace_experiment,
    summarize_behaviorspace_output,
    write_behaviorspace_manifest,
)


MODEL = Path("tests/fixtures/netlogo/Virus_on_a_Network.nlogo")
SIR_TABLE = Path("tests/fixtures/netlogo/output/sir_trajectories.csv")
TOPOLOGY_TABLE = Path("tests/fixtures/netlogo/output/network_topology.csv")


def test_extracts_committed_behaviorspace_experiments():
    experiments = extract_behaviorspace_experiments(MODEL)

    assert [e.name for e in experiments] == [
        "oracle_sir_network_GT",
        "oracle_network_topology",
    ]

    sir = find_behaviorspace_experiment(MODEL, "oracle_sir_network_GT")
    assert sir.setup == "setup"
    assert sir.go == "go"
    assert sir.repetitions == 30
    assert sir.run_metrics_every_step is True
    assert sir.time_limit_steps == 250
    assert "count turtles with [infected?]" in sir.metrics
    assert sir.enumerated_values["number-of-nodes"] == ("150",)
    assert sir.to_dict()["enumerated_values"]["virus-spread-chance"] == ["4.4"]


def test_missing_behaviorspace_experiment_raises_clear_error():
    with pytest.raises(ValueError, match="BehaviorSpace experiment not found"):
        find_behaviorspace_experiment(MODEL, "missing_experiment")


def test_reduces_committed_topology_output_table():
    summary = summarize_behaviorspace_output(TOPOLOGY_TABLE, metrics=("count links",))

    assert summary["row_count"] == 30
    assert summary["run_count"] == 30
    assert summary["max_step"] == 770
    assert summary["metrics"]["count links"] == {
        "final_mean": 450.0,
        "max_mean": 450.0,
    }


def test_builds_manifest_with_command_experiment_tool_and_reduction():
    manifest = build_behaviorspace_manifest(
        MODEL,
        "oracle_sir_network_GT",
        SIR_TABLE,
    )

    assert manifest["schema"] == "netlogo-behaviorspace-manifest/v1"
    assert manifest["model_path"] == str(MODEL)
    assert manifest["experiment_name"] == "oracle_sir_network_GT"
    assert manifest["output_table_path"] == str(SIR_TABLE)
    assert manifest["command"][1:] == [
        "--model",
        str(MODEL),
        "--experiment",
        "oracle_sir_network_GT",
        "--table",
        str(SIR_TABLE),
    ]
    assert manifest["command"][0].endswith("netlogo-headless.sh")
    assert set(manifest["tool"]) == {"netlogo_dir", "java_home", "available"}
    assert manifest["experiment"]["repetitions"] == 30
    assert manifest["experiment"]["run_metrics_every_step"] is True
    assert manifest["experiment"]["time_limit_steps"] == 250
    assert "count turtles with [infected?]" in manifest["experiment"]["metrics"]
    assert manifest["reduction"]["row_count"] == 7530
    assert manifest["reduction"]["run_count"] == 30
    assert manifest["reduction"]["max_step"] == 250
    assert "count turtles with [infected?]" in manifest["reduction"]["metrics"]


def test_manifest_json_round_trip_has_stable_sorted_keys(tmp_path):
    manifest = build_behaviorspace_manifest(
        MODEL,
        "oracle_network_topology",
        TOPOLOGY_TABLE,
    )
    out = write_behaviorspace_manifest(manifest, tmp_path / "manifest.json")

    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded == manifest
    first_line = out.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "{"
