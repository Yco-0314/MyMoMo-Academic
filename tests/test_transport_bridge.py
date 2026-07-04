from __future__ import annotations

from pathlib import Path

from abm_auto.transport_bridge import (
    load_transport_bridge_manifest,
    summarize_transport_bridge_manifest,
    validate_transport_bridge_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_MANIFEST = (
    REPO_ROOT
    / "docs/reproduce/transport-bridge/synthetic-evacuation/bridge-manifest.json"
)


def _manifest(**overrides):
    manifest = {
        "schema": "abm-auto/transport-bridge-manifest/v1",
        "bridge_id": "synthetic-evacuation-bridge-v1",
        "engine": {
            "name": "external",
            "version": "not-run",
            "command": ["external-traffic-engine", "--scenario", "scenario.json"],
        },
        "scenario": {
            "name": "synthetic evacuation",
            "time_unit": "tick",
            "spatial_scope": "synthetic road network",
        },
        "inputs": [
            {"key": "network", "path": "inputs/network.json", "role": "road network"},
            {"key": "demand", "path": "inputs/demand.json", "role": "agent demand"},
        ],
        "outputs": [
            {
                "key": "edge_travel_time",
                "path": "outputs/edge_travel_time.csv",
                "reduction_metric": "mean edge travel time",
            }
        ],
        "claims": [
            {
                "id": "traffic-flow-audit",
                "metric": "mean edge travel time",
                "boundary_note": "manifest contract only; no external engine was run",
            }
        ],
    }
    manifest.update(overrides)
    return manifest


def test_valid_transport_bridge_manifest_passes():
    result = validate_transport_bridge_manifest(_manifest())

    assert result == {"ok": True, "issues": []}


def test_invalid_engine_fails():
    manifest = _manifest(engine={
        "name": "unsupported",
        "version": "1",
        "command": ["unsupported-engine"],
    })

    result = validate_transport_bridge_manifest(manifest)

    assert result["ok"] is False
    assert "engine.name must be one of MATSim, SUMO, external" in result["issues"]


def test_absolute_input_path_fails():
    manifest = _manifest(inputs=[
        {"key": "network", "path": "/tmp/network.json", "role": "road network"},
    ])

    result = validate_transport_bridge_manifest(manifest)

    assert result["ok"] is False
    assert "inputs[0].path must be relative" in result["issues"]


def test_duplicate_input_keys_fail():
    manifest = _manifest(inputs=[
        {"key": "network", "path": "inputs/network-a.json", "role": "road network"},
        {"key": "network", "path": "inputs/network-b.json", "role": "road network"},
    ])

    result = validate_transport_bridge_manifest(manifest)

    assert result["ok"] is False
    assert "duplicate input key network" in result["issues"]


def test_output_without_reduction_metric_fails():
    manifest = _manifest(outputs=[
        {"key": "travel_time", "path": "outputs/travel_time.csv"},
    ])

    result = validate_transport_bridge_manifest(manifest)

    assert result["ok"] is False
    assert "outputs[0].reduction_metric must be a non-empty string" in result["issues"]


def test_committed_seed_manifest_validates_and_loads():
    manifest = load_transport_bridge_manifest(SEED_MANIFEST)

    result = validate_transport_bridge_manifest(manifest)

    assert result["ok"] is True


def test_transport_bridge_summary_reports_counts():
    summary = summarize_transport_bridge_manifest(_manifest())

    assert summary == {
        "bridge_id": "synthetic-evacuation-bridge-v1",
        "engine": "external",
        "inputs": 2,
        "outputs": 1,
        "claims": 1,
    }
