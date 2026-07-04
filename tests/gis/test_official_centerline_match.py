import json
import shutil
from pathlib import Path

import pytest

from abm_auto.gis._official_centerline_match import (
    OFFICIAL_CENTERLINE_MATCH_SCHEMA,
    SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
    load_official_centerline_geonet,
    load_official_centerline_match_manifest,
    official_centerline_edge_match_gate,
    official_centerline_edge_match_report,
    verify_official_centerline_match_checksums,
)


def _copy_fixture(tmp_path: Path) -> Path:
    source_dir = SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST.parent
    dest_parent = tmp_path / source_dir.parent.name
    shutil.copytree(source_dir.parent, dest_parent)
    return dest_parent / source_dir.name / "manifest.json"


def _write_manifest_override(path: Path, **overrides) -> Path:
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw.update(overrides)
    path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    return path


def test_centerline_match_manifest_loads_and_preserves_provenance():
    manifest = load_official_centerline_match_manifest(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST
    )

    assert manifest["schema"] == OFFICIAL_CENTERLINE_MATCH_SCHEMA
    assert manifest["dataset"] == "Seattle SDOT 2023 FLOWMAP centerline match"
    assert manifest["source_agency"] == "Seattle Department of Transportation"
    assert manifest["road_dataset"] == "Seattle Streets"
    assert manifest["crs"] == "EPSG:2926"
    assert manifest["expected_min_coverage"] == 1.0
    assert manifest["expected_max_match_distance_m"] == pytest.approx(0.001)
    assert manifest["expected_station_streets"] == {
        "sdot-342953": "15TH AVE NE",
        "sdot-342077": "17TH AVE S",
        "sdot-342019": "MARINE VIEW DR SW",
    }
    assert Path(manifest["traffic_count_manifest_path"]).exists()
    assert Path(manifest["centerline_raw_path"]).exists()


def test_centerline_match_checksums_cover_counts_and_streets():
    manifest = load_official_centerline_match_manifest(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST
    )

    checksum = verify_official_centerline_match_checksums(manifest)

    assert checksum == {
        "traffic_count_checked": True,
        "traffic_count_ok": True,
        "centerline_raw_checked": True,
        "centerline_raw_ok": True,
        "issues": [],
        "ok": True,
    }


def test_arcgis_centerline_fixture_builds_segmented_geonet():
    manifest = load_official_centerline_match_manifest(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST
    )

    loaded = load_official_centerline_geonet(manifest)

    assert loaded["geonet"].crs == "EPSG:2926"
    assert loaded["n_features"] == 3
    assert loaded["n_segments"] == 9
    assert loaded["geonet"].graph.number_of_edges() == 9
    assert loaded["street_names"] == [
        "15TH AVE NE",
        "17TH AVE S",
        "MARINE VIEW DR SW",
    ]


def test_official_centerline_report_matches_count_points_to_real_streets():
    report = official_centerline_edge_match_report(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST
    )

    assert report["ok"] is True
    assert report["reason"] == ""
    assert report["diagnostics"]["coverage"] == 1.0
    assert report["diagnostics"]["matched_edges"] == 3
    assert report["diagnostics"]["max_match_distance_m"] < 0.001
    assert report["station_streets"] == {
        "sdot-342953": "15TH AVE NE",
        "sdot-342077": "17TH AVE S",
        "sdot-342019": "MARINE VIEW DR SW",
    }
    assert report["station_objectids"] == {
        "sdot-342953": 9659868,
        "sdot-342077": 9638977,
        "sdot-342019": 9645707,
    }
    assert report["observed_edge_values"] == {
        ((1276115, 246592), (1276138, 247362)): 5497.0,
        ((1275907, 218141), (1275915, 218541)): 1164.0,
        ((1257176, 188607), (1257591, 188593)): 1047.0,
    }


def test_official_centerline_gate_passes_with_boundary_text():
    ok, desc = official_centerline_edge_match_gate(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST
    )

    assert ok, desc
    assert "official centerline edge match passed" in desc
    assert "Seattle SDOT 2023 FLOWMAP centerline match" in desc
    assert "coverage=1.0" in desc
    assert "streets=3" in desc
    assert "not traffic-flow validity" in desc
    assert "not production map matching" in desc


def test_centerline_report_fails_when_distance_tolerance_is_too_strict(tmp_path):
    manifest_path = _copy_fixture(tmp_path)
    _write_manifest_override(manifest_path, expected_max_match_distance_m=0.000001)

    report = official_centerline_edge_match_report(manifest_path)

    assert report["ok"] is False
    assert "max match distance exceeds expected_max_match_distance_m" in report[
        "reason"
    ]
    assert report["diagnostics"]["coverage"] == 1.0


def test_centerline_report_fails_when_street_expectation_changes(tmp_path):
    manifest_path = _copy_fixture(tmp_path)
    _write_manifest_override(
        manifest_path,
        expected_station_streets={
            "sdot-342953": "15TH AVE NE",
            "sdot-342077": "WRONG STREET",
            "sdot-342019": "MARINE VIEW DR SW",
        },
    )

    report = official_centerline_edge_match_report(manifest_path)

    assert report["ok"] is False
    assert "station street mismatch" in report["reason"]
    assert report["station_streets"]["sdot-342077"] == "17TH AVE S"


def test_centerline_report_fails_before_matching_on_crs_mismatch(tmp_path):
    manifest_path = _copy_fixture(tmp_path)
    _write_manifest_override(manifest_path, crs="EPSG:3857")

    report = official_centerline_edge_match_report(manifest_path)

    assert report["ok"] is False
    assert report["reason"] == "official centerline edge match CRS mismatch"
    assert report["diagnostics"] is None


def test_centerline_report_fails_when_centerline_checksum_changes(tmp_path):
    manifest_path = _copy_fixture(tmp_path)
    manifest = load_official_centerline_match_manifest(manifest_path)
    Path(manifest["centerline_raw_path"]).write_text(
        "{\"features\": []}\n",
        encoding="utf-8",
    )

    report = official_centerline_edge_match_report(manifest_path)

    assert report["ok"] is False
    assert "centerline_raw_sha256 mismatch" in report["reason"]
    assert report["checksum"]["centerline_raw_ok"] is False
