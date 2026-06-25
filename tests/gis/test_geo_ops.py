from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork


def _gn():
    lines = [LineString([(0, 0), (100, 0)]), LineString([(100, 0), (100, 100)])]
    return GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)


def test_nearest_node_picks_closest():
    gn = _gn()
    n = gn.nearest_node(5, 2)
    assert (gn.graph.nodes[n]["x"], gn.graph.nodes[n]["y"]) == (0.0, 0.0)


def test_network_distance_follows_edges():
    gn = _gn()
    a = gn.nearest_node(0, 0)
    c = gn.nearest_node(100, 100)
    assert gn.network_distance(a, c) == 200.0   # 100 + 100, not the 141 straight line
