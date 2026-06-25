"""End-to-end: GeoTIFF on disk -> load_raster -> RasterSpace -> raster-SIR -> gate."""
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from rasterio.crs import CRS

from abm_auto.gis._io import load_raster
from abm_auto.gis._raster_space import RasterSpace
from abm_auto.gis._sir import run_raster_sir
from abm_auto.gis._gate import spatial_spread_gate

FIX = Path("data/fixtures/ghsl_city.tif")


def _write_density_tiff(path, n=24):
    yy, xx = np.mgrid[0:n, 0:n]
    d = np.exp(-(((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / (2 * (n / 5) ** 2))).astype("float32")
    with rasterio.open(path, "w", driver="GTiff", height=n, width=n, count=1,
                       dtype="float32", crs=CRS.from_epsg(3857),
                       transform=Affine(100, 0, 0, 0, -100, n * 100)) as dst:
        dst.write(d, 1)


def test_synthetic_end_to_end_passes_gate(tmp_path):
    # exercises the WHOLE path through real GeoTIFF I/O (not skipped)
    p = tmp_path / "density.tif"
    _write_density_tiff(p)
    sp = RasterSpace(load_raster(p))
    res = run_raster_sir(sp, seed=1, steps=60)
    passed, desc = spatial_spread_gate(res, sp.field.data)
    assert passed, desc


def test_real_fixture_passes_gate():
    if not FIX.exists():
        import pytest
        pytest.skip("GHSL fixture not generated yet (run data/fixtures/fetch_clip.py)")
    sp = RasterSpace(load_raster(FIX))
    res = run_raster_sir(sp, seed=1, steps=60)
    passed, desc = spatial_spread_gate(res, sp.field.data)
    assert passed, desc
