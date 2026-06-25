from shapely.geometry import LineString, Polygon

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._point_space import PointSpace
from abm_auto.gis._polygon_space import PolygonSpace
from abm_auto.gis._space_zoo_gate import (
    point_network_risk_gate,
    polygon_point_zoning_gate,
)


def _geonet():
    lines = [
        LineString([(0, 0), (100, 0)]),
        LineString([(100, 0), (100, 100)]),
    ]
    return GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)


def _edge(geonet, ax, ay, bx, by):
    a = geonet.nearest_node(ax, ay)
    b = geonet.nearest_node(bx, by)
    return tuple(sorted((a, b)))


def test_point_network_risk_gate_passes_when_loaded_risky_edge_lights_up():
    geonet = _geonet()
    points = PointSpace.from_coords([(50, 5), (1000, 1000)], crs="EPSG:3857")
    risky = _edge(geonet, 0, 0, 100, 0)
    dry = _edge(geonet, 100, 0, 100, 100)

    ok, desc = point_network_risk_gate(
        geonet,
        points,
        radius=10.0,
        edge_load={risky: 4, dry: 7},
    )

    assert ok, desc
    assert "loaded risky edge" in desc
    assert "dry loaded edges stay zero" in desc


def test_point_network_risk_gate_fails_when_no_loaded_risky_edge_lights_up():
    geonet = _geonet()
    points = PointSpace.from_coords([(1000, 1000)], crs="EPSG:3857")
    risky = _edge(geonet, 0, 0, 100, 0)

    ok, desc = point_network_risk_gate(
        geonet,
        points,
        radius=10.0,
        edge_load={risky: 4},
    )

    assert not ok
    assert "no loaded risky edge" in desc


def _polygons():
    west = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    east = Polygon([(10, 0), (20, 0), (20, 10), (10, 10)])
    return PolygonSpace.from_polygons(
        [west, east],
        crs="EPSG:3857",
        ids=["west", "east"],
    )


def test_polygon_point_zoning_gate_passes_for_expected_assignments():
    points = PointSpace.from_coords([(5, 5), (15, 5), (50, 50)], crs="EPSG:3857")
    polygons = _polygons()

    ok, desc = polygon_point_zoning_gate(
        points,
        polygons,
        expected={"west": [0], "east": [1]},
    )

    assert ok, desc
    assert "polygon-point zoning" in desc


def test_polygon_point_zoning_gate_fails_on_mismatched_expected_assignments():
    points = PointSpace.from_coords([(5, 5), (15, 5), (50, 50)], crs="EPSG:3857")
    polygons = _polygons()

    ok, desc = polygon_point_zoning_gate(
        points,
        polygons,
        expected={"west": [0], "east": [2]},
    )

    assert not ok
    assert "expected" in desc
