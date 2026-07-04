"""Official traffic-count to official centerline edge matching.

This module connects a bounded official count-point sample to bounded official
street-centerline geometry. It performs local checksum, CRS, and deterministic
nearest-edge diagnostics only. It does not download data, reproject coordinates,
or implement production map matching.
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
from abm_auto.gis._official_traffic_intake import (
    load_official_traffic_count_manifest,
    verify_official_traffic_count_checksums,
)
from abm_auto.gis._traffic_count_repro import (
    _expected_edge_values,
    traffic_count_match_diagnostics,
)
from abm_auto.gis._traffic_counts import (
    load_traffic_count_csv,
    match_traffic_counts_to_edges,
    observed_network_from_traffic_counts,
)


OFFICIAL_CENTERLINE_MATCH_SCHEMA = "abm-auto/official-centerline-edge-match/v1"
SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST = Path(
    "data/fixtures/official-traffic-counts/"
    "seattle-sdot-2023-centerline-match/manifest.json"
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


def _preparation_steps(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("preparation_steps must be a non-empty list of strings")
    return [_non_empty_string("preparation_steps", item) for item in value]


def _schema(value: Any) -> str:
    if value != OFFICIAL_CENTERLINE_MATCH_SCHEMA:
        raise ValueError(f"schema must be {OFFICIAL_CENTERLINE_MATCH_SCHEMA}")
    return OFFICIAL_CENTERLINE_MATCH_SCHEMA


def _station_string_map(name: str, value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{name} must be a non-empty dict")
    return {
        _non_empty_string(f"{name}.station_id", station_id): _non_empty_string(
            f"{name}.{station_id}",
            street,
        )
        for station_id, street in value.items()
    }


def _station_int_map(name: str, value: Any) -> dict[str, int]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{name} must be a non-empty dict")
    out: dict[str, int] = {}
    for station_id, objectid in value.items():
        if isinstance(objectid, bool) or not isinstance(objectid, int):
            raise ValueError(f"{name} values must be integers")
        out[_non_empty_string(f"{name}.station_id", station_id)] = objectid
    return out


def _file_sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _snap(pt: tuple[float, float], snap_tol: float) -> tuple[int, int]:
    return (round(pt[0] / snap_tol), round(pt[1] / snap_tol))


def _edge_key_from_points(
    a: tuple[float, float],
    b: tuple[float, float],
    *,
    snap_tol: float,
) -> tuple:
    return tuple(sorted((_snap(a, snap_tol), _snap(b, snap_tol)), key=repr))


def _finite_coordinate(value: Any) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("ArcGIS polyline coordinates must be [x, y]")
    x, y = value
    if (
        isinstance(x, bool)
        or isinstance(y, bool)
        or not isinstance(x, (int, float))
        or not isinstance(y, (int, float))
    ):
        raise ValueError("ArcGIS polyline coordinates must be finite numbers")
    x_out = float(x)
    y_out = float(y)
    if not math.isfinite(x_out) or not math.isfinite(y_out):
        raise ValueError("ArcGIS polyline coordinates must be finite numbers")
    return x_out, y_out


def _wkid_to_crs(raw: dict) -> str:
    spatial_ref = raw.get("spatialReference")
    if not isinstance(spatial_ref, dict):
        raise ValueError("ArcGIS response missing spatialReference")
    wkid = spatial_ref.get("latestWkid", spatial_ref.get("wkid"))
    if isinstance(wkid, bool) or not isinstance(wkid, int):
        raise ValueError("ArcGIS response spatialReference must contain wkid")
    return f"EPSG:{wkid}"


def load_official_centerline_match_manifest(path) -> dict:
    """Load and validate an official centerline edge-match manifest."""
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
            "query_url": _non_empty_string("query_url", raw.get("query_url")),
            "source_agency": _non_empty_string(
                "source_agency",
                raw.get("source_agency"),
            ),
            "road_dataset": _non_empty_string(
                "road_dataset",
                raw.get("road_dataset"),
            ),
            "license": _non_empty_string("license", raw.get("license")),
            "downloaded_at": _iso_date("downloaded_at", raw.get("downloaded_at")),
            "traffic_count_manifest_path": _resolve_required_path(
                manifest_path,
                "traffic_count_manifest_path",
                raw.get("traffic_count_manifest_path"),
            ),
            "centerline_raw_path": _resolve_required_path(
                manifest_path,
                "centerline_raw_path",
                raw.get("centerline_raw_path"),
            ),
            "centerline_raw_sha256": _sha256_digest(
                "centerline_raw_sha256",
                raw.get("centerline_raw_sha256"),
            ),
            "preparation_steps": _preparation_steps(raw.get("preparation_steps")),
            "crs": _non_empty_string("crs", raw.get("crs")),
            "max_distance_m": _positive_finite_number(
                "max_distance_m",
                raw.get("max_distance_m"),
            ),
            "expected_min_coverage": _coverage(raw.get("expected_min_coverage")),
            "expected_max_match_distance_m": _positive_finite_number(
                "expected_max_match_distance_m",
                raw.get("expected_max_match_distance_m"),
            ),
            "expected_station_streets": _station_string_map(
                "expected_station_streets",
                raw.get("expected_station_streets"),
            ),
            "expected_station_objectids": _station_int_map(
                "expected_station_objectids",
                raw.get("expected_station_objectids"),
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


def verify_official_centerline_match_checksums(manifest: dict) -> dict:
    """Verify count-manifest and centerline raw checksums."""
    issues: list[str] = []
    count_manifest = load_official_traffic_count_manifest(
        manifest["traffic_count_manifest_path"]
    )
    count_checksum = verify_official_traffic_count_checksums(count_manifest)
    traffic_count_ok = bool(count_checksum["ok"])
    centerline_raw_ok = (
        _file_sha256(manifest["centerline_raw_path"])
        == manifest["centerline_raw_sha256"]
    )
    if not traffic_count_ok:
        issues.extend(
            f"traffic_count_{issue}"
            for issue in count_checksum["issues"]
        )
    if not centerline_raw_ok:
        issues.append("centerline_raw_sha256 mismatch")
    return {
        "traffic_count_checked": True,
        "traffic_count_ok": traffic_count_ok,
        "centerline_raw_checked": True,
        "centerline_raw_ok": centerline_raw_ok,
        "issues": issues,
        "ok": not issues,
    }


def _load_arcgis_centerline_raw(path: str) -> dict:
    with Path(path).open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raise ValueError("ArcGIS centerline raw source must be a JSON object")
    if raw.get("geometryType") != "esriGeometryPolyline":
        raise ValueError("ArcGIS centerline raw source must be esriGeometryPolyline")
    features = raw.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("ArcGIS centerline raw source must contain features")
    return raw


def load_official_centerline_geonet(manifest: dict, *, snap_tol: float = 1.0) -> dict:
    """Build a segmented GeoNetwork from a validated centerline match manifest."""
    snap_tol = _positive_finite_number("snap_tol", snap_tol)
    raw = _load_arcgis_centerline_raw(manifest["centerline_raw_path"])
    raw_crs = _wkid_to_crs(raw)
    if raw_crs != manifest["crs"]:
        raise ValueError("ArcGIS centerline CRS does not match manifest CRS")

    lines: list[LineString] = []
    segments: list[dict] = []
    edge_metadata: dict[tuple, dict] = {}
    street_names: set[str] = set()

    for feature_index, feature in enumerate(raw["features"]):
        if not isinstance(feature, dict):
            raise ValueError("ArcGIS centerline feature must be an object")
        attrs = feature.get("attributes")
        geometry = feature.get("geometry")
        if not isinstance(attrs, dict) or not isinstance(geometry, dict):
            raise ValueError("ArcGIS centerline feature missing attributes/geometry")
        street = _non_empty_string("STNAME_ORD", attrs.get("STNAME_ORD"))
        objectid = attrs.get("OBJECTID")
        if isinstance(objectid, bool) or not isinstance(objectid, int):
            raise ValueError("OBJECTID must be an integer")
        paths = geometry.get("paths")
        if not isinstance(paths, list) or not paths:
            raise ValueError("ArcGIS centerline geometry must contain paths")

        street_names.add(street)
        for path_index, path in enumerate(paths):
            if not isinstance(path, list) or len(path) < 2:
                raise ValueError("ArcGIS centerline path must contain two points")
            coords = [_finite_coordinate(coord) for coord in path]
            for segment_index, (a, b) in enumerate(zip(coords, coords[1:])):
                line = LineString([a, b])
                if line.length <= 0:
                    raise ValueError("ArcGIS centerline segment must have length")
                edge = _edge_key_from_points(a, b, snap_tol=snap_tol)
                metadata = {
                    "feature_index": feature_index,
                    "path_index": path_index,
                    "segment_index": segment_index,
                    "objectid": objectid,
                    "compkey": attrs.get("COMPKEY"),
                    "street": street,
                    "onstreet": attrs.get("ONSTREET"),
                    "arterial_class": attrs.get("ARTDESCRIPT"),
                    "speed_limit": attrs.get("SPEEDLIMIT"),
                    "segment_length": attrs.get("SEGLENGTH"),
                }
                if edge in edge_metadata:
                    raise ValueError(f"duplicate centerline edge after snap: {edge}")
                edge_metadata[edge] = metadata
                segments.append({"edge": edge, "line": line, **metadata})
                lines.append(line)

    geonet = GeoNetwork.from_lines(lines, crs=manifest["crs"], snap_tol=snap_tol)
    return {
        "geonet": geonet,
        "segments": segments,
        "edge_metadata": edge_metadata,
        "n_features": len(raw["features"]),
        "n_segments": len(segments),
        "street_names": sorted(street_names),
    }


def _load_count_stations(count_manifest: dict):
    columns = count_manifest["columns"]
    return load_traffic_count_csv(
        count_manifest["prepared_csv_path"],
        id_col=columns["id"],
        x_col=columns["x"],
        y_col=columns["y"],
        count_col=columns["count"],
    )


def _report(
    manifest: dict,
    checksum: dict | None,
    *,
    ok: bool,
    reason: str,
    diagnostics: dict | None = None,
    observed_edge_values: dict | None = None,
    station_streets: dict | None = None,
    station_objectids: dict | None = None,
    geonet_edges: int | None = None,
    centerline_features: int | None = None,
    centerline_segments: int | None = None,
) -> dict:
    return {
        "ok": ok,
        "reason": reason,
        "manifest": manifest,
        "checksum": checksum,
        "dataset": manifest["dataset"],
        "source_url": manifest["source_url"],
        "query_url": manifest["query_url"],
        "source_agency": manifest["source_agency"],
        "road_dataset": manifest["road_dataset"],
        "license": manifest["license"],
        "downloaded_at": manifest["downloaded_at"],
        "boundary_note": manifest["boundary_note"],
        "diagnostics": diagnostics,
        "observed_edge_values": observed_edge_values,
        "station_streets": station_streets,
        "station_objectids": station_objectids,
        "geonet_edges": geonet_edges,
        "centerline_features": centerline_features,
        "centerline_segments": centerline_segments,
    }


def official_centerline_edge_match_report(manifest_path) -> dict:
    """Return structured official count-to-centerline match diagnostics."""
    manifest = load_official_centerline_match_manifest(manifest_path)
    checksum = verify_official_centerline_match_checksums(manifest)
    if not checksum["ok"]:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason=(
                "official centerline edge match checksum failed: "
                + "; ".join(checksum["issues"])
            ),
        )

    count_manifest = load_official_traffic_count_manifest(
        manifest["traffic_count_manifest_path"]
    )
    if count_manifest["crs"] != manifest["crs"]:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason="official centerline edge match CRS mismatch",
        )

    try:
        loaded_centerline = load_official_centerline_geonet(manifest)
    except ValueError as exc:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason=f"official centerline edge match centerline load failed: {exc}",
        )

    geonet = loaded_centerline["geonet"]
    stations = _load_count_stations(count_manifest)
    if geonet.crs != count_manifest["crs"]:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason="official centerline edge match CRS mismatch",
            geonet_edges=geonet.graph.number_of_edges(),
            centerline_features=loaded_centerline["n_features"],
            centerline_segments=loaded_centerline["n_segments"],
        )

    try:
        matches = match_traffic_counts_to_edges(
            geonet,
            stations,
            max_distance_m=manifest["max_distance_m"],
        )
    except ValueError as exc:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason=f"official centerline edge match matching failed: {exc}",
            geonet_edges=geonet.graph.number_of_edges(),
            centerline_features=loaded_centerline["n_features"],
            centerline_segments=loaded_centerline["n_segments"],
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
        aggregation="sum",
    )
    edge_metadata = loaded_centerline["edge_metadata"]
    station_streets = {
        match.station_id: edge_metadata[match.edge]["street"]
        for match in matches
    }
    station_objectids = {
        match.station_id: edge_metadata[match.edge]["objectid"]
        for match in matches
    }

    common_report = {
        "diagnostics": diagnostics,
        "observed_edge_values": observed.edge_values,
        "station_streets": station_streets,
        "station_objectids": station_objectids,
        "geonet_edges": geonet.graph.number_of_edges(),
        "centerline_features": loaded_centerline["n_features"],
        "centerline_segments": loaded_centerline["n_segments"],
    }
    if observed.edge_values != manifest["expected_edge_values"]:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason="official centerline edge match produced unexpected edge values",
            **common_report,
        )
    if diagnostics["coverage"] < manifest["expected_min_coverage"]:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason=(
                "official centerline edge match coverage below "
                "expected_min_coverage "
                f"({diagnostics['coverage']} < "
                f"{manifest['expected_min_coverage']})"
            ),
            **common_report,
        )
    if (
        diagnostics["max_match_distance_m"]
        > manifest["expected_max_match_distance_m"]
    ):
        return _report(
            manifest,
            checksum,
            ok=False,
            reason=(
                "official centerline edge match max match distance exceeds "
                "expected_max_match_distance_m "
                f"({diagnostics['max_match_distance_m']} > "
                f"{manifest['expected_max_match_distance_m']})"
            ),
            **common_report,
        )
    if station_streets != manifest["expected_station_streets"]:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason=(
                "official centerline edge match station street mismatch "
                f"(expected={manifest['expected_station_streets']}, "
                f"got={station_streets})"
            ),
            **common_report,
        )
    if station_objectids != manifest["expected_station_objectids"]:
        return _report(
            manifest,
            checksum,
            ok=False,
            reason=(
                "official centerline edge match station OBJECTID mismatch "
                f"(expected={manifest['expected_station_objectids']}, "
                f"got={station_objectids})"
            ),
            **common_report,
        )

    return _report(
        manifest,
        checksum,
        ok=True,
        reason="",
        **common_report,
    )


def official_centerline_edge_match_gate(
    manifest_path=SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
) -> tuple[bool, str]:
    """Gate proving official count points match official centerline geometry."""
    report = official_centerline_edge_match_report(manifest_path)
    if not report["ok"]:
        return False, report["reason"]

    diagnostics = report["diagnostics"]
    return (
        True,
        "official centerline edge match passed "
        f"(dataset={report['dataset']}, road_dataset={report['road_dataset']}, "
        f"agency={report['source_agency']}, stations={diagnostics['n_stations']}, "
        f"streets={len(set(report['station_streets'].values()))}, "
        f"coverage={diagnostics['coverage']}, "
        f"max_match_distance_m={diagnostics['max_match_distance_m']}, "
        f"centerline_segments={report['centerline_segments']}); "
        f"{report['boundary_note']}",
    )


__all__ = [
    "OFFICIAL_CENTERLINE_MATCH_SCHEMA",
    "SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST",
    "load_official_centerline_geonet",
    "load_official_centerline_match_manifest",
    "official_centerline_edge_match_gate",
    "official_centerline_edge_match_report",
    "verify_official_centerline_match_checksums",
]
