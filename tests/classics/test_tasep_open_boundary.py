"""Faithful-rule + determinism tests for the open-boundary TASEP reproduction.

These pin the MECHANICS of the totally asymmetric simple exclusion process on an open
chain — the totally-asymmetric right-only hop, hard-core exclusion, the rate-gated left
injection / right extraction, the L+1 candidate-move set, central-bond current counting,
central-third bulk density, and determinism. They are faithfulness tests of the RULES, NOT
prediction tests — the locked clauses P1/P2/P3 (maximal-current plateau J=1/4, low-density
J=alpha(1-alpha) & rho=alpha, coexistence density jump) are graded by
examples/repro_tasep_open_boundary/run.py.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.tasep_open_boundary import (
    LEFT_INJECT,
    TASEP,
    mean_field_current,
    mean_field_density,
    profile_linearity,
    run_many_seeds,
    run_tasep,
)


# -- construction / validation -------------------------------------------------

def test_invalid_params_raise():
    with pytest.raises(ValueError):
        TASEP(L=2)                      # too short (need left, bulk, right)
    with pytest.raises(ValueError):
        TASEP(L=50, alpha=1.5)          # rate out of [0,1]
    with pytest.raises(ValueError):
        TASEP(L=50, beta=-0.1)
    with pytest.raises(ValueError):
        run_tasep(50, 0.5, 0.5, warmup=0, measure=0)   # measure must be > 0
    with pytest.raises(ValueError):
        run_many_seeds(50, 0.5, 0.5, warmup=10, measure=10, n_seeds=0)


def test_starts_empty():
    m = TASEP(L=100, alpha=0.5, beta=0.5, seed=0)
    assert m.occ.shape == (100,)
    assert int(m.occ.sum()) == 0
    assert m.central_bond == 50


# -- the elementary bulk hop (totally asymmetric + exclusion) ------------------

def test_bulk_hop_moves_particle_right():
    # An isolated particle with an empty right neighbour hops right (rate-1, u<1 always).
    m = TASEP(L=10, alpha=0.5, beta=0.5, seed=0)
    m.occ[:] = 0
    m.occ[3] = 1
    hopped = m._apply_move(3, 0.999)     # bulk bond 3 -> 4
    assert hopped == 0                   # not the central bond, so returns 0
    assert m.occ[3] == 0 and m.occ[4] == 1


def test_bulk_hop_blocked_by_occupied_right_neighbour():
    # Hard-core exclusion: a particle cannot hop onto an occupied site.
    m = TASEP(L=10, alpha=0.5, beta=0.5, seed=0)
    m.occ[:] = 0
    m.occ[3] = 1
    m.occ[4] = 1
    m._apply_move(3, 0.0)                # attempt bond 3 -> 4 (right occupied)
    assert m.occ[3] == 1 and m.occ[4] == 1   # unchanged


def test_no_left_hop_totally_asymmetric():
    # There is no leftward move: a particle with an empty LEFT neighbour but occupied right
    # neighbour is stuck (TASEP is totally asymmetric — hops go only rightwards).
    m = TASEP(L=10, alpha=0.0, beta=0.0, seed=0)
    m.occ[:] = 0
    m.occ[5] = 1
    m.occ[6] = 1
    # every bulk bond attempt leaves this pair frozen (5 can't move; 6 could only if 7 empty)
    m._apply_move(4, 0.0)               # bond 4->5: site4 empty, nothing to move
    assert m.occ[5] == 1
    # site 5 can never move left; only bond 5->6 could move it and 6 is occupied
    m._apply_move(5, 0.0)
    assert m.occ[5] == 1 and m.occ[6] == 1


def test_central_bond_hop_is_counted():
    # A successful hop across the fixed central bond returns 1 (this is what the current
    # counter sums).
    m = TASEP(L=20, alpha=0.5, beta=0.5, seed=0)   # central_bond = 10
    m.occ[:] = 0
    m.occ[10] = 1
    counted = m._apply_move(10, 0.5)               # bond 10 -> 11
    assert counted == 1
    assert m.occ[10] == 0 and m.occ[11] == 1


# -- boundaries (rate-gated injection / extraction) ----------------------------

def test_left_injection_respects_rate_and_occupancy():
    m = TASEP(L=10, alpha=0.4, beta=0.5, seed=0)
    m.occ[:] = 0
    # u < alpha injects into empty site 0
    m._apply_move(LEFT_INJECT, 0.1)
    assert m.occ[0] == 1
    # u >= alpha does NOT inject
    m.occ[0] = 0
    m._apply_move(LEFT_INJECT, 0.9)
    assert m.occ[0] == 0
    # cannot inject onto an already-occupied site 0 even with u < alpha
    m.occ[0] = 1
    m._apply_move(LEFT_INJECT, 0.0)
    assert m.occ[0] == 1


def test_right_extraction_respects_rate_and_occupancy():
    L = 10
    m = TASEP(L=L, alpha=0.5, beta=0.3, seed=0)
    m.occ[:] = 0
    m.occ[L - 1] = 1
    # u >= beta does NOT extract
    m._apply_move(L - 1, 0.9)
    assert m.occ[L - 1] == 1
    # u < beta extracts an occupied right site
    m._apply_move(L - 1, 0.1)
    assert m.occ[L - 1] == 0
    # nothing to extract from an empty right site
    m._apply_move(L - 1, 0.0)
    assert m.occ[L - 1] == 0


def test_alpha_zero_beta_zero_chain_is_frozen_after_fill():
    # With alpha=0 no particle ever enters; the chain stays empty forever.
    m = TASEP(L=50, alpha=0.0, beta=0.5, seed=1)
    for _ in range(200):
        m.sweep()
    assert int(m.occ.sum()) == 0


def test_beta_zero_chain_fills_and_current_vanishes():
    # With beta=0 particles enter (alpha>0) but can never leave: the chain saturates to
    # all-occupied and the steady-state current is 0 (nowhere to hop).
    res = run_tasep(80, alpha=0.6, beta=0.0, warmup=800, measure=800, seed=0)
    assert res["bulk_density"] > 0.98        # jammed full
    assert res["current"] < 0.02             # no throughput


# -- conservation of the sweep bookkeeping -------------------------------------

def test_sweep_returns_nonneg_and_updates_occupancy():
    m = TASEP(L=60, alpha=0.8, beta=0.8, seed=2)
    total = 0
    for _ in range(300):
        total += m.sweep()
    assert total > 0                         # in the maximal-current regime hops happen
    assert set(np.unique(m.occ)).issubset({0, 1})   # occupations stay binary


def test_bulk_density_reads_central_third():
    m = TASEP(L=90, alpha=0.5, beta=0.5, seed=0)
    m.occ[:] = 0
    m.occ[30:60] = 1                          # fill exactly the central third
    assert m.bulk_density() == pytest.approx(1.0)
    m.occ[:] = 0
    assert m.bulk_density() == pytest.approx(0.0)


# -- analytic mean-field targets (the phase-diagram reference) -----------------

def test_mean_field_current_branches():
    # low-density (alpha<0.5, alpha<beta): J = alpha(1-alpha)
    assert mean_field_current(0.3, 0.8) == pytest.approx(0.3 * 0.7)
    # high-density (beta<0.5, beta<alpha): J = beta(1-beta)
    assert mean_field_current(0.8, 0.3) == pytest.approx(0.3 * 0.7)
    # maximal-current (both > 0.5): J = 1/4
    assert mean_field_current(0.7, 0.9) == pytest.approx(0.25)
    assert mean_field_current(0.9, 0.7) == pytest.approx(0.25)


def test_mean_field_density_branches():
    assert mean_field_density(0.3, 0.8) == pytest.approx(0.3)        # rho = alpha
    assert mean_field_density(0.8, 0.3) == pytest.approx(0.7)        # rho = 1 - beta
    assert mean_field_density(0.7, 0.9) == pytest.approx(0.5)        # rho = 1/2


def test_profile_linearity_on_exact_line():
    # A perfectly linear ramp profile gives R^2 ~ 1 and the fitted slope of the ramp.
    n = 120
    prof = np.linspace(0.2, 0.8, n)
    lin = profile_linearity(prof)
    assert lin["r2"] == pytest.approx(1.0, abs=1e-9)
    assert lin["slope"] == pytest.approx((0.8 - 0.2) / (n - 1), rel=1e-6)
    # a flat profile has ~zero slope
    flat = np.full(n, 0.5)
    assert abs(profile_linearity(flat)["slope"]) < 1e-9


# -- determinism ---------------------------------------------------------------

def test_determinism_same_seed():
    a = run_tasep(120, 0.7, 0.9, warmup=200, measure=400, seed=7)
    b = run_tasep(120, 0.7, 0.9, warmup=200, measure=400, seed=7)
    assert a["current"] == b["current"]
    assert a["bulk_density"] == b["bulk_density"]
    assert a["density_profile"] == b["density_profile"]


def test_different_seed_differs():
    a = run_tasep(120, 0.5, 0.5, warmup=200, measure=400, seed=1)
    b = run_tasep(120, 0.5, 0.5, warmup=200, measure=400, seed=2)
    # different RNG streams give different microscopic trajectories -> different mean current
    assert a["current"] != b["current"] or a["bulk_density"] != b["bulk_density"]


def test_run_many_seeds_shape_and_determinism():
    r1 = run_many_seeds(100, 0.7, 0.9, warmup=200, measure=400, n_seeds=3, seed_base=0)
    r2 = run_many_seeds(100, 0.7, 0.9, warmup=200, measure=400, n_seeds=3, seed_base=0)
    assert len(r1["per_seed_current"]) == 3
    assert len(r1["mean_density_profile"]) == 100
    assert r1["mean_current"] == r2["mean_current"]                 # deterministic
    assert r1["per_seed_current"] == r2["per_seed_current"]
