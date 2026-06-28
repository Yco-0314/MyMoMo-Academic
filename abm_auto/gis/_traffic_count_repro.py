"""Local traffic-count reproducibility pack helpers.

This module validates manifests, loads station rows, reports map-match
diagnostics, and builds manifest-backed observed network targets. It does not
run traffic-count reproduction gates.
"""
from __future__ import annotations

import ast
import json
import math
from pathlib import Path
from typing import Any

from abm_auto.gis._network_validation import network_validation_gate
from abm_auto.gis._traffic_counts import (
    load_traffic_count_csv,
    match_traffic_counts_to_edges,
    observed_network_from_traffic_counts,
)


DEFAULT_TRAFFIC_COUNT_MANIFEST = Path(
    "data/fixtures/traffic-counts/test_manifest.json"
)


def _non_empty_string(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _positive_finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive finite number")
    out = float(value)
    if not math.isfinite(out) or out <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return out


def _finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} values must be finite numbers")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} values must be finite numbers")
    return out


def _resolve_csv_path(manifest_path: Path, csv_path: str) -> str:
    raw = Path(csv_path)
    resolved = raw if raw.is_absolute() else manifest_path.parent / raw
    resolved = resolved.resolve()
    if not resolved.exists():
        raise ValueError(f"csv_path does not exist: {resolved}")
    return str(resolved)


def _columns(value: Any) -> dict[str, str]:
    required = {"id", "x", "y", "count"}
    if not isinstance(value, dict) or not required.issubset(value):
        raise ValueError("columns must contain id, x, y, and count")
    return {
        key: _non_empty_string(f"columns.{key}", value[key])
        for key in ("id", "x", "y", "count")
    }


def _aggregation(value: Any) -> str:
    if value not in {"sum", "mean"}:
        raise ValueError("aggregation must be 'sum' or 'mean'")
    return value


def _edge_key(value: str):
    if not isinstance(value, str) or "|" not in value:
        raise ValueError(
            "expected_edge_values keys must use repr(node_a)|repr(node_b)"
        )
    left, sep, right = value.partition("|")
    if not sep or not left.strip() or not right.strip():
        raise ValueError(
            "expected_edge_values keys must use repr(node_a)|repr(node_b)"
        )
    try:
        edge = tuple(
            sorted(
                (ast.literal_eval(left), ast.literal_eval(right)),
                key=repr,
            )
        )
        hash(edge)
    except (SyntaxError, ValueError, TypeError) as exc:
        raise ValueError(
            "expected_edge_values keys must use repr(node_a)|repr(node_b)"
        ) from exc
    return edge


def _expected_edge_values(value: Any) -> dict[tuple, float]:
    if not isinstance(value, dict) or not value:
        raise ValueError("expected_edge_values must be a non-empty dict")
    out: dict[tuple, float] = {}
    for key, number in value.items():
        edge = _edge_key(key)
        if edge in out:
            raise ValueError(f"duplicate normalized expected edge key: {edge}")
        out[edge] = _finite_number("expected_edge_values", number)
    return out


def load_traffic_count_manifest(path) -> dict:
    """Load and validate a local traffic-count reproducibility manifest."""
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raise ValueError("manifest must be a JSON object")

    manifest = dict(raw)
    manifest.update(
        {
            "csv_path": _resolve_csv_path(
                manifest_path,
                _non_empty_string("csv_path", raw.get("csv_path")),
            ),
            "dataset": _non_empty_string("dataset", raw.get("dataset")),
            "source_url": _non_empty_string("source_url", raw.get("source_url")),
            "license": _non_empty_string("license", raw.get("license")),
            "crs": _non_empty_string("crs", raw.get("crs")),
            "columns": _columns(raw.get("columns")),
            "max_distance_m": _positive_finite_number(
                "max_distance_m",
                raw.get("max_distance_m"),
            ),
            "aggregation": _aggregation(raw.get("aggregation")),
            "expected_edge_values": _expected_edge_values(
                raw.get("expected_edge_values")
            ),
            "description": (
                raw.get("description", "").strip()
                if isinstance(raw.get("description", ""), str)
                else ""
            ),
        }
    )
    return manifest


def _manifest_metadata(manifest: dict) -> dict:
    return {
        "manifest_dataset": manifest["dataset"],
        "manifest_source_url": manifest["source_url"],
        "manifest_license": manifest["license"],
        "manifest_csv_path": manifest["csv_path"],
        "manifest_crs": manifest["crs"],
    }


def load_traffic_count_stations_from_manifest(path) -> dict:
    """Load traffic-count stations using the CSV columns declared by a manifest."""
    manifest = load_traffic_count_manifest(path)
    columns = manifest["columns"]
    stations = load_traffic_count_csv(
        manifest["csv_path"],
        id_col=columns["id"],
        x_col=columns["x"],
        y_col=columns["y"],
        count_col=columns["count"],
    )
    return {
        "manifest": manifest,
        "stations": stations,
        **_manifest_metadata(manifest),
    }


def _station_ids(stations) -> list[str]:
    return [station.station_id for station in stations]


def _match_station_ids(matches) -> list[str]:
    return [match.station_id for match in matches]


def _geonet_edge_keys(geonet) -> set[tuple]:
    if not hasattr(geonet, "graph"):
        raise ValueError("geonet must be a GeoNetwork")
    return {
        tuple(sorted((u, v), key=repr))
        for u, v in geonet.graph.edges
    }


def traffic_count_match_diagnostics(
    geonet,
    stations,
    matches,
    *,
    max_distance_m,
) -> dict:
    """Summarize map-matching coverage and duplicate edge assignments."""
    max_distance = _positive_finite_number("max_distance_m", max_distance_m)
    geonet_edges = _geonet_edge_keys(geonet)
    station_ids = _station_ids(stations)
    match_ids = _match_station_ids(matches)
    if sorted(station_ids) != sorted(match_ids):
        raise ValueError("matches must correspond to stations")

    matched_ids = set(match_ids)
    unmatched = sorted(
        station_id for station_id in station_ids if station_id not in matched_ids
    )
    distances = [float(match.distance_m) for match in matches]
    edge_to_ids: dict[tuple, list[str]] = {}
    for match in matches:
        if match.edge not in geonet_edges:
            raise ValueError(f"match edge is not in GeoNetwork: {match.edge}")
        if match.distance_m > max_distance:
            raise ValueError(
                "match distance exceeds max_distance_m "
                f"for station {match.station_id}"
            )
        edge_to_ids.setdefault(match.edge, []).append(match.station_id)

    duplicate_groups = []
    for edge in sorted(edge_to_ids, key=repr):
        ids = sorted(edge_to_ids[edge])
        if len(ids) > 1:
            duplicate_groups.append(
                {
                    "edge": edge,
                    "station_ids": ids,
                    "count": len(ids),
                }
            )

    n_stations = len(station_ids)
    matched_stations = len(match_ids)
    return {
        "n_stations": n_stations,
        "matched_stations": matched_stations,
        "unmatched_stations": unmatched,
        "coverage": matched_stations / n_stations if n_stations else 0.0,
        "max_distance_m": max_distance,
        "mean_distance_m": sum(distances) / len(distances) if distances else 0.0,
        "max_match_distance_m": max(distances) if distances else 0.0,
        "matched_edges": len(edge_to_ids),
        "duplicate_edge_groups": duplicate_groups,
    }


def observed_network_from_traffic_count_manifest(geonet, manifest_path) -> dict:
    """Build a manifest-backed observed network target with match diagnostics."""
    loaded = load_traffic_count_stations_from_manifest(manifest_path)
    manifest = loaded["manifest"]
    stations = loaded["stations"]
    if geonet.crs != manifest["crs"]:
        raise ValueError("manifest CRS does not match GeoNetwork CRS")

    matches = match_traffic_counts_to_edges(
        geonet,
        stations,
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
    diagnostics = traffic_count_match_diagnostics(
        geonet,
        stations,
        matches,
        max_distance_m=manifest["max_distance_m"],
    )
    return {
        "observed": observed,
        "stations": stations,
        "matches": matches,
        "diagnostics": diagnostics,
        "manifest": manifest,
        **_manifest_metadata(manifest),
    }


def _fixture_geonet():
    from shapely.geometry import LineString

    from abm_auto.gis._geo_network import GeoNetwork

    return GeoNetwork.from_lines(
        [
            LineString([(0, 0), (10, 0)]),
            LineString([(0, 10), (10, 10)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )


def traffic_count_repro_gate(
    manifest_path=DEFAULT_TRAFFIC_COUNT_MANIFEST,
) -> tuple[bool, str]:
    """Gate for local manifest-backed traffic-count edge validation."""
    result = observed_network_from_traffic_count_manifest(
        _fixture_geonet(),
        manifest_path,
    )
    manifest = result["manifest"]
    observed_values = result["observed"].edge_values
    expected_values = manifest["expected_edge_values"]
    if observed_values != expected_values:
        return (
            False,
            "traffic-count repro pack produced unexpected observed edge values "
            f"(expected={expected_values}, got={observed_values})",
        )

    diagnostics = result["diagnostics"]
    if diagnostics["coverage"] != 1.0:
        return False, f"traffic-count repro pack coverage below 1.0: {diagnostics}"
    if not diagnostics["duplicate_edge_groups"]:
        return False, "traffic-count repro pack did not report duplicate edge groups"

    ok, desc = network_validation_gate(expected_values, result["observed"])
    if not ok:
        return False, f"traffic-count repro pack validation failed: {desc}"

    return (
        True,
        "traffic-count repro pack matched manifest stations "
        f"(dataset={result['manifest_dataset']}, "
        f"matched={diagnostics['matched_stations']}, "
        f"edges={diagnostics['matched_edges']}); "
        "this is local manifest-backed observed-network plumbing, "
        "not official traffic-data download, not full map matching, "
        "and not traffic-flow calibration",
    )
