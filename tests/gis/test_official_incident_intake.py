import hashlib
import json
from pathlib import Path

import pytest
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._official_incident_intake import (
    DEFAULT_OFFICIAL_INCIDENT_EVENT_MANIFEST,
    OFFICIAL_INCIDENT_EVENT_SCHEMA,
    OfficialIncidentEvent,
    load_official_incident_event_manifest,
    load_official_incident_events_csv,
    match_incident_events_to_edges,
    official_incident_event_edge_match_gate,
    official_incident_event_edge_match_report,
    verify_official_incident_event_checksums,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_fixture_files(tmp_path: Path) -> dict[str, str]:
    raw = tmp_path / "test_raw.csv"
    prepared = tmp_path / "test_prepared_events.csv"
    raw.write_text(
        "raw_id,description,x,y,tick,status\n"
        "raw-close,Incident closes bottleneck,150,0.2,1,closed\n"
        "raw-open,Incident reopens bottleneck,150,-0.2,3,reopened\n",
        encoding="utf-8",
    )
    prepared.write_text(
        "event_id,x,y,t,closed,description,raw_id\n"
        "evt-close,150,0.2,1,closed,Incident closes bottleneck,raw-close\n"
        "evt-open,150,-0.2,3,reopened,Incident reopens bottleneck,raw-open\n",
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
        "schema": OFFICIAL_INCIDENT_EVENT_SCHEMA,
        "dataset": "Synthetic official-style incident fixture",
        "source_url": "https://example.test/transport/incidents",
        "source_agency": "Example Department of Transportation",
        "license": "Synthetic fixture for tests; cite source in real manifests",
        "downloaded_at": "2026-07-03",
        "raw_local_path": files["raw"],
        "raw_sha256": files["raw_sha256"],
        "prepared_events_path": files["prepared"],
        "prepared_sha256": files["prepared_sha256"],
        "preparation_steps": [
            "Prepared two official-style event rows for deterministic tests.",
            "Mapped source timestamps to integer simulation ticks by hand.",
        ],
        "crs": "EPSG:3857",
        "columns": {
            "id": "event_id",
            "x": "x",
            "y": "y",
            "t": "t",
            "closed": "closed",
        },
        "event_time_unit": "tick",
        "geographic_scope": "synthetic incident detour fixture",
        "max_distance_m": 1.0,
        "expected_min_coverage": 1.0,
        "expected_max_match_distance_m": 0.2,
        "expected_event_edges": {
            "evt-close": {
                "edge": "(100, 0)|(200, 0)",
                "t": 1,
                "closed": True,
            },
            "evt-open": {
                "edge": "(100, 0)|(200, 0)",
                "t": 3,
                "closed": False,
            },
        },
        "boundary_note": (
            "Official incident intake plumbing only; not traffic-flow validity, "
            "not production map matching, and not optimal incident management."
        ),
    }
    manifest.update(overrides)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def _geonet():
    return GeoNetwork.from_lines(
        [
            LineString([(0, 0), (100, 0)]),
            LineString([(100, 0), (200, 0)]),
            LineString([(0, 100), (200, 0)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )


def test_load_manifest_resolves_paths_and_preserves_provenance(tmp_path):
    manifest = load_official_incident_event_manifest(_write_manifest(tmp_path))

    assert manifest["schema"] == OFFICIAL_INCIDENT_EVENT_SCHEMA
    assert manifest["dataset"] == "Synthetic official-style incident fixture"
    assert manifest["source_agency"] == "Example Department of Transportation"
    assert manifest["event_time_unit"] == "tick"
    assert manifest["crs"] == "EPSG:3857"
    assert Path(manifest["raw_local_path"]).exists()
    assert Path(manifest["prepared_events_path"]).exists()
    assert manifest["expected_event_edges"]["evt-close"]["edge"] == (
        (100, 0),
        (200, 0),
    )


def test_manifest_checksum_verification_passes_for_unchanged_files(tmp_path):
    manifest = load_official_incident_event_manifest(_write_manifest(tmp_path))

    result = verify_official_incident_event_checksums(manifest)

    assert result == {
        "raw_checked": True,
        "raw_ok": True,
        "prepared_checked": True,
        "prepared_ok": True,
        "issues": [],
        "ok": True,
    }


def test_manifest_checksum_verification_fails_for_changed_prepared_file(tmp_path):
    manifest = load_official_incident_event_manifest(_write_manifest(tmp_path))
    Path(manifest["prepared_events_path"]).write_text(
        "event_id,x,y,t,closed\nchanged,150,0,1,closed\n",
        encoding="utf-8",
    )

    result = verify_official_incident_event_checksums(manifest)

    assert result["ok"] is False
    assert result["prepared_ok"] is False
    assert "prepared_sha256 mismatch" in result["issues"]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "schema",
            "wrong",
            "schema must be abm-auto/official-incident-event-intake/v1",
        ),
        ("source_url", "", "source_url must be a non-empty string"),
        ("source_agency", "", "source_agency must be a non-empty string"),
        ("license", "", "license must be a non-empty string"),
        ("downloaded_at", "20260703", "downloaded_at must be an ISO date"),
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
        ("event_time_unit", "timestamp", "event_time_unit must be 'tick'"),
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
        ("boundary_note", "", "boundary_note must be a non-empty string"),
    ],
)
def test_load_manifest_rejects_malformed_fields(tmp_path, field, value, message):
    manifest_path = _write_manifest(tmp_path, **{field: value})

    with pytest.raises(ValueError, match=message):
        load_official_incident_event_manifest(manifest_path)


def test_load_manifest_rejects_missing_required_columns(tmp_path):
    manifest_path = _write_manifest(tmp_path, columns={"id": "event_id"})

    with pytest.raises(ValueError, match="columns must contain id, x, y, t, and closed"):
        load_official_incident_event_manifest(manifest_path)


def test_load_events_csv_parses_boolean_encodings_and_preserves_raw(tmp_path):
    manifest = load_official_incident_event_manifest(_write_manifest(tmp_path))

    events = load_official_incident_events_csv(
        manifest["prepared_events_path"],
        columns=manifest["columns"],
    )

    assert events == [
        OfficialIncidentEvent(
            event_id="evt-close",
            x=150.0,
            y=0.2,
            t=1,
            closed=True,
            raw={
                "event_id": "evt-close",
                "x": "150",
                "y": "0.2",
                "t": "1",
                "closed": "closed",
                "description": "Incident closes bottleneck",
                "raw_id": "raw-close",
            },
        ),
        OfficialIncidentEvent(
            event_id="evt-open",
            x=150.0,
            y=-0.2,
            t=3,
            closed=False,
            raw={
                "event_id": "evt-open",
                "x": "150",
                "y": "-0.2",
                "t": "3",
                "closed": "reopened",
                "description": "Incident reopens bottleneck",
                "raw_id": "raw-open",
            },
        ),
    ]


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ("evt-a,nan,0,1,closed\n", "x must be finite"),
        ("evt-a,150,inf,1,closed\n", "y must be finite"),
        ("evt-a,150,0,true,closed\n", "t must be a non-negative integer"),
        ("evt-a,150,0,-1,closed\n", "t must be a non-negative integer"),
        ("evt-a,150,0,1,maybe\n", "closed must be a deterministic boolean encoding"),
    ],
)
def test_load_events_csv_rejects_malformed_rows(tmp_path, row, message):
    csv_path = tmp_path / "events.csv"
    csv_path.write_text("event_id,x,y,t,closed\n" + row, encoding="utf-8")
    columns = {"id": "event_id", "x": "x", "y": "y", "t": "t", "closed": "closed"}

    with pytest.raises(ValueError, match=message):
        load_official_incident_events_csv(csv_path, columns=columns)


def test_load_events_csv_rejects_duplicate_event_ids(tmp_path):
    csv_path = tmp_path / "events.csv"
    csv_path.write_text(
        "event_id,x,y,t,closed\n"
        "evt-a,150,0,1,closed\n"
        "evt-a,150,0,3,reopened\n",
        encoding="utf-8",
    )
    columns = {"id": "event_id", "x": "x", "y": "y", "t": "t", "closed": "closed"}

    with pytest.raises(ValueError, match="duplicate event_id"):
        load_official_incident_events_csv(csv_path, columns=columns)


def test_match_incident_events_to_edges_returns_dynamic_incident_events(tmp_path):
    manifest = load_official_incident_event_manifest(_write_manifest(tmp_path))
    events = load_official_incident_events_csv(
        manifest["prepared_events_path"],
        columns=manifest["columns"],
    )

    matches = match_incident_events_to_edges(_geonet(), events, max_distance_m=1.0)

    assert [match.event_id for match in matches] == ["evt-close", "evt-open"]
    assert [match.t for match in matches] == [1, 3]
    assert [match.closed for match in matches] == [True, False]
    assert matches[0].edge == ((100, 0), (200, 0))
    assert matches[1].edge == ((100, 0), (200, 0))
    assert matches[0].distance_m == pytest.approx(0.2)


def test_report_emits_diagnostics_and_matched_incidents(tmp_path):
    report = official_incident_event_edge_match_report(_write_manifest(tmp_path))

    assert report["ok"] is True
    assert report["reason"] == ""
    assert report["n_events"] == 2
    assert report["diagnostics"]["coverage"] == 1.0
    assert report["diagnostics"]["matched_events"] == 2
    assert report["diagnostics"]["matched_edges"] == 1
    assert report["diagnostics"]["events_by_t"] == {1: 1, 3: 1}
    assert report["diagnostics"]["closures"] == 1
    assert report["diagnostics"]["reopenings"] == 1
    assert report["matched_incidents"] == [
        {"t": 1, "edge": ((100, 0), (200, 0)), "closed": True},
        {"t": 3, "edge": ((100, 0), (200, 0)), "closed": False},
    ]


def test_gate_passes_with_boundary_text(tmp_path):
    ok, desc = official_incident_event_edge_match_gate(_write_manifest(tmp_path))

    assert ok, desc
    assert "official incident event intake passed" in desc
    assert "Synthetic official-style incident fixture" in desc
    assert "coverage=1.0" in desc
    assert "not traffic-flow validity" in desc
    assert "not production map matching" in desc
    assert "not optimal incident management" in desc


def test_report_fails_on_crs_mismatch(tmp_path):
    report = official_incident_event_edge_match_report(
        _write_manifest(tmp_path, crs="EPSG:4326"),
        geonet=_geonet(),
    )

    assert report["ok"] is False
    assert report["reason"] == "official incident event intake CRS mismatch"


def test_report_fails_when_distance_tolerance_is_too_strict(tmp_path):
    report = official_incident_event_edge_match_report(
        _write_manifest(tmp_path, expected_max_match_distance_m=0.01)
    )

    assert report["ok"] is False
    assert "max match distance exceeds expected_max_match_distance_m" in report["reason"]


def test_report_fails_when_expected_event_edge_changes(tmp_path):
    report = official_incident_event_edge_match_report(
        _write_manifest(
            tmp_path,
            expected_event_edges={
                "evt-close": {"edge": "(0, 0)|(100, 0)", "t": 1, "closed": True},
                "evt-open": {"edge": "(100, 0)|(200, 0)", "t": 3, "closed": False},
            },
        )
    )

    assert report["ok"] is False
    assert "unexpected incident event edge assignments" in report["reason"]


def test_report_fails_when_checksum_changes(tmp_path):
    manifest_path = _write_manifest(tmp_path)
    manifest = load_official_incident_event_manifest(manifest_path)
    Path(manifest["prepared_events_path"]).write_text(
        "event_id,x,y,t,closed\nchanged,150,0,1,closed\n",
        encoding="utf-8",
    )

    report = official_incident_event_edge_match_report(manifest_path)

    assert report["ok"] is False
    assert "prepared_sha256 mismatch" in report["reason"]


def test_committed_fixture_gate_passes():
    ok, desc = official_incident_event_edge_match_gate(
        DEFAULT_OFFICIAL_INCIDENT_EVENT_MANIFEST
    )

    assert ok, desc
    assert "official incident event intake passed" in desc
