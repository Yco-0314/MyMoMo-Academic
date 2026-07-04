"""Coupled flood-evacuation demo (raster x network) — the first coupled-seam ABM.

Synthetic grid city + a flood band with a gap: agents in the south evacuate to safe
nodes in the north; flooded roads are removed; the gate confirms more flood -> worse.
Your real Beijing road network + a real flood DEM plug into the exact same calls
(build GeoNetwork from the shapefile, RasterSpace from the DEM).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
from affine import Affine
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._flood_model import run_flood_evacuation
from abm_auto.gis._flood_gate import flood_gate
from abm_auto.gis._geo_viz import render_network


def grid_city(n=10, step=100.0):
    lines = []
    for r in range(n):
        for c in range(n):
            if c + 1 < n:
                lines.append(LineString([(c * step, r * step), ((c + 1) * step, r * step)]))
            if r + 1 < n:
                lines.append(LineString([(c * step, r * step), (c * step, (r + 1) * step)]))
    return GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)


def main():
    n, step = 10, 100.0
    gn = grid_city(n, step)
    # flood raster over the city; a mid-latitude band (depth 5) with a 1-cell gap
    rows = cols = n
    data = np.zeros((rows, cols))
    mid = rows // 2
    data[mid, :] = 5.0
    data[mid, cols - 1] = 0.0          # leave a gap on the east edge -> a detour exists
    transform = Affine(step, 0, 0, 0, -step, rows * step)
    flood = RasterSpace(RasterField(data=data, transform=transform, crs="EPSG:3857"))

    safe = [gn.nearest_node(c * step, (n - 1) * step) for c in range(n)]   # north edge
    agents = [gn.nearest_node(c * step, 0) for c in range(n)]              # south edge

    print(f"city: {gn.graph.number_of_nodes()} nodes, {gn.graph.number_of_edges()} edges")
    for t in (100, 1):
        r = run_flood_evacuation(gn, flood, threshold=t, safe_nodes=safe, agent_nodes=agents)
        tag = "dry" if t == 100 else "flood"
        print(f"  {tag:>5}: {r['reached']}/{r['n_agents']} reached, "
              f"{r['stranded']} stranded, mean detour {r['mean_detour_m']:.0f} m, "
              f"{r['n_flooded_edges']} flooded edges")

    ok, desc = flood_gate(gn, flood, safe, agents, thresholds=[100, 1])
    print(f"  flood gate: {'PASS' if ok else 'FAIL'} — {desc}")

    depths = {}
    from abm_auto.gis._coupling import flood_depth_per_edge
    depths = flood_depth_per_edge(gn, flood)
    render_network(gn, {e: (1 if d > 1 else 0) for e, d in depths.items()},
                   Path(__file__).parent / "flood_map.png")
    print(f"  map -> examples/gis_flood/flood_map.png")


if __name__ == "__main__":
    main()
