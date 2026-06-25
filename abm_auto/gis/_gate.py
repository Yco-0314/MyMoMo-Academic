"""Spatial-spread gate: a deterministic spatial signature for a raster epidemic.

Asserts three things a correct geographic SIR must show:
  1. it actually spread (final ever-infected > seed),
  2. infection couples to density (corr(density, infected) > 0),
  3. infection is spatially clustered (Moran's I > a shuffle baseline).
"""
from __future__ import annotations

import numpy as np

from abm_auto.gis._ops import morans_i


def spatial_spread_gate(result, density: np.ndarray):
    inf = result.final_infected_field
    if inf.sum() <= 1:
        return False, "no spread (final infected <= 1)"

    # 2. density coupling
    corr = np.corrcoef(density.ravel(), inf.ravel())[0, 1]
    if not (corr > 0):
        return False, f"infection not density-coupled (corr={corr:.2f})"

    # 3. spatial clustering vs a shuffle baseline
    obs = morans_i(inf)
    rng = np.random.default_rng(12345)
    baseline = max(
        morans_i(rng.permutation(inf.ravel()).reshape(inf.shape)) for _ in range(20)
    )
    if not (obs > baseline):
        return False, f"infection not clustered (Moran's I {obs:.2f} <= baseline {baseline:.2f})"

    return True, f"spread + density-coupled (corr={corr:.2f}) + clustered (I={obs:.2f})"
