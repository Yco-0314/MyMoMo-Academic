import random

from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._road_model import run_road_model
from abm_auto.gis._geo_gate import geo_network_gate


def _grid_network(n=5, step=100.0):
    lines = []
    for r in range(n):
        for c in range(n):
            if c + 1 < n:
                lines.append(LineString([(c * step, r * step), ((c + 1) * step, r * step)]))
            if r + 1 < n:
                lines.append(LineString([(c * step, r * step), (c * step, (r + 1) * step)]))
    return GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)


def test_gate_passes_on_real_run():
    gn = _grid_network()
    res = run_road_model(gn, n_trips=200, seed=1)
    passed, desc = geo_network_gate(res, gn)
    assert passed, desc


def test_gate_fails_when_load_is_random():
    gn = _grid_network()
    res = run_road_model(gn, n_trips=200, seed=1)
    rng = random.Random(0)
    keys = list(res["edge_load"])
    res["edge_load"] = {k: rng.randint(0, 5) for k in keys}   # destroy load<->centrality
    passed, _ = geo_network_gate(res, gn)
    assert not passed
