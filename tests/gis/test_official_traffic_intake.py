import hashlib
import json
from pathlib import Path

import pytest
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._official_traffic_intake import (
    DEFAULT_OFFICIAL_TRAFFIC_COUNT_MANIFEST,
    OFFICIAL_TRAFFIC_COUNT_SCHEMA,
    SEATTLE_SDOT_2023_FLOWMAP_MANIFEST,
    load_official_traffic_count_manifest,
    official_traffic_count_intake_gate,
    official_traffic_count_intake_report,
    verify_official_traffic_count_checksums,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_fixture_files(tmp_path: Path) -> dict[str, str]:
    raw = tmp_path / "raw_caltrans_fixture.csv"
    prepared = tmp_path / "prepared_counts.csv"
    raw.write_text(
        "raw_record_id,route,postmile,aadt,x,y\n"
        "r1,80,1.0,70,2,0.2\n"
        "r2,80,2.0,30,6,-0.3\n"
        "r3,80,3.0,40,5,9.6\n",
        encoding="utf-8",
    )
    prepared.write_text(
        "station_id,x,y,count,route,postmile,direction,county,raw_record_id\n"
        "main-a,2,0.2,70,80,1.0,E,Test,r1\n"
        "main-b,6,-0.3,30,80,2.0,E,Test,r2\n"
        "north,5,9.6,40,80,3.0,E,Test,r3\n",
        encoding="utf-8",
    )
    return {
        "raw": raw.name,
        "raw_sha256": _sha256(raw),
        "prepared": prepared.name,
        "prepared_sha256": _sha256(prepared),
    }


def _write_manifest(tmp_path: Path, **overrides) -> Path:
    files = _write_fixture_files(tmp_path)
    manifest = {
        "schema": OFFICIAL_TRAFFIC_COUNT_SCHEMA,
        "dataset": "Caltrans 2024 AADT synthetic fixture",
        "source_url": "https://dot.ca.gov/programs/traffic-operations/census",
        "source_agency": "California Department of Transportation",
        "license": "Public traffic census data; cite Caltrans Traffic Census Program",
        "downloaded_at": "2026-07-02",
        "raw_local_path": files["raw"],
        "raw_sha256": files["raw_sha256"],
        "prepared_csv_path": files["prepared"],
        "prepared_sha256": files["prepared_sha256"],
        "preparation_steps": [
            "Downloaded AADT source manually from the Caltrans Traffic Census page.",
            "Selected three synthetic fixture records for deterministic tests.",
            "Projected x/y columns into EPSG:3857 fixture coordinates.",
        ],
        "crs": "EPSG:3857",
        "columns": {
            "id": "station_id",
            "x": "x",
            "y": "y",
            "count": "count",
        },
        "count_metric": "AADT",
        "year": 2024,
        "geographic_scope": "synthetic Caltrans-style corridor fixture",
        "max_distance_m": 1.0,
        "aggregation": "sum",
        "expected_min_coverage": 1.0,
        "expected_max_match_distance_m": 0.5,
        "expected_edge_values": {
            "(0, 0)|(10, 0)": 100.0,
            "(0, 10)|(10, 10)": 40.0,
        },
        "boundary_note": "Official intake plumbing only; not traffic-flow validity.",
    }
    manifest.update(overrides)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def test_load_official_manifest_resolves_paths_and_preserves_provenance(tmp_path):
    manifest_path = _write_manifest(tmp_path)

    manifest = load_official_traffic_count_manifest(manifest_path)

    assert manifest["schema"] == OFFICIAL_TRAFFIC_COUNT_SCHEMA
    assert manifest["dataset"] == "Caltrans 2024 AADT synthetic fixture"
    assert manifest["source_agency"] == "California Department of Transportation"
    assert (
        manifest["source_url"]
        == "https://dot.ca.gov/programs/traffic-operations/census"
    )
    assert manifest["count_metric"] == "AADT"
    assert manifest["year"] == 2024
    assert manifest["crs"] == "EPSG:3857"
    assert manifest["raw_local_path"] == str(
        (tmp_path / "raw_caltrans_fixture.csv").resolve()
    )
    assert manifest["prepared_csv_path"] == str(
        (tmp_path / "prepared_counts.csv").resolve()
    )
    assert manifest["expected_min_coverage"] == 1.0
    assert manifest["expected_max_match_distance_m"] == 0.5
    assert (
        manifest["boundary_note"]
        == "Official intake plumbing only; not traffic-flow validity."
    )


def test_official_manifest_checksum_verification_passes_for_unchanged_files(tmp_path):
    manifest = load_official_traffic_count_manifest(_write_manifest(tmp_path))

    result = verify_official_traffic_count_checksums(manifest)

    assert result == {
        "raw_checked": True,
        "raw_ok": True,
        "prepared_checked": True,
        "prepared_ok": True,
        "issues": [],
        "ok": True,
    }


def test_official_manifest_checksum_verification_fails_for_changed_prepared_file(
    tmp_path,
):
    manifest = load_official_traffic_count_manifest(_write_manifest(tmp_path))
    Path(manifest["prepared_csv_path"]).write_text(
        "station_id,x,y,count\nchanged,0,0,1\n",
        encoding="utf-8",
    )

    result = verify_official_traffic_count_checksums(manifest)

    assert result["ok"] is False
    assert result["prepared_checked"] is True
    assert result["prepared_ok"] is False
    assert "prepared_sha256 mismatch" in result["issues"]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "schema",
            "wrong",
            "schema must be abm-auto/official-traffic-count-intake/v1",
        ),
        ("source_url", "", "source_url must be a non-empty string"),
        ("source_agency", "", "source_agency must be a non-empty string"),
        ("license", "", "license must be a non-empty string"),
        ("downloaded_at", "20260702", "downloaded_at must be an ISO date"),
        (
            "raw_sha256",
            "bad",
            "raw_sha256 must be a 64-character sha256 hex digest",
        ),
        (
            "prepared_sha256",
            "bad",
            "prepared_sha256 must be a 64-character sha256 hex digest",
        ),
        (
            "preparation_steps",
            [],
            "preparation_steps must be a non-empty list of strings",
        ),
        ("count_metric", "", "count_metric must be a non-empty string"),
        ("year", 1800, "year must be an integer between 1900 and 2100"),
        ("geographic_scope", "", "geographic_scope must be a non-empty string"),
        (
            "expected_min_coverage",
            1.5,
            "expected_min_coverage must be between 0 and 1",
        ),
        (
            "expected_max_match_distance_m",
            0,
            "expected_max_match_distance_m must be a positive finite number",
        ),
        ("aggregation", "median", "aggregation must be 'sum' or 'mean'"),
        ("boundary_note", "", "boundary_note must be a non-empty string"),
    ],
)
def test_load_official_manifest_rejects_malformed_fields(
    tmp_path,
    field,
    value,
    message,
):
    manifest_path = _write_manifest(tmp_path, **{field: value})

    with pytest.raises(ValueError, match=message):
        load_official_traffic_count_manifest(manifest_path)


def _geonet():
    return GeoNetwork.from_lines(
        [
            LineString([(0, 0), (10, 0)]),
            LineString([(0, 10), (10, 10)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )


def _seattle_sdot_geonet():
    return GeoNetwork.from_lines(
        [
            LineString(
                [
                    (1276126.7011755407, 246900.0),
                    (1276126.7011755407, 247050.0),
                ]
            ),
            LineString(
                [
                    (1275850.0, 218425.30344371498),
                    (1276000.0, 218425.30344371498),
                ]
            ),
            LineString(
                [
                    (1257400.0, 188596.15525317192),
                    (1257600.0, 188596.15525317192),
                ]
            ),
        ],
        crs="EPSG:2926",
        snap_tol=1.0,
    )


def test_committed_official_fixture_loads_and_gate_passes():
    manifest = load_official_traffic_count_manifest(
        DEFAULT_OFFICIAL_TRAFFIC_COUNT_MANIFEST
    )
    checksum = verify_official_traffic_count_checksums(manifest)

    ok, desc = official_traffic_count_intake_gate(
        DEFAULT_OFFICIAL_TRAFFIC_COUNT_MANIFEST
    )

    assert checksum["ok"] is True
    assert ok, desc
    assert "official traffic-count intake passed" in desc
    assert "Caltrans 2024 AADT synthetic fixture" in desc
    assert "coverage=1.0" in desc
    assert "max_match_distance_m=0.4" in desc
    assert "not traffic-flow validity" in desc


def test_seattle_sdot_real_pack_manifest_loads_and_checksums_pass():
    manifest = load_official_traffic_count_manifest(
        SEATTLE_SDOT_2023_FLOWMAP_MANIFEST
    )
    checksum = verify_official_traffic_count_checksums(manifest)

    assert (
        manifest["dataset"]
        == "Seattle SDOT Traffic Study Flow Counts 2023 FLOWMAP sample"
    )
    assert manifest["source_agency"] == "Seattle Department of Transportation"
    assert manifest["crs"] == "EPSG:2926"
    assert manifest["count_metric"] == "STUDY_ADT"
    assert manifest["year"] == 2023
    assert checksum["ok"] is True


def test_official_report_returns_structured_seattle_match_diagnostics():
    report = official_traffic_count_intake_report(
        SEATTLE_SDOT_2023_FLOWMAP_MANIFEST,
        geonet=_seattle_sdot_geonet(),
    )

    assert report["ok"] is True
    assert report["reason"] == ""
    assert (
        report["dataset"]
        == "Seattle SDOT Traffic Study Flow Counts 2023 FLOWMAP sample"
    )
    assert report["source_agency"] == "Seattle Department of Transportation"
    assert report["year"] == 2023
    assert report["count_metric"] == "STUDY_ADT"
    assert report["n_stations"] == 3
    assert report["diagnostics"]["coverage"] == 1.0
    assert report["diagnostics"]["matched_edges"] == 3
    assert report["diagnostics"]["max_match_distance_m"] == pytest.approx(0.0)
    assert report["observed_edge_values"] == {
        ((1276127, 246900), (1276127, 247050)): 5497.0,
        ((1275850, 218425), (1276000, 218425)): 1164.0,
        ((1257400, 188596), (1257600, 188596)): 1047.0,
    }
    assert "not traffic-flow validity" in report["boundary_note"]


def test_official_gate_passes_for_seattle_real_pack():
    ok, desc = official_traffic_count_intake_gate(
        SEATTLE_SDOT_2023_FLOWMAP_MANIFEST,
        geonet=_seattle_sdot_geonet(),
    )

    assert ok, desc
    assert "official traffic-count intake passed" in desc
    assert "Seattle SDOT Traffic Study Flow Counts 2023 FLOWMAP sample" in desc
    assert "stations=3" in desc
    assert "coverage=1.0" in desc
    assert "not traffic-flow validity" in desc


def test_official_gate_fails_when_expected_coverage_is_too_high(tmp_path):
    manifest_path = _write_manifest(tmp_path, expected_min_coverage=1.0)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["expected_min_coverage"] = 1.1
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="expected_min_coverage must be between 0 and 1",
    ):
        load_official_traffic_count_manifest(manifest_path)


def test_official_gate_fails_when_match_distance_threshold_is_too_strict(
    tmp_path,
):
    manifest_path = _write_manifest(tmp_path, expected_max_match_distance_m=0.1)

    ok, desc = official_traffic_count_intake_gate(manifest_path, geonet=_geonet())

    assert ok is False
    assert "max match distance exceeds expected_max_match_distance_m" in desc


def test_official_report_preserves_diagnostics_on_match_threshold_failure(
    tmp_path,
):
    manifest_path = _write_manifest(
        tmp_path,
        expected_max_match_distance_m=0.1,
    )

    report = official_traffic_count_intake_report(manifest_path, geonet=_geonet())

    assert report["ok"] is False
    assert "max match distance exceeds expected_max_match_distance_m" in report[
        "reason"
    ]
    assert report["diagnostics"]["coverage"] == 1.0


def test_official_gate_fails_when_checksum_changes(tmp_path):
    manifest_path = _write_manifest(tmp_path)
    manifest = load_official_traffic_count_manifest(manifest_path)
    Path(manifest["raw_local_path"]).write_text("changed\n", encoding="utf-8")

    ok, desc = official_traffic_count_intake_gate(manifest_path, geonet=_geonet())

    assert ok is False
    assert "raw_sha256 mismatch" in desc


def test_official_report_fails_with_structured_checksum_reason(tmp_path):
    manifest_path = _write_manifest(tmp_path)
    manifest = load_official_traffic_count_manifest(manifest_path)
    Path(manifest["prepared_csv_path"]).write_text(
        "station_id,x,y,count\nchanged,0,0,1\n",
        encoding="utf-8",
    )

    report = official_traffic_count_intake_report(manifest_path, geonet=_geonet())

    assert report["ok"] is False
    assert "prepared_sha256 mismatch" in report["reason"]
    assert report["checksum"]["prepared_ok"] is False
    assert report["diagnostics"] is None


def test_official_report_fails_before_matching_on_crs_mismatch(tmp_path):
    manifest_path = _write_manifest(tmp_path, crs="EPSG:4326")

    report = official_traffic_count_intake_report(manifest_path, geonet=_geonet())

    assert report["ok"] is False
    assert report["reason"] == "official traffic-count intake CRS mismatch"
    assert report["diagnostics"] is None
