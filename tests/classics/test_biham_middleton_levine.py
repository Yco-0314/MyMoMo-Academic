"""Faithful-rule + determinism tests for the Biham-Middleton-Levine traffic CA.

These pin the two-species move rule (red east on even ticks, blue north on odd
ticks; a car moves iff its target cell is EMPTY in the CURRENT grid — the classic
simultaneous BML update), toroidal wrap, car conservation, equal red/blue
placement, the active-colour velocity metric, and determinism (same seed =>
identical evolution). They are FAITHFULNESS tests, NOT prediction tests — the
locked P1-P3 (free-flow->gridlock transition, sharp two-phase order, near-step)
are evaluated by examples/repro_biham_middleton_levine/run.py.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.biham_middleton_levine import (
    BLUE,
    EMPTY,
    RED,
    BMLModel,
    _move_colour,
    critical_density,
    place_cars,
    run_single,
    step,
    transition_width,
)


# -- placement ----------------------------------------------------------------

def test_placement_density_and_equal_colours():
    L = 100
    grid = place_cars(L, 0.3, seed=0)
    n_occ = int((grid != EMPTY).sum())
    assert n_occ == round(0.3 * L * L)
    n_red = int((grid == RED).sum())
    n_blue = int((grid == BLUE).sum())
    # split as evenly as possible (red gets the extra when n_occ is odd)
    assert n_red - n_blue in (0, 1)
    assert n_red + n_blue == n_occ


def test_placement_empty_and_full():
    assert int((place_cars(10, 0.0, 0) != EMPTY).sum()) == 0
    full = place_cars(10, 1.0, 0)
    assert int((full != EMPTY).sum()) == 100


def test_placement_rejects_bad_params():
    with pytest.raises(ValueError):
        place_cars(0, 0.3, 0)
    with pytest.raises(ValueError):
        place_cars(10, 1.5, 0)


# -- the two-species move rule ------------------------------------------------

def test_red_moves_east_into_empty():
    g = np.zeros((5, 5), dtype=np.int8)
    g[2, 3] = RED
    new_g, n_moved, n_cars = _move_colour(g, RED)
    assert (n_moved, n_cars) == (1, 1)
    assert new_g[2, 4] == RED and new_g[2, 3] == EMPTY  # east = +1 along columns


def test_blue_moves_north_into_empty():
    g = np.zeros((5, 5), dtype=np.int8)
    g[3, 2] = BLUE
    new_g, n_moved, n_cars = _move_colour(g, BLUE)
    assert (n_moved, n_cars) == (1, 1)
    assert new_g[2, 2] == BLUE and new_g[3, 2] == EMPTY  # north = -1 along rows


def test_moves_wrap_toroidally():
    # red at the last column wraps to column 0; blue at row 0 wraps to the last row.
    gr = np.zeros((5, 5), dtype=np.int8)
    gr[2, 4] = RED
    new_r, _, _ = _move_colour(gr, RED)
    assert new_r[2, 0] == RED and new_r[2, 4] == EMPTY

    gb = np.zeros((5, 5), dtype=np.int8)
    gb[0, 2] = BLUE
    new_b, _, _ = _move_colour(gb, BLUE)
    assert new_b[4, 2] == BLUE and new_b[0, 2] == EMPTY


def test_car_blocked_by_stationary_occupant_stays():
    # a red car whose target holds a BLUE car (blue is not active on a red tick,
    # so it cannot vacate) does not move: the "target empty NOW" test blocks it.
    g = np.zeros((5, 5), dtype=np.int8)
    g[2, 3] = RED
    g[2, 4] = BLUE
    new_g, n_moved, n_cars = _move_colour(g, RED)
    assert (n_moved, n_cars) == (0, 1)
    assert new_g[2, 3] == RED and new_g[2, 4] == BLUE


def test_simultaneous_convoy_only_leader_moves():
    # Classic BML: two adjacent reds. The LEADER's target is empty (moves); the
    # TRAILER's target is occupied NOW (it stays) — the "target empty in the
    # current grid" test is evaluated against the frozen configuration, so a car
    # never chases into a cell that is only vacated on the same tick.
    g = np.zeros((5, 5), dtype=np.int8)
    g[2, 1] = RED
    g[2, 2] = RED
    new_g, n_moved, n_cars = _move_colour(g, RED)
    assert (n_moved, n_cars) == (1, 2)
    assert new_g[2, 1] == RED   # trailer stayed
    assert new_g[2, 3] == RED   # leader advanced
    assert new_g[2, 2] == EMPTY


def test_gridlocked_ring_nobody_moves():
    # A fully packed red ring (every target occupied) is frozen: zero velocity.
    g = np.full((1, 6), RED, dtype=np.int8)
    _new_g, n_moved, n_cars = _move_colour(g, RED)
    assert n_moved == 0 and n_cars == 6


def test_step_alternates_colour_by_tick_parity():
    g = place_cars(16, 0.2, seed=1)
    _g0, colour_even, _m0, _c0 = step(g, tick=0)
    _g1, colour_odd, _m1, _c1 = step(g, tick=1)
    assert colour_even == RED    # even tick -> red active
    assert colour_odd == BLUE    # odd tick -> blue active


def test_move_conserves_car_count():
    # cars are never created or destroyed by a move (occupied count is invariant).
    m = BMLModel(L=64, rho=0.35, seed=2)
    n0 = m.n_cars
    for _ in range(80):
        m.step()
    assert m.n_cars == n0
    # red and blue counts are each individually conserved too
    _e, r, b = m.counts()
    g0 = place_cars(64, 0.35, seed=2)
    assert r == int((g0 == RED).sum())
    assert b == int((g0 == BLUE).sum())


def test_step_velocity_is_moved_over_active_cars():
    # instantaneous velocity returned by BMLModel.step equals n_moved / n_cars of
    # the active colour on that tick. Two reds on different rows with empty targets
    # both advance -> velocity 1.0.
    g = np.zeros((5, 5), dtype=np.int8)
    g[1, 0] = RED   # target (1,1) empty -> moves
    g[3, 2] = RED   # target (3,3) empty -> moves
    m = BMLModel(L=5, rho=0.0, seed=0)
    m.grid = g.copy()
    m.tick = 0      # even -> red active
    v = m.step()
    assert v == pytest.approx(1.0)  # both reds moved

    # one blocked (blue ahead), one free -> velocity 0.5
    g2 = np.zeros((5, 5), dtype=np.int8)
    g2[1, 0] = RED          # free -> moves
    g2[3, 2] = RED          # blocked by a stationary blue ahead
    g2[3, 3] = BLUE
    m2 = BMLModel(L=5, rho=0.0, seed=0)
    m2.grid = g2.copy()
    m2.tick = 0
    assert m2.step() == pytest.approx(0.5)


# -- transition-analysis helpers (pure, on hand-built curves) -----------------

def test_critical_density_and_width_on_step_curve():
    # a synthetic sharp curve: v = 1 below 0.3, drops linearly to 0 across [0.3, 0.4].
    def v_of(rho):
        if rho <= 0.30:
            return 1.0
        if rho >= 0.40:
            return 0.0
        return 1.0 - (rho - 0.30) / 0.10
    rhos = [round(0.02 * k, 2) for k in range(0, 36)]  # 0.00..0.70
    rows = [{"rho": r, "mean_velocity": v_of(r)} for r in rhos]
    rho_c = critical_density(rows)
    width = transition_width(rows, high=0.9, low=0.1)
    assert rho_c is not None and 0.30 <= rho_c <= 0.40
    # 0.9->0.1 spans [0.31, 0.39] = 0.08 wide on this exact ramp
    assert width is not None and width < 0.15


def test_critical_density_none_when_never_crosses():
    rows = [{"rho": 0.1, "mean_velocity": 1.0}, {"rho": 0.2, "mean_velocity": 0.99}]
    assert critical_density(rows) is None  # never drops below 0.5


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_grid():
    a = BMLModel(L=48, rho=0.3, seed=7)
    b = BMLModel(L=48, rho=0.3, seed=7)
    assert np.array_equal(a.grid, b.grid)          # identical placement
    for _ in range(200):
        a.step()
        b.step()
    assert np.array_equal(a.grid, b.grid)          # identical evolution, bit-for-bit


def test_determinism_run_summary_reproducible():
    a = run_single(0.3, L=48, seed=3, warmup=100, measure=100)
    b = run_single(0.3, L=48, seed=3, warmup=100, measure=100)
    assert a["mean_velocity"] == b["mean_velocity"]
    assert a["velocity_series"] == b["velocity_series"]


def test_different_seed_differs():
    a = BMLModel(L=48, rho=0.3, seed=1)
    b = BMLModel(L=48, rho=0.3, seed=2)
    assert not np.array_equal(a.grid, b.grid)      # different placement
