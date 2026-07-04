"""Path B: run the GeoNetwork foundation on the user's REAL road network.

Proves real data runs end-to-end on the framework. This is an ORIGINATION demo
on the user's own data — NOT a paper reproduction. Reads from an external path
(the road data is large and is NOT committed to the repo).

Note on CRS: the data declares EPSG:4326 (lon/lat). For a self-contained model
this is fine even if the coordinates are actually GCJ-02 — the geometry is
internally consistent. We reproject to a projected metric CRS for distances.
(Only overlaying with true-WGS-84 basemaps would need the GCJ-02 correction.)
"""
import sys
import time
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

ROADS = os.environ.get("GIS_ROADS_PATH")
METRIC_CRS = "EPSG:32650"  # UTM zone 50N (Beijing area), metres


def main():
    import geopandas as gpd
    import networkx as nx
    from abm_auto.gis._geo_network import GeoNetwork
    from abm_auto.gis._road_model import run_road_model
    from abm_auto.gis._geo_viz import render_network

    if not ROADS:
        raise SystemExit("Set GIS_ROADS_PATH to a road-network shapefile before running this demo.")

    t0 = time.time()
    gdf = gpd.read_file(ROADS, encoding="gbk")
    declared = gdf.crs
    # the largest component is stored as one MultiLineString -> explode to segments
    gdf = gdf.to_crs(METRIC_CRS).explode(index_parts=False)
    lines = [g for g in gdf.geometry if g is not None and g.geom_type == "LineString"]
    print(f"loaded {len(lines)} road segments; declared CRS {declared} -> reprojected {METRIC_CRS}")

    gn = GeoNetwork.from_lines(lines, crs=METRIC_CRS, snap_tol=1.0)
    print(f"GeoNetwork: {gn.graph.number_of_nodes()} nodes, {gn.graph.number_of_edges()} edges "
          f"({time.time() - t0:.1f}s)")

    # route within the largest connected component (snapping can fragment)
    gcc_nodes = max(nx.connected_components(gn.graph), key=len)
    gn.graph = gn.graph.subgraph(gcc_nodes).copy()
    print(f"largest connected component: {gn.graph.number_of_nodes()} nodes")

    res = run_road_model(gn, n_trips=200, seed=1)
    print(f"road model: {res['reached']}/{res['n_trips']} trips reached; "
          f"total edge load {sum(res['edge_load'].values())}")

    out = Path(__file__).parent / "real_road_load.png"
    render_network(gn, res["edge_load"], out)
    print(f"map -> {out}  ({time.time() - t0:.1f}s total)")


if __name__ == "__main__":
    main()
