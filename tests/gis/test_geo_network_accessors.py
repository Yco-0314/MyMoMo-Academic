"""Tests for GeoNetwork.node_coord / edge_geom — the coordinate/geometry accessors
that concentrate the node-attribute schema, so callers no longer reach into
graph.nodes[n]['x']/['y'] or rebuild edge LineStrings by hand."""
from __future__ import annotations

from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork


def _net():
    return GeoNetwork.from_lines(
        [LineString([(0, 0), (10, 0)]), LineString([(10, 0), (10, 20)])],
        crs="EPSG:3857", snap_tol=1.0,
    )


def test_node_coord_returns_xy_floats():
    net = _net()
    x, y = net.node_coord(net.nearest_node(0, 0))
    assert (x, y) == (0.0, 0.0)
    assert isinstance(x, float) and isinstance(y, float)


def test_edge_geom_builds_linestring_from_node_coords():
    net = _net()
    u, v = next(iter(net.graph.edges))
    geom = net.edge_geom(u, v)
    assert isinstance(geom, LineString)
    assert list(geom.coords) == [net.node_coord(u), net.node_coord(v)]


def test_nearest_node_resolves_via_node_coord():
    net = _net()
    assert net.node_coord(net.nearest_node(10, 20)) == (10.0, 20.0)
    assert net.node_coord(net.nearest_node(0, 0)) == (0.0, 0.0)
