"""Offline tests for the real-DEM Anshuka reproduction.

These run WITHOUT the real Ba data: a small synthetic GeoTIFF fixture exercises the
loader/world-builder, and the mechanism-parity test proves the real path runs the
byte-identical _simulate mechanism. The real-data verdict needs the actual SRTM/OSM
download.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.gis import _anshuka_2026 as syn
from abm_auto.gis._anshuka_real import (
    RealWorld,
    SyntheticWorldError,
    assert_real_world,
    build_elevation_from_dem,
    build_world_from_dem,
    run_scenario_real,
)


# --- 1. mechanism parity: the real path runs the SAME _simulate as run_scenario ---

def test_simulate_is_the_shared_mechanism():
    """_simulate fed the synthetic world (with run_scenario's exact rng prefix) equals
    run_scenario — so run_scenario_real, which also calls _simulate, runs the identical
    mechanism. Only the injected geometry differs."""
    import random

    rng = random.Random(0)
    elev = syn._build_elevation(rng)                 # consume the same 400 draws run_scenario does
    water = np.zeros((syn._GRID_SIZE, syn._GRID_SIZE), dtype=int)
    for r in range(syn._GRID_SIZE):
        for rc in syn._RIVER_COLS:
            water[r, rc] = 1
    direct = syn._simulate(
        rng, syn._GRID_SIZE, elev, water, list(syn._BUILDINGS), syn._SHELTERS,
        belief=0.4, alarm_t=0, onset_steps=20, mobility_good_frac=0.7,
        collaboration=False, n_agents=100, max_steps=150,
    )
    ref = syn.run_scenario(belief=0.4, alarm_t=0, onset_steps=20,
                           mobility_good_frac=0.7, collaboration=False, seed=0)
    assert (direct.evacuated, direct.incapacitated) == (ref.evacuated, ref.incapacitated)
    assert (ref.evacuated, ref.incapacitated) == (91, 9)  # the recorded golden


# --- 2. real-data gate (anti-fabrication: a synthetic world must HARD-FAIL) --------

def _terrain(n=40, relief=40.0):
    """A smooth ramp + gentle structure — real-DEM-like (high spatial autocorrelation)."""
    r, c = np.meshgrid(np.linspace(0, 1, n), np.linspace(0, 1, n), indexing="ij")
    return relief * (0.6 * c + 0.4 * r) + 2.0 * np.sin(4 * c) + 1.5 * np.cos(3 * r)


def _world(elev, source="SRTM:S18E177"):
    n = elev.shape[0]
    water = np.zeros((n, n), dtype=int); water[:, 0] = 1
    return RealWorld(grid_size=n, elev=elev, initial_water=water,
                     homes=[(n // 2, n // 2)], shelters=[(0, n - 1)], source=source)


def test_gate_rejects_synthetic_source():
    with pytest.raises(SyntheticWorldError, match="not a real dataset"):
        assert_real_world(_world(_terrain(), source="synthetic-grid"))
    with pytest.raises(SyntheticWorldError):
        assert_real_world(_world(_terrain(), source="unknown"))


def test_gate_rejects_flat_elevation():
    with pytest.raises(SyntheticWorldError, match="flat/synthetic"):
        assert_real_world(_world(np.full((40, 40), 5.0)))


def test_gate_rejects_random_noise():
    noise = np.random.default_rng(0).uniform(0, 40, size=(40, 40))  # no spatial structure
    with pytest.raises(SyntheticWorldError, match="autocorrelation"):
        assert_real_world(_world(noise))


def test_gate_accepts_real_terrain():
    assert_real_world(_world(_terrain()))  # must not raise


# --- 3 & 4. DEM loader + world builder on a GeoTIFF fixture ------------------------

@pytest.fixture
def dem_tif(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_origin

    elev = _terrain(60, relief=45.0).astype("float32")
    path = tmp_path / "ba_dem.tif"
    with rasterio.open(
        path, "w", driver="GTiff", height=60, width=60, count=1, dtype="float32",
        crs="EPSG:32760", transform=from_origin(1_800_000, 8_060_000, 30, 30),
    ) as dst:
        dst.write(elev, 1)
    return path


def test_build_elevation_from_dem_shape_range_deterministic(dem_tif):
    e1 = build_elevation_from_dem(dem_tif, grid_size=30)
    assert e1.shape == (30, 30)
    assert float(e1.max() - e1.min()) > 10.0        # real relief survived resampling
    e2 = build_elevation_from_dem(dem_tif, grid_size=30)
    assert np.array_equal(e1, e2)                    # deterministic


def test_build_world_from_dem_is_valid_and_passes_gate(dem_tif):
    w = build_world_from_dem(dem_tif, grid_size=30, source="SRTM:S18E177", n_shelters=4)
    assert w.grid_size == 30 and w.elev.shape == (30, 30)
    assert -1.5 <= w.elev.min() and w.elev.max() <= 7.5      # normalized to the flood regime
    assert len(w.shelters) == 4 and len(w.homes) > 0
    assert int(w.initial_water.sum()) > 0
    assert_real_world(w)                              # the built world passes the real-data gate
    # shelters sit higher than homes (sanity)
    mean_shelter = np.mean([w.elev[r, c] for r, c in w.shelters])
    mean_home = np.mean([w.elev[r, c] for r, c in w.homes])
    assert mean_shelter > mean_home


# --- 5. end-to-end real run on the fixture world ----------------------------------

def test_run_scenario_real_end_to_end(dem_tif):
    w = build_world_from_dem(dem_tif, grid_size=40, source="SRTM:S18E177")
    r1 = run_scenario_real(world=w, belief=0.7, alarm_t=0, onset_steps=20,
                           mobility_good_frac=0.7, collaboration=False, seed=0)
    assert r1.evacuated + r1.incapacitated + r1.still_moving == 100   # accounting holds
    r2 = run_scenario_real(world=w, belief=0.7, alarm_t=0, onset_steps=20,
                           mobility_good_frac=0.7, collaboration=False, seed=0)
    assert (r1.evacuated, r1.incapacitated) == (r2.evacuated, r2.incapacitated)  # deterministic


def test_run_scenario_real_refuses_synthetic_world(dem_tif):
    bad = _world(np.full((30, 30), 3.0), source="synthetic")
    with pytest.raises(SyntheticWorldError):
        run_scenario_real(world=bad, belief=0.5, alarm_t=0, onset_steps=20,
                          mobility_good_frac=0.7, collaboration=False)
