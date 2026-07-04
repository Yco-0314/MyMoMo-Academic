import json
import shutil
from pathlib import Path

import pytest

from abm_auto.gis._official_incident_clock import (
    DEFAULT_OFFICIAL_INCIDENT_CLOCK_MAP_MANIFEST,
    OFFICIAL_INCIDENT_CLOCK_MAP_SCHEMA,
    load_official_incident_clock_map_manifest,
    load_timestamped_incident_intervals_csv,
    map_incident_intervals_to_tick_events,
    official_incident_clock_map_gate,
    official_incident_clock_map_report,
    verify_official_incident_clock_map_checksum,
)


def _copy_clock_fixture(tmp_path: Path) -> Path:
    source_dir = DEFAULT_OFFICIAL_INCIDENT_CLOCK_MAP_MANIFEST.parent
    dest_dir = tmp_path / source_dir.name
    shutil.copytree(source_dir, dest_dir)
    return dest_dir / "manifest.json"


def _write_manifest_override(path: Path, **overrides) -> Path:
    raw = json.loads(path.read_text(encoding="utf-8"))
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(raw.get(key), dict):
            raw[key].update(value)
        else:
            raw[key] = value
    path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    return path


def _columns():
    return {
        "id": "incident_id",
        "x": "x",
        "y": "y",
        "started_at": "started_at",
        "ended_at": "ended_at",
    }


def _clock(**overrides):
    clock = {
        "simulation_start": "2026-07-03T08:00:00-07:00",
        "tick_seconds": 600,
        "local_utc_offset": None,
        "start_rounding": "floor",
        "end_rounding": "ceil",
    }
    clock.update(overrides)
    return clock


def _write_csv(path: Path, rows: list[str]) -> Path:
    path.write_text(
        "incident_id,x,y,started_at,ended_at,description\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )
    return path


def test_clock_map_manifest_loads_and_resolves_paths():
    manifest = load_official_incident_clock_map_manifest(
        DEFAULT_OFFICIAL_INCIDENT_CLOCK_MAP_MANIFEST
    )

    assert manifest["schema"] == OFFICIAL_INCIDENT_CLOCK_MAP_SCHEMA
    assert manifest["dataset"] == "Synthetic official-style incident timestamp clock map"
    assert Path(manifest["timestamped_events_path"]).exists()
    assert manifest["clock"]["tick_seconds"] == 600
    assert manifest["expected_tick_events"]["evt-closure:close"] == {
        "incident_id": "evt-closure",
        "t": 1,
        "closed": True,
    }


def test_clock_map_checksum_passes_for_committed_fixture():
    manifest = load_official_incident_clock_map_manifest(
        DEFAULT_OFFICIAL_INCIDENT_CLOCK_MAP_MANIFEST
    )

    result = verify_official_incident_clock_map_checksum(manifest)

    assert result == {
        "timestamped_checked": True,
        "timestamped_ok": True,
        "issues": [],
        "ok": True,
    }


def test_clock_map_report_converts_interval_to_close_and_reopen_ticks():
    report = official_incident_clock_map_report(
        DEFAULT_OFFICIAL_INCIDENT_CLOCK_MAP_MANIFEST
    )

    assert report["ok"] is True
    assert report["reason"] == ""
    assert report["n_intervals"] == 1
    assert report["n_tick_events"] == 2
    assert report["events_by_t"] == {1: 1, 3: 1}
    assert report["closures"] == 1
    assert report["reopenings"] == 1
    assert report["tick_events"] == [
        {
            "event_id": "evt-closure:close",
            "incident_id": "evt-closure",
            "x": 150.0,
            "y": 0.2,
            "t": 1,
            "closed": True,
        },
        {
            "event_id": "evt-closure:reopen",
            "incident_id": "evt-closure",
            "x": 150.0,
            "y": 0.2,
            "t": 3,
            "closed": False,
        },
    ]
    assert "not traffic-flow validity" in report["boundary_note"]


def test_clock_map_gate_passes_with_boundary_text():
    ok, desc = official_incident_clock_map_gate(
        DEFAULT_OFFICIAL_INCIDENT_CLOCK_MAP_MANIFEST
    )

    assert ok, desc
    assert "official incident clock map passed" in desc
    assert "intervals=1" in desc
    assert "tick_events=2" in desc
    assert "events_by_t={1: 1, 3: 1}" in desc
    assert "timestamp-to-clock plumbing only" in desc
    assert "not traffic-flow validity" in desc


def test_naive_timestamps_parse_when_local_offset_is_supplied(tmp_path):
    csv_path = _write_csv(
        tmp_path / "events.csv",
        [
            "evt-local,150,0.2,2026-07-03T08:10:00,2026-07-03T08:30:00,local timestamps"
        ],
    )

    intervals = load_timestamped_incident_intervals_csv(
        csv_path,
        columns=_columns(),
        local_utc_offset="-07:00",
    )
    events = map_incident_intervals_to_tick_events(
        intervals,
        _clock(local_utc_offset="-07:00"),
    )

    assert [event["t"] for event in events] == [1, 3]


def test_timestamp_without_offset_and_without_local_offset_fails(tmp_path):
    csv_path = _write_csv(
        tmp_path / "events.csv",
        [
            "evt-local,150,0.2,2026-07-03T08:10:00,2026-07-03T08:30:00,local timestamps"
        ],
    )

    with pytest.raises(ValueError, match="timestamp offset required"):
        load_timestamped_incident_intervals_csv(
            csv_path,
            columns=_columns(),
            local_utc_offset=None,
        )


def test_manifest_rejects_bool_tick_seconds(tmp_path):
    manifest_path = _copy_clock_fixture(tmp_path)
    _write_manifest_override(manifest_path, clock={"tick_seconds": True})

    with pytest.raises(ValueError, match="tick_seconds must be a positive integer"):
        load_official_incident_clock_map_manifest(manifest_path)


def test_ended_at_must_be_after_started_at(tmp_path):
    csv_path = _write_csv(
        tmp_path / "events.csv",
        [
            "evt-bad,150,0.2,2026-07-03T08:30:00-07:00,2026-07-03T08:30:00-07:00,bad"
        ],
    )

    with pytest.raises(ValueError, match="ended_at must be after started_at"):
        load_timestamped_incident_intervals_csv(csv_path, columns=_columns())


def test_started_at_before_simulation_start_fails(tmp_path):
    csv_path = _write_csv(
        tmp_path / "events.csv",
        [
            "evt-early,150,0.2,2026-07-03T07:59:00-07:00,2026-07-03T08:10:00-07:00,early"
        ],
    )
    intervals = load_timestamped_incident_intervals_csv(csv_path, columns=_columns())

    with pytest.raises(ValueError, match="started_at must be at or after simulation_start"):
        map_incident_intervals_to_tick_events(intervals, _clock())


@pytest.mark.parametrize(
    "rows, message",
    [
        (
            [",150,0.2,2026-07-03T08:10:00-07:00,2026-07-03T08:30:00-07:00,empty"],
            "incident_id must be a non-empty string",
        ),
        (
            [
                "evt-dup,150,0.2,2026-07-03T08:10:00-07:00,2026-07-03T08:30:00-07:00,one",
                "evt-dup,151,0.2,2026-07-03T08:40:00-07:00,2026-07-03T08:50:00-07:00,two",
            ],
            "duplicate incident id",
        ),
    ],
)
def test_empty_or_duplicate_incident_ids_fail(tmp_path, rows, message):
    csv_path = _write_csv(tmp_path / "events.csv", rows)

    with pytest.raises(ValueError, match=message):
        load_timestamped_incident_intervals_csv(csv_path, columns=_columns())


def test_expected_tick_event_mismatch_fails_report(tmp_path):
    manifest_path = _copy_clock_fixture(tmp_path)
    _write_manifest_override(
        manifest_path,
        expected_tick_events={
            "evt-closure:close": {
                "incident_id": "evt-closure",
                "t": 2,
                "closed": True,
            },
            "evt-closure:reopen": {
                "incident_id": "evt-closure",
                "t": 3,
                "closed": False,
            },
        },
    )

    report = official_incident_clock_map_report(manifest_path)

    assert report["ok"] is False
    assert report["reason"] == "tick events did not match expected_tick_events"
    assert report["tick_events"] is not None
