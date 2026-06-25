from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._congestion_gate import dynamic_congestion_reroute_gate


def _node(geonet, x, y):
    return geonet.nearest_node(x, y)


def _diamond_network():
    return GeoNetwork.from_lines(
        [
            LineString([(0, 0), (100, 0)]),
            LineString([(100, 0), (200, 0)]),
            LineString([(200, 0), (300, 0)]),
            LineString([(0, 0), (100, -100)]),
            LineString([(100, -100), (200, -100)]),
            LineString([(200, -100), (300, 0)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )


def test_dynamic_congestion_reroute_gate_passes_on_synthetic_case():
    geonet = _diamond_network()
    ok, desc = dynamic_congestion_reroute_gate(
        geonet,
        safe_nodes=[_node(geonet, 300, 0)],
        agent_nodes=[
            _node(geonet, 100, 0),
            _node(geonet, 100, 0),
            _node(geonet, 0, 0),
        ],
        n_steps=8,
        speed_m_per_tick=100,
        congestion_alpha=3.0,
    )

    assert ok, desc
    assert "moving-agent congestion rerouting changes deterministic outcomes" in desc
    assert "not a traffic-flow or congestion-validity claim" in desc


def test_dynamic_congestion_reroute_gate_fails_without_congestion_effect():
    geonet = _diamond_network()
    ok, desc = dynamic_congestion_reroute_gate(
        geonet,
        safe_nodes=[_node(geonet, 300, 0)],
        agent_nodes=[
            _node(geonet, 100, 0),
            _node(geonet, 100, 0),
            _node(geonet, 0, 0),
        ],
        n_steps=8,
        speed_m_per_tick=100,
        congestion_alpha=0.0,
    )

    assert not ok
    assert "no successful congestion reroute" in desc or "did not improve" in desc


def test_dynamic_congestion_reroute_gate_fails_without_reroute_opportunity():
    geonet = GeoNetwork.from_lines(
        [
            LineString([(0, 0), (100, 0)]),
            LineString([(100, 0), (200, 0)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    ok, desc = dynamic_congestion_reroute_gate(
        geonet,
        safe_nodes=[_node(geonet, 200, 0)],
        agent_nodes=[_node(geonet, 0, 0)],
        n_steps=3,
        speed_m_per_tick=100,
        congestion_alpha=3.0,
    )

    assert not ok
    assert "no successful congestion reroute" in desc
