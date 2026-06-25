"""Traffic count station CSV loading utilities."""
from __future__ import annotations

import csv
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from shapely.geometry import LineString, Point

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._network_validation import (
    network_validation_gate,
    observed_network_from_mapping,
)


def _station_id(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("station_id must be a non-empty stripped string")
    return value.strip()


def _finite_number(name: str, value: Any) -> float:
    # ponytail: deliberately lenient (try/float, not the strict isinstance check used by
    # the _finite_number in the other GIS modules) — this loader parses CSV string values
    # like "3.5". Do NOT consolidate it with the strict variants or CSV ingestion breaks.
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(out):
        raise ValueError(f"{name} must be a finite number")
    return out


def _finite_non_negative_number(name: str, value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite non-negative number")
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite non-negative number") from exc
    if not math.isfinite(out) or out < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return out


def _positive_finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive finite number")
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive finite number") from exc
    if not math.isfinite(out) or out <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return out


def _edge_key(edge: Any) -> tuple:
    try:
        nodes = tuple(edge)
    except TypeError as exc:
        raise ValueError("edge must contain exactly two nodes") from exc
    if len(nodes) != 2:
        raise ValueError("edge must contain exactly two nodes")
    return tuple(sorted(nodes, key=repr))


@dataclass(frozen=True)
class TrafficCountStation:
    """Observed traffic count at a georeferenced station point."""

    station_id: str
    x: float
    y: float
    count: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "station_id", _station_id(self.station_id))
        object.__setattr__(self, "x", _finite_number("x", self.x))
        object.__setattr__(self, "y", _finite_number("y", self.y))
        object.__setattr__(
            self,
            "count",
            _finite_non_negative_number("count", self.count),
        )


@dataclass(frozen=True)
class TrafficCountEdgeMatch:
    """Traffic count station snapped to a normalized undirected road edge."""

    station_id: str
    edge: tuple
    distance_m: float
    count: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "station_id", _station_id(self.station_id))
        object.__setattr__(self, "edge", _edge_key(self.edge))
        object.__setattr__(
            self,
            "distance_m",
            _finite_non_negative_number("distance_m", self.distance_m),
        )
        object.__setattr__(
            self,
            "count",
            _finite_non_negative_number("count", self.count),
        )


def _traffic_count_stations(stations: Any) -> list[TrafficCountStation]:
    if (
        isinstance(stations, (str, bytes))
        or not isinstance(stations, Sequence)
        or len(stations) == 0
    ):
        raise ValueError("stations must be non-empty sequence of TrafficCountStation")
    out = list(stations)
    if not all(isinstance(station, TrafficCountStation) for station in out):
        raise ValueError("stations must be non-empty sequence of TrafficCountStation")
    return out


def _geonet_edges(geonet: Any) -> list[tuple[tuple, LineString]]:
    if not hasattr(geonet, "graph") or not hasattr(geonet, "crs"):
        raise ValueError("geonet must be a GeoNetwork")
    graph = geonet.graph
    if not hasattr(graph, "number_of_edges") or not hasattr(graph, "edges"):
        raise ValueError("geonet must be a GeoNetwork")
    if graph.number_of_edges() < 1:
        raise ValueError("geonet must contain at least one edge")

    edges: list[tuple[tuple, LineString]] = []
    for u, v in graph.edges:
        try:
            u_attrs = graph.nodes[u]
            v_attrs = graph.nodes[v]
            u_x = _finite_number("x", u_attrs["x"])
            u_y = _finite_number("y", u_attrs["y"])
            v_x = _finite_number("x", v_attrs["x"])
            v_y = _finite_number("y", v_attrs["y"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("geonet must be a GeoNetwork") from exc
        edges.append((_edge_key((u, v)), LineString([(u_x, u_y), (v_x, v_y)])))
    return edges


def match_traffic_counts_to_edges(
    geonet: Any,
    stations: Sequence[TrafficCountStation],
    *,
    max_distance_m,
) -> list[TrafficCountEdgeMatch]:
    """Match each traffic-count station to the nearest road edge."""
    max_distance = _positive_finite_number("max_distance_m", max_distance_m)
    station_list = _traffic_count_stations(stations)
    edges = _geonet_edges(geonet)

    matches: list[TrafficCountEdgeMatch] = []
    for station in station_list:
        point = Point(station.x, station.y)
        candidates = [
            (edge, float(point.distance(geometry)))
            for edge, geometry in edges
        ]
        edge, distance = min(candidates, key=lambda item: (item[1], repr(item[0])))
        if distance > max_distance:
            raise ValueError(
                "no GeoNetwork edge within max_distance_m "
                f"for station {station.station_id}"
            )
        matches.append(
            TrafficCountEdgeMatch(
                station.station_id,
                edge,
                distance,
                station.count,
            )
        )
    return matches


def observed_network_from_traffic_counts(
    geonet: Any,
    stations: Sequence[TrafficCountStation],
    *,
    max_distance_m,
    source,
    dataset,
    metric: str = "edge_load",
    aggregation: str = "sum",
):
    """Build an observed network target from map-matched traffic counts."""
    if aggregation not in {"sum", "mean"}:
        raise ValueError("aggregation must be 'sum' or 'mean'")
    matches = match_traffic_counts_to_edges(
        geonet,
        stations,
        max_distance_m=max_distance_m,
    )

    counts_by_edge: dict[tuple, list[float]] = {}
    for match in matches:
        counts_by_edge.setdefault(match.edge, []).append(match.count)

    if aggregation == "sum":
        edge_values = {
            edge: sum(counts)
            for edge, counts in counts_by_edge.items()
        }
    else:
        edge_values = {
            edge: sum(counts) / len(counts)
            for edge, counts in counts_by_edge.items()
        }

    return observed_network_from_mapping(
        edge_values,
        source=source,
        dataset=dataset,
        metric=metric,
    )


def traffic_count_edge_matching_gate() -> tuple[bool, str]:
    """Gate proving count stations can be matched into observed edge values."""
    geonet = GeoNetwork.from_lines(
        [
            LineString([(0, 0), (10, 0)]),
            LineString([(0, 10), (10, 10)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    stations = [
        TrafficCountStation("main-a", 2.0, 0.2, 70.0),
        TrafficCountStation("main-b", 6.0, -0.3, 30.0),
        TrafficCountStation("north", 5.0, 9.6, 40.0),
    ]
    expected_edge_values = {
        _edge_key(((0, 0), (10, 0))): 100.0,
        _edge_key(((0, 10), (10, 10))): 40.0,
    }

    observed = observed_network_from_traffic_counts(
        geonet,
        stations,
        max_distance_m=1.0,
        source="synthetic traffic count stations",
        dataset="traffic-count-edge-matching-gate",
        aggregation="sum",
    )

    if observed.edge_values != expected_edge_values:
        return (
            False,
            "traffic count edge matching produced unexpected observed values "
            f"(expected={expected_edge_values}, got={observed.edge_values})",
        )

    ok, desc = network_validation_gate(expected_edge_values, observed)
    if not ok:
        return False, f"traffic count edge matching validation failed: {desc}"

    return (
        True,
        "traffic count stations matched to GeoNetwork edges "
        f"(n_edges={len(observed.edge_values)}, aggregation=sum); "
        "this is observed edge-value plumbing, not traffic-flow calibration "
        "and not full map matching",
    )


def load_traffic_count_csv(
    path,
    *,
    id_col: str = "station_id",
    x_col: str = "x",
    y_col: str = "y",
    count_col: str = "count",
) -> list[TrafficCountStation]:
    """Load traffic count station rows from a CSV file."""
    required_columns = (id_col, x_col, y_col, count_col)

    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        if not fieldnames:
            raise ValueError("traffic count CSV must contain at least one row")
        missing = [column for column in required_columns if column not in fieldnames]
        if missing:
            raise ValueError(
                "traffic count CSV missing required columns: " + ", ".join(missing)
            )
        rows = list(reader)

    if not rows:
        raise ValueError("traffic count CSV must contain at least one row")

    stations: list[TrafficCountStation] = []
    for row_number, row in enumerate(rows, start=2):
        try:
            stations.append(
                TrafficCountStation(
                    station_id=row[id_col],
                    x=row[x_col],
                    y=row[y_col],
                    count=row[count_col],
                )
            )
        except ValueError as exc:
            raise ValueError(f"traffic count CSV row {row_number}: {exc}") from exc
    return stations
