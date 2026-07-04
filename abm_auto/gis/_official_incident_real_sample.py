"""Bounded real official incident sample repro pack.

This module validates a small committed King County road-closure sample and
routes it through the existing incident clock, intake, and dynamic event-effect
bridges. It does not download live data, perform production map matching, or
claim traffic-flow validity.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import math
from numbers import Integral
from pathlib import Path
from typing import Any

from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._official_incident_clock import official_incident_clock_map_report
from abm_auto.gis._official_incident_intake import (
    official_incident_event_edge_match_report,
)
from abm_auto.gis._official_incident_validation import (
    official_dynamic_incident_event_effect_report,
)


OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_SCHEMA = (
    "abm-auto/official-incident-real-sample-repro/v1"
)
OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_MANIFEST = Path(
    "data/fixtures/official-incident-events/"
    "king-county-road-closures-sample/repro_manifest.json"
)


def _non_empty_string(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _schema(value: Any) -> str:
    if value != OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_SCHEMA:
        raise ValueError(
            f"schema must be {OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_SCHEMA}"
        )
    return OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_SCHEMA


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


def _positive_integer(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be a finite number")
    return out


def _positive_finite_number(name: str, value: Any) -> float:
    out = _finite_number(name, value)
    if out <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return out


def _bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def _run(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("run must be an object")
    return {
        "n_steps": _positive_integer("n_steps", raw.get("n_steps")),
        "speed_m_per_tick": _positive_finite_number(
            "speed_m_per_tick",
            raw.get("speed_m_per_tick"),
        ),
        "reroute": _bool("reroute", raw.get("reroute")),
    }


def _expected(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("expected must be an object")
    return {
        "expected_raw_features": _positive_integer(
            "expected_raw_features",
            raw.get("expected_raw_features"),
        ),
        "expected_timestamped_intervals": _positive_integer(
            "expected_timestamped_intervals",
            raw.get("expected_timestamped_intervals"),
        ),
        "expected_tick_events": _positive_integer(
            "expected_tick_events",
            raw.get("expected_tick_events"),
        ),
        "expected_matched_incidents": _positive_integer(
            "expected_matched_incidents",
            raw.get("expected_matched_incidents"),
        ),
        "expected_dynamic_changed": _bool(
            "expected_dynamic_changed",
            raw.get("expected_dynamic_changed"),
        ),
    }


def load_official_incident_real_sample_manifest(path) -> dict:
    """Load and validate the bounded real incident sample repro manifest."""
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
                "source_agency",
                raw.get("source_agency"),
            ),
            "license": _non_empty_string("license", raw.get("license")),
            "downloaded_at": _iso_date("downloaded_at", raw.get("downloaded_at")),
            "raw_arcgis_path": _resolve_required_path(
                manifest_path,
                "raw_arcgis_path",
                raw.get("raw_arcgis_path"),
            ),
            "raw_arcgis_sha256": _sha256_digest(
                "raw_arcgis_sha256",
                raw.get("raw_arcgis_sha256"),
            ),
            "clock_manifest_path": _resolve_required_path(
                manifest_path,
                "clock_manifest_path",
                raw.get("clock_manifest_path"),
            ),
            "intake_manifest_path": _resolve_required_path(
                manifest_path,
                "intake_manifest_path",
                raw.get("intake_manifest_path"),
            ),
            "run": _run(raw.get("run")),
            "expected": _expected(raw.get("expected")),
            "boundary_note": _non_empty_string(
                "boundary_note",
                raw.get("boundary_note"),
            ),
        }
    )
    return manifest


def _file_sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_official_incident_real_sample_checksums(manifest: dict) -> dict:
    """Verify the raw ArcGIS JSON checksum declared by a real-sample manifest."""
    issues: list[str] = []
    raw_ok = _file_sha256(manifest["raw_arcgis_path"]) == manifest["raw_arcgis_sha256"]
    if not raw_ok:
        issues.append("raw_arcgis_sha256 mismatch")
    return {
        "raw_arcgis_checked": True,
        "raw_arcgis_ok": raw_ok,
        "issues": issues,
        "ok": not issues,
    }


def load_arcgis_closure_features(path) -> list[dict]:
    """Load closure features from a saved ArcGIS FeatureServer JSON response."""
    with Path(path).open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raise ValueError("ArcGIS response must be a JSON object")
    features = raw.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("features must be a non-empty list")
    for feature in features:
        if not isinstance(feature, dict):
            raise ValueError("features must contain JSON objects")
    return features


def _epoch_ms(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an epoch millisecond integer")
    return int(value)


def _point(value: Any) -> tuple[float, float]:
    if not isinstance(value, list | tuple) or len(value) < 2:
        raise ValueError("geometry points must be coordinate pairs")
    return (_finite_number("x", value[0]), _finite_number("y", value[1]))


def _first_path(feature: dict) -> list:
    geometry = feature.get("geometry")
    if not isinstance(geometry, dict):
        raise ValueError("feature geometry must be an object")
    paths = geometry.get("paths")
    if not isinstance(paths, list) or not paths:
        raise ValueError("geometry.paths must be a non-empty list")
    path = paths[0]
    if not isinstance(path, list) or len(path) < 2:
        raise ValueError("first geometry path must contain at least two points")
    return path


def _feature_attributes(feature: dict) -> dict:
    attrs = feature.get("attributes")
    if not isinstance(attrs, dict):
        raise ValueError("feature attributes must be an object")
    return attrs


def _iso_from_epoch_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def _incident_id(attrs: dict) -> str:
    globalid = attrs.get("globalid")
    if isinstance(globalid, str) and globalid.strip():
        return globalid.strip()
    objectid = attrs.get("OBJECTID")
    if isinstance(objectid, bool) or not isinstance(objectid, Integral):
        raise ValueError("OBJECTID or globalid is required")
    return str(int(objectid))


def prepare_arcgis_closure_timestamp_rows(features: list[dict]) -> list[dict]:
    """Convert saved ArcGIS closure features into timestamped incident rows."""
    if not isinstance(features, list) or not features:
        raise ValueError("features must be a non-empty list")
    rows: list[dict] = []
    seen: set[str] = set()
    for feature in features:
        if not isinstance(feature, dict):
            raise ValueError("features must contain JSON objects")
        attrs = _feature_attributes(feature)
        description = str(attrs.get("description") or "").strip()
        if "TEST" in description.upper():
            raise ValueError("TEST closure descriptions are not accepted")
        started_ms = _epoch_ms("starttime", attrs.get("starttime"))
        ended_ms = _epoch_ms("endtime", attrs.get("endtime"))
        if ended_ms <= started_ms:
            raise ValueError("endtime must be after starttime")
        path = _first_path(feature)
        p0 = _point(path[0])
        p1 = _point(path[1])
        x = (p0[0] + p1[0]) / 2.0
        y = (p0[1] + p1[1]) / 2.0
        incident_id = _incident_id(attrs)
        if incident_id in seen:
            raise ValueError(f"duplicate incident id: {incident_id}")
        seen.add(incident_id)
        objectid = attrs.get("OBJECTID")
        rows.append(
            {
                "incident_id": incident_id,
                "x": x,
                "y": y,
                "started_at": _iso_from_epoch_ms(started_ms),
                "ended_at": _iso_from_epoch_ms(ended_ms),
                "street": str(attrs.get("street") or "").strip(),
                "description": description,
                "objectid": str(objectid),
                "globalid": str(attrs.get("globalid") or "").strip(),
            }
        )
    return rows


def _snap(point: tuple[float, float], snap_tol: float = 1.0) -> tuple[int, int]:
    return (round(point[0] / snap_tol), round(point[1] / snap_tol))


def _sample_geometry(features: list[dict]) -> tuple[GeoNetwork, tuple, tuple]:
    path = _first_path(features[0])
    p0 = _point(path[0])
    p1 = _point(path[1])
    p2 = _point(path[-1])
    detour = (p0[0], p0[1] + 1500.0)
    geonet = GeoNetwork.from_lines(
        [
            LineString([p0, p1]),
            LineString([p1, p2]),
            LineString([p0, detour, p2]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    return geonet, _snap(p0), _snap(p2)


def _failure_report(
    manifest: dict,
    checksum: dict | None,
    *,
    reason: str,
    features: list[dict] | None = None,
    rows: list[dict] | None = None,
    clock_report: dict | None = None,
    intake_report: dict | None = None,
    dynamic_report: dict | None = None,
) -> dict:
    return _report(
        manifest,
        checksum,
        ok=False,
        reason=reason,
        features=features,
        rows=rows,
        clock_report=clock_report,
        intake_report=intake_report,
        dynamic_report=dynamic_report,
    )


def _summary(
    features: list[dict] | None,
    rows: list[dict] | None,
    clock_report: dict | None,
    intake_report: dict | None,
    dynamic_report: dict | None,
) -> dict | None:
    if (
        features is None
        or rows is None
        or clock_report is None
        or intake_report is None
        or dynamic_report is None
    ):
        return None
    return {
        "raw_features": len(features),
        "timestamped_intervals": len(rows),
        "tick_events": int(clock_report["n_tick_events"]),
        "matched_incidents": int(intake_report["diagnostics"]["matched_events"]),
        "dynamic_changed": bool(dynamic_report["effect"]["changed"]),
    }


def _report(
    manifest: dict,
    checksum: dict | None,
    *,
    ok: bool,
    reason: str,
    features: list[dict] | None = None,
    rows: list[dict] | None = None,
    clock_report: dict | None = None,
    intake_report: dict | None = None,
    dynamic_report: dict | None = None,
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
        "n_raw_features": len(features) if features is not None else None,
        "n_timestamped_intervals": len(rows) if rows is not None else None,
        "clock_report": clock_report,
        "intake_report": intake_report,
        "dynamic_report": dynamic_report,
        "summary": _summary(features, rows, clock_report, intake_report, dynamic_report),
        "boundary_note": manifest["boundary_note"],
    }


def _compare_expected(manifest: dict, summary: dict) -> str:
    expected = manifest["expected"]
    comparisons = [
        (
            "raw feature count did not match expected_raw_features",
            summary["raw_features"],
            expected["expected_raw_features"],
        ),
        (
            "timestamped interval count did not match expected_timestamped_intervals",
            summary["timestamped_intervals"],
            expected["expected_timestamped_intervals"],
        ),
        (
            "tick event count did not match expected_tick_events",
            summary["tick_events"],
            expected["expected_tick_events"],
        ),
        (
            "matched incident count did not match expected_matched_incidents",
            summary["matched_incidents"],
            expected["expected_matched_incidents"],
        ),
        (
            "dynamic changed flag did not match expected_dynamic_changed",
            summary["dynamic_changed"],
            expected["expected_dynamic_changed"],
        ),
    ]
    for reason, observed, expected_value in comparisons:
        if observed != expected_value:
            return reason
    return ""


def official_incident_real_sample_report(
    manifest_path=OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_MANIFEST,
) -> dict:
    """Run the bounded real official incident sample repro pack."""
    manifest = load_official_incident_real_sample_manifest(manifest_path)
    checksum = verify_official_incident_real_sample_checksums(manifest)
    if not checksum["ok"]:
        return _failure_report(
            manifest,
            checksum,
            reason=(
                "official incident real sample checksum failed: "
                + "; ".join(checksum["issues"])
            ),
        )

    try:
        features = load_arcgis_closure_features(manifest["raw_arcgis_path"])
        rows = prepare_arcgis_closure_timestamp_rows(features)
        geonet, agent_node, safe_node = _sample_geometry(features)
    except ValueError as exc:
        return _failure_report(
            manifest,
            checksum,
            reason=f"official incident real sample preparation failed: {exc}",
        )

    if len(features) != manifest["expected"]["expected_raw_features"]:
        return _failure_report(
            manifest,
            checksum,
            reason="raw feature count did not match expected_raw_features",
            features=features,
            rows=rows,
        )
    if len(rows) != manifest["expected"]["expected_timestamped_intervals"]:
        return _failure_report(
            manifest,
            checksum,
            reason="timestamped interval count did not match expected_timestamped_intervals",
            features=features,
            rows=rows,
        )

    clock_report = official_incident_clock_map_report(manifest["clock_manifest_path"])
    if not clock_report["ok"]:
        return _failure_report(
            manifest,
            checksum,
            reason="official incident clock map failed: " + clock_report["reason"],
            features=features,
            rows=rows,
            clock_report=clock_report,
        )

    intake_report = official_incident_event_edge_match_report(
        manifest["intake_manifest_path"],
        geonet=geonet,
    )
    if not intake_report["ok"]:
        return _failure_report(
            manifest,
            checksum,
            reason="official incident intake failed: " + intake_report["reason"],
            features=features,
            rows=rows,
            clock_report=clock_report,
            intake_report=intake_report,
        )

    run = manifest["run"]
    dynamic_report = official_dynamic_incident_event_effect_report(
        manifest["intake_manifest_path"],
        geonet=geonet,
        safe_nodes=[safe_node],
        agent_nodes=[agent_node],
        n_steps=run["n_steps"],
        speed_m_per_tick=run["speed_m_per_tick"],
        reroute=run["reroute"],
    )
    if not dynamic_report["ok"]:
        return _failure_report(
            manifest,
            checksum,
            reason="official dynamic incident effect failed: "
            + dynamic_report["reason"],
            features=features,
            rows=rows,
            clock_report=clock_report,
            intake_report=intake_report,
            dynamic_report=dynamic_report,
        )

    report = _report(
        manifest,
        checksum,
        ok=True,
        reason="",
        features=features,
        rows=rows,
        clock_report=clock_report,
        intake_report=intake_report,
        dynamic_report=dynamic_report,
    )
    mismatch = _compare_expected(manifest, report["summary"])
    if mismatch:
        return _failure_report(
            manifest,
            checksum,
            reason=mismatch,
            features=features,
            rows=rows,
            clock_report=clock_report,
            intake_report=intake_report,
            dynamic_report=dynamic_report,
        )
    return report


def official_incident_real_sample_gate(
    manifest_path=OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_MANIFEST,
) -> tuple[bool, str]:
    """Gate for the bounded real official incident sample repro pack."""
    report = official_incident_real_sample_report(manifest_path)
    if not report["ok"]:
        return False, report["reason"]

    summary = report["summary"]
    return (
        True,
        "official incident real sample pack passed "
        f"(dataset={report['dataset']}, agency={report['source_agency']}, "
        f"raw_features={summary['raw_features']}, "
        f"timestamped_intervals={summary['timestamped_intervals']}, "
        f"tick_events={summary['tick_events']}, "
        f"matched_incidents={summary['matched_incidents']}, "
        f"dynamic_changed={summary['dynamic_changed']}); "
        f"{report['boundary_note']}",
    )


__all__ = [
    "OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_MANIFEST",
    "OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_SCHEMA",
    "load_arcgis_closure_features",
    "load_official_incident_real_sample_manifest",
    "official_incident_real_sample_gate",
    "official_incident_real_sample_report",
    "prepare_arcgis_closure_timestamp_rows",
    "verify_official_incident_real_sample_checksums",
]
