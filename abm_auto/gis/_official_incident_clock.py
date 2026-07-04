"""Timestamp-to-simulation-clock bridge for official incident events.

This module converts timestamped incident intervals into tick closure/reopen
events compatible with the existing official incident intake. It does not
perform edge matching, traffic-flow validation, or incident calibration.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from numbers import Integral
from pathlib import Path
from typing import Any


OFFICIAL_INCIDENT_CLOCK_MAP_SCHEMA = "abm-auto/official-incident-clock-map/v1"
DEFAULT_OFFICIAL_INCIDENT_CLOCK_MAP_MANIFEST = Path(
    "data/fixtures/official-incident-events/timestamp-clock-map/manifest.json"
)


@dataclass(frozen=True)
class TimestampedIncidentInterval:
    incident_id: str
    x: float
    y: float
    started_at: datetime
    ended_at: datetime
    raw: dict[str, str]


def _non_empty_string(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _schema(value: Any) -> str:
    if value != OFFICIAL_INCIDENT_CLOCK_MAP_SCHEMA:
        raise ValueError(f"schema must be {OFFICIAL_INCIDENT_CLOCK_MAP_SCHEMA}")
    return OFFICIAL_INCIDENT_CLOCK_MAP_SCHEMA


def _iso_date(name: str, value: Any) -> str:
    value = _non_empty_string(name, value)
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise ValueError(f"{name} must be an ISO date")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO date") from exc
    return value


def _sha256_digest(name: str, value: Any) -> str:
    value = _non_empty_string(name, value)
    if len(value) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise ValueError(f"{name} must be a 64-character sha256 hex digest")
    return value.lower()


def _resolve_required_path(manifest_path: Path, field: str, value: Any) -> str:
    raw = Path(_non_empty_string(field, value))
    resolved = raw if raw.is_absolute() else manifest_path.parent / raw
    resolved = resolved.resolve()
    if not resolved.exists():
        raise ValueError(f"{field} does not exist: {resolved}")
    return str(resolved)


def _preparation_steps(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("preparation_steps must be a non-empty list of strings")
    return [_non_empty_string("preparation_steps", item) for item in value]


def _columns(value: Any) -> dict[str, str]:
    required = {"id", "x", "y", "started_at", "ended_at"}
    if not isinstance(value, dict) or not required.issubset(value):
        raise ValueError("columns must contain id, x, y, started_at, and ended_at")
    return {key: _non_empty_string(f"columns.{key}", value[key]) for key in required}


def _positive_integer(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _utc_offset(value: Any):
    if value is None:
        return None
    value = _non_empty_string("local_utc_offset", value)
    if len(value) != 6 or value[0] not in "+-" or value[3] != ":":
        raise ValueError("local_utc_offset must use +HH:MM or -HH:MM")
    try:
        hours = int(value[1:3])
        minutes = int(value[4:6])
    except ValueError as exc:
        raise ValueError("local_utc_offset must use +HH:MM or -HH:MM") from exc
    if hours > 23 or minutes > 59:
        raise ValueError("local_utc_offset must use +HH:MM or -HH:MM")
    sign = 1 if value[0] == "+" else -1
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def _parse_timestamp(value: Any, local_utc_offset=None) -> datetime:
    raw = _non_empty_string("timestamp", value)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    if dt.tzinfo is None:
        local_tz = _utc_offset(local_utc_offset)
        if local_tz is None:
            raise ValueError("timestamp offset required")
        dt = dt.replace(tzinfo=local_tz)
    return dt.astimezone(timezone.utc)


def _rounding(name: str, value: Any, expected: str) -> str:
    if value != expected:
        raise ValueError(f"{name} must be {expected!r}")
    return expected


def _clock(value: Any) -> dict:
    if not isinstance(value, dict):
        raise ValueError("clock must be an object")
    local_utc_offset = value.get("local_utc_offset")
    _utc_offset(local_utc_offset)
    return {
        "simulation_start": _non_empty_string(
            "clock.simulation_start", value.get("simulation_start")
        ),
        "tick_seconds": _positive_integer(
            "tick_seconds", value.get("tick_seconds")
        ),
        "local_utc_offset": local_utc_offset,
        "start_rounding": _rounding(
            "start_rounding", value.get("start_rounding"), "floor"
        ),
        "end_rounding": _rounding("end_rounding", value.get("end_rounding"), "ceil"),
    }


def _expected_tick_events(value: Any) -> dict[str, dict]:
    if not isinstance(value, dict) or not value:
        raise ValueError("expected_tick_events must be a non-empty dict")
    out: dict[str, dict] = {}
    for event_id, expected in value.items():
        event_id = _non_empty_string("expected_tick_events.event_id", event_id)
        if not isinstance(expected, dict):
            raise ValueError("expected_tick_events values must be objects")
        incident_id = _non_empty_string(
            "expected_tick_events.incident_id", expected.get("incident_id")
        )
        t = expected.get("t")
        if isinstance(t, bool) or not isinstance(t, int) or t < 0:
            raise ValueError("expected_tick_events t must be a non-negative integer")
        closed = expected.get("closed")
        if not isinstance(closed, bool):
            raise ValueError("expected_tick_events closed must be boolean")
        out[event_id] = {"incident_id": incident_id, "t": t, "closed": closed}
    return out


def load_official_incident_clock_map_manifest(path) -> dict:
    """Load and validate an official incident timestamp clock-map manifest."""
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raise ValueError("manifest must be a JSON object")

    manifest = dict(raw)
    manifest.update(
        {
            "schema": _schema(raw.get("schema")),
            "dataset": _non_empty_string("dataset", raw.get("dataset")),
            "source_url": _non_empty_string("source_url", raw.get("source_url")),
            "source_agency": _non_empty_string(
                "source_agency", raw.get("source_agency")
            ),
            "license": _non_empty_string("license", raw.get("license")),
            "downloaded_at": _iso_date("downloaded_at", raw.get("downloaded_at")),
            "timestamped_events_path": _resolve_required_path(
                manifest_path,
                "timestamped_events_path",
                raw.get("timestamped_events_path"),
            ),
            "timestamped_sha256": _sha256_digest(
                "timestamped_sha256", raw.get("timestamped_sha256")
            ),
            "preparation_steps": _preparation_steps(raw.get("preparation_steps")),
            "columns": _columns(raw.get("columns")),
            "clock": _clock(raw.get("clock")),
            "expected_tick_events": _expected_tick_events(
                raw.get("expected_tick_events")
            ),
            "boundary_note": _non_empty_string(
                "boundary_note", raw.get("boundary_note")
            ),
        }
    )
    return manifest


def _file_sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_official_incident_clock_map_checksum(manifest: dict) -> dict:
    """Verify the timestamped incident file checksum declared by a manifest."""
    issues: list[str] = []
    timestamped_ok = (
        _file_sha256(manifest["timestamped_events_path"])
        == manifest["timestamped_sha256"]
    )
    if not timestamped_ok:
        issues.append("timestamped_sha256 mismatch")
    return {
        "timestamped_checked": True,
        "timestamped_ok": timestamped_ok,
        "issues": issues,
        "ok": not issues,
    }


def _finite_number(name: str, value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite")
    return out


def load_timestamped_incident_intervals_csv(
    path,
    *,
    columns: dict[str, str],
    local_utc_offset=None,
) -> list[TimestampedIncidentInterval]:
    """Load timestamped incident intervals from CSV."""
    with Path(path).open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    intervals: list[TimestampedIncidentInterval] = []
    seen: set[str] = set()
    for row in rows:
        incident_id = _non_empty_string("incident_id", row.get(columns["id"]))
        if incident_id in seen:
            raise ValueError(f"duplicate incident id: {incident_id}")
        seen.add(incident_id)
        started_at = _parse_timestamp(
            row.get(columns["started_at"]),
            local_utc_offset=local_utc_offset,
        )
        ended_at = _parse_timestamp(
            row.get(columns["ended_at"]),
            local_utc_offset=local_utc_offset,
        )
        if ended_at <= started_at:
            raise ValueError("ended_at must be after started_at")
        intervals.append(
            TimestampedIncidentInterval(
                incident_id=incident_id,
                x=_finite_number("x", row.get(columns["x"])),
                y=_finite_number("y", row.get(columns["y"])),
                started_at=started_at,
                ended_at=ended_at,
                raw=dict(row),
            )
        )
    return intervals


def map_incident_intervals_to_tick_events(
    intervals: list[TimestampedIncidentInterval],
    clock: dict,
) -> list[dict]:
    """Map timestamped incident intervals to close/reopen tick events."""
    clock = _clock(clock)
    simulation_start = _parse_timestamp(
        clock["simulation_start"],
        local_utc_offset=clock["local_utc_offset"],
    )
    tick_seconds = clock["tick_seconds"]
    events: list[dict] = []
    for interval in intervals:
        if interval.started_at < simulation_start:
            raise ValueError("started_at must be at or after simulation_start")
        start_delta = (interval.started_at - simulation_start).total_seconds()
        end_delta = (interval.ended_at - simulation_start).total_seconds()
        start_tick = math.floor(start_delta / tick_seconds)
        end_tick = math.ceil(end_delta / tick_seconds)
        if start_tick < 0 or end_tick < 0:
            raise ValueError("mapped ticks must be non-negative")
        if end_tick <= start_tick:
            raise ValueError("close and reopen ticks must differ")
        events.extend(
            [
                {
                    "event_id": f"{interval.incident_id}:close",
                    "incident_id": interval.incident_id,
                    "x": interval.x,
                    "y": interval.y,
                    "t": int(start_tick),
                    "closed": True,
                },
                {
                    "event_id": f"{interval.incident_id}:reopen",
                    "incident_id": interval.incident_id,
                    "x": interval.x,
                    "y": interval.y,
                    "t": int(end_tick),
                    "closed": False,
                },
            ]
        )
    return sorted(events, key=lambda event: (event["t"], event["event_id"]))


def _events_by_t(events: list[dict]) -> dict[int, int]:
    out: dict[int, int] = {}
    for event in events:
        out[event["t"]] = out.get(event["t"], 0) + 1
    return dict(sorted(out.items()))


def _observed_expected(events: list[dict]) -> dict[str, dict]:
    return {
        event["event_id"]: {
            "incident_id": event["incident_id"],
            "t": event["t"],
            "closed": event["closed"],
        }
        for event in events
    }


def _report(
    manifest: dict,
    checksum: dict | None,
    *,
    ok: bool,
    reason: str,
    intervals: list[TimestampedIncidentInterval] | None = None,
    tick_events: list[dict] | None = None,
) -> dict:
    tick_events = tick_events if tick_events is not None else None
    events_by_t = _events_by_t(tick_events) if tick_events is not None else None
    closures = (
        sum(1 for event in tick_events if event["closed"])
        if tick_events is not None
        else None
    )
    reopenings = (
        sum(1 for event in tick_events if not event["closed"])
        if tick_events is not None
        else None
    )
    return {
        "ok": ok,
        "reason": reason,
        "manifest": manifest,
        "checksum": checksum,
        "dataset": manifest["dataset"],
        "source_url": manifest["source_url"],
        "source_agency": manifest["source_agency"],
        "license": manifest["license"],
        "downloaded_at": manifest["downloaded_at"],
        "boundary_note": manifest["boundary_note"],
        "clock": manifest["clock"],
        "n_intervals": len(intervals) if intervals is not None else None,
        "n_tick_events": len(tick_events) if tick_events is not None else None,
        "events_by_t": events_by_t,
        "closures": closures,
        "reopenings": reopenings,
        "tick_events": tick_events,
        "observed_tick_events": (
            _observed_expected(tick_events) if tick_events is not None else None
        ),
    }


def official_incident_clock_map_report(manifest_path) -> dict:
    """Return structured timestamp-to-clock diagnostics for incident intervals."""
    manifest = load_official_incident_clock_map_manifest(manifest_path)
    checksum = verify_official_incident_clock_map_checksum(manifest)
    if not checksum["ok"]:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason=(
                "official incident clock map checksum failed: "
                + "; ".join(checksum["issues"])
            ),
        )

    try:
        intervals = load_timestamped_incident_intervals_csv(
            manifest["timestamped_events_path"],
            columns=manifest["columns"],
            local_utc_offset=manifest["clock"]["local_utc_offset"],
        )
        tick_events = map_incident_intervals_to_tick_events(
            intervals,
            manifest["clock"],
        )
    except ValueError as exc:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason=f"official incident clock map failed: {exc}",
        )

    common = {"intervals": intervals, "tick_events": tick_events}
    if _observed_expected(tick_events) != manifest["expected_tick_events"]:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason="tick events did not match expected_tick_events",
            **common,
        )
    if not any(event["closed"] for event in tick_events) or not any(
        not event["closed"] for event in tick_events
    ):
        return _report(
            manifest,
            checksum,
            ok=False,
            reason="tick events must include at least one closure and one reopening",
            **common,
        )
    return _report(manifest, checksum, ok=True, reason="", **common)


def official_incident_clock_map_gate(manifest_path) -> tuple[bool, str]:
    """Gate timestamped incident interval conversion to deterministic ticks."""
    report = official_incident_clock_map_report(manifest_path)
    if not report["ok"]:
        return False, report["reason"]

    return (
        True,
        "official incident clock map passed "
        f"(dataset={report['dataset']}, intervals={report['n_intervals']}, "
        f"tick_events={report['n_tick_events']}, "
        f"events_by_t={report['events_by_t']}, closures={report['closures']}, "
        f"reopenings={report['reopenings']}); {report['boundary_note']}",
    )


__all__ = [
    "DEFAULT_OFFICIAL_INCIDENT_CLOCK_MAP_MANIFEST",
    "OFFICIAL_INCIDENT_CLOCK_MAP_SCHEMA",
    "TimestampedIncidentInterval",
    "load_official_incident_clock_map_manifest",
    "load_timestamped_incident_intervals_csv",
    "map_incident_intervals_to_tick_events",
    "official_incident_clock_map_gate",
    "official_incident_clock_map_report",
    "verify_official_incident_clock_map_checksum",
]
