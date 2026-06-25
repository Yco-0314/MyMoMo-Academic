"""Raster focal operations on RasterField (NetLogo gis parity, Phase 2).

Pure functions returning new RasterFields; existing transform/CRS preserved
(convolve) or rescaled to the same world envelope (resample). scipy is lazy-
imported to keep the base import light.
"""
from __future__ import annotations

from typing import Tuple, Union

import numpy as np

from abm_auto.gis._raster_space import RasterField


_Point = Tuple[float, float]
_Envelope = Tuple[float, float, float, float]


def convolve(field: RasterField, kernel, mode: str = "reflect") -> RasterField:
    """Convolve `field.data` with `kernel` (2D array). Preserves transform / crs /
    nodata. nodata cells participate as zeros in the convolution sum and remain
    nodata in the output."""
    from scipy.ndimage import convolve as _ndi_convolve

    k = np.asarray(kernel, dtype=float)
    if k.ndim != 2:
        raise ValueError(f"kernel must be 2D, got shape {k.shape}")
    data = np.asarray(field.data, dtype=float)
    nodata_mask = (data == field.nodata) if field.nodata is not None else None
    work = data.copy()
    if nodata_mask is not None:
        work[nodata_mask] = 0.0
    out = _ndi_convolve(work, k, mode=mode)
    if nodata_mask is not None:
        out[nodata_mask] = field.nodata
    return RasterField(data=out, transform=field.transform, crs=field.crs,
                       nodata=field.nodata)


def resample(field: RasterField, new_width: int, new_height: int,
             method: str = "nearest") -> RasterField:
    """Resample `field` to a new (width, height) covering the SAME world envelope.

    Methods: 'nearest' (NetLogo default for discrete data), 'bilinear' (continuous).
    The new affine transform is rescaled so pixel-centre coordinates of the corners
    match the original envelope. Resample to the same shape with 'nearest' is the
    identity."""
    from affine import Affine

    if new_width <= 0 or new_height <= 0:
        raise ValueError(f"new_width and new_height must be positive, "
                         f"got ({new_width}, {new_height})")

    src = np.asarray(field.data, dtype=float)
    src_h, src_w = src.shape

    # Identity short-circuit (byte-stable for the same-shape nearest case).
    if (new_width, new_height) == (src_w, src_h) and method == "nearest":
        return RasterField(data=src.copy(), transform=field.transform,
                           crs=field.crs, nodata=field.nodata)

    # Affine scale: new pixel size = old pixel size * (old_n / new_n) along each axis.
    a, b, c, d, e, f = (field.transform.a, field.transform.b, field.transform.c,
                        field.transform.d, field.transform.e, field.transform.f)
    new_a = a * src_w / new_width
    new_e = e * src_h / new_height
    new_transform = Affine(new_a, b, c, d, new_e, f)

    # Sample source at the world-coord of each new pixel centre.
    inv = ~field.transform
    out = np.empty((new_height, new_width), dtype=float)
    for r in range(new_height):
        for col in range(new_width):
            x, y = new_transform * (col + 0.5, r + 0.5)
            src_col_f, src_row_f = inv * (x, y)
            src_col_f -= 0.5   # pixel-centre to pixel-corner
            src_row_f -= 0.5
            if method == "nearest":
                sc = int(np.clip(round(src_col_f), 0, src_w - 1))
                sr = int(np.clip(round(src_row_f), 0, src_h - 1))
                out[r, col] = src[sr, sc]
            elif method == "bilinear":
                c0 = int(np.floor(src_col_f)); c1 = min(c0 + 1, src_w - 1)
                r0 = int(np.floor(src_row_f)); r1 = min(r0 + 1, src_h - 1)
                c0 = max(c0, 0); r0 = max(r0, 0)
                fc = src_col_f - c0; fr = src_row_f - r0
                v = ((1 - fr) * ((1 - fc) * src[r0, c0] + fc * src[r0, c1])
                     + fr * ((1 - fc) * src[r1, c0] + fc * src[r1, c1]))
                out[r, col] = v
            else:
                raise ValueError(f"unknown resample method {method!r}; "
                                 f"expected 'nearest' or 'bilinear'")

    return RasterField(data=out, transform=new_transform, crs=field.crs,
                       nodata=field.nodata)


def raster_sample(field: RasterField, geom: Union[_Point, _Envelope]) -> float:
    """Sample raster value at a point (x, y) or mean across an envelope
    (xmin, ymin, xmax, ymax). Out-of-bounds returns field.nodata (or NaN)."""
    miss = field.nodata if field.nodata is not None else float("nan")
    inv = ~field.transform
    h, w = field.data.shape

    if len(geom) == 2:
        x, y = geom
        fc, fr = inv * (x, y)
        col, row = int(np.floor(fc)), int(np.floor(fr))
        if 0 <= col < w and 0 <= row < h:
            return float(field.data[row, col])
        return float(miss)

    if len(geom) == 4:
        xmin, ymin, xmax, ymax = geom
        if xmin > xmax:
            xmin, xmax = xmax, xmin
        if ymin > ymax:
            ymin, ymax = ymax, ymin
        corners = [inv * (xmin, ymin), inv * (xmax, ymin),
                   inv * (xmin, ymax), inv * (xmax, ymax)]
        cols = [c for c, _ in corners]
        rows = [r for _, r in corners]
        c_lo = max(int(np.floor(min(cols))), 0)
        c_hi = min(int(np.ceil(max(cols))), w)
        r_lo = max(int(np.floor(min(rows))), 0)
        r_hi = min(int(np.ceil(max(rows))), h)
        if c_lo >= c_hi or r_lo >= r_hi:
            return float(miss)
        return float(field.data[r_lo:r_hi, c_lo:c_hi].mean())

    raise ValueError(f"geom must be (x,y) or (xmin,ymin,xmax,ymax), got len={len(geom)}")


def focal_gate(field: RasterField):
    """Deterministic focal-operator contract:
      1. identity kernel returns the input array exactly,
      2. 3x3 mean kernel strictly lowers variance on a noisy field,
      3. resample to same shape with 'nearest' returns the input exactly.
    """
    identity = convolve(field, [[1.0]])
    if not np.array_equal(identity.data, field.data):
        return False, "identity convolution did not return the input array"

    mean_kernel = np.full((3, 3), 1.0 / 9.0)
    smoothed = convolve(field, mean_kernel)
    if not (np.var(smoothed.data) < np.var(field.data)):
        return False, (f"3x3 mean smoothing did not reduce variance "
                       f"({np.var(field.data):.4f} -> {np.var(smoothed.data):.4f})")

    h, w = field.data.shape
    same = resample(field, w, h, method="nearest")
    if not np.array_equal(same.data, field.data):
        return False, "resample to same shape ('nearest') did not return the input array"

    return True, (f"focal ops OK: identity convolution exact, mean smoothing "
                  f"variance {np.var(field.data):.4f} -> {np.var(smoothed.data):.4f}, "
                  f"same-shape resample exact")
