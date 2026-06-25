"""Raster focal operations: convolve / resample / raster_sample / focal_gate.

Each test pins a known-kernel-on-known-field answer; the gate test confirms
focal_gate fails on a broken convolve, not just passes on a correct one.
"""
import numpy as np
import pytest
from affine import Affine

from abm_auto.gis._focal import convolve, focal_gate, raster_sample, resample
from abm_auto.gis._raster_space import RasterField


def _field(data, transform=None, crs="EPSG:3857", nodata=None):
    if transform is None:
        h, w = np.asarray(data).shape
        transform = Affine(100.0, 0, 0, 0, -100.0, h * 100.0)
    return RasterField(data=np.asarray(data, dtype=float), transform=transform,
                       crs=crs, nodata=nodata)


# ── F1 convolve ──────────────────────────────────────────────────────────────

def test_convolve_identity_returns_input_exactly():
    f = _field([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    out = convolve(f, [[1.0]])
    assert np.array_equal(out.data, f.data)
    assert out.transform == f.transform and out.crs == f.crs


def test_convolve_3x3_mean_kernel_reduces_variance():
    rng = np.random.default_rng(0)
    f = _field(rng.normal(size=(20, 20)))
    mean_kernel = np.full((3, 3), 1.0 / 9.0)
    smoothed = convolve(f, mean_kernel)
    assert np.var(smoothed.data) < np.var(f.data)


def test_convolve_known_answer_on_known_kernel_and_field():
    # 3x3 ones * mean 1/9 kernel -> 1.0 at the centre (reflect mode at edges)
    f = _field(np.ones((3, 3)))
    mean = np.full((3, 3), 1.0 / 9.0)
    out = convolve(f, mean)
    assert np.allclose(out.data[1, 1], 1.0)


def test_convolve_rejects_non_2d_kernel():
    f = _field([[1, 2], [3, 4]])
    with pytest.raises(ValueError, match="2D"):
        convolve(f, [1.0, 2.0, 3.0])


def test_convolve_preserves_nodata_cells():
    f = _field([[1, 2, 3], [4, -1, 6], [7, 8, 9]], nodata=-1.0)
    out = convolve(f, np.full((3, 3), 1.0 / 9.0))
    assert out.data[1, 1] == -1.0   # nodata cell stays nodata in the output


# ── F2 resample ──────────────────────────────────────────────────────────────

def test_resample_to_same_shape_nearest_is_identity():
    f = _field([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    out = resample(f, 3, 3, method="nearest")
    assert np.array_equal(out.data, f.data)
    # affine unchanged for the identity case
    assert out.transform == f.transform


def test_resample_downsample_2x2_to_1x1_picks_a_source_value():
    f = _field([[10, 20], [30, 40]])
    out = resample(f, 1, 1, method="nearest")
    assert out.data.shape == (1, 1)
    assert float(out.data[0, 0]) in {10.0, 20.0, 30.0, 40.0}


def test_resample_upsample_2x_doubles_dimensions_and_preserves_envelope():
    f = _field([[1, 2], [3, 4]])    # 2x2 over [0..200] x [0..200] (100m pixels)
    out = resample(f, 4, 4, method="nearest")
    assert out.data.shape == (4, 4)
    # new pixel size is half: 50m
    assert out.transform.a == 50.0
    assert out.transform.e == -50.0
    # all original values present in the upsampled output
    assert set(out.data.flatten()) == {1.0, 2.0, 3.0, 4.0}


def test_resample_bilinear_interpolates_between_corners():
    f = _field([[0, 10], [0, 10]])     # ramps in x
    out = resample(f, 4, 1, method="bilinear")
    # bilinear should produce values between 0 and 10, monotonic in x
    row = out.data[0]
    assert row[0] < row[1] < row[2] < row[3]
    assert 0 <= row[0] and row[-1] <= 10


def test_resample_rejects_non_positive_shape():
    f = _field([[1, 2], [3, 4]])
    with pytest.raises(ValueError, match="positive"):
        resample(f, 0, 1)


def test_resample_rejects_unknown_method():
    f = _field([[1, 2], [3, 4]])
    with pytest.raises(ValueError, match="method"):
        resample(f, 2, 2, method="cubic")


# ── F3 raster_sample ─────────────────────────────────────────────────────────

def test_raster_sample_point_returns_cell_value():
    f = _field([[10, 20, 30], [40, 50, 60], [70, 80, 90]])
    # affine: 100m pixels, origin (0, 300) (rows go down).  cell (0,0) world centre = (50, 250)
    assert raster_sample(f, (50.0, 250.0)) == 10.0
    assert raster_sample(f, (250.0, 50.0)) == 90.0     # cell (2, 2)


def test_raster_sample_envelope_returns_mean():
    f = _field([[10, 20], [30, 40]])      # mean = 25
    # envelope spanning the whole raster
    assert raster_sample(f, (0.0, 0.0, 200.0, 200.0)) == 25.0


def test_raster_sample_out_of_bounds_returns_nodata():
    f = _field([[1, 2], [3, 4]], nodata=-1.0)
    assert raster_sample(f, (-100.0, -100.0)) == -1.0


def test_raster_sample_out_of_bounds_no_nodata_returns_nan():
    f = _field([[1, 2], [3, 4]])
    assert np.isnan(raster_sample(f, (-100.0, -100.0)))


def test_raster_sample_rejects_invalid_geom_shape():
    f = _field([[1, 2], [3, 4]])
    with pytest.raises(ValueError, match="geom"):
        raster_sample(f, (1.0, 2.0, 3.0))


# ── F4 focal_gate (must fail on broken ops, not just pass on real) ───────────

def test_focal_gate_passes_on_noisy_field():
    rng = np.random.default_rng(0)
    f = _field(rng.normal(size=(15, 15)))
    ok, desc = focal_gate(f)
    assert ok, desc
    assert "identity convolution exact" in desc


def test_focal_gate_fails_when_convolve_is_broken(monkeypatch):
    # A broken stub: ignore the kernel and double the data.  focal_gate's
    # identity check must catch this.
    def broken_convolve(field, kernel, mode="reflect"):
        return RasterField(data=field.data * 2.0, transform=field.transform,
                           crs=field.crs, nodata=field.nodata)
    import abm_auto.gis._focal as focal_mod
    monkeypatch.setattr(focal_mod, "convolve", broken_convolve)

    rng = np.random.default_rng(0)
    f = _field(rng.normal(size=(10, 10)))
    ok, desc = focal_gate(f)
    assert not ok
    assert "identity convolution" in desc


def test_focal_gate_fails_when_resample_is_broken(monkeypatch):
    # Broken: same-shape resample returns zeros instead of the input.  Must catch.
    def broken_resample(field, w, h, method="nearest"):
        return RasterField(data=np.zeros_like(field.data), transform=field.transform,
                           crs=field.crs, nodata=field.nodata)
    import abm_auto.gis._focal as focal_mod
    monkeypatch.setattr(focal_mod, "resample", broken_resample)

    rng = np.random.default_rng(0)
    f = _field(rng.normal(size=(10, 10)))
    ok, desc = focal_gate(f)
    assert not ok
    assert "resample to same shape" in desc
