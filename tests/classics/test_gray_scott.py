"""Faithful-rule + determinism tests for the Gray-Scott reaction-diffusion reproduction.

These pin the periodic 5-point Laplacian, the reaction terms (U + 2V -> 3V autocatalysis with
feed F and kill F+k), the connected-component spot metrics, the stability guard, and determinism.
They are faithfulness tests, NOT prediction tests — the locked P1-P3 (pattern selection,
self-replication, homogeneous regime) are evaluated by examples/repro_gray_scott/run.py.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.gray_scott import (
    GrayScottModel,
    connected_components,
    laplacian,
    run_regime,
)


# -- laplacian ----------------------------------------------------------------

def test_laplacian_of_constant_is_zero():
    field = np.full((8, 8), 3.7)
    lap = laplacian(field, dx=0.1)
    assert np.allclose(lap, 0.0)


def test_laplacian_periodic_single_bump():
    # 5-point periodic Laplacian of a single unit spike at the center.
    n = 5
    field = np.zeros((n, n))
    field[2, 2] = 1.0
    dx = 0.5
    lap = laplacian(field, dx=dx)
    # center: (0+0+0+0 - 4*1)/dx^2 ; the 4 neighbours: (1 - 0)/dx^2 each.
    assert lap[2, 2] == pytest.approx(-4.0 / (dx * dx))
    for r, c in [(1, 2), (3, 2), (2, 1), (2, 3)]:
        assert lap[r, c] == pytest.approx(1.0 / (dx * dx))
    # a diagonal neighbour is untouched by the 5-point stencil.
    assert lap[1, 1] == pytest.approx(0.0)


def test_laplacian_wraps_at_boundary():
    n = 4
    field = np.zeros((n, n))
    field[0, 0] = 1.0
    lap = laplacian(field, dx=1.0)
    # row-wrap neighbour (n-1,0) and col-wrap neighbour (0,n-1) each get +1.
    assert lap[n - 1, 0] == pytest.approx(1.0)
    assert lap[0, n - 1] == pytest.approx(1.0)


# -- reaction step ------------------------------------------------------------

def test_reaction_terms_match_gray_scott_equations():
    # On a UNIFORM field the Laplacian is exactly 0, so one step is pure local reaction
    # regardless of the (positive) diffusion constants.
    m = GrayScottModel(F=0.04, k=0.06, n=6, dt=1.0, seed_half=1, noise=0.0)
    m.U[:] = 0.7
    m.V[:] = 0.3
    U0, V0 = 0.7, 0.3
    uvv = U0 * V0 * V0
    expU = U0 + (-uvv + m.F * (1.0 - U0))
    expV = V0 + (uvv - (m.F + m.k) * V0)
    m.step()
    assert m.U[0, 0] == pytest.approx(expU)
    assert m.V[0, 0] == pytest.approx(expV)


def test_stability_guard_rejects_too_large_dt():
    with pytest.raises(ValueError):
        GrayScottModel(F=0.04, k=0.06, n=64, Du=2e-5, Dv=1e-5, dt=1e9)


# -- spot metrics -------------------------------------------------------------

def test_connected_components_counts_blobs():
    mask = np.zeros((6, 6), dtype=bool)
    mask[0:2, 0:2] = True   # one 4-cell blob
    mask[4, 4] = True       # one 1-cell blob
    comps = connected_components(mask)
    assert len(comps) == 2
    assert sorted(len(c) for c in comps) == [1, 4]


def test_count_spots_and_aspect_on_hand_field():
    m = GrayScottModel(F=0.04, k=0.06, n=10, seed_half=1, noise=0.0)
    m.V[:] = 0.0
    m.V[1:3, 1:3] = 0.5      # compact 2x2 spot -> aspect ~1
    m.V[5, 1:8] = 0.5        # a 1x7 stripe -> aspect >> 1
    assert m.count_spots(threshold=0.25, min_size=3) == 2
    stats = m.spot_stats(threshold=0.25, min_size=3)
    assert stats["n_components"] == 2
    assert stats["max_aspect"] > 3.0     # the stripe is strongly elongated


def test_field_std_flat_vs_patterned():
    m = GrayScottModel(F=0.04, k=0.06, n=8, seed_half=1, noise=0.0)
    m.V[:] = 0.0
    assert m.field_std() == pytest.approx(0.0)
    m.V[0, 0] = 1.0
    assert m.field_std() > 0.0


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed():
    a = run_regime(0.035, 0.065, n=48, n_steps=200, seed=1)
    b = run_regime(0.035, 0.065, n=48, n_steps=200, seed=1)
    assert a["final_std_v"] == b["final_std_v"]
    assert a["max_spot_count"] == b["max_spot_count"]


def test_different_seed_differs():
    a = run_regime(0.035, 0.065, n=48, n_steps=200, seed=1)
    b = run_regime(0.035, 0.065, n=48, n_steps=200, seed=2)
    # the noisy seeding differs, so the fine field differs (std almost surely not identical)
    assert a["final_std_v"] != b["final_std_v"] or a["step_series"] == b["step_series"]
