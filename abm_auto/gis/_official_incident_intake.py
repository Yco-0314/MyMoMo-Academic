"""Official incident-event intake and edge-match diagnostics.

This module validates local manifest-backed incident event rows and matches
them to GeoNetwork edges. It does not download official data, infer traffic
flow, or perform production map matching.
"""
from __future__ import annotations

import ast
import csv
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from shapely.geometry import LineString, Point

from abm_auto.gis._geo_network import GeoNetwork


OFFICIAL_INCIDENT_EVENT_SCHEMA = "abm-auto/official-incident-event-intake/v1"
DEFAULT_OFFICIAL_INCIDENT_EVENT_MANIFEST = Path(
    "data/fixtures/official-incident-events/test_manifest.json"
)


@dataclass(frozen=True)
class OfficialIncidentEvent:
    event_id: str
    x: float
    y: float
    t: int
    closed: bool
    raw: dict[str, str]


@dataclass(frozen=True)
class IncidentEventEdgeMatch:
    event_id: str
    edge: tuple
    distance_m: float
    t: int
    closed: bool


def _non_empty_string(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


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


def _iso_date(name: str, value: Any) -> str:
    value = _non_empty_string(name, value)
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise ValueError(f"{name} must be an ISO date")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO date") from exc
    return value


def _preparation_steps(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("preparation_steps must be a non-empty list of strings")
    return [_non_empty_string("preparation_steps", item) for item in value]


def _positive_finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive finite number")
    out = float(value)
    if not math.isfinite(out) or out <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return out


def _coverage(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("expected_min_coverage must be between 0 and 1")
    out = float(value)
    if not math.isfinite(out) or out < 0 or out > 1:
        raise ValueError("expected_min_coverage must be between 0 and 1")
    return out


def _schema(value: Any) -> str:
    if value != OFFICIAL_INCIDENT_EVENT_SCHEMA:
        raise ValueError(f"schema must be {OFFICIAL_INCIDENT_EVENT_SCHEMA}")
    return OFFICIAL_INCIDENT_EVENT_SCHEMA


def _event_time_unit(value: Any) -> str:
    if value != "tick":
        raise ValueError("event_time_unit must be 'tick'")
    return "tick"


def _columns(value: Any) -> dict[str, str]:
    required = {"id", "x", "y", "t", "closed"}
    if not isinstance(value, dict) or not required.issubset(value):
        raise ValueError("columns must contain id, x, y, t, and closed")
    return {key: _non_empty_string(f"columns.{key}", value[key]) for key in required}


def _edge_key(value: Any):
    if not isinstance(value, str) or "|" not in value:
        raise ValueError("edge keys must use repr(node_a)|repr(node_b)")
    left, sep, right = value.partition("|")
    if not sep or not left.strip() or not right.strip():
        raise ValueError("edge keys must use repr(node_a)|repr(node_b)")
    try:
        edge = tuple(
            sorted((ast.literal_eval(left), ast.literal_eval(right)), key=repr)
        )
        hash(edge)
    except (SyntaxError, ValueError, TypeError) as exc:
        raise ValueError("edge keys must use repr(node_a)|repr(node_b)") from exc
    return edge


def _expected_event_edges(value: Any) -> dict[str, dict]:
    if not isinstance(value, dict) or not value:
        raise ValueError("expected_event_edges must be a non-empty dict")
    out: dict[str, dict] = {}
    for event_id, expected in value.items():
        event_id = _non_empty_string("expected_event_edges.event_id", event_id)
        if not isinstance(expected, dict):
            raise ValueError("expected_event_edges values must be objects")
        t = expected.get("t")
        if isinstance(t, bool) or not isinstance(t, int) or t < 0:
            raise ValueError("expected_event_edges t must be a non-negative integer")
        closed = expected.get("closed")
        if not isinstance(closed, bool):
            raise ValueError("expected_event_edges closed must be boolean")
        out[event_id] = {
            "edge": _edge_key(expected.get("edge")),
            "t": t,
            "closed": closed,
        }
    return out


def load_official_incident_event_manifest(path) -> dict:
    """Load and validate an official incident-event intake manifest."""
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
            "raw_local_path": _resolve_required_path(
                manifest_path,
                "raw_local_path",
                raw.get("raw_local_path"),
            ),
            "raw_sha256": _sha256_digest("raw_sha256", raw.get("raw_sha256")),
            "prepared_events_path": _resolve_required_path(
                manifest_path,
                "prepared_events_path",
                raw.get("prepared_events_path"),
            ),
            "prepared_sha256": _sha256_digest(
                "prepared_sha256",
                raw.get("prepared_sha256"),
            ),
            "preparation_steps": _preparation_steps(raw.get("preparation_steps")),
            "crs": _non_empty_string("crs", raw.get("crs")),
            "columns": _columns(raw.get("columns")),
            "event_time_unit": _event_time_unit(raw.get("event_time_unit")),
            "geographic_scope": _non_empty_string(
                "geographic_scope",
                raw.get("geographic_scope"),
            ),
            "max_distance_m": _positive_finite_number(
                "max_distance_m",
                raw.get("max_distance_m"),
            ),
            "expected_min_coverage": _coverage(raw.get("expected_min_coverage")),
            "expected_max_match_distance_m": _positive_finite_number(
                "expected_max_match_distance_m",
                raw.get("expected_max_match_distance_m"),
            ),
            "expected_event_edges": _expected_event_edges(
                raw.get("expected_event_edges")
            ),
            "boundary_note": _non_empty_string(
                "boundary_note",
                raw.get("boundary_note"),
            ),
        }
    )
    return manifest


def _file_sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_official_incident_event_checksums(manifest: dict) -> dict:
    """Verify raw and prepared file checksums declared by a manifest."""
    issues: list[str] = []
    raw_ok = _file_sha256(manifest["raw_local_path"]) == manifest["raw_sha256"]
    prepared_ok = (
        _file_sha256(manifest["prepared_events_path"]) == manifest["prepared_sha256"]
    )
    if not raw_ok:
        issues.append("raw_sha256 mismatch")
    if not prepared_ok:
        issues.append("prepared_sha256 mismatch")
    return {
        "raw_checked": True,
        "raw_ok": raw_ok,
        "prepared_checked": True,
        "prepared_ok": prepared_ok,
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


def _tick(value: Any) -> int:
    if str(value).strip().lower() in {"true", "false"}:
        raise ValueError("t must be a non-negative integer")
    try:
        out = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("t must be a non-negative integer") from exc
    if str(out) != str(value).strip() or out < 0:
        raise ValueError("t must be a non-negative integer")
    return out


def _closed(value: Any) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "closed"}:
        return True
    if normalized in {"false", "0", "no", "open", "reopened"}:
        return False
    raise ValueError("closed must be a deterministic boolean encoding")


def load_official_incident_events_csv(
    path,
    *,
    columns: dict[str, str],
) -> list[OfficialIncidentEvent]:
    """Load prepared incident-event rows from CSV."""
    with Path(path).open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    events: list[OfficialIncidentEvent] = []
    seen: set[str] = set()
    for row in rows:
        event_id = _non_empty_string("event_id", row.get(columns["id"]))
        if event_id in seen:
            raise ValueError(f"duplicate event_id {event_id!r}")
        seen.add(event_id)
        events.append(
            OfficialIncidentEvent(
                event_id=event_id,
                x=_finite_number("x", row.get(columns["x"])),
                y=_finite_number("y", row.get(columns["y"])),
                t=_tick(row.get(columns["t"])),
                closed=_closed(row.get(columns["closed"])),
                raw=dict(row),
            )
        )
    return events


def _default_geonet() -> GeoNetwork:
    return GeoNetwork.from_lines(
        [
            LineString([(0, 0), (100, 0)]),
            LineString([(100, 0), (200, 0)]),
            LineString([(0, 100), (200, 0)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )


def _geonet_edge_keys(geonet) -> set[tuple]:
    if not hasattr(geonet, "graph"):
        raise ValueError("geonet must be a GeoNetwork")
    return {tuple(sorted((u, v), key=repr)) for u, v in geonet.graph.edges}


def match_incident_events_to_edges(
    geonet,
    events: list[OfficialIncidentEvent],
    max_distance_m,
) -> list[IncidentEventEdgeMatch]:
    """Match incident-event points to nearest GeoNetwork edges."""
    max_distance = _positive_finite_number("max_distance_m", max_distance_m)
    matches: list[IncidentEventEdgeMatch] = []
    for event in events:
        point = Point(event.x, event.y)
        best_edge = None
        best_distance = math.inf
        for u, v, data in geonet.graph.edges(data=True):
            line = data.get("geometry")
            if line is None:
                line = LineString([u, v])
            distance = float(line.distance(point))
            edge = tuple(sorted((u, v), key=repr))
            if distance < best_distance or (
                distance == best_distance and repr(edge) < repr(best_edge)
            ):
                best_edge = edge
                best_distance = distance
        if best_edge is None:
            raise ValueError("GeoNetwork has no edges")
        if best_distance > max_distance:
            raise ValueError(
                "incident event match distance exceeds max_distance_m "
                f"for event {event.event_id}"
            )
        matches.append(
            IncidentEventEdgeMatch(
                event_id=event.event_id,
                edge=best_edge,
                distance_m=best_distance,
                t=event.t,
                closed=event.closed,
            )
        )
    return matches


def _match_diagnostics(geonet, events, matches, *, max_distance_m) -> dict:
    max_distance = _positive_finite_number("max_distance_m", max_distance_m)
    geonet_edges = _geonet_edge_keys(geonet)
    event_ids = [event.event_id for event in events]
    match_ids = [match.event_id for match in matches]
    if sorted(event_ids) != sorted(match_ids):
        raise ValueError("matches must correspond to events")

    distances = [float(match.distance_m) for match in matches]
    edge_to_ids: dict[tuple, list[str]] = {}
    events_by_t: dict[int, int] = {}
    closures = 0
    reopenings = 0
    for match in matches:
        if match.edge not in geonet_edges:
            raise ValueError(f"match edge is not in GeoNetwork: {match.edge}")
        if match.distance_m > max_distance:
            raise ValueError(
                "match distance exceeds max_distance_m "
                f"for event {match.event_id}"
            )
        edge_to_ids.setdefault(match.edge, []).append(match.event_id)
        events_by_t[match.t] = events_by_t.get(match.t, 0) + 1
        if match.closed:
            closures += 1
        else:
            reopenings += 1

    duplicate_edge_groups = [
        {"edge": edge, "event_ids": sorted(ids), "count": len(ids)}
        for edge, ids in sorted(edge_to_ids.items(), key=lambda item: repr(item[0]))
        if len(ids) > 1
    ]
    n_events = len(events)
    matched_events = len(matches)
    return {
        "n_events": n_events,
        "matched_events": matched_events,
        "coverage": 1.0 if n_events == 0 else matched_events / n_events,
        "matched_edges": len(edge_to_ids),
        "max_match_distance_m": max(distances) if distances else 0.0,
        "mean_match_distance_m": (
            sum(distances) / len(distances) if distances else 0.0
        ),
        "events_by_t": dict(sorted(events_by_t.items())),
        "closures": closures,
        "reopenings": reopenings,
        "unmatched_event_ids": [],
        "duplicate_edge_groups": duplicate_edge_groups,
    }


def _observed_event_edges(matches: list[IncidentEventEdgeMatch]) -> dict[str, dict]:
    return {
        match.event_id: {
            "edge": match.edge,
            "t": match.t,
            "closed": match.closed,
        }
        for match in matches
    }


def _matched_incidents(matches: list[IncidentEventEdgeMatch]) -> list[dict]:
    return [
        {"t": match.t, "edge": match.edge, "closed": match.closed}
        for match in sorted(matches, key=lambda item: (item.t, item.event_id))
    ]


def _report(
    manifest: dict,
    checksum: dict | None,
    *,
    ok: bool,
    reason: str,
    n_events: int | None = None,
    diagnostics: dict | None = None,
    matched_incidents: list[dict] | None = None,
    observed_event_edges: dict | None = None,
) -> dict:
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
        "geographic_scope": manifest["geographic_scope"],
        "boundary_note": manifest["boundary_note"],
        "n_events": n_events,
        "diagnostics": diagnostics,
        "matched_incidents": matched_incidents,
        "observed_event_edges": observed_event_edges,
    }


def official_incident_event_edge_match_report(manifest_path, geonet=None) -> dict:
    """Return structured official incident-event edge-match diagnostics."""
    manifest = load_official_incident_event_manifest(manifest_path)
    checksum = verify_official_incident_event_checksums(manifest)
    if not checksum["ok"]:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason=(
                "official incident event intake checksum failed: "
                + "; ".join(checksum["issues"])
            ),
        )

    geonet = _default_geonet() if geonet is None else geonet
    if geonet.crs != manifest["crs"]:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason="official incident event intake CRS mismatch",
        )

    try:
        events = load_official_incident_events_csv(
            manifest["prepared_events_path"],
            columns=manifest["columns"],
        )
        matches = match_incident_events_to_edges(
            geonet,
            events,
            max_distance_m=manifest["max_distance_m"],
        )
        diagnostics = _match_diagnostics(
            geonet,
            events,
            matches,
            max_distance_m=manifest["max_distance_m"],
        )
    except ValueError as exc:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason=f"official incident event intake matching failed: {exc}",
        )

    observed_event_edges = _observed_event_edges(matches)
    matched_incidents = _matched_incidents(matches)
    common = {
        "n_events": len(events),
        "diagnostics": diagnostics,
        "matched_incidents": matched_incidents,
        "observed_event_edges": observed_event_edges,
    }
    if observed_event_edges != manifest["expected_event_edges"]:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason=(
                "official incident event intake produced unexpected incident "
                "event edge assignments"
            ),
            **common,
        )
    if diagnostics["coverage"] < manifest["expected_min_coverage"]:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason=(
                "official incident event intake coverage below expected_min_coverage "
                f"({diagnostics['coverage']} < {manifest['expected_min_coverage']})"
            ),
            **common,
        )
    if diagnostics["max_match_distance_m"] > manifest["expected_max_match_distance_m"]:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason=(
                "official incident event intake max match distance exceeds "
                "expected_max_match_distance_m "
                f"({diagnostics['max_match_distance_m']} > "
                f"{manifest['expected_max_match_distance_m']})"
            ),
            **common,
        )
    return _report(manifest, checksum, ok=True, reason="", **common)


def official_incident_event_edge_match_gate(
    manifest_path,
    geonet=None,
) -> tuple[bool, str]:
    """Gate official incident-event intake and edge-match diagnostics."""
    report = official_incident_event_edge_match_report(manifest_path, geonet=geonet)
    if not report["ok"]:
        return False, report["reason"]

    diagnostics = report["diagnostics"]
    return (
        True,
        "official incident event intake passed "
        f"(dataset={report['dataset']}, agency={report['source_agency']}, "
        f"scope={report['geographic_scope']}, events={diagnostics['n_events']}, "
        f"coverage={diagnostics['coverage']}, "
        f"max_match_distance_m={diagnostics['max_match_distance_m']}, "
        f"closures={diagnostics['closures']}, reopenings={diagnostics['reopenings']}); "
        f"{report['boundary_note']}",
    )


__all__ = [
    "DEFAULT_OFFICIAL_INCIDENT_EVENT_MANIFEST",
    "OFFICIAL_INCIDENT_EVENT_SCHEMA",
    "IncidentEventEdgeMatch",
    "OfficialIncidentEvent",
    "load_official_incident_event_manifest",
    "load_official_incident_events_csv",
    "match_incident_events_to_edges",
    "official_incident_event_edge_match_gate",
    "official_incident_event_edge_match_report",
    "verify_official_incident_event_checksums",
]
