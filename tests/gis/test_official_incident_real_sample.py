import copy
import json
import shutil
from pathlib import Path

import pytest

from abm_auto.gis._official_incident_real_sample import (
    OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_MANIFEST,
    OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_SCHEMA,
    load_arcgis_closure_features,
    load_official_incident_real_sample_manifest,
    official_incident_real_sample_gate,
    official_incident_real_sample_report,
    prepare_arcgis_closure_timestamp_rows,
    verify_official_incident_real_sample_checksums,
)


def _copy_fixture(tmp_path: Path) -> Path:
    source_dir = OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_MANIFEST.parent
    dest_dir = tmp_path / source_dir.name
    shutil.copytree(source_dir, dest_dir)
    return dest_dir / "repro_manifest.json"


def _write_manifest_override(path: Path, **overrides) -> Path:
    raw = json.loads(path.read_text(encoding="utf-8"))
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(raw.get(key), dict):
            raw[key].update(value)
        else:
            raw[key] = value
    path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    return path


def _sample_feature() -> dict:
    return load_arcgis_closure_features(
        OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_MANIFEST.parent / "raw.json"
    )[0]


def test_real_sample_manifest_loads_and_resolves_paths():
    manifest = load_official_incident_real_sample_manifest(
        OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_MANIFEST
    )

    assert manifest["schema"] == OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_SCHEMA
    assert manifest["dataset"] == "King County RoadClosures_public bounded closure sample"
    assert manifest["source_agency"] == "King County Emergency Management"
    assert Path(manifest["raw_arcgis_path"]).exists()
    assert Path(manifest["clock_manifest_path"]).exists()
    assert Path(manifest["intake_manifest_path"]).exists()
    assert manifest["expected"]["expected_raw_features"] == 1


def test_real_sample_checksum_verification_passes():
    manifest = load_official_incident_real_sample_manifest(
        OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_MANIFEST
    )

    result = verify_official_incident_real_sample_checksums(manifest)

    assert result == {
        "raw_arcgis_checked": True,
        "raw_arcgis_ok": True,
        "issues": [],
        "ok": True,
    }


def test_load_arcgis_closure_features_returns_committed_feature():
    features = load_arcgis_closure_features(
        OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_MANIFEST.parent / "raw.json"
    )

    assert len(features) == 1
    assert features[0]["attributes"]["OBJECTID"] == 73
    assert features[0]["attributes"]["street"] == "Maple Valley Highway"


def test_load_arcgis_closure_features_rejects_malformed_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"features": "not-a-list"}), encoding="utf-8")

    with pytest.raises(ValueError, match="features must be a non-empty list"):
        load_arcgis_closure_features(path)


def test_prepare_arcgis_closure_timestamp_rows_converts_epoch_ms_to_utc():
    rows = prepare_arcgis_closure_timestamp_rows([_sample_feature()])

    assert rows == [
        {
            "incident_id": "67da9afb-5c94-42a1-8406-659ced32b886",
            "x": -13602219.6296413,
            "y": 6020749.277737305,
            "started_at": "2025-12-17T07:41:22+00:00",
            "ended_at": "2025-12-17T16:00:00+00:00",
            "street": "Maple Valley Highway",
            "description": "One lane closed due to landslide across from Riviera Apartments",
            "objectid": "73",
            "globalid": "67da9afb-5c94-42a1-8406-659ced32b886",
        }
    ]


def test_prepare_arcgis_closure_timestamp_rows_rejects_test_description():
    feature = copy.deepcopy(_sample_feature())
    feature["attributes"]["description"] = "TEST ROAD CLOSURE"

    with pytest.raises(ValueError, match="TEST closure descriptions are not accepted"):
        prepare_arcgis_closure_timestamp_rows([feature])


def test_prepare_arcgis_closure_timestamp_rows_rejects_missing_endtime():
    feature = copy.deepcopy(_sample_feature())
    feature["attributes"]["endtime"] = None

    with pytest.raises(ValueError, match="endtime must be an epoch millisecond integer"):
        prepare_arcgis_closure_timestamp_rows([feature])


def test_prepare_arcgis_closure_timestamp_rows_rejects_bad_geometry():
    feature = copy.deepcopy(_sample_feature())
    feature["geometry"]["paths"] = [[[-13602372.2365563, 6020903.491046]]]

    with pytest.raises(ValueError, match="first geometry path must contain at least two points"):
        prepare_arcgis_closure_timestamp_rows([feature])


def test_real_sample_report_passes_with_subreports():
    report = official_incident_real_sample_report(
        OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_MANIFEST
    )

    assert report["ok"] is True
    assert report["reason"] == ""
    assert report["n_raw_features"] == 1
    assert report["n_timestamped_intervals"] == 1
    assert report["clock_report"]["n_tick_events"] == 2
    assert report["intake_report"]["diagnostics"]["matched_events"] == 2
    assert report["dynamic_report"]["effect"]["changed"] is True
    assert report["summary"] == {
        "raw_features": 1,
        "timestamped_intervals": 1,
        "tick_events": 2,
        "matched_incidents": 2,
        "dynamic_changed": True,
    }
    assert "not traffic-flow validity" in report["boundary_note"]


def test_real_sample_gate_passes_with_boundary_text():
    ok, desc = official_incident_real_sample_gate(
        OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_MANIFEST
    )

    assert ok, desc
    assert "official incident real sample pack passed" in desc
    assert "King County RoadClosures_public" in desc
    assert "raw_features=1" in desc
    assert "matched_incidents=2" in desc
    assert "bounded real official road-closure sample" in desc
    assert "not traffic-flow validity" in desc


def test_expected_raw_feature_mismatch_fails(tmp_path):
    manifest_path = _copy_fixture(tmp_path)
    _write_manifest_override(
        manifest_path,
        expected={"expected_raw_features": 2},
    )

    report = official_incident_real_sample_report(manifest_path)

    assert report["ok"] is False
    assert report["reason"] == "raw feature count did not match expected_raw_features"
