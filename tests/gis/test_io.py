import numpy as np
import rasterio
from affine import Affine
from rasterio.crs import CRS

from abm_auto.gis._io import load_raster


def _write_tiff(path):
    data = np.arange(12, dtype="float32").reshape(3, 4)
    transform = Affine(100.0, 0, 1000.0, 0, -100.0, 5000.0)
    with rasterio.open(
        path, "w", driver="GTiff", height=3, width=4, count=1,
        dtype="float32", crs=CRS.from_epsg(3857), transform=transform, nodata=-1.0,
    ) as dst:
        dst.write(data, 1)


def test_load_raster_reads_array_and_georef(tmp_path):
    p = tmp_path / "t.tif"
    _write_tiff(p)
    f = load_raster(p)
    assert f.data.shape == (3, 4)
    assert f.data[2, 3] == 11.0
    assert "3857" in str(f.crs)
    assert f.nodata == -1.0
    assert f.transform.a == 100.0  # pixel width
