import numpy as np
from affine import Affine

from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._viz import render_map


def test_render_map_writes_png(tmp_path):
    data = np.random.default_rng(0).random((10, 10))
    sp = RasterSpace(RasterField(
        data=data, transform=Affine(100, 0, 0, 0, -100, 1000), crs="EPSG:3857"))
    infected = np.zeros((10, 10)); infected[4:6, 4:6] = 1
    out = tmp_path / "map.png"
    render_map(sp, infected, out)
    assert out.exists() and out.stat().st_size > 0
