import numpy as np
from affine import Affine

from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._sir import run_raster_sir


def _density_space(n=20):
    # density gradient: dense centre, sparse edges
    yy, xx = np.mgrid[0:n, 0:n]
    d = np.exp(-(((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / (2 * (n / 5) ** 2)))
    transform = Affine(100.0, 0, 0, 0, -100.0, n * 100.0)
    return RasterSpace(RasterField(data=d, transform=transform, crs="EPSG:3857"))


def test_sir_runs_deterministically_and_spreads():
    sp = _density_space()
    a = run_raster_sir(sp, seed=1, steps=40, beta=0.4, gamma=0.05)
    b = run_raster_sir(sp, seed=1, steps=40, beta=0.4, gamma=0.05)
    assert a.infected_history == b.infected_history          # deterministic
    assert max(a.infected_history) > a.infected_history[0]   # epidemic grows
    assert a.final_infected_field.sum() > 0                  # some infection
    assert a.final_infected_field.shape == sp.field.data.shape


def test_different_seeds_differ():
    sp = _density_space()
    a = run_raster_sir(sp, seed=1, steps=40)
    b = run_raster_sir(sp, seed=2, steps=40)
    assert a.infected_history != b.infected_history
