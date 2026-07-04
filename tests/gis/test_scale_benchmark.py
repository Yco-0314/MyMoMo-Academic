"""ADR-024 ladder #3 — the scale test-stone.

Pins that the evacuation model actually RUNS at the paper's resolution (100x100 /
~10,000 cells, n=100 agents) — so an audit verdict means "ran at paper resolution", not
"ran on a 20x20 toy" — and guards the vectorised _bathtub_step against a perf regression
(the Python triple-loop would make a 100x100 sweep take minutes; the vectorised version is
~0.02s/run). This is a scale/perf benchmark, not a real-data fidelity test, so it uses a
synthetic gradient world with verify_real=False.
"""
from __future__ import annotations

import time

import numpy as np
import pytest

from abm_auto.gis._anshuka_real import RealWorld, run_scenario_real


def _gradient_world(n: int) -> RealWorld:
    """A real-sized n×n world with synthetic terrain (gradient) for scale/perf testing."""
    rr, cc = np.meshgrid(np.linspace(0, 1, n), np.linspace(0, 1, n), indexing="ij")
    elev = (-1.0 + 8.0 * (0.6 * cc + 0.4 * rr)).astype(float)  # synthetic-flood regime
    water = np.zeros((n, n), dtype=int)
    water[:, 0] = 1                                            # river on the low (west) edge
    homes = [((i * 3) % n, 2 + (i * 7) % max(2, n // 4)) for i in range(60)]
    shelters = [(0, n - 1), (n - 1, n - 1), (n // 2, n - 1), (n // 4, n - 1)]
    return RealWorld(grid_size=n, elev=elev, initial_water=water,
                     homes=homes, shelters=shelters, source="SYNTH:scale-bench")


@pytest.mark.parametrize("n", [50, 100])
def test_runs_at_paper_resolution(n):
    """The model runs at real resolution (up to the paper's ~100x100) with accounting intact."""
    w = _gradient_world(n)
    r = run_scenario_real(world=w, belief=0.6, alarm_t=0, onset_steps=20,
                          mobility_good_frac=0.7, collaboration=False, seed=0,
                          max_steps=400, verify_real=False)
    assert r.evacuated + r.incapacitated + r.still_moving == 100   # accounting holds at scale
    assert r.evacuated > 0 and r.incapacitated > 0                 # a non-degenerate run


def test_scale_perf_budget_100x100():
    """Perf guard: a 100x100 / n=100 / <=400-step run must finish well under budget.
    Vectorised bathtub ~0.02-0.1s; the 10s budget catches a catastrophic regression
    (e.g. reverting _bathtub_step to the O(9*cells) Python loop)."""
    w = _gradient_world(100)
    t0 = time.perf_counter()
    run_scenario_real(world=w, belief=0.7, alarm_t=0, onset_steps=20,
                      mobility_good_frac=0.7, collaboration=False, seed=0,
                      max_steps=400, verify_real=False)
    dt = time.perf_counter() - t0
    print(f"[scale-bench] 100x100 × 100 agents × ≤400 steps: {dt:.3f}s")
    assert dt < 10.0, f"100x100 run took {dt:.2f}s (>10s) — likely a _bathtub_step perf regression"


def test_deterministic_at_scale():
    """Same seed + same 100x100 world ⇒ identical outcome (determinism survives scale)."""
    w = _gradient_world(100)
    kw = dict(belief=0.5, alarm_t=0, onset_steps=20, mobility_good_frac=0.7,
              collaboration=False, seed=3, max_steps=400, verify_real=False)
    r1 = run_scenario_real(world=w, **kw)
    r2 = run_scenario_real(world=w, **kw)
    assert (r1.evacuated, r1.incapacitated) == (r2.evacuated, r2.incapacitated)
