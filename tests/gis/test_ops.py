import numpy as np
from affine import Affine

from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._ops import metric_distance, morans_i


def _space():
    data = np.zeros((5, 5))
    transform = Affine(100.0, 0, 0, 0, -100.0, 500.0)  # 100 m pixels
    return RasterSpace(RasterField(data=data, transform=transform, crs="EPSG:3857"))


def test_metric_distance_in_metres():
    sp = _space()
    # cells (0,0) and (3,0) are 3 pixels = 300 m apart in x
    assert round(metric_distance(sp, (0, 0), (3, 0))) == 300


def test_morans_i_clustered_gt_random():
    rng = np.random.default_rng(0)
    n = 10
    clustered = np.zeros((n, n)); clustered[:, : n // 2] = 1
    rand = rng.integers(0, 2, size=(n, n)).astype(float)
    assert morans_i(clustered) > morans_i(rand)
    assert morans_i(clustered) > 0.5  # strong positive autocorrelation


def test_morans_i_uniform_field_is_zero():
    assert morans_i(np.ones((6, 6))) == 0.0
