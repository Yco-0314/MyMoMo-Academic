import pytest
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._risk import edge_risk_from_points, risk_exposure


def _gn():
    # two edges: (0,0)-(100,0) and (100,0)-(100,100)
    lines = [LineString([(0, 0), (100, 0)]), LineString([(100, 0), (100, 100)])]
    return GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)


def test_edge_risk_counts_nearby_points():
    gn = _gn()
    # one risk point right on the first edge, one far away
    risk = edge_risk_from_points(gn, [(50, 5), (1000, 1000)], radius=10.0)
    a = gn.nearest_node(0, 0)
    b = gn.nearest_node(100, 0)
    assert risk[tuple(sorted((a, b)))] == 1            # near edge 1
    assert sum(risk.values()) == 1                     # the far point hits nothing


def test_edge_risk_from_points_rejects_negative_radius():
    gn = _gn()

    with pytest.raises(ValueError, match="radius"):
        edge_risk_from_points(gn, [(50, 5)], radius=-1.0)


def test_risk_exposure_is_load_times_risk():
    edge_load = {("a", "b"): 4, ("b", "c"): 7}
    edge_risk = {("a", "b"): 2, ("b", "c"): 0}
    exp = risk_exposure(edge_load, edge_risk)
    assert exp[("a", "b")] == 8
    assert exp[("b", "c")] == 0


def test_risk_exposure_gate_lights_up_only_loaded_risky_edge():
    gn = _gn()
    risk = edge_risk_from_points(gn, [(50, 5), (1000, 1000)], radius=10.0)
    a = gn.nearest_node(0, 0)
    b = gn.nearest_node(100, 0)
    c = gn.nearest_node(100, 100)
    risky = tuple(sorted((a, b)))
    dry = tuple(sorted((b, c)))

    exposure = risk_exposure({risky: 4, dry: 7}, risk)

    assert exposure[risky] == 4
    assert exposure[dry] == 0
