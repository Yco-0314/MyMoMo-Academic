from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._road_model import run_road_model
from abm_auto.gis._geo_viz import render_network


def test_render_network_writes_png(tmp_path):
    lines = [LineString([(0, 0), (100, 0)]), LineString([(100, 0), (100, 100)])]
    gn = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    res = run_road_model(gn, n_trips=10, seed=1)
    out = tmp_path / "net.png"
    render_network(gn, res["edge_load"], out)
    assert out.exists() and out.stat().st_size > 0
