import math

import pytest
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._traffic_counts import (
    TrafficCountEdgeMatch,
    TrafficCountStation,
    load_traffic_count_csv,
    match_traffic_counts_to_edges,
    observed_network_from_traffic_counts,
    traffic_count_edge_matching_gate,
)


def _synthetic_geonet():
    lines = [
        LineString([(0, 0), (10, 0)]),
        LineString([(0, 0), (0, 10)]),
        LineString([(20, 0), (30, 0)]),
    ]
    return GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)


def _edge(a, b):
    return tuple(sorted((a, b), key=repr))


def test_load_traffic_count_csv_preserves_row_order(tmp_path):
    path = tmp_path / "traffic_counts.csv"
    path.write_text(
        "station_id,x,y,count\n"
        "station-b,100.5,30.25,1250\n"
        "station-a,101.0,31.5,980.5\n",
        encoding="utf-8",
    )

    stations = load_traffic_count_csv(path)

    assert stations == [
        TrafficCountStation("station-b", 100.5, 30.25, 1250.0),
        TrafficCountStation("station-a", 101.0, 31.5, 980.5),
    ]
    assert [station.station_id for station in stations] == ["station-b", "station-a"]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"station_id": "   "}, "station_id must be a non-empty stripped string"),
        ({"x": math.nan}, "x must be a finite number"),
        ({"y": True}, "y must be a finite number"),
        ({"count": math.nan}, "count must be a finite non-negative number"),
        ({"count": -1}, "count must be a finite non-negative number"),
        ({"count": False}, "count must be a finite non-negative number"),
    ],
)
def test_traffic_count_station_rejects_invalid_values(overrides, message):
    kwargs = {"station_id": "station-a", "x": 100.5, "y": 30.25, "count": 1250}
    kwargs.update(overrides)

    with pytest.raises(ValueError, match=message):
        TrafficCountStation(**kwargs)


def test_load_traffic_count_csv_rejects_missing_required_columns(tmp_path):
    path = tmp_path / "traffic_counts.csv"
    path.write_text("station_id,x,count\nstation-a,100.5,1250\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required columns"):
        load_traffic_count_csv(path)


@pytest.mark.parametrize("contents", ["", "station_id,x,y,count\n"])
def test_load_traffic_count_csv_rejects_empty_file_or_no_rows(tmp_path, contents):
    path = tmp_path / "traffic_counts.csv"
    path.write_text(contents, encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="traffic count CSV must contain at least one row",
    ):
        load_traffic_count_csv(path)


def test_match_traffic_counts_to_edges_assigns_nearest_edge():
    geonet = _synthetic_geonet()
    stations = [
        TrafficCountStation("near-horizontal", 4, 1, 100),
        TrafficCountStation("near-remote", 24, 2, 50),
    ]

    matches = match_traffic_counts_to_edges(
        geonet,
        stations,
        max_distance_m=3.0,
    )

    assert matches == [
        TrafficCountEdgeMatch(
            "near-horizontal",
            _edge((0, 0), (10, 0)),
            1.0,
            100.0,
        ),
        TrafficCountEdgeMatch(
            "near-remote",
            _edge((20, 0), (30, 0)),
            2.0,
            50.0,
        ),
    ]


def test_match_traffic_counts_to_edges_breaks_equal_distance_ties_deterministically():
    geonet = _synthetic_geonet()
    stations = [TrafficCountStation("on-shared-node", 0, 0, 10)]

    matches = match_traffic_counts_to_edges(
        geonet,
        stations,
        max_distance_m=1.0,
    )

    assert matches == [
        TrafficCountEdgeMatch(
            "on-shared-node",
            _edge((0, 0), (0, 10)),
            0.0,
            10.0,
        )
    ]


def test_match_traffic_counts_to_edges_rejects_station_outside_tolerance():
    geonet = _synthetic_geonet()
    stations = [TrafficCountStation("too-far", 100, 100, 10)]

    with pytest.raises(
        ValueError,
        match="no GeoNetwork edge within max_distance_m.*too-far",
    ):
        match_traffic_counts_to_edges(geonet, stations, max_distance_m=5.0)


def test_observed_network_from_traffic_counts_aggregates_duplicate_edges_with_sum():
    geonet = _synthetic_geonet()
    stations = [
        TrafficCountStation("a", 4, 1, 100),
        TrafficCountStation("b", 7, 1, 25),
        TrafficCountStation("c", 25, 2, 50),
    ]

    observed = observed_network_from_traffic_counts(
        geonet,
        stations,
        max_distance_m=3.0,
        source="synthetic traffic counter",
        dataset="phase-1-test",
        aggregation="sum",
    )

    assert observed.edge_values == {
        _edge((0, 0), (10, 0)): 125.0,
        _edge((20, 0), (30, 0)): 50.0,
    }
    assert observed.provenance() == {
        "source": "synthetic traffic counter",
        "dataset": "phase-1-test",
        "metric": "edge_load",
        "n_edges": 2,
    }


def test_observed_network_from_traffic_counts_aggregates_duplicate_edges_with_mean():
    geonet = _synthetic_geonet()
    stations = [
        TrafficCountStation("a", 4, 1, 100),
        TrafficCountStation("b", 7, 1, 25),
        TrafficCountStation("c", 25, 2, 50),
    ]

    observed = observed_network_from_traffic_counts(
        geonet,
        stations,
        max_distance_m=3.0,
        source="synthetic traffic counter",
        dataset="phase-1-test",
        metric="daily_vehicles",
        aggregation="mean",
    )

    assert observed.edge_values == {
        _edge((0, 0), (10, 0)): 62.5,
        _edge((20, 0), (30, 0)): 50.0,
    }
    assert observed.metric == "daily_vehicles"


def test_observed_network_from_traffic_counts_rejects_unknown_aggregation():
    geonet = _synthetic_geonet()
    stations = [TrafficCountStation("a", 4, 1, 100)]

    with pytest.raises(ValueError, match="aggregation must be 'sum' or 'mean'"):
        observed_network_from_traffic_counts(
            geonet,
            stations,
            max_distance_m=3.0,
            source="synthetic traffic counter",
            dataset="phase-1-test",
            aggregation="median",
        )


def test_traffic_count_edge_matching_gate_passes_with_boundary_text():
    ok, desc = traffic_count_edge_matching_gate()

    assert ok, desc
    assert "traffic count stations matched to GeoNetwork edges" in desc
    assert "not traffic-flow calibration" in desc
    assert "not full map matching" in desc


def test_match_traffic_counts_to_edges_rejects_invalid_inputs():
    geonet = _synthetic_geonet()

    with pytest.raises(ValueError, match="stations must be non-empty"):
        match_traffic_counts_to_edges(geonet, [], max_distance_m=3.0)

    with pytest.raises(
        ValueError,
        match="max_distance_m must be a positive finite number",
    ):
        match_traffic_counts_to_edges(
            geonet,
            [TrafficCountStation("a", 4, 1, 100)],
            max_distance_m=0,
        )

    with pytest.raises(
        ValueError,
        match="max_distance_m must be a positive finite number",
    ):
        match_traffic_counts_to_edges(
            geonet,
            [TrafficCountStation("a", 4, 1, 100)],
            max_distance_m=True,
        )

    empty_geonet = GeoNetwork.from_lines([], crs="EPSG:3857", snap_tol=1.0)
    with pytest.raises(ValueError, match="geonet must contain at least one edge"):
        match_traffic_counts_to_edges(
            empty_geonet,
            [TrafficCountStation("a", 4, 1, 100)],
            max_distance_m=3.0,
        )

    with pytest.raises(ValueError, match="geonet must be a GeoNetwork"):
        match_traffic_counts_to_edges(
            object(),
            [TrafficCountStation("a", 4, 1, 100)],
            max_distance_m=3.0,
        )
