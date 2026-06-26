"""Coupling operators between GIS space layers — the first operators of the
coupled multi-layer space seam.

flood_depth_per_edge couples a road GeoNetwork with a flood-depth RasterSpace:
for each road edge, the max flood depth sampled along the segment.
"""
from __future__ import annotations

import numpy as np


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
