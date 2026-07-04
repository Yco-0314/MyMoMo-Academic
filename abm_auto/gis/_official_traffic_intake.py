"""Official traffic-count intake helpers.

This module validates externally prepared official traffic-count manifests. It
does not download official data, reproject coordinates, or perform full traffic
map matching.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._traffic_count_repro import (
    _aggregation,
    _columns,
    _expected_edge_values,
    traffic_count_match_diagnostics,
)
from abm_auto.gis._traffic_counts import (
    load_traffic_count_csv,
    match_traffic_counts_to_edges,
    observed_network_from_traffic_counts,
)


OFFICIAL_TRAFFIC_COUNT_SCHEMA = "abm-auto/official-traffic-count-intake/v1"
DEFAULT_OFFICIAL_TRAFFIC_COUNT_MANIFEST = Path(
    "data/fixtures/official-traffic-counts/test_manifest.json"
)
SEATTLE_SDOT_2023_FLOWMAP_MANIFEST = Path(
    "data/fixtures/official-traffic-counts/seattle-sdot-2023-flowmap/manifest.json"
)


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


def _year(value: Any) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1900
        or value > 2100
    ):
        raise ValueError("year must be an integer between 1900 and 2100")
    return value


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
    if value != OFFICIAL_TRAFFIC_COUNT_SCHEMA:
        raise ValueError(f"schema must be {OFFICIAL_TRAFFIC_COUNT_SCHEMA}")
    return OFFICIAL_TRAFFIC_COUNT_SCHEMA


def load_official_traffic_count_manifest(path) -> dict:
    """Load and validate an official traffic-count intake manifest."""
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
            "raw_local_path": _resolve_required_path(
                manifest_path,
                "raw_local_path",
                raw.get("raw_local_path"),
            ),
            "raw_sha256": _sha256_digest("raw_sha256", raw.get("raw_sha256")),
            "prepared_csv_path": _resolve_required_path(
                manifest_path,
                "prepared_csv_path",
                raw.get("prepared_csv_path"),
            ),
            "prepared_sha256": _sha256_digest(
                "prepared_sha256",
                raw.get("prepared_sha256"),
            ),
            "preparation_steps": _preparation_steps(raw.get("preparation_steps")),
            "crs": _non_empty_string("crs", raw.get("crs")),
            "columns": _columns(raw.get("columns")),
            "count_metric": _non_empty_string("count_metric", raw.get("count_metric")),
            "year": _year(raw.get("year")),
            "geographic_scope": _non_empty_string(
                "geographic_scope",
                raw.get("geographic_scope"),
            ),
            "max_distance_m": _positive_finite_number(
                "max_distance_m",
                raw.get("max_distance_m"),
            ),
            "aggregation": _aggregation(raw.get("aggregation")),
            "expected_min_coverage": _coverage(raw.get("expected_min_coverage")),
            "expected_max_match_distance_m": _positive_finite_number(
                "expected_max_match_distance_m",
                raw.get("expected_max_match_distance_m"),
            ),
            "expected_edge_values": _expected_edge_values(
                raw.get("expected_edge_values")
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


def verify_official_traffic_count_checksums(manifest: dict) -> dict:
    """Verify raw and prepared file checksums declared by a validated manifest."""
    issues: list[str] = []
    raw_ok = _file_sha256(manifest["raw_local_path"]) == manifest["raw_sha256"]
    prepared_ok = (
        _file_sha256(manifest["prepared_csv_path"]) == manifest["prepared_sha256"]
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


def _default_geonet() -> GeoNetwork:
    return GeoNetwork.from_lines(
        [
            LineString([(0, 0), (10, 0)]),
            LineString([(0, 10), (10, 10)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )


def _load_stations_from_official_manifest(manifest: dict):
    columns = manifest["columns"]
    return load_traffic_count_csv(
        manifest["prepared_csv_path"],
        id_col=columns["id"],
        x_col=columns["x"],
        y_col=columns["y"],
        count_col=columns["count"],
    )


def _official_report(
    manifest: dict,
    checksum: dict | None,
    *,
    ok: bool,
    reason: str,
    n_stations: int | None = None,
    diagnostics: dict | None = None,
    observed_edge_values: dict | None = None,
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
        "year": manifest["year"],
        "count_metric": manifest["count_metric"],
        "geographic_scope": manifest["geographic_scope"],
        "boundary_note": manifest["boundary_note"],
        "n_stations": n_stations,
        "diagnostics": diagnostics,
        "observed_edge_values": observed_edge_values,
    }


def official_traffic_count_intake_report(manifest_path, geonet=None) -> dict:
    """Return structured official traffic-count intake diagnostics."""
    manifest = load_official_traffic_count_manifest(manifest_path)
    checksum = verify_official_traffic_count_checksums(manifest)
    if not checksum["ok"]:
        return _official_report(
            manifest,
            checksum,
            ok=False,
            reason=(
                "official traffic-count intake checksum failed: "
                + "; ".join(checksum["issues"])
            ),
        )

    geonet = _default_geonet() if geonet is None else geonet
    if geonet.crs != manifest["crs"]:
        return _official_report(
            manifest,
            checksum,
            ok=False,
            reason="official traffic-count intake CRS mismatch",
        )

    stations = _load_stations_from_official_manifest(manifest)
    try:
        matches = match_traffic_counts_to_edges(
            geonet,
            stations,
            max_distance_m=manifest["max_distance_m"],
        )
    except ValueError as exc:
        return _official_report(
            manifest,
            checksum,
            ok=False,
            reason=f"official traffic-count intake matching failed: {exc}",
            n_stations=len(stations),
        )
    diagnostics = traffic_count_match_diagnostics(
        geonet,
        stations,
        matches,
        max_distance_m=manifest["max_distance_m"],
    )
    observed = observed_network_from_traffic_counts(
        geonet,
        stations,
        max_distance_m=manifest["max_distance_m"],
        source=f"{manifest['dataset']}: {manifest['source_url']}",
        dataset=manifest["dataset"],
        aggregation=manifest["aggregation"],
    )
    observed_edge_values = observed.edge_values
    if observed.edge_values != manifest["expected_edge_values"]:
        return _official_report(
            manifest,
            checksum,
            ok=False,
            reason=(
                "official traffic-count intake produced unexpected observed "
                "edge values"
            ),
            n_stations=len(stations),
            diagnostics=diagnostics,
            observed_edge_values=observed_edge_values,
        )
    if diagnostics["coverage"] < manifest["expected_min_coverage"]:
        return _official_report(
            manifest,
            checksum,
            ok=False,
            reason=(
                "official traffic-count intake coverage below "
                "expected_min_coverage "
                f"({diagnostics['coverage']} < "
                f"{manifest['expected_min_coverage']})"
            ),
            n_stations=len(stations),
            diagnostics=diagnostics,
            observed_edge_values=observed_edge_values,
        )
    if (
        diagnostics["max_match_distance_m"]
        > manifest["expected_max_match_distance_m"]
    ):
        return _official_report(
            manifest,
            checksum,
            ok=False,
            reason=(
                "official traffic-count intake max match distance exceeds "
                "expected_max_match_distance_m "
                f"({diagnostics['max_match_distance_m']} > "
                f"{manifest['expected_max_match_distance_m']})"
            ),
            n_stations=len(stations),
            diagnostics=diagnostics,
            observed_edge_values=observed_edge_values,
        )

    return _official_report(
        manifest,
        checksum,
        ok=True,
        reason="",
        n_stations=len(stations),
        diagnostics=diagnostics,
        observed_edge_values=observed_edge_values,
    )


def official_traffic_count_intake_gate(manifest_path, geonet=None) -> tuple[bool, str]:
    """Gate official traffic-count intake provenance and edge-match diagnostics."""
    report = official_traffic_count_intake_report(manifest_path, geonet=geonet)
    if not report["ok"]:
        return False, report["reason"]

    diagnostics = report["diagnostics"]
    return (
        True,
        "official traffic-count intake passed "
        f"(dataset={report['dataset']}, agency={report['source_agency']}, "
        f"year={report['year']}, metric={report['count_metric']}, "
        f"scope={report['geographic_scope']}, "
        f"stations={diagnostics['n_stations']}, coverage={diagnostics['coverage']}, "
        f"max_match_distance_m={diagnostics['max_match_distance_m']}); "
        f"{report['boundary_note']}",
    )


__all__ = [
    "DEFAULT_OFFICIAL_TRAFFIC_COUNT_MANIFEST",
    "OFFICIAL_TRAFFIC_COUNT_SCHEMA",
    "SEATTLE_SDOT_2023_FLOWMAP_MANIFEST",
    "load_official_traffic_count_manifest",
    "official_traffic_count_intake_gate",
    "official_traffic_count_intake_report",
    "verify_official_traffic_count_checksums",
]
