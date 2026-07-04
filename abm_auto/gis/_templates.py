"""GIS codegen templates: render a GISModelSpec to runnable model code.

Deterministic (no LLM). Generated code imports only from abm_auto.gis and calls
into the GIS runtime (RasterSpace / GeoNetwork) — codegen emits *calls*, not physics.
"""
from __future__ import annotations

from abm_auto.gis._capabilities import resolve_capability
from abm_auto.gis._model_spec import GISModelSpec

_RASTER = '''"""Generated GIS model — raster {mechanism}."""
import numpy as np
from affine import Affine

from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._sir import run_raster_sir
from abm_auto.gis._gate import spatial_spread_gate
{io_import}

def build_space():
{build_body}

def main():
    sp = build_space()
    res = run_raster_sir(sp, seed={seed}, steps={steps})
    ok, desc = spatial_spread_gate(res, sp.field.data)
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''

_RASTER_SYNTH = '''    n = 24
    yy, xx = np.mgrid[0:n, 0:n]
    d = np.exp(-(((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / (2 * (n / 5) ** 2)))
    transform = Affine(100, 0, 0, 0, -100, n * 100)
    return RasterSpace(RasterField(data=d, transform=transform, crs="EPSG:3857"))'''

_NETWORK = '''"""Generated GIS model — network {mechanism}."""
import geopandas as gpd
import networkx as nx

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._road_model import run_road_model
from abm_auto.gis._geo_gate import geo_network_gate

DATA = {data_path!r}
CRS = {crs!r}

def main():
    gdf = gpd.read_file(DATA).to_crs(CRS).explode(index_parts=False)
    lines = [g for g in gdf.geometry if g is not None and g.geom_type == "LineString"]
    gn = GeoNetwork.from_lines(lines, crs=CRS, snap_tol=2.0)
    gn.graph = gn.graph.subgraph(max(nx.connected_components(gn.graph), key=len)).copy()
    res = run_road_model(gn, n_trips={n_trips}, seed={seed})
    ok, desc = geo_network_gate(res, gn)
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''

_FLOOD = '''"""Generated GIS model - coupled flood evacuation."""
import numpy as np
from affine import Affine
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._flood_model import run_flood_evacuation
from abm_auto.gis._flood_gate import flood_gate

THRESHOLD = {threshold}

def build_layers():
    lines = [
        LineString([(0, 0), (0, 400)]),
        LineString([(0, 0), (200, 0)]),
        LineString([(200, 0), (200, 400)]),
        LineString([(200, 400), (0, 400)]),
    ]
    geonet = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    flood_data = np.zeros((5, 5), dtype=float)
    flood_data[2, 0] = 5.0
    flood = RasterSpace(RasterField(
        data=flood_data,
        transform=Affine(100, 0, 0, 0, -100, 500),
        crs="EPSG:3857",
    ))
    agent = geonet.nearest_node(0, 0)
    safe = geonet.nearest_node(0, 400)
    return geonet, flood, [safe], [agent]

def main():
    geonet, flood, safe_nodes, agent_nodes = build_layers()
    run_flood_evacuation(
        geonet,
        flood,
        THRESHOLD,
        safe_nodes=safe_nodes,
        agent_nodes=agent_nodes,
    )
    ok, desc = flood_gate(
        geonet,
        flood,
        safe_nodes=safe_nodes,
        agent_nodes=agent_nodes,
        thresholds=[100.0, THRESHOLD],
    )
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''

_SOCIAL_SPATIAL = '''"""Generated GIS model - social-spatial contagion."""
import networkx as nx

from abm_auto.gis._coupling import combined_neighbors
from abm_auto.gis._social import run_contagion, social_lift_gate

N_AGENTS = {n_agents}
SIDE = {side}
BETA = {beta}
STEPS = {steps}
SEED = {seed}

def grid_neighbors(side):
    def neighbors_of(i):
        row, col = divmod(i, side)
        out = []
        for d_row, d_col in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = row + d_row, col + d_col
            if 0 <= rr < side and 0 <= cc < side:
                out.append(rr * side + cc)
        return out
    return neighbors_of

def build_layers():
    spatial_neighbors_of = grid_neighbors(SIDE)
    social_graph = nx.watts_strogatz_graph(N_AGENTS, 4, 0.3, seed=SEED)
    combined_neighbors(0, spatial_neighbors_of, social_graph)
    return spatial_neighbors_of, social_graph

def main():
    spatial_neighbors_of, social_graph = build_layers()
    run_contagion(
        N_AGENTS,
        spatial_neighbors_of,
        social_graph,
        beta=BETA,
        steps=STEPS,
        seed=SEED,
    )
    ok, desc = social_lift_gate(
        N_AGENTS,
        spatial_neighbors_of,
        social_graph,
        beta=BETA,
        steps=STEPS,
        seed=SEED,
    )
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''

_POINT_NETWORK_RISK = '''"""Generated GIS model - point-network risk."""
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._point_space import PointSpace
from abm_auto.gis._coupling import point_risk_per_edge
from abm_auto.gis._risk import risk_exposure
from abm_auto.gis._space_zoo_gate import point_network_risk_gate

RADIUS = {radius}

def build_layers():
    lines = [
        LineString([(0, 0), (100, 0)]),
        LineString([(100, 0), (100, 100)]),
    ]
    geonet = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    points = PointSpace.from_coords([(50, 5), (1000, 1000)], crs="EPSG:3857")
    risky = tuple(sorted((geonet.nearest_node(0, 0), geonet.nearest_node(100, 0))))
    dry = tuple(sorted((geonet.nearest_node(100, 0), geonet.nearest_node(100, 100))))
    edge_load = {{risky: 4, dry: 7}}
    return geonet, points, edge_load

def main():
    geonet, points, edge_load = build_layers()
    edge_risk = point_risk_per_edge(geonet, points, RADIUS)
    risk_exposure(edge_load, edge_risk)
    ok, desc = point_network_risk_gate(
        geonet,
        points,
        radius=RADIUS,
        edge_load=edge_load,
    )
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''

_POLYGON_POINT_ZONING = '''"""Generated GIS model - polygon-point zoning."""
from shapely.geometry import Polygon

from abm_auto.gis._point_space import PointSpace
from abm_auto.gis._polygon_space import PolygonSpace
from abm_auto.gis._coupling import assign_points_to_polygons
from abm_auto.gis._space_zoo_gate import polygon_point_zoning_gate

def build_layers():
    west = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    east = Polygon([(10, 0), (20, 0), (20, 10), (10, 10)])
    polygons = PolygonSpace.from_polygons(
        [west, east],
        crs="EPSG:3857",
        ids=["west", "east"],
    )
    points = PointSpace.from_coords([(5, 5), (15, 5), (50, 50)], crs="EPSG:3857")
    expected = {"west": [0], "east": [1]}
    return points, polygons, expected

def main():
    points, polygons, expected = build_layers()
    assign_points_to_polygons(points, polygons)
    ok, desc = polygon_point_zoning_gate(
        points,
        polygons,
        expected=expected,
    )
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''

_RASTER_SPATIAL_VALIDATION = '''"""Generated GIS model - raster spatial validation."""
import numpy as np

from abm_auto.gis._spatial_validation import (
    raster_pattern_metrics,
    raster_spatial_loss,
    raster_validation_gate,
)

def _cluster(top, left, size=2, shape=(6, 6)):
    raster = np.zeros(shape, dtype=float)
    raster[top:top + size, left:left + size] = 1.0
    return raster

def main():
    observed = _cluster(2, 2)
    simulated = observed.copy()
    metrics = raster_pattern_metrics(simulated, observed)
    raster_spatial_loss(metrics)
    ok, desc = raster_validation_gate(simulated, observed)
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''

_RASTER_SPATIAL_CALIBRATION = '''"""Generated GIS model - raster spatial calibration."""
import numpy as np

from abm_auto.gis._spatial_calibration import (
    grid_search_raster_calibration,
    raster_spatial_calibration_gate,
)
from abm_auto.gis._spatial_validation import raster_spatial_loss

def _cluster(top, left, size=2, shape=(6, 6)):
    raster = np.zeros(shape, dtype=float)
    raster[top:top + size, left:left + size] = 1.0
    return raster

def _location_simulator(params):
    return _cluster(int(params["row"]), int(params["col"]))

def main():
    observed = _cluster(2, 3)
    result = grid_search_raster_calibration(
        _location_simulator,
        observed,
        {"row": [0.0, 2.0], "col": [0.0, 3.0]},
    )
    raster_spatial_loss(result["best_metrics"])
    ok, desc = raster_spatial_calibration_gate()
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''

_RASTER_SPATIAL_CALIBRATION_MANIFEST = '''"""Generated GIS model - manifest-backed raster spatial calibration."""
import numpy as np

from abm_auto.gis._observed_raster_repro import (
    calibrate_observed_raster_from_manifest,
    observed_raster_repro_gate,
)
from abm_auto.gis._spatial_validation import raster_spatial_loss

MANIFEST_PATH = {manifest_path!r}

def _cluster(top, left, size=2, shape=(6, 6)):
    raster = np.zeros(shape, dtype=float)
    raster[top:top + size, left:left + size] = 1.0
    return raster

def _location_simulator(params):
    return _cluster(int(params["row"]), int(params["col"]))

def main():
    result = calibrate_observed_raster_from_manifest(
        _location_simulator,
        MANIFEST_PATH,
    )
    raster_spatial_loss(result["best_metrics"])
    ok, desc = observed_raster_repro_gate(MANIFEST_PATH)
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''

_MECHANISM_THRESHOLD_ADOPTION = '''"""Generated GIS model - threshold adoption mechanism."""
from abm_auto.gis._mechanisms import (
    mechanism_space_gate,
    run_threshold_adoption,
)

N_AGENTS = {n_agents}
THRESHOLD = {threshold}
STEPS = {steps}

def _chain_neighbors(n_agents):
    def neighbors_of(i):
        out = []
        if i > 0:
            out.append(i - 1)
        if i < n_agents - 1:
            out.append(i + 1)
        return out
    return neighbors_of

def main():
    neighbors_of = _chain_neighbors(N_AGENTS)
    run_threshold_adoption(
        N_AGENTS,
        neighbors_of,
        threshold=THRESHOLD,
        steps=STEPS,
        seeds=(0,),
    )
    ok, desc = mechanism_space_gate(
        connected_neighbors_of=neighbors_of,
        n_agents=N_AGENTS,
        threshold=THRESHOLD,
        steps=STEPS,
        seeds=(0,),
    )
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''

_MECHANISM_CONTAGION = '''"""Generated GIS model - contagion mechanism."""
from abm_auto.gis._mechanisms import (
    mechanism_contagion_gate,
    run_contagion,
)

N_AGENTS = {n_agents}
BETA = {beta}
STEPS = {steps}
SEED = {seed}
INITIAL_INFECTED = 0

def _chain_neighbors(n_agents):
    def neighbors_of(i):
        out = []
        if i > 0:
            out.append(i - 1)
        if i < n_agents - 1:
            out.append(i + 1)
        return out
    return neighbors_of

def main():
    neighbors_of = _chain_neighbors(N_AGENTS)
    run_contagion(
        N_AGENTS,
        neighbors_of,
        beta=BETA,
        steps=STEPS,
        seed=SEED,
        seeds=(INITIAL_INFECTED,),
    )
    ok, desc = mechanism_contagion_gate(
        connected_neighbors_of=neighbors_of,
        n_agents=N_AGENTS,
        beta=BETA,
        steps=STEPS,
        seed=SEED,
        seeds=(INITIAL_INFECTED,),
    )
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''

_TEMPORAL_FLOOD = '''"""Generated GIS model - temporal flood evacuation."""
import numpy as np
from affine import Affine
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._temporal import RasterTimeline
from abm_auto.gis._flood_model import run_temporal_flood_evacuation
from abm_auto.gis._flood_gate import temporal_flood_gate

THRESHOLD = {threshold}

def build_layers():
    lines = [
        LineString([(0, 0), (0, 400)]),
        LineString([(0, 0), (200, 0)]),
        LineString([(200, 0), (200, 400)]),
        LineString([(200, 400), (0, 400)]),
    ]
    geonet = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    transform = Affine(100, 0, 0, 0, -100, 500)

    def raster(data):
        return RasterSpace(RasterField(
            data=np.array(data, dtype=float),
            transform=transform,
            crs="EPSG:3857",
        ))

    dry = np.zeros((5, 5), dtype=float)
    flooded = np.zeros((5, 5), dtype=float)
    flooded[2, 0] = 5.0
    receded = np.zeros((5, 5), dtype=float)
    flood_timeline = RasterTimeline.from_frames([
        raster(dry),
        raster(flooded),
        raster(receded),
    ])
    agent = geonet.nearest_node(0, 0)
    safe = geonet.nearest_node(0, 400)
    return geonet, flood_timeline, [safe], [agent]

def main():
    geonet, flood_timeline, safe_nodes, agent_nodes = build_layers()
    run_temporal_flood_evacuation(
        geonet,
        flood_timeline,
        THRESHOLD,
        safe_nodes=safe_nodes,
        agent_nodes=agent_nodes,
    )
    ok, desc = temporal_flood_gate(
        geonet,
        flood_timeline,
        safe_nodes=safe_nodes,
        agent_nodes=agent_nodes,
        threshold=THRESHOLD,
    )
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''

_DYNAMIC_FLOOD = '''"""Generated GIS model - dynamic flood evacuation."""
import numpy as np
from affine import Affine
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._temporal import RasterTimeline
from abm_auto.gis._dynamic_flood import run_dynamic_flood_evacuation
from abm_auto.gis._flood_gate import dynamic_flood_reroute_gate

THRESHOLD = {threshold}

def build_layers():
    lines = [
        LineString([(0, 0), (0, 100)]),
        LineString([(0, 100), (0, 200)]),
        LineString([(0, 200), (200, 200)]),
        LineString([(0, 100), (300, 100)]),
        LineString([(300, 100), (300, 200)]),
        LineString([(300, 200), (200, 200)]),
    ]
    geonet = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    transform = Affine(100, 0, 0, 0, -100, 500)

    def raster(data):
        return RasterSpace(RasterField(
            data=np.array(data, dtype=float),
            transform=transform,
            crs="EPSG:3857",
        ))

    dry = np.zeros((5, 5), dtype=float)
    flooded_direct = np.zeros((5, 5), dtype=float)
    flooded_direct[3, 0] = 5.0
    flood_timeline = RasterTimeline.from_frames([
        raster(dry),
        raster(flooded_direct),
        raster(flooded_direct),
        raster(flooded_direct),
        raster(flooded_direct),
        raster(flooded_direct),
    ])
    agent = geonet.nearest_node(0, 0)
    safe = geonet.nearest_node(200, 200)
    return geonet, flood_timeline, [safe], [agent]

def main():
    geonet, flood_timeline, safe_nodes, agent_nodes = build_layers()
    run_dynamic_flood_evacuation(
        geonet,
        flood_timeline,
        THRESHOLD,
        safe_nodes=safe_nodes,
        agent_nodes=agent_nodes,
        reroute=True,
    )
    ok, desc = dynamic_flood_reroute_gate(
        geonet,
        flood_timeline,
        safe_nodes=safe_nodes,
        agent_nodes=agent_nodes,
        threshold=THRESHOLD,
    )
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''

_DYNAMIC_CONGESTION = '''"""Generated GIS model - dynamic congestion routing."""
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._dynamic_congestion import run_dynamic_congestion_routing
from abm_auto.gis._congestion_gate import dynamic_congestion_reroute_gate

N_STEPS = {n_steps}
SPEED_M_PER_TICK = {speed_m_per_tick}
CONGESTION_ALPHA = {congestion_alpha}

def build_layers():
    lines = [
        LineString([(0, 0), (100, 0)]),
        LineString([(100, 0), (200, 0)]),
        LineString([(200, 0), (300, 0)]),
        LineString([(0, 0), (100, -100)]),
        LineString([(100, -100), (200, -100)]),
        LineString([(200, -100), (300, 0)]),
    ]
    geonet = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    leader = geonet.nearest_node(100, 0)
    follower = geonet.nearest_node(0, 0)
    safe = geonet.nearest_node(300, 0)
    return geonet, [safe], [leader, leader, follower]

def main():
    geonet, safe_nodes, agent_nodes = build_layers()
    run_dynamic_congestion_routing(
        geonet,
        safe_nodes=safe_nodes,
        agent_nodes=agent_nodes,
        n_steps=N_STEPS,
        speed_m_per_tick=SPEED_M_PER_TICK,
        congestion_alpha=CONGESTION_ALPHA,
        reroute=True,
    )
    ok, desc = dynamic_congestion_reroute_gate(
        geonet,
        safe_nodes=safe_nodes,
        agent_nodes=agent_nodes,
        n_steps=N_STEPS,
        speed_m_per_tick=SPEED_M_PER_TICK,
        congestion_alpha=CONGESTION_ALPHA,
    )
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''

_DYNAMIC_INCIDENT = '''"""Generated GIS model - dynamic incident routing."""
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._dynamic_incident import run_dynamic_incident_routing
from abm_auto.gis._incident_gate import dynamic_incident_reroute_gate

N_STEPS = {n_steps}
SPEED_M_PER_TICK = {speed_m_per_tick}

def build_layers():
    lines = [
        LineString([(0, 0), (100, 0)]),
        LineString([(100, 0), (200, 0)]),
        LineString([(0, 0), (0, 100)]),
        LineString([(0, 100), (200, 0)]),
    ]
    geonet = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    start = geonet.nearest_node(0, 0)
    bottleneck = geonet.nearest_node(100, 0)
    safe = geonet.nearest_node(200, 0)
    incidents = [{{"t": 1, "edge": (bottleneck, safe), "closed": True}}]
    return geonet, [safe], [start], incidents

def main():
    geonet, safe_nodes, agent_nodes, incidents = build_layers()
    run_dynamic_incident_routing(
        geonet,
        safe_nodes=safe_nodes,
        agent_nodes=agent_nodes,
        incidents=incidents,
        n_steps=N_STEPS,
        speed_m_per_tick=SPEED_M_PER_TICK,
        reroute=True,
    )
    ok, desc = dynamic_incident_reroute_gate(
        geonet,
        safe_nodes=safe_nodes,
        agent_nodes=agent_nodes,
        incidents=incidents,
        n_steps=N_STEPS,
        speed_m_per_tick=SPEED_M_PER_TICK,
    )
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''


_TERRAIN_NETWORK_COST = '''"""Generated GIS model - terrain-network edge cost."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from shapely.geometry import LineString

from abm_auto.gis._coupling import (
    terrain_cost_per_edge,
    terrain_network_coupling_gate,
)
from abm_auto.gis._geo_network import GeoNetwork

HEIGHTFIELD = "1 2 3\\n2 3 4\\n3 4 5\\n"
GRADE_WEIGHT = {grade_weight}
N_SAMPLES = {n_samples}
THRESHOLD = {threshold}

def build_manifest(tmpdir):
    terrain_path = Path(tmpdir) / "terrain.asc"
    terrain_path.write_text(HEIGHTFIELD, encoding="utf-8")
    return {{
        "schema": "abm-auto/terrain-bridge-manifest/v1",
        "manifest_id": "generated-terrain-network-cost",
        "title": "Generated terrain-network cost fixture",
        "boundary_note": (
            "This terrain bridge manifest is not a 3D renderer and not a "
            "physical simulation certificate."
        ),
        "boundary_rules": {{
            "no_3d_renderer_claim": "The template records a heightfield contract and renders nothing.",
            "no_physical_solver_claim": "The template runs no hydrology, erosion, collision, or terrain solver.",
            "no_real_world_accuracy_claim": "The heightfield is synthetic and has no real-world terrain accuracy claim.",
            "vertical_units_declared": "Vertical units are explicit for downstream consumers.",
        }},
        "consumers": [
            {{
                "id": "gisabm",
                "domain": "gisabm",
                "role": "terrain-network cost consumer",
                "boundary_note": "Consumes a synthetic heightfield contract only.",
            }}
        ],
        "coordinate_frame": {{
            "crs": "EPSG:3857",
            "grid_shape": [3, 3],
            "extent": [0.0, 0.0, 3.0, 3.0],
            "horizontal_units": "metre",
            "vertical_units": "metre",
            "vertical_datum": "synthetic-local",
        }},
        "terrain_source": {{
            "kind": "ascii_heightfield",
            "path": "terrain.asc",
            "provenance": "Synthetic 3x3 monotone heightfield generated by GIS codegen.",
            "sha256": hashlib.sha256(HEIGHTFIELD.encode("utf-8")).hexdigest(),
            "synthetic": True,
        }},
        "verification": {{
            "expected_result": "PASS",
            "gate_command": "python main.py",
            "non_claims": [
                "does not render 3D scenes",
                "does not build meshes",
                "does not run physical terrain solvers",
                "does not claim real-world terrain accuracy",
            ],
        }},
    }}

def build_network():
    return GeoNetwork.from_lines(
        [
            LineString([(0.25, 0.25), (0.75, 0.25)]),
            LineString([(0.25, 0.25), (2.75, 2.75)]),
        ],
        crs="EPSG:3857",
        snap_tol=0.01,
    )

def main():
    geonet = build_network()
    with TemporaryDirectory() as tmpdir:
        manifest = build_manifest(tmpdir)
        costs = terrain_cost_per_edge(
            geonet,
            manifest,
            repo=tmpdir,
            n_samples=N_SAMPLES,
            grade_weight=GRADE_WEIGHT,
        )
        if not costs:
            raise RuntimeError("terrain cost template produced no edge costs")
        ok, desc = terrain_network_coupling_gate(
            geonet,
            manifest,
            repo=tmpdir,
            threshold=THRESHOLD,
        )
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''


_TERRAIN_AWARE_ROUTING = '''"""Generated GIS model - terrain-aware routing."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from shapely.geometry import LineString

from abm_auto.gis._coupling import (
    terrain_aware_routing_gate,
    terrain_aware_shortest_path,
)
from abm_auto.gis._geo_network import GeoNetwork

HEIGHTFIELD = "0 0 0\\n0 10 0\\n0 0 0\\n"
GRADE_WEIGHT = {grade_weight}
N_SAMPLES = {n_samples}

def build_manifest(tmpdir):
    terrain_path = Path(tmpdir) / "terrain.asc"
    terrain_path.write_text(HEIGHTFIELD, encoding="utf-8")
    return {{
        "schema": "abm-auto/terrain-bridge-manifest/v1",
        "manifest_id": "generated-terrain-aware-routing",
        "title": "Generated terrain-aware routing fixture",
        "boundary_note": (
            "This terrain bridge manifest is not a 3D renderer and not a "
            "physical simulation certificate."
        ),
        "boundary_rules": {{
            "no_3d_renderer_claim": "The template records a heightfield contract and renders nothing.",
            "no_physical_solver_claim": "The template runs no hydrology, erosion, collision, or terrain solver.",
            "no_real_world_accuracy_claim": "The heightfield is synthetic and has no real-world terrain accuracy claim.",
            "vertical_units_declared": "Vertical units are explicit for downstream consumers.",
        }},
        "consumers": [
            {{
                "id": "gisabm",
                "domain": "gisabm",
                "role": "terrain-aware route-choice consumer",
                "boundary_note": "Consumes a synthetic heightfield contract only.",
            }}
        ],
        "coordinate_frame": {{
            "crs": "EPSG:3857",
            "grid_shape": [3, 3],
            "extent": [0.0, 0.0, 3.0, 3.0],
            "horizontal_units": "metre",
            "vertical_units": "metre",
            "vertical_datum": "synthetic-local",
        }},
        "terrain_source": {{
            "kind": "ascii_heightfield",
            "path": "terrain.asc",
            "provenance": "Synthetic 3x3 heightfield generated by GIS codegen.",
            "sha256": hashlib.sha256(HEIGHTFIELD.encode("utf-8")).hexdigest(),
            "synthetic": True,
        }},
        "verification": {{
            "expected_result": "PASS",
            "gate_command": "python main.py",
            "non_claims": [
                "does not render 3D scenes",
                "does not build meshes",
                "does not run physical terrain solvers",
                "does not claim real-world terrain accuracy",
            ],
        }},
    }}

def build_network():
    return GeoNetwork.from_lines(
        [
            LineString([(0.25, 0.25), (1.5, 1.5)]),
            LineString([(1.5, 1.5), (2.75, 2.75)]),
            LineString([(0.25, 0.25), (0.25, 2.75)]),
            LineString([(0.25, 2.75), (2.75, 2.75)]),
        ],
        crs="EPSG:3857",
        snap_tol=0.01,
    )

def main():
    geonet = build_network()
    source = geonet.nearest_node(0.25, 0.25)
    target = geonet.nearest_node(2.75, 2.75)
    with TemporaryDirectory() as tmpdir:
        manifest = build_manifest(tmpdir)
        terrain_aware_shortest_path(
            geonet,
            manifest,
            source,
            target,
            repo=tmpdir,
            n_samples=N_SAMPLES,
            grade_weight=GRADE_WEIGHT,
        )
        ok, desc = terrain_aware_routing_gate(
            geonet,
            manifest,
            source,
            target,
            repo=tmpdir,
            n_samples=N_SAMPLES,
            grade_weight=GRADE_WEIGHT,
        )
    print(("PASS" if ok else "FAIL") + ": " + desc)

if __name__ == "__main__":
    main()
'''


# ── NetLogo gis-extension parity templates ────────────────────────────────

_TOPOLOGY_CLIP = '''"""Generated GIS model - line x polygon clip (NetLogo parity)."""
from shapely.geometry import LineString, box

from abm_auto.gis._coupling import line_polygon_gate, lines_in_polygon


def main():
    poly = box(0, 0, 10, 10)
    inside = [LineString([(1, 1), (1, 9)])]                     # length 8 inside
    outside = [LineString([(20, 0), (30, 0)])]                  # entirely outside
    ok, desc = line_polygon_gate(inside, outside, poly)
    print(("PASS" if ok else "FAIL") + ": " + desc)


if __name__ == "__main__":
    main()
'''

_RASTER_FOCAL = '''"""Generated GIS model - raster focal smoothing (NetLogo parity)."""
import numpy as np
from affine import Affine

from abm_auto.gis._focal import convolve, focal_gate
from abm_auto.gis._raster_space import RasterField


def main():
    rng = np.random.default_rng({seed})
    data = rng.normal(size=({rows}, {cols}))
    field = RasterField(data=data,
                        transform=Affine(100.0, 0, 0, 0, -100.0, {rows} * 100),
                        crs="EPSG:3857")
    kernel = np.full((3, 3), 1.0 / 9.0)
    smoothed = convolve(field, kernel)
    ok, desc = focal_gate(field)
    print(("PASS" if ok else "FAIL") + ": " + desc
          + f" (smoothed variance={{float(np.var(smoothed.data)):.4f}})")


if __name__ == "__main__":
    main()
'''

_RASTER_COVERAGE = '''"""Generated GIS model - areal coverage (NetLogo parity)."""
import numpy as np
from affine import Affine
from shapely.geometry import box

from abm_auto.gis._coverage import apply_coverage, apply_coverage_gate
from abm_auto.gis._raster_space import RasterField


def main():
    h, w = {rows}, {cols}
    template = RasterField(data=np.zeros((h, w), dtype=float),
                           transform=Affine(100.0, 0, 0, 0, -100.0, h * 100.0),
                           crs="EPSG:3857")
    # left-half / right-half polygons over the template envelope
    left = box(0, 0, w * 50.0, h * 100.0)
    right = box(w * 50.0, 0, w * 100.0, h * 100.0)
    raster = apply_coverage([left, right], [1.0, 9.0], template)
    ok, desc = apply_coverage_gate([], [], template)
    print(("PASS" if ok else "FAIL") + ": " + desc
          + f" (sample mean={{float(raster.data.mean()):.2f}})")


if __name__ == "__main__":
    main()
'''

_PLATFORM_ABM = '''"""Generated GIS model - platform ABM (GISAgent / GISModel, ADR-020)."""
from abm_auto.gis._platform import DataCollector, GISAgent, GISModel


class DiffuseAgent(GISAgent):
    def __init__(self, agent_id, model, value):
        super().__init__(agent_id, model)
        self.value = value

    def step(self):
        m = self.model
        nbrs = [m.agents_by_id[j] for j in (self.id - 1, self.id + 1)
                if 0 <= j < len(m.agents_by_id)]
        if nbrs:
            self.value = (self.value + sum(a.value for a in nbrs)) / (1 + len(nbrs))


class DiffuseModel(GISModel):
    def __init__(self, n={n}, seed={seed}):
        super().__init__(seed=seed)
        self.agents_by_id = []
        for i in range(n):
            a = DiffuseAgent(i, self, value=(100.0 if i == 0 else 0.0))
            self.agents_by_id.append(a)
            self.add_agent(a)
        self.reporter = DataCollector(
            {{"spread": lambda m: sum(1 for a in m.agents_by_id if a.value > 0.01)}}
        )


def main():
    series = [r["spread"] for r in DiffuseModel().run({n})]
    ok = series[-1] > series[0] and all(
        series[i] <= series[i + 1] for i in range(len(series) - 1)
    )
    print(("PASS" if ok else "FAIL") + ": diffusion spread "
          + str(series[0]) + " -> " + str(series[-1]))


if __name__ == "__main__":
    main()
'''


def render(spec: GISModelSpec) -> dict:
    """Render a validated spec to a dict of {filename: source}."""
    spec.validate()
    cap = resolve_capability(spec.spatial_type, spec.mechanism, spec.capability)
    if not cap.renderable:
        raise ValueError(
            f"capability {cap.key!r} is registered but not codegen-renderable"
        )

    if cap.key == "raster_sir":
        if spec.data_path:
            io_import = "from abm_auto.gis._io import load_raster"
            build_body = f'    return RasterSpace(load_raster({spec.data_path!r}))'
        else:
            io_import = ""
            build_body = _RASTER_SYNTH
        code = _RASTER.format(
            mechanism=spec.mechanism, io_import=io_import, build_body=build_body,
            seed=spec.seed, steps=spec.params.get("steps", 60))
        return {"main.py": code}

    if cap.key == "flood_evacuation":
        code = _FLOOD.format(threshold=float(spec.params.get("threshold", 1.0)))
        return {"main.py": code}

    if cap.key == "social_spatial_contagion":
        code = _SOCIAL_SPATIAL.format(
            n_agents=int(spec.params.get("n_agents", 100)),
            side=int(spec.params.get("side", 10)),
            beta=float(spec.params.get("beta", 0.2)),
            steps=int(spec.params.get("steps", 6)),
            seed=spec.seed,
        )
        return {"main.py": code}

    if cap.key == "point_network_risk":
        code = _POINT_NETWORK_RISK.format(
            radius=float(spec.params.get("radius", 10.0))
        )
        return {"main.py": code}

    if cap.key == "polygon_point_zoning":
        return {"main.py": _POLYGON_POINT_ZONING}

    if cap.key == "raster_spatial_validation":
        return {"main.py": _RASTER_SPATIAL_VALIDATION}

    if cap.key == "raster_spatial_calibration":
        if spec.data_path:
            return {"main.py": _RASTER_SPATIAL_CALIBRATION_MANIFEST.format(
                manifest_path=spec.data_path
            )}
        return {"main.py": _RASTER_SPATIAL_CALIBRATION}

    if cap.key == "mechanism_threshold_adoption":
        code = _MECHANISM_THRESHOLD_ADOPTION.format(
            n_agents=int(spec.params.get("n_agents", 8)),
            threshold=int(spec.params.get("threshold", 1)),
            steps=int(spec.params.get("steps", 7)),
        )
        return {"main.py": code}

    if cap.key == "mechanism_contagion":
        code = _MECHANISM_CONTAGION.format(
            n_agents=int(spec.params.get("n_agents", 8)),
            beta=float(spec.params.get("beta", 1.0)),
            steps=int(spec.params.get("steps", 7)),
            seed=spec.seed,
        )
        return {"main.py": code}

    if cap.key == "temporal_flood_evacuation":
        code = _TEMPORAL_FLOOD.format(
            threshold=float(spec.params.get("threshold", 1.0))
        )
        return {"main.py": code}

    if cap.key == "dynamic_flood_evacuation":
        code = _DYNAMIC_FLOOD.format(
            threshold=float(spec.params.get("threshold", 1.0))
        )
        return {"main.py": code}

    if cap.key == "dynamic_congestion_routing":
        code = _DYNAMIC_CONGESTION.format(
            n_steps=int(spec.params.get("n_steps", 8)),
            speed_m_per_tick=float(spec.params.get("speed_m_per_tick", 100.0)),
            congestion_alpha=float(spec.params.get("congestion_alpha", 3.0)),
        )
        return {"main.py": code}

    if cap.key == "dynamic_incident_routing":
        code = _DYNAMIC_INCIDENT.format(
            n_steps=int(spec.params.get("n_steps", 6)),
            speed_m_per_tick=float(spec.params.get("speed_m_per_tick", 100.0)),
        )
        return {"main.py": code}

    if cap.key == "terrain_network_cost":
        code = _TERRAIN_NETWORK_COST.format(
            grade_weight=float(spec.params.get("grade_weight", 1.0)),
            n_samples=int(spec.params.get("n_samples", 5)),
            threshold=float(spec.params.get("threshold", 0.01)),
        )
        return {"main.py": code}

    if cap.key == "terrain_aware_routing":
        code = _TERRAIN_AWARE_ROUTING.format(
            grade_weight=float(spec.params.get("grade_weight", 0.25)),
            n_samples=int(spec.params.get("n_samples", 5)),
        )
        return {"main.py": code}

    if cap.key == "topology_clip":
        return {"main.py": _TOPOLOGY_CLIP}

    if cap.key == "raster_focal":
        code = _RASTER_FOCAL.format(
            rows=int(spec.params.get("rows", 15)),
            cols=int(spec.params.get("cols", 15)),
            seed=spec.seed,
        )
        return {"main.py": code}

    if cap.key == "raster_coverage":
        code = _RASTER_COVERAGE.format(
            rows=int(spec.params.get("rows", 4)),
            cols=int(spec.params.get("cols", 4)),
        )
        return {"main.py": code}

    if cap.key == "gis_abm_platform":
        code = _PLATFORM_ABM.format(
            n=int(spec.params.get("n", 12)),
            seed=spec.seed,
        )
        return {"main.py": code}

    # network_routing_load
    code = _NETWORK.format(
        mechanism=spec.mechanism, data_path=spec.data_path,
        crs=spec.params.get("crs", "EPSG:27700"),
        n_trips=spec.params.get("n_trips", 300), seed=spec.seed)
    return {"main.py": code}
