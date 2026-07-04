"""Coupling operators between GIS space layers — the first operators of the
coupled multi-layer space seam (ADR-019).

flood_depth_per_edge couples a road GeoNetwork with a flood-depth RasterSpace:
for each road edge, the max flood depth sampled along the segment.
"""
from __future__ import annotations

from pathlib import Path

import networkx as nx
import numpy as np

from abm_auto.terrain_bridge import (
    load_terrain_bridge_manifest,
    validate_terrain_bridge_manifest,
)


def _edge_key(u, v) -> tuple:
    return tuple(sorted((u, v), key=repr))


def flood_depth_per_edge(geonet, flood, n_samples: int = 8) -> dict:
    """Max flood depth along each road edge.

    The network and the flood raster must be in the SAME CRS (the caller reprojects
    the raster to the network's CRS first). Out-of-bounds samples count as depth 0.
    Returns {(u, v) sorted: depth}.
    """
    g = geonet.graph
    ts = np.linspace(0.0, 1.0, n_samples)
    depths = {}
    for u, v in g.edges:
        x1, y1 = geonet.node_coord(u)
        x2, y2 = geonet.node_coord(v)
        maxd = 0.0
        for t in ts:
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            col, row = flood.world_to_cell(x, y)
            if 0 <= col < flood.width and 0 <= row < flood.height:
                d = flood.value_at(col, row)
                if d > maxd:
                    maxd = d
        depths[tuple(sorted((u, v)))] = maxd
    return depths


def _require_n_samples(n_samples: int) -> None:
    if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples < 2:
        raise ValueError("n_samples must be an integer >= 2")


def _terrain_repo(repo) -> Path:
    return Path.cwd().resolve() if repo is None else Path(repo).resolve()


def _terrain_grid_from_manifest(terrain_manifest: dict, repo=None) -> list[list[float]]:
    repo_root = _terrain_repo(repo)
    validation = validate_terrain_bridge_manifest(terrain_manifest, repo=repo_root)
    if not validation["ok"]:
        raise ValueError(f"invalid terrain bridge manifest: {validation['issues'][:3]}")

    source = terrain_manifest["terrain_source"]
    if source["kind"] != "ascii_heightfield":
        raise ValueError("terrain network coupling supports ascii_heightfield only")

    path = Path(source["path"])
    source_path = path if path.is_absolute() else repo_root / path
    rows: list[list[float]] = []
    for line_no, line in enumerate(source_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = [float(value) for value in stripped.split()]
        except ValueError as exc:
            raise ValueError(
                f"terrain_source ASCII row {line_no} contains a non-numeric value"
            ) from exc
        rows.append(row)

    if not rows or not rows[0]:
        raise ValueError("terrain_source ASCII heightfield is empty")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("terrain_source ASCII rows have inconsistent column counts")
    return rows


def _terrain_extent(terrain_manifest: dict) -> tuple[float, float, float, float]:
    frame = terrain_manifest.get("coordinate_frame", {})
    extent = frame.get("extent")
    if (
        not isinstance(extent, list)
        or len(extent) != 4
        or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in extent)
    ):
        raise ValueError("coordinate_frame.extent is required as [min_x, min_y, max_x, max_y]")
    min_x, min_y, max_x, max_y = (float(value) for value in extent)
    if min_x >= max_x or min_y >= max_y:
        raise ValueError("coordinate_frame.extent bounds must be increasing")
    return min_x, min_y, max_x, max_y


def _require_matching_terrain_crs(geonet, terrain_manifest: dict) -> None:
    terrain_crs = terrain_manifest.get("coordinate_frame", {}).get("crs")
    if geonet.crs != terrain_crs:
        raise ValueError("terrain CRS must match GeoNetwork CRS")


def _terrain_value_at_world(
    rows: list[list[float]],
    extent: tuple[float, float, float, float],
    x: float,
    y: float,
) -> float:
    min_x, min_y, max_x, max_y = extent
    if not (min_x <= x <= max_x and min_y <= y <= max_y):
        raise ValueError("terrain sample is outside extent")

    n_rows = len(rows)
    n_cols = len(rows[0])
    col = min(n_cols - 1, int(np.floor((x - min_x) / (max_x - min_x) * n_cols)))
    row = min(n_rows - 1, int(np.floor((y - min_y) / (max_y - min_y) * n_rows)))
    return rows[row][col]


def terrain_elevation_delta_per_edge(
    geonet,
    terrain_manifest: dict,
    *,
    repo=None,
    n_samples: int = 8,
) -> dict:
    """Elevation relief sampled along each GeoNetwork edge from a terrain manifest.

    This is a deterministic terrain×network coupling operator. It reads an
    ASCII heightfield through a terrain bridge manifest and returns
    `{edge_key: max(sampled elevation) - min(sampled elevation)}`.
    """
    _require_n_samples(n_samples)
    _require_matching_terrain_crs(geonet, terrain_manifest)
    rows = _terrain_grid_from_manifest(terrain_manifest, repo=repo)
    extent = _terrain_extent(terrain_manifest)
    ts = np.linspace(0.0, 1.0, n_samples)
    deltas = {}
    for u, v in geonet.graph.edges:
        x1, y1 = geonet.node_coord(u)
        x2, y2 = geonet.node_coord(v)
        samples = [
            _terrain_value_at_world(
                rows,
                extent,
                x1 + float(t) * (x2 - x1),
                y1 + float(t) * (y2 - y1),
            )
            for t in ts
        ]
        deltas[_edge_key(u, v)] = max(samples) - min(samples)
    return deltas


def terrain_grade_proxy_per_edge(
    geonet,
    terrain_manifest: dict,
    *,
    repo=None,
    n_samples: int = 8,
) -> dict:
    """Edge terrain relief divided by edge length.

    This is a simple coupling proxy, not a physical slope or engineering grade.
    """
    deltas = terrain_elevation_delta_per_edge(
        geonet,
        terrain_manifest,
        repo=repo,
        n_samples=n_samples,
    )
    grades = {}
    for u, v, attrs in geonet.graph.edges(data=True):
        length = float(attrs.get("length", 0.0))
        grades[_edge_key(u, v)] = 0.0 if length <= 0.0 else deltas[_edge_key(u, v)] / length
    return grades


def terrain_cost_per_edge(
    geonet,
    terrain_manifest: dict,
    *,
    repo=None,
    n_samples: int = 8,
    grade_weight: float = 1.0,
) -> dict:
    """Length-based edge cost with a deterministic terrain grade penalty."""
    if grade_weight < 0:
        raise ValueError("grade_weight must be non-negative")
    grades = terrain_grade_proxy_per_edge(
        geonet,
        terrain_manifest,
        repo=repo,
        n_samples=n_samples,
    )
    costs = {}
    for u, v, attrs in geonet.graph.edges(data=True):
        length = float(attrs.get("length", 0.0))
        costs[_edge_key(u, v)] = length * (1.0 + float(grade_weight) * grades[_edge_key(u, v)])
    return costs


def _require_distinct_existing_nodes(geonet, source, target) -> None:
    if source not in geonet.graph:
        raise ValueError("source node is not in GeoNetwork")
    if target not in geonet.graph:
        raise ValueError("target node is not in GeoNetwork")
    if source == target:
        raise ValueError("source and target must be distinct")


def _path_edge_pairs(path) -> list[tuple]:
    return list(zip(path, path[1:]))


def _path_attr_cost(graph, path, attr: str) -> float:
    return sum(float(graph.edges[u, v].get(attr, 0.0)) for u, v in _path_edge_pairs(path))


def _path_edge_cost(costs: dict, path) -> float:
    return sum(float(costs[_edge_key(u, v)]) for u, v in _path_edge_pairs(path))


def terrain_aware_shortest_path(
    geonet,
    terrain_manifest: dict,
    source,
    target,
    *,
    repo=None,
    n_samples: int = 8,
    grade_weight: float = 1.0,
) -> dict:
    """Compare length-only routing with terrain-cost routing."""
    _require_distinct_existing_nodes(geonet, source, target)
    edge_costs = terrain_cost_per_edge(
        geonet,
        terrain_manifest,
        repo=repo,
        n_samples=n_samples,
        grade_weight=grade_weight,
    )
    terrain_graph = geonet.graph.copy()
    for u, v in terrain_graph.edges:
        terrain_graph.edges[u, v]["terrain_cost"] = edge_costs[_edge_key(u, v)]

    try:
        length_path = nx.shortest_path(geonet.graph, source, target, weight="length")
        terrain_path = nx.shortest_path(terrain_graph, source, target, weight="terrain_cost")
    except nx.NetworkXNoPath as exc:
        raise ValueError("source and target are not connected") from exc

    return {
        "length_path": length_path,
        "terrain_path": terrain_path,
        "length_path_length_m": _path_attr_cost(geonet.graph, length_path, "length"),
        "length_path_terrain_cost": _path_edge_cost(edge_costs, length_path),
        "terrain_path_length_m": _path_attr_cost(geonet.graph, terrain_path, "length"),
        "terrain_path_cost": _path_edge_cost(edge_costs, terrain_path),
        "changed_path": length_path != terrain_path,
        "edge_costs": edge_costs,
    }


def terrain_aware_routing_gate(
    geonet,
    terrain_manifest: dict,
    source,
    target,
    *,
    repo=None,
    n_samples: int = 8,
    grade_weight: float = 1.0,
) -> tuple[bool, str]:
    """Gate proving terrain-derived edge cost can change shortest-path routing."""
    result = terrain_aware_shortest_path(
        geonet,
        terrain_manifest,
        source,
        target,
        repo=repo,
        n_samples=n_samples,
        grade_weight=grade_weight,
    )
    evidence = (
        f"length_path={result['length_path']} "
        f"terrain_path={result['terrain_path']} "
        f"length_path_terrain_cost={result['length_path_terrain_cost']:.6f} "
        f"terrain_path_cost={result['terrain_path_cost']:.6f}"
    )
    if not result["changed_path"]:
        return (
            False,
            "terrain did not change shortest-path routing; "
            "not traffic flow, vehicle dynamics, or 3D terrain physics; "
            f"{evidence}",
        )
    if result["terrain_path_cost"] >= result["length_path_terrain_cost"]:
        return (
            False,
            "terrain changed path but did not reduce terrain-weighted route cost; "
            "not traffic flow, vehicle dynamics, or 3D terrain physics; "
            f"{evidence}",
        )
    return (
        True,
        "terrain changes shortest-path routing; "
        "not traffic flow, vehicle dynamics, or 3D terrain physics; "
        f"{evidence}",
    )


def terrain_network_coupling_gate(
    geonet,
    terrain_manifest: dict,
    *,
    repo=None,
    threshold: float = 0.01,
) -> tuple[bool, str]:
    """Gate for terrain×network coupling.

    Passes when sampled terrain creates a positive edge-grade signal and changes
    deterministic network edge cost. This is not a 3D renderer or physical
    traffic model.
    """
    if threshold < 0:
        raise ValueError("threshold must be non-negative")

    grades = terrain_grade_proxy_per_edge(geonet, terrain_manifest, repo=repo)
    costs = terrain_cost_per_edge(geonet, terrain_manifest, repo=repo)
    max_grade = max(grades.values()) if grades else 0.0
    min_cost = min(costs.values()) if costs else 0.0
    max_cost = max(costs.values()) if costs else 0.0
    if max_grade <= threshold:
        return (
            False,
            f"terrain network coupling gate failed: no terrain grade above threshold "
            f"(max_grade={max_grade:.6f}, threshold={threshold:.6f}); "
            "not a 3D renderer or physical traffic model",
        )
    if max_cost <= min_cost:
        return (
            False,
            f"terrain network coupling gate failed: terrain cost range did not change "
            f"(min_cost={min_cost:.6f}, max_cost={max_cost:.6f}); "
            "not a 3D renderer or physical traffic model",
        )
    return (
        True,
        f"terrain changes network edge cost: max_grade={max_grade:.6f}, "
        f"min_cost={min_cost:.6f}, max_cost={max_cost:.6f}; "
        "not a 3D renderer or physical traffic model",
    )


def sample_raster_at_points(raster, points) -> dict:
    """Sample raster values at each point in a PointSpace.

    The raster and points must be in the same CRS. Out-of-bounds points return 0.0,
    matching the dry out-of-bounds convention used by flood_depth_per_edge.
    """
    values = {}
    for point_id in range(points.n_points):
        x, y = points.coord_of(point_id)
        col, row = raster.world_to_cell(x, y)
        if 0 <= col < raster.width and 0 <= row < raster.height:
            values[point_id] = raster.value_at(col, row)
        else:
            values[point_id] = 0.0
    return values


def point_risk_per_edge(geonet, points, radius: float) -> dict:
    """Count PointSpace points within radius of each GeoNetwork edge.

    The network and points must be in the same projected CRS. Returns
    {(u, v) sorted: nearby point count}.
    """
    if radius < 0:
        raise ValueError("radius must be non-negative")

    from shapely.geometry import Point
    from shapely.strtree import STRtree

    g = geonet.graph
    edges = list(g.edges)
    geoms = [geonet.edge_geom(u, v) for u, v in edges]
    risk = {tuple(sorted(e)): 0 for e in edges}
    if not geoms:
        return risk

    tree = STRtree(geoms)
    for point_id in range(points.n_points):
        px, py = points.coord_of(point_id)
        p = Point(px, py)
        for i in tree.query(p.buffer(radius)):
            idx = int(i)
            if geoms[idx].distance(p) <= radius:
                u, v = edges[idx]
                risk[tuple(sorted((u, v)))] += 1
    return risk


def assign_points_to_polygons(points, polygons) -> dict:
    """Assign PointSpace point ids to containing PolygonSpace region ids."""
    return polygons.assign_points(points)


def combined_neighbors(i, spatial_neighbors_of, social_graph) -> set:
    """Couple a GIS layer with a social network: agent i's neighbours are its
    spatial neighbours (geography) UNION its social ties (the social graph).

    `spatial_neighbors_of(i) -> iterable of agent ids` decouples the mechanism
    from the concrete space (grid cells, network nodes, ...). The two layers give
    different reach — local clusters vs long-range social ties.
    """
    nbrs = set(spatial_neighbors_of(i))
    if i in social_graph:
        nbrs |= set(social_graph.neighbors(i))
    return nbrs


# ── DE-9IM vector topology (NetLogo gis parity, Phase 1) ────────────────────
#
# Thin wrappers over shapely so callers can rely on a stable abm_auto.gis API
# (and so we can swap implementations later). Each predicate is the shapely
# DE-9IM relation of the same name.


def intersects(a, b) -> bool:
    return a.intersects(b)


def contains(a, b) -> bool:
    """True if geometry `a` contains geometry `b` (b is inside a)."""
    return a.contains(b)


def within(a, b) -> bool:
    """True if geometry `a` is within geometry `b` (a is inside b)."""
    return a.within(b)


def touches(a, b) -> bool:
    return a.touches(b)


def crosses(a, b) -> bool:
    return a.crosses(b)


def overlaps(a, b) -> bool:
    return a.overlaps(b)


def relate(a, b) -> str:
    """The DE-9IM matrix string (9 chars) describing how `a` relates to `b`."""
    return a.relate(b)


def _features_matching(features, query, predicate) -> list:
    """STRtree-indexed indices of `features` whose geometry satisfies `predicate`
    against `query`. The tree gives bbox-level candidates; `predicate` is the exact
    DE-9IM refinement (STRtree.query is bounding-box, so the refine is required)."""
    from shapely.strtree import STRtree

    features = list(features)
    if not features:
        return []
    tree = STRtree(features)
    return [int(i) for i in tree.query(query) if predicate(features[int(i)], query)]


def features_intersecting(features, query) -> list:
    """Indices of `features` (shapely geometries) whose geometry intersects `query`."""
    return _features_matching(features, query, lambda f, q: f.intersects(q))


def features_containing(features, point) -> list:
    """Indices of polygon `features` that contain `point`."""
    return _features_matching(features, point, lambda f, p: f.contains(p))


# ── New coupling cells (line × polygon, polygon × polygon) ──────────────────


def lines_in_polygon(lines, polygon) -> float:
    """Total length of `lines` (iterable of shapely LineString) inside `polygon`.

    Each line is clipped to the polygon via `intersection`; the clipped length
    is summed. A line entirely outside contributes 0; entirely inside contributes
    its own length. Crossing lines contribute the inside portion only."""
    total = 0.0
    for line in lines:
        clipped = line.intersection(polygon)
        if clipped.is_empty:
            continue
        total += float(clipped.length)
    return total


def polygon_overlap_areas(a_polys, b_polys) -> dict:
    """Pairwise intersection areas between two polygon layers.

    Returns {(i, j): area} for every (a_polys[i], b_polys[j]) pair whose
    intersection has positive area. STRtree-indexed so it scales."""
    from shapely.strtree import STRtree

    a_list = list(a_polys)
    b_list = list(b_polys)
    if not a_list or not b_list:
        return {}
    tree = STRtree(b_list)
    out: dict = {}
    for i, a in enumerate(a_list):
        for raw_j in tree.query(a):
            j = int(raw_j)
            inter = a.intersection(b_list[j])
            if inter.is_empty:
                continue
            area = float(inter.area)
            if area > 0:
                out[(i, j)] = area
    return out


# ── Gates for the new coupling cells ────────────────────────────────────────


def line_polygon_gate(lines_inside, lines_outside, polygon):
    """Pass iff `lines_inside` contribute positive clipped length AND
    `lines_outside` contribute zero. Catches the trivial misuse where the
    polygon is ignored and totals come back length-of-all-lines."""
    inside_len = lines_in_polygon(lines_inside, polygon)
    outside_len = lines_in_polygon(lines_outside, polygon)
    if inside_len <= 0:
        return False, f"inside-clipped length non-positive ({inside_len})"
    if outside_len > 0:
        return False, f"outside-clipped length non-zero ({outside_len})"
    return True, f"line×polygon clip: inside={inside_len:.2f}, outside=0"


def polygon_overlap_gate(a_polys, b_polys):
    """Pass iff overlap of identical-input layers is the full self-area AND
    overlap of `a_polys` with an empty list is empty."""
    self_overlap = polygon_overlap_areas(a_polys, a_polys)
    if not self_overlap:
        return False, "self-overlap empty (operator is broken)"
    empty_overlap = polygon_overlap_areas(a_polys, [])
    if empty_overlap:
        return False, f"overlap with empty layer non-empty ({len(empty_overlap)} pairs)"
    real_overlap = polygon_overlap_areas(a_polys, b_polys)
    return True, (f"polygon×polygon overlap: self={len(self_overlap)} pairs, "
                  f"a×b={len(real_overlap)} pairs")
