import numpy as np
from affine import Affine

from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._sir import run_raster_sir
from abm_auto.gis._gate import spatial_spread_gate


def _density_space(n=20):
    yy, xx = np.mgrid[0:n, 0:n]
    d = np.exp(-(((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / (2 * (n / 5) ** 2)))
    transform = Affine(100.0, 0, 0, 0, -100.0, n * 100.0)
    return RasterSpace(RasterField(data=d, transform=transform, crs="EPSG:3857"))


def test_gate_passes_on_real_run():
    sp = _density_space()
    res = run_raster_sir(sp, seed=1, steps=40)
    passed, desc = spatial_spread_gate(res, sp.field.data)
    assert passed, desc


def test_gate_fails_on_scrambled_infection():
    sp = _density_space()
    res = run_raster_sir(sp, seed=1, steps=40)
    rng = np.random.default_rng(0)
    res.final_infected_field = rng.permutation(
        res.final_infected_field.ravel()
    ).reshape(res.final_infected_field.shape)
    passed, _ = spatial_spread_gate(res, sp.field.data)
    assert not passed   # spatially-random infection must fail
