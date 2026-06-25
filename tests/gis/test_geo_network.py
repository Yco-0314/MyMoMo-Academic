from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork


def _lines():
    return [
        LineString([(0, 0), (100, 0)]),
        LineString([(100, 0), (100, 100)]),
        LineString([(100, 0), (200, 0)]),
    ]


def test_build_nodes_and_edges_with_length():
    gn = GeoNetwork.from_lines(_lines(), crs="EPSG:3857", snap_tol=1.0)
    assert gn.graph.number_of_nodes() == 4   # endpoints, (100,0) shared
    assert gn.graph.number_of_edges() == 3
    a = gn.nearest_node(0, 0)
    b = gn.nearest_node(100, 0)
    assert gn.graph.edges[a, b]["length"] == 100.0


def test_snapping_merges_near_coincident_endpoints():
    lines = [LineString([(0, 0), (10, 0)]), LineString([(10.4, 0), (20, 0)])]
    gn = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    assert gn.graph.number_of_nodes() == 3
