"""Areal coverage: polygon attribute -> raster, area-weighted.

Tests pin known answers; reverse monkeypatch tests confirm apply_coverage_gate
FAILS on broken implementations (anti-fabrication: a gate that always passes
is no gate at all).
"""
import numpy as np
import pytest
from affine import Affine
from shapely.geometry import box

from abm_auto.gis._coverage import _cell_polygon, apply_coverage, apply_coverage_gate
from abm_auto.gis._raster_space import RasterField


def _template(shape=(4, 4), pixel=100.0):
    """A simple raster template: origin (0, h*pixel), pixels of `pixel` m,
    pointing y-down (rows go down → world y decreases as row increases)."""
    h, w = shape
    return RasterField(
        data=np.zeros((h, w), dtype=float),
        transform=Affine(pixel, 0, 0, 0, -pixel, h * pixel),
        crs="EPSG:3857",
    )


def _envelope(template: RasterField):
    h, w = template.data.shape
    x0, y0 = template.transform * (0, 0)
    x1, y1 = template.transform * (w, h)
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


# ── C1.a _cell_polygon ──────────────────────────────────────────────────────


def test_cell_polygon_matches_one_pixel_box():
    t = _template(shape=(4, 4), pixel=100.0)
    cell = _cell_polygon(t, 0, 0)
    # cell (0,0) world envelope = x∈[0,100], y∈[300,400] (origin y=400)
    minx, miny, maxx, maxy = cell.bounds
    assert (minx, miny, maxx, maxy) == (0.0, 300.0, 100.0, 400.0)
    assert cell.area == 100.0 * 100.0   # 10_000 m²


# ── C1.b apply_coverage ─────────────────────────────────────────────────────


def test_apply_coverage_constant_attribute_fills_entire_raster():
    t = _template()
    env = box(*_envelope(t))
    out = apply_coverage([env], [42.0], t)
    assert np.allclose(out.data, 42.0)
    assert out.transform == t.transform and out.crs == t.crs


def test_apply_coverage_empty_input_fills_default():
    t = _template()
    out = apply_coverage([], [], t, default=-3.0)
    assert np.allclose(out.data, -3.0)


def test_apply_coverage_disjoint_polygons_area_weighted_per_cell():
    # 4x4 raster, 100m pixels, world envelope [0..400] x [0..400].  Split into
    # left half (x<200) = 1.0 and right half (x>=200) = 9.0.  Left 2 cols == 1.0,
    # right 2 cols == 9.0 (cells fully inside one polygon -> exact value).
    t = _template(shape=(4, 4), pixel=100.0)
    xmin, ymin, xmax, ymax = _envelope(t)
    left = box(xmin, ymin, (xmin + xmax) / 2.0, ymax)
    right = box((xmin + xmax) / 2.0, ymin, xmax, ymax)
    out = apply_coverage([left, right], [1.0, 9.0], t)
    assert np.allclose(out.data[:, :2], 1.0)
    assert np.allclose(out.data[:, 2:], 9.0)


def test_apply_coverage_split_through_cell_is_area_weighted_average():
    # 2x2 raster of 100m pixels (envelope [0..200] x [0..200]).  A left band
    # x<150 = 10.0; a right band x>=150 = 0.0.  Right cells (cols 1) span x
    # 100..200: 50% of their area is in the left band (10.0) and 50% in the
    # right (0.0) -> area-weighted = 5.0.  Left cells (col 0, x 0..100) are
    # entirely in the left band -> 10.0.
    t = _template(shape=(2, 2), pixel=100.0)
    left = box(0, 0, 150, 200)
    right = box(150, 0, 200, 200)
    out = apply_coverage([left, right], [10.0, 0.0], t)
    assert np.allclose(out.data[:, 0], 10.0)
    assert np.allclose(out.data[:, 1], 5.0)


def test_apply_coverage_cell_not_touched_by_any_polygon_takes_default():
    # Small polygon in the top-left only; other cells must take `default`.
    t = _template(shape=(4, 4), pixel=100.0)
    poly = box(0, 300, 100, 400)        # exactly cell (col=0, row=0)
    out = apply_coverage([poly], [99.0], t, default=-1.0)
    assert out.data[0, 0] == 99.0
    # all other cells -> default
    rest = out.data.copy()
    rest[0, 0] = -1.0
    assert np.all(rest == -1.0)


def test_apply_coverage_rejects_mismatched_lengths():
    t = _template()
    with pytest.raises(ValueError, match="same length"):
        apply_coverage([box(0, 0, 100, 100), box(0, 0, 200, 200)], [1.0], t)


def test_apply_coverage_preserves_nodata_metadata():
    t = RasterField(
        data=np.zeros((2, 2), dtype=float),
        transform=Affine(100, 0, 0, 0, -100, 200),
        crs="EPSG:3857",
        nodata=-9999.0,
    )
    out = apply_coverage([], [], t, default=0.0)
    assert out.nodata == -9999.0


# ── C2 apply_coverage_gate ──────────────────────────────────────────────────


def test_coverage_gate_passes_on_real_template():
    t = _template()
    ok, desc = apply_coverage_gate([], [], t)   # the gate constructs its own test inputs
    assert ok, desc
    assert "coverage OK" in desc


def test_coverage_gate_fails_when_apply_coverage_sums_without_dividing(monkeypatch):
    """A broken stub that returns Σ(area × v) without dividing by Σ(area).
    The constant-attribute identity check must catch it (sum >> v).
    """
    import abm_auto.gis._coverage as cov_mod

    def broken_apply_coverage(polygons, values, raster_template, default=0.0):
        h, w = raster_template.data.shape
        polys = list(polygons); vals = list(values)
        out = np.full((h, w), float(default), dtype=float)
        if not polys:
            return RasterField(data=out, transform=raster_template.transform,
                               crs=raster_template.crs, nodata=raster_template.nodata)
        # buggy: total area-weighted sum, no division -> orders of magnitude wrong
        for row in range(h):
            for col in range(w):
                cell = cov_mod._cell_polygon(raster_template, col, row)
                s = 0.0
                for p, v in zip(polys, vals):
                    inter = p.intersection(cell)
                    if not inter.is_empty:
                        s += float(inter.area) * float(v)
                out[row, col] = s
        return RasterField(data=out, transform=raster_template.transform,
                           crs=raster_template.crs, nodata=raster_template.nodata)

    monkeypatch.setattr(cov_mod, "apply_coverage", broken_apply_coverage)
    t = _template()
    ok, desc = apply_coverage_gate([], [], t)
    assert not ok
    assert "constant-attribute identity" in desc


def test_coverage_gate_fails_when_apply_coverage_ignores_polygons(monkeypatch):
    """A broken stub that always returns `default`.  The constant-attribute
    check sees mean=default instead of v -> fail."""
    import abm_auto.gis._coverage as cov_mod

    def broken_apply_coverage(polygons, values, raster_template, default=0.0):
        h, w = raster_template.data.shape
        out = np.full((h, w), float(default), dtype=float)
        return RasterField(data=out, transform=raster_template.transform,
                           crs=raster_template.crs, nodata=raster_template.nodata)

    monkeypatch.setattr(cov_mod, "apply_coverage", broken_apply_coverage)
    t = _template()
    ok, desc = apply_coverage_gate([], [], t)
    assert not ok
    assert "constant-attribute identity" in desc
