import numpy as np
import rasterio
from affine import Affine
from rasterio.crs import CRS

from abm_auto.gis._fixtures import clip_window


def _src(tmp_path):
    p = tmp_path / "src.tif"
    data = np.arange(100, dtype="float32").reshape(10, 10)
    with rasterio.open(p, "w", driver="GTiff", height=10, width=10, count=1,
                       dtype="float32", crs=CRS.from_epsg(3857),
                       transform=Affine(100, 0, 0, 0, -100, 1000)) as d:
        d.write(data, 1)
    return p


def test_clip_window_extracts_subgrid(tmp_path):
    src = _src(tmp_path)
    out = tmp_path / "clip.tif"
    clip_window(src, out, col_off=2, row_off=3, width=4, height=4)
    with rasterio.open(out) as r:
        assert r.width == 4 and r.height == 4
        assert r.read(1)[0, 0] == 32.0   # row 3, col 2 of source
        # affine shifted to the window origin
        x, y = r.transform * (0, 0)
        assert (round(x), round(y)) == (200, 700)
