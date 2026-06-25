import numpy as np
import pytest
from affine import Affine
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._temporal import RasterTimeline
from abm_auto.gis._dynamic_flood import run_dynamic_flood_evacuation


def _raster(data):
    return RasterSpace(
        RasterField(
            data=np.array(data, dtype=float),
            transform=Affine(100, 0, 0, 0, -100, 500),
            crs="EPSG:3857",
        )
    )


def _timeline(*frames):
    return RasterTimeline.from_frames([_raster(frame) for frame in frames])


def _node(geonet, x, y):
    return geonet.nearest_node(x, y)


def test_two_tick_single_edge_arrival_history():
    geonet = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 200)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 200)
    dry = np.zeros((5, 5))

    result = run_dynamic_flood_evacuation(
        geonet,
        _timeline(dry, dry),
        threshold=1,
        safe_nodes=[safe],
        agent_nodes=[start],
        speed_m_per_tick=100,
    )

    assert result["n_steps"] == 2
    assert result["n_agents"] == 1
    assert result["steps"][0]["moving"] == 1
    assert result["steps"][0]["arrived"] == 0
    assert result["steps"][1]["arrived"] == 1
    assert result["mean_arrival_t"] == 1
    assert result["agents"][0]["arrived"] is True
    assert result["agents"][0]["arrival_t"] == 1


def test_speed_does_not_carry_across_edge_boundaries():
    dry = np.zeros((5, 5))
    single_edge = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 200)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    split_edges = GeoNetwork.from_lines(
        [
            LineString([(0, 0), (0, 100)]),
            LineString([(0, 100), (0, 200)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )

    single = run_dynamic_flood_evacuation(
        single_edge,
        _timeline(dry, dry),
        threshold=1,
        safe_nodes=[_node(single_edge, 0, 200)],
        agent_nodes=[_node(single_edge, 0, 0)],
        speed_m_per_tick=200,
    )
    split = run_dynamic_flood_evacuation(
        split_edges,
        _timeline(dry, dry),
        threshold=1,
        safe_nodes=[_node(split_edges, 0, 200)],
        agent_nodes=[_node(split_edges, 0, 0)],
        speed_m_per_tick=200,
    )

    assert single["agents"][0]["arrival_t"] == 0
    assert split["agents"][0]["arrival_t"] == 1
    assert split["agents"][0]["arrival_t"] != single["agents"][0]["arrival_t"]
    assert single["mean_arrival_t"] == 0
    assert split["mean_arrival_t"] == 1


def test_equal_length_routes_are_stable_across_line_insertion_order():
    dry = np.zeros((5, 5))
    top_path = [
        LineString([(0, 0), (100, 100)]),
        LineString([(100, 100), (200, 0)]),
    ]
    bottom_path = [
        LineString([(0, 0), (100, -100)]),
        LineString([(100, -100), (200, 0)]),
    ]

    first = GeoNetwork.from_lines(top_path + bottom_path, crs="EPSG:3857", snap_tol=1.0)
    second = GeoNetwork.from_lines(bottom_path + top_path, crs="EPSG:3857", snap_tol=1.0)

    first_result = run_dynamic_flood_evacuation(
        first,
        _timeline(dry),
        threshold=1,
        safe_nodes=[_node(first, 200, 0)],
        agent_nodes=[_node(first, 0, 0)],
        speed_m_per_tick=1,
    )
    second_result = run_dynamic_flood_evacuation(
        second,
        _timeline(dry),
        threshold=1,
        safe_nodes=[_node(second, 200, 0)],
        agent_nodes=[_node(second, 0, 0)],
        speed_m_per_tick=1,
    )

    assert first_result["agents"][0]["edge"] == second_result["agents"][0]["edge"]
    assert first_result["agents"][0]["route"] == second_result["agents"][0]["route"]


def test_node_reroute_takes_dry_detour_while_static_route_waits():
    lines = [
        LineString([(0, 0), (0, 100)]),
        LineString([(0, 100), (0, 200)]),
        LineString([(0, 200), (200, 200)]),
        LineString([(0, 100), (300, 100)]),
        LineString([(300, 100), (300, 200)]),
        LineString([(300, 200), (200, 200)]),
    ]
    geonet = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 200, 200)
    dry = np.zeros((5, 5))
    flooded_direct = np.zeros((5, 5))
    flooded_direct[3, 0] = 5.0

    rerouted = run_dynamic_flood_evacuation(
        geonet,
        _timeline(dry, flooded_direct, flooded_direct, flooded_direct, flooded_direct, flooded_direct),
        threshold=1,
        safe_nodes=[safe],
        agent_nodes=[start],
        speed_m_per_tick=100,
        reroute=True,
    )
    static = run_dynamic_flood_evacuation(
        geonet,
        _timeline(dry, flooded_direct, flooded_direct, flooded_direct, flooded_direct, flooded_direct),
        threshold=1,
        safe_nodes=[safe],
        agent_nodes=[start],
        speed_m_per_tick=100,
        reroute=False,
    )

    assert rerouted["arrived"] == 1
    assert rerouted["stranded"] == 0
    assert rerouted["total_reroutes"] > 0
    assert any(step["reroutes_this_step"] > 0 for step in rerouted["steps"])
    assert static["arrived"] == 0
    assert static["stranded"] == 1
    assert static["agents"][0]["stranded_reason"] == "not_arrived"


def test_failed_reroute_without_alternative_does_not_increment_counts():
    geonet = GeoNetwork.from_lines(
        [
            LineString([(0, 0), (0, 100)]),
            LineString([(0, 100), (0, 200)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 200)
    dry = np.zeros((5, 5))
    flooded_next = np.zeros((5, 5))
    flooded_next[3, 0] = 5.0

    result = run_dynamic_flood_evacuation(
        geonet,
        _timeline(dry, flooded_next),
        threshold=1,
        safe_nodes=[safe],
        agent_nodes=[start],
        speed_m_per_tick=100,
        reroute=True,
    )

    assert result["arrived"] == 0
    assert result["agents"][0]["stranded_reason"] == "not_arrived"
    assert result["total_reroutes"] == 0
    assert result["agents"][0]["reroutes"] == 0
    assert result["steps"][1]["reroutes_this_step"] == 0


def test_agent_on_edge_becomes_stranded_when_edge_floods_next_tick():
    geonet = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 200)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 200)
    dry = np.zeros((5, 5))
    flooded = np.zeros((5, 5))
    flooded[4, 0] = 4.0

    result = run_dynamic_flood_evacuation(
        geonet,
        _timeline(dry, flooded),
        threshold=1,
        safe_nodes=[safe],
        agent_nodes=[start],
        speed_m_per_tick=75,
    )

    agent = result["agents"][0]
    assert agent["stranded"] is True
    assert agent["stranded_reason"] == "flooded_on_edge"
    assert agent["exposure_depth"] > 0
    assert result["steps"][1]["stranded"] == 1


def test_missing_or_unreachable_safe_nodes_end_not_arrived():
    geonet = GeoNetwork.from_lines(
        [
            LineString([(0, 0), (0, 100)]),
            LineString([(300, 0), (300, 100)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    disconnected_safe = _node(geonet, 300, 100)
    dry = np.zeros((5, 5))

    no_safe = run_dynamic_flood_evacuation(
        geonet,
        _timeline(dry),
        threshold=1,
        safe_nodes=[],
        agent_nodes=[start],
    )
    unreachable = run_dynamic_flood_evacuation(
        geonet,
        _timeline(dry),
        threshold=1,
        safe_nodes=[disconnected_safe],
        agent_nodes=[start],
    )

    assert no_safe["agents"][0]["stranded_reason"] == "not_arrived"
    assert unreachable["agents"][0]["stranded_reason"] == "not_arrived"
    assert no_safe["stranded"] == 1
    assert unreachable["stranded"] == 1


def test_rejects_non_positive_speed():
    geonet = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 100)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    dry = np.zeros((5, 5))
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 100)

    with pytest.raises(ValueError, match="speed"):
        run_dynamic_flood_evacuation(
            geonet,
            _timeline(dry),
            threshold=1,
            safe_nodes=[safe],
            agent_nodes=[start],
            speed_m_per_tick=0,
        )


def test_rejects_duck_and_forged_raster_timelines():
    geonet = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 100)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    dry = _raster(np.zeros((5, 5)))
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 100)

    class FakeTimeline:
        n_steps = 1

        def at(self, _t):
            return dry

    with pytest.raises((TypeError, ValueError), match="RasterTimeline|timeline"):
        run_dynamic_flood_evacuation(
            geonet,
            FakeTimeline(),
            threshold=1,
            safe_nodes=[safe],
            agent_nodes=[start],
        )

    mismatched = RasterSpace(
        RasterField(
            data=np.zeros((3, 3), dtype=float),
            transform=Affine(100, 0, 0, 0, -100, 500),
            crs="EPSG:4326",
        )
    )
    forged = RasterTimeline.__new__(RasterTimeline)
    object.__setattr__(forged, "_frames", (dry, mismatched))

    with pytest.raises(ValueError, match="CRS|shape|dimensions|transform|RasterTimeline"):
        run_dynamic_flood_evacuation(
            geonet,
            forged,
            threshold=1,
            safe_nodes=[safe],
            agent_nodes=[start],
        )
