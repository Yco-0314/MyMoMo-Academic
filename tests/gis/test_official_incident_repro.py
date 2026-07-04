import json
import shutil
from pathlib import Path

import pytest

from abm_auto.gis._official_incident_repro import (
    OFFICIAL_DYNAMIC_INCIDENT_REPRO_MANIFEST,
    OFFICIAL_DYNAMIC_INCIDENT_REPRO_SCHEMA,
    load_official_dynamic_incident_repro_manifest,
    official_dynamic_incident_repro_gate,
    official_dynamic_incident_repro_report,
)


def _copy_repro_fixture(tmp_path: Path) -> Path:
    source_dir = OFFICIAL_DYNAMIC_INCIDENT_REPRO_MANIFEST.parent
    source_root = source_dir.parent
    dest_root = tmp_path / source_root.name
    shutil.copytree(source_root, dest_root)
    return dest_root / source_dir.name / "manifest.json"


def _write_manifest_override(path: Path, **overrides) -> Path:
    raw = json.loads(path.read_text(encoding="utf-8"))
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(raw.get(key), dict):
            raw[key].update(value)
        else:
            raw[key] = value
    path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    return path


def test_official_dynamic_incident_repro_manifest_loads():
    manifest = load_official_dynamic_incident_repro_manifest(
        OFFICIAL_DYNAMIC_INCIDENT_REPRO_MANIFEST
    )

    assert manifest["schema"] == OFFICIAL_DYNAMIC_INCIDENT_REPRO_SCHEMA
    assert (
        manifest["dataset"]
        == "Synthetic official-style incident dynamic event-effect smoke"
    )
    assert Path(manifest["incident_manifest_path"]).exists()
    assert manifest["run"] == {
        "n_steps": 4,
        "speed_m_per_tick": 100.0,
        "reroute": False,
    }
    assert manifest["expected"]["expected_n_matched_incidents"] == 2
    assert manifest["expected"]["expected_incident_steps_with_closed_edges"] == [1, 2]


def test_official_dynamic_incident_repro_report_passes_with_summary():
    report = official_dynamic_incident_repro_report(
        OFFICIAL_DYNAMIC_INCIDENT_REPRO_MANIFEST
    )

    assert report["ok"] is True
    assert report["reason"] == ""
    assert report["summary"]["n_matched_incidents"] == 2
    assert report["summary"]["arrival_delay"] == 2.0
    assert report["summary"]["waiting_delta"] == 2
    assert report["summary"]["incident_steps_with_closed_edges"] == [1, 2]
    assert report["summary"]["max_closed_edges"] == 1
    assert report["summary"]["changed"] is True
    assert report["summary"]["baseline_mean_arrival_t"] == 1.0
    assert report["summary"]["incident_mean_arrival_t"] == 3.0
    assert report["smoke_report"]["ok"] is True
    json.dumps(report["summary"])


def test_official_dynamic_incident_repro_gate_passes_with_boundary_text():
    ok, desc = official_dynamic_incident_repro_gate(
        OFFICIAL_DYNAMIC_INCIDENT_REPRO_MANIFEST
    )

    assert ok, desc
    assert "official dynamic incident repro pack passed" in desc
    assert "matched_incidents=2" in desc
    assert "arrival_delay=2.0" in desc
    assert "waiting_delta=2" in desc
    assert "closed_edge_steps=[1, 2]" in desc
    assert "not traffic-flow validity" in desc
    assert "not production map matching" in desc
    assert "not real incident calibration" in desc


def test_official_dynamic_incident_repro_report_fails_when_expected_waiting_delta_is_wrong(
    tmp_path,
):
    manifest_path = _copy_repro_fixture(tmp_path)
    _write_manifest_override(
        manifest_path,
        expected={"expected_waiting_delta": 999.0},
    )

    report = official_dynamic_incident_repro_report(manifest_path)

    assert report["ok"] is False
    assert report["reason"] == "waiting delta did not match expected_waiting_delta"
    assert report["smoke_report"]["ok"] is True


def test_official_dynamic_incident_repro_manifest_rejects_bool_n_steps(tmp_path):
    manifest_path = _copy_repro_fixture(tmp_path)
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw["run"]["n_steps"] = True
    manifest_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="n_steps must be a positive integer"):
        load_official_dynamic_incident_repro_manifest(manifest_path)


def test_official_dynamic_incident_repro_manifest_rejects_empty_closed_steps(
    tmp_path,
):
    manifest_path = _copy_repro_fixture(tmp_path)
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw["expected"]["expected_incident_steps_with_closed_edges"] = []
    manifest_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            "expected_incident_steps_with_closed_edges must be a non-empty "
            "list of non-negative integers"
        ),
    ):
        load_official_dynamic_incident_repro_manifest(manifest_path)
