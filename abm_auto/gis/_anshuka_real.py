"""Candidate #10 — the real-DEM reproduction of Anshuka et al. 2026.

The fidelity test-stone (ADR-023 #10 / ADR-024 D3 step 1). It swaps ONLY the world
geometry of the synthetic [_anshuka_2026] reproduction for a REAL Ba-catchment SRTM
DEM, and runs the byte-identical [_anshuka_2026._simulate] mechanism on it — so any
magnitude movement toward the paper is attributable to geometry alone. See
``docs/reproduce/anshuka-2026-real-dem/PREDICTIONS-locked.md`` (locked before any run).

This is also ladder step #2 (real-data codegen): the world comes through
``_io.load_raster`` from a real GeoTIFF, and ``assert_real_world`` HARD-FAILS a
synthetic/degenerate elevation — so the fidelity gate verifies a REAL DEM, not np.random.

Note: the synthetic mechanism moves agents on the GRID (Manhattan, avoiding water); it
does NOT route on a road graph. So candidate #10 needs only the DEM (elevation drives the
flood + the agent-to-shelter distances that the FINDINGS root-cause is about). OSM
buildings/shelters are an optional v2 refinement, not required for the geometry test.

Additive GIS module. Zero change to runtime/codegen/calibration/agents/pipeline.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

from abm_auto.gis._anshuka_2026 import ScenarioResult, _simulate
from abm_auto.gis._io import load_raster


@dataclass
class RealWorld:
    """An injected world for the shared mechanism. ``source`` records provenance so
    the real-data gate can refuse a synthetic world."""
    grid_size: int
    elev: np.ndarray                       # (grid_size, grid_size) float, real metres
    initial_water: np.ndarray              # (grid_size, grid_size) int, river/source cells = 1
    homes: List[Tuple[int, int]]           # agent start cells (low floodplain)
    shelters: List[Tuple[int, int]]        # evacuation targets (high ground)
    source: str = "unknown"                # e.g. "SRTM:S18E177" — "synthetic*" is rejected


# ── Real-data gate (ladder #2: the wall must verify a REAL DEM, not np.random) ──

class SyntheticWorldError(ValueError):
    """Raised when a world that claims to be real is actually synthetic/degenerate."""


def assert_real_world(world: RealWorld, *, min_relief: float = 1.0) -> None:
    """HARD-FAIL if the world is not a real DEM. Anti-fabrication: a run that silently
    falls back to a synthetic/flat/np.random elevation must fail the gate, not pass.

    Checks: (1) provenance is not synthetic; (2) elevation is finite and non-degenerate
    (real relief, std/range above ``min_relief`` metres); (3) it has spatial structure —
    a real DEM's lag-1 spatial autocorrelation is high; uncorrelated np.random noise is ~0."""
    src = (world.source or "").lower()
    if src.startswith("synthetic") or "random" in src or src in ("", "unknown"):
        raise SyntheticWorldError(f"world.source={world.source!r} is not a real dataset")
    e = np.asarray(world.elev, dtype=float)
    if not np.isfinite(e).all():
        raise SyntheticWorldError("elevation contains non-finite values")
    if float(np.nanmax(e) - np.nanmin(e)) < min_relief or float(e.std()) < min_relief / 3.0:
        raise SyntheticWorldError(
            f"elevation relief {float(np.nanmax(e) - np.nanmin(e)):.3f} < {min_relief} m — looks flat/synthetic"
        )
    if _lag1_autocorr(e) < 0.3:
        raise SyntheticWorldError(
            "elevation has near-zero spatial autocorrelation — looks like noise, not terrain"
        )


def _lag1_autocorr(a: np.ndarray) -> float:
    """Mean of horizontal+vertical lag-1 Pearson correlation. ~1 for smooth terrain,
    ~0 for i.i.d. noise — a cheap real-DEM-vs-np.random discriminator."""
    a = np.asarray(a, dtype=float)
    pairs = []
    for x, y in ((a[:, :-1], a[:, 1:]), (a[:-1, :], a[1:, :])):
        xf, yf = x.ravel(), y.ravel()
        if xf.std() == 0 or yf.std() == 0:
            return 0.0
        pairs.append(float(np.corrcoef(xf, yf)[0, 1]))
    return float(np.mean(pairs))


# ── Scenario runner (the SAME mechanism, a real world) ──────────────────────────

def run_scenario_real(
    *,
    world: RealWorld,
    belief: float,
    alarm_t: int,
    onset_steps: int,
    mobility_good_frac: float,
    collaboration: bool,
    prior_experience_frac: Optional[float] = None,
    n_agents: int = 100,
    seed: int = 0,
    max_steps: int = 400,        # larger than the synthetic 150: real distances need more ticks
    verify_real: bool = True,
) -> ScenarioResult:
    """Run the byte-identical Anshuka mechanism on a REAL Ba world. By default verifies
    the world is a real DEM (set ``verify_real=False`` only for mechanism-parity tests)."""
    if verify_real:
        assert_real_world(world)
    rng = random.Random(seed)
    return _simulate(
        rng, world.grid_size, world.elev, world.initial_water.copy(),
        list(world.homes), list(world.shelters),
        belief=belief, alarm_t=alarm_t, onset_steps=onset_steps,
        mobility_good_frac=mobility_good_frac, collaboration=collaboration,
        prior_experience_frac=prior_experience_frac,
        n_agents=n_agents, max_steps=max_steps,
    )


def mean_outcome_real(*, world: RealWorld, n_iter: int = 5, base_seed: int = 0, **kwargs) -> dict:
    """Multi-seed mean for the real world (mirrors ``_anshuka_2026.mean_outcome``)."""
    e, i = [], []
    for k in range(n_iter):
        r = run_scenario_real(world=world, seed=base_seed + k, **kwargs)
        e.append(r.evacuated)
        i.append(r.incapacitated)
    return {"evac": float(np.mean(e)), "incap": float(np.mean(i)),
            "evac_std": float(np.std(e)), "incap_std": float(np.std(i)), "n_iter": n_iter}


# ── World builders (the real Ba DEM → an injected world) ────────────────────────

def build_elevation_from_dem(
    dem_path,
    grid_size: int,
    bbox: Optional[Tuple[float, float, float, float]] = None,
) -> np.ndarray:
    """Load a (pre-reprojected, metric-CRS) DEM GeoTIFF via ``_io.load_raster``, clip to
    ``bbox`` (minx, miny, maxx, maxy in the raster's CRS), and resample to
    ``(grid_size, grid_size)``. Reprojection to UTM 60S is a data-prep step (see
    DATA-acquisition.md); pass an already-metric DEM here."""
    rf = load_raster(dem_path)
    data = np.asarray(rf.data, dtype=float)
    if rf.nodata is not None:
        data = np.where(data == rf.nodata, np.nan, data)
    if bbox is not None:
        data = _clip_to_bbox(data, rf.transform, bbox)
    return _resample(data, grid_size)


def build_world_from_dem(
    dem_path,
    *,
    grid_size: int = 100,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    source: str,
    n_shelters: int = 4,
    river_quantile: float = 0.03,
    home_band: Tuple[float, float] = (0.05, 0.45),
    n_homes: int = 60,
) -> RealWorld:
    """Build a RealWorld from JUST the DEM (lowest cells = river/source; a low-elevation
    band = floodplain homes; the highest cells = shelters). OSM building/shelter locations
    are an optional v2 refinement; the geometry test only needs real elevation + distances."""
    elev = build_elevation_from_dem(dem_path, grid_size, bbox=bbox)
    finite = np.isfinite(elev)
    vals = elev[finite]
    lo, hi = float(vals.min()), float(vals.max())
    # Normalize real metres to the synthetic flood-vs-level regime [-1, 7] so the
    # IDENTICAL bathtub mechanic (flood +0.4/onset_steps in _simulate) floods the plain
    # over the horizon. The REAL variable that changes is the grid GEOMETRY — size,
    # relative terrain SHAPE, and agent-to-shelter DISTANCES — which is exactly the
    # FINDINGS root-cause (the synthetic 20x20 was too small to punish hesitation).
    # A linear rescale preserves relative terrain + spatial autocorrelation (so the
    # real-DEM gate still distinguishes it from np.random noise).
    if hi > lo:
        elev = -1.0 + 8.0 * (elev - lo) / (hi - lo)
        lo, hi = -1.0, 7.0

    # river/source = the lowest cells (bottom `river_quantile`)
    thr = float(np.nanquantile(elev, river_quantile))
    initial_water = ((elev <= thr) & finite).astype(int)

    # homes = a low-elevation floodplain band (deterministic, sorted for stability)
    lob = lo + home_band[0] * (hi - lo)
    hib = lo + home_band[1] * (hi - lo)
    home_cells = [
        (int(r), int(c)) for r, c in zip(*np.where((elev >= lob) & (elev <= hib) & finite))
    ]
    home_cells.sort()
    if not home_cells:
        raise ValueError("no floodplain cells found for homes; widen home_band")
    # spread n_homes evenly across the band (deterministic stride)
    stride = max(1, len(home_cells) // n_homes)
    homes = home_cells[::stride][:n_homes] or home_cells[:n_homes]

    # shelters = the highest-ground cells, spread out
    flat = [(float(elev[r, c]), int(r), int(c)) for r, c in zip(*np.where(finite))]
    flat.sort(reverse=True)
    shelters = _spread_pick([(r, c) for _, r, c in flat[: max(50, n_shelters * 10)]], n_shelters)

    return RealWorld(grid_size=grid_size, elev=elev, initial_water=initial_water,
                     homes=homes, shelters=shelters, source=source)


# ── helpers ─────────────────────────────────────────────────────────────────────

def _clip_to_bbox(data, transform, bbox):
    minx, miny, maxx, maxy = bbox
    inv = ~transform
    c0, r0 = inv * (minx, maxy)   # upper-left
    c1, r1 = inv * (maxx, miny)   # lower-right
    r_lo, r_hi = sorted((int(r0), int(r1)))
    c_lo, c_hi = sorted((int(c0), int(c1)))
    r_lo, c_lo = max(0, r_lo), max(0, c_lo)
    r_hi, c_hi = min(data.shape[0], r_hi + 1), min(data.shape[1], c_hi + 1)
    clip = data[r_lo:r_hi, c_lo:c_hi]
    if clip.size == 0:
        raise ValueError(f"bbox {bbox} does not overlap the raster")
    return clip


def _resample(data: np.ndarray, grid_size: int) -> np.ndarray:
    """Resample to (grid_size, grid_size) with bilinear zoom; nan filled with the mean."""
    from scipy.ndimage import zoom

    a = np.asarray(data, dtype=float)
    if np.isnan(a).any():
        a = np.where(np.isnan(a), np.nanmean(a), a)
    zr = grid_size / a.shape[0]
    zc = grid_size / a.shape[1]
    out = zoom(a, (zr, zc), order=1)
    # zoom can be off-by-one; trim/pad to exact size
    out = out[:grid_size, :grid_size]
    if out.shape != (grid_size, grid_size):
        fixed = np.full((grid_size, grid_size), float(out.mean()))
        fixed[: out.shape[0], : out.shape[1]] = out
        out = fixed
    return out


def _spread_pick(cells: Sequence[Tuple[int, int]], k: int) -> List[Tuple[int, int]]:
    """Pick k cells spread apart (greedy farthest-point) for non-clustered shelters."""
    cells = list(cells)
    if not cells:
        raise ValueError("no candidate cells")
    chosen = [cells[0]]
    while len(chosen) < k and len(chosen) < len(cells):
        far = max(
            cells,
            key=lambda p: min((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 for q in chosen),
        )
        if far in chosen:
            break
        chosen.append(far)
    return chosen
