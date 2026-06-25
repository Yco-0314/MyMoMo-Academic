from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._road_model import run_road_model
from abm_auto.gis._geo_gate import geo_network_gate


def _grid(n=6, step=100.0):
    lines = []
    for r in range(n):
        for c in range(n):
            if c + 1 < n:
                lines.append(LineString([(c * step, r * step), ((c + 1) * step, r * step)]))
            if r + 1 < n:
                lines.append(LineString([(c * step, r * step), (c * step, (r + 1) * step)]))
    return lines


def test_full_geonetwork_path_passes_gate():
    gn = GeoNetwork.from_lines(_grid(), crs="EPSG:3857", snap_tol=1.0)
    res = run_road_model(gn, n_trips=300, seed=1)
    passed, desc = geo_network_gate(res, gn)
    assert passed, desc
