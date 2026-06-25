"""Areal coverage: polygon attribute -> raster cell, area-weighted.

NetLogo `gis:apply-coverage` parity. For each cell of the raster template, each
polygon contributes its attribute value weighted by the polygon-cell intersection
area. Cells touched by no polygon take `default`. STRtree-indexed so it scales.

Pure function on RasterField; shapely is lazy-imported.
"""
from __future__ import annotations

import numpy as np

from abm_auto.gis._raster_space import RasterField


def _cell_polygon(template: RasterField, col: int, row: int):
    """The world-coordinate polygon for cell (col, row) of the template raster."""
    from shapely.geometry import box

    x0, y0 = template.transform * (col, row)
    x1, y1 = template.transform * (col + 1, row + 1)
    return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def apply_coverage(polygons, values, raster_template: RasterField,
                   default: float = 0.0) -> RasterField:
    """Rasterise polygon attributes onto `raster_template`'s grid, area-weighted.

    Args:
        polygons:        iterable of shapely Polygon (any geometry with `area`
                         and `intersection` works).
        values:          parallel iterable of floats, one per polygon.
        raster_template: defines the output shape / transform / crs / nodata.
        default:         value for cells touched by no polygon (default 0.0).

    Returns a new RasterField; the template is not modified.
    """
    from shapely.geometry import box
    from shapely.strtree import STRtree

    polys = list(polygons)
    vals = list(values)
    if len(polys) != len(vals):
        raise ValueError(f"polygons ({len(polys)}) and values ({len(vals)}) "
                         "must have the same length")

    h, w = raster_template.data.shape
    out = np.full((h, w), float(default), dtype=float)

    if not polys:
        return RasterField(data=out, transform=raster_template.transform,
                           crs=raster_template.crs, nodata=raster_template.nodata)

    tree = STRtree(polys)
    for row in range(h):
        for col in range(w):
            cell = _cell_polygon(raster_template, col, row)
            total_area = 0.0
            weighted = 0.0
            for raw_i in tree.query(cell):
                i = int(raw_i)
                inter = polys[i].intersection(cell)
                if inter.is_empty:
                    continue
                a = float(inter.area)
                if a <= 0.0:
                    continue
                total_area += a
                weighted += a * float(vals[i])
            if total_area > 0.0:
                out[row, col] = weighted / total_area
    return RasterField(data=out, transform=raster_template.transform,
                       crs=raster_template.crs, nodata=raster_template.nodata)


def apply_coverage_gate(polygons, values, raster_template: RasterField,
                        default: float = 0.0):
    """Deterministic contract for apply_coverage:

      1. constant-attribute identity: a single polygon covering the whole raster
         with attribute v -> every cell == v;
      2. disjoint area-weighted average: two non-overlapping polygons covering
         the raster with attributes vA, vB -> each cell == vA or vB (the one it
         falls inside), proving the area weights are used (and not summed);
      3. empty-input identity: zero polygons -> every cell == default.
    """
    from shapely.geometry import box

    h, w = raster_template.data.shape
    # World envelope of the template.
    x0, y0 = raster_template.transform * (0, 0)
    x1, y1 = raster_template.transform * (w, h)
    env_xmin, env_xmax = min(x0, x1), max(x0, x1)
    env_ymin, env_ymax = min(y0, y1), max(y0, y1)
    env = box(env_xmin, env_ymin, env_xmax, env_ymax)
    mid_x = (env_xmin + env_xmax) / 2.0

    # 1. constant identity
    const_v = 7.5
    const_out = apply_coverage([env], [const_v], raster_template, default=default)
    if not np.allclose(const_out.data, const_v):
        return False, (f"constant-attribute identity failed: cell mean "
                       f"{const_out.data.mean():.4f}, expected {const_v}")

    # 2. disjoint area-weighted: left half = vA, right half = vB
    left = box(env_xmin, env_ymin, mid_x, env_ymax)
    right = box(mid_x, env_ymin, env_xmax, env_ymax)
    vA, vB = 1.0, 9.0
    split_out = apply_coverage([left, right], [vA, vB], raster_template,
                               default=default)
    expected_mean = (vA + vB) / 2.0
    if abs(split_out.data.mean() - expected_mean) > 0.5:
        return False, (f"disjoint area-weighted mean {split_out.data.mean():.4f} "
                       f"deviates from expected {expected_mean}")
    if not (split_out.data.min() >= min(vA, vB) - 1e-9
            and split_out.data.max() <= max(vA, vB) + 1e-9):
        return False, (f"disjoint cell values out of [vA, vB] range: "
                       f"min={split_out.data.min()}, max={split_out.data.max()}")

    # 3. empty-input identity
    empty_out = apply_coverage([], [], raster_template, default=default)
    if not np.allclose(empty_out.data, default):
        return False, (f"empty-input did not fill with default {default}: "
                       f"got mean {empty_out.data.mean():.4f}")

    return True, (f"coverage OK: constant=={const_v}, split mean "
                  f"{split_out.data.mean():.3f} (expected {expected_mean}), "
                  f"empty=={default}")
