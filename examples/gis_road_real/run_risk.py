"""Risk-exposure on the user's REAL road network + risk points.

Where does heavy traffic coincide with road risk points? Origination model on
the user's own data (NOT a paper reproduction). External data, not committed.
"""
import sys
import time
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

ROADS = os.environ.get("GIS_ROADS_PATH")
RISK = os.environ.get("GIS_RISK_POINTS_PATH")
METRIC_CRS = "EPSG:32650"  # UTM zone 50N (Beijing area), metres
RADIUS = 50.0              # metres: a risk point "affects" edges within 50 m


def main():
    import geopandas as gpd
    import networkx as nx
    from abm_auto.gis._geo_network import GeoNetwork
    from abm_auto.gis._road_model import run_road_model
    from abm_auto.gis._risk import edge_risk_from_points, risk_exposure
    from abm_auto.gis._geo_viz import render_network

    if not ROADS or not RISK:
        raise SystemExit(
            "Set GIS_ROADS_PATH and GIS_RISK_POINTS_PATH before running this demo."
        )

    t0 = time.time()
    roads = gpd.read_file(ROADS, encoding="gbk").to_crs(METRIC_CRS).explode(index_parts=False)
    lines = [g for g in roads.geometry if g is not None and g.geom_type == "LineString"]
    gn = GeoNetwork.from_lines(lines, crs=METRIC_CRS, snap_tol=1.0)
    gcc = max(nx.connected_components(gn.graph), key=len)
    gn.graph = gn.graph.subgraph(gcc).copy()
    print(f"GeoNetwork: {gn.graph.number_of_nodes()} nodes, {gn.graph.number_of_edges()} edges")

    risk_gdf = gpd.read_file(RISK, encoding="gbk").to_crs(METRIC_CRS).explode(index_parts=False)
    pts = [(g.x, g.y) for g in risk_gdf.geometry if g is not None and g.geom_type == "Point"]
    print(f"risk points: {len(pts)}")

    edge_risk = edge_risk_from_points(gn, pts, radius=RADIUS)
    n_risky = sum(1 for v in edge_risk.values() if v > 0)
    print(f"edges within {RADIUS:.0f} m of a risk point: {n_risky}")

    res = run_road_model(gn, n_trips=500, seed=1)
    exposure = risk_exposure(res["edge_load"], edge_risk)
    total = sum(exposure.values())
    top = sorted(exposure.values(), reverse=True)[:5]
    print(f"trips {res['reached']}/{res['n_trips']}; total risk-exposure {total}; top edges {top}")

    out = Path(__file__).parent / "real_risk_exposure.png"
    render_network(gn, exposure, out)
    print(f"map -> {out}  ({time.time() - t0:.1f}s total)")


if __name__ == "__main__":
    main()
