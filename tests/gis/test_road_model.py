from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._road_model import run_road_model


def _grid_network(n=5, step=100.0):
    lines = []
    for r in range(n):
        for c in range(n):
            if c + 1 < n:
                lines.append(LineString([(c * step, r * step), ((c + 1) * step, r * step)]))
            if r + 1 < n:
                lines.append(LineString([(c * step, r * step), (c * step, (r + 1) * step)]))
    return GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)


def test_road_model_routes_all_trips_and_loads_edges():
    gn = _grid_network()
    res = run_road_model(gn, n_trips=40, seed=1)
    assert res["reached"] == res["n_trips"] == 40
    assert sum(res["edge_load"].values()) > 0
    res2 = run_road_model(gn, n_trips=40, seed=1)
    assert res["edge_load"] == res2["edge_load"]   # deterministic
