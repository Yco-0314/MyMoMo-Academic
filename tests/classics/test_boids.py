"""Faithful-rule + determinism tests for the Boids flocking (Reynolds 1987)
reproduction.

These pin the periodic geometry, the order parameter phi and mean nearest-neighbour
distance, the three steering rules (separation / alignment / cohesion), the synchronous
steer+move micro-rule with the speed clamp + periodic wrap, the cell-list neighbour
lookup (== brute force), the alignment-OFF control (w_align forced to 0, nothing else
changed), the steady-state estimator, and determinism (same seed -> identical result).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3 (φ>0.7
full, φ<0.3 alignment-OFF, cohesion bounded) are evaluated by examples/repro_boids/run.py.
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.boids import (
    BoidAgent,
    BoidsModel,
    periodic_delta,
    periodic_dist2,
    run_single,
    tail_mean,
)


# -- periodic geometry --------------------------------------------------------

def test_periodic_delta_minimum_image():
    L = 10.0
    assert periodic_delta(1.0, 2.0, L) == pytest.approx(-1.0)
    assert periodic_delta(2.0, 1.0, L) == pytest.approx(1.0)
    # wrapping: 9 and 1 are 2 apart across the boundary, not 8.
    assert periodic_delta(9.0, 1.0, L) == pytest.approx(-2.0)
    assert periodic_delta(1.0, 9.0, L) == pytest.approx(2.0)
    assert abs(periodic_delta(0.0, 7.3, L)) <= L / 2 + 1e-9


def test_periodic_dist2_is_toroidal():
    L = 10.0
    assert periodic_dist2(1.0, 1.0, 4.0, 5.0, L) == pytest.approx(9.0 + 16.0)
    # across the seam: (0.5,0.5) and (9.5,9.5) are sqrt(0.5^2+0.5^2) apart, not huge.
    assert periodic_dist2(0.5, 0.5, 9.5, 9.5, L) == pytest.approx(1.0 + 1.0)


# -- order parameter ----------------------------------------------------------

def test_order_parameter_perfectly_aligned_is_one():
    m = BoidsModel(n=50, L=50.0, seed=0)
    for a in m.agent_list:
        a.vx, a.vy = 0.8, 0.0   # all identical heading (+x)
    assert m.order_parameter() == pytest.approx(1.0)


def test_order_parameter_differing_speeds_same_heading_is_one():
    # phi normalises velocity, so differing speeds but a common heading is still phi=1.
    m = BoidsModel(n=10, L=50.0, seed=0)
    for i, a in enumerate(m.agent_list):
        spd = 0.5 + 0.05 * i
        a.vx, a.vy = spd * math.cos(0.3), spd * math.sin(0.3)
    assert m.order_parameter() == pytest.approx(1.0)


def test_order_parameter_opposed_pair_is_zero():
    m = BoidsModel(n=2, L=50.0, seed=0)
    m.agent_list[0].vx, m.agent_list[0].vy = 1.0, 0.0
    m.agent_list[1].vx, m.agent_list[1].vy = -1.0, 0.0   # opposite headings cancel
    assert m.order_parameter() == pytest.approx(0.0, abs=1e-12)


def test_order_parameter_in_unit_interval():
    m = BoidsModel(n=200, L=50.0, seed=1)
    assert 0.0 <= m.order_parameter() <= 1.0


# -- model construction + invariants ------------------------------------------

def test_population_is_boid_agents_in_box_within_speed_band():
    m = BoidsModel(n=200, L=50.0, vmin=0.5, vmax=1.0, seed=0)
    assert len(m.agent_list) == 200
    assert all(isinstance(a, BoidAgent) for a in m.agent_list)
    for a in m.agent_list:
        assert 0.0 <= a.x < m.L and 0.0 <= a.y < m.L
        spd = math.hypot(a.vx, a.vy)
        assert m.vmin - 1e-9 <= spd <= m.vmax + 1e-9


def test_alignment_off_forces_weight_zero():
    full = BoidsModel(n=10, seed=0, align=True, w_align=1.0)
    off = BoidsModel(n=10, seed=0, align=False, w_align=1.0)
    assert full.w_align == 1.0 and full.align is True
    assert off.w_align == 0.0 and off.align is False
    # the control changes ONLY alignment: every other knob is identical.
    for attr in ("n", "L", "r", "r_sep", "w_sep", "w_coh", "vmin", "vmax"):
        assert getattr(full, attr) == getattr(off, attr)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        BoidsModel(n=0)
    with pytest.raises(ValueError):
        BoidsModel(n=10, r=0.0)
    with pytest.raises(ValueError):
        BoidsModel(n=10, r_sep=0.0)
    with pytest.raises(ValueError):
        BoidsModel(n=10, vmin=2.0, vmax=1.0)   # vmin > vmax
    with pytest.raises(ValueError):
        BoidsModel(n=10, r=1.0, r_sep=5.0)     # r_sep > r


# -- the elementary mechanics: speed clamp + periodic motion ------------------

def test_speed_stays_within_clamp_each_tick():
    m = BoidsModel(n=200, L=50.0, vmin=0.5, vmax=1.0, seed=2)
    for _ in range(5):
        m.step()
        for a in m.agent_list:
            spd = math.hypot(a.vx, a.vy)
            assert m.vmin - 1e-9 <= spd <= m.vmax + 1e-9


def test_positions_wrap_into_box():
    m = BoidsModel(n=200, L=50.0, seed=4)
    for _ in range(20):
        m.step()
    for a in m.agent_list:
        assert 0.0 <= a.x < m.L and 0.0 <= a.y < m.L


def test_displacement_equals_new_velocity():
    # Each boid moves by exactly its (new) velocity per tick (minimum-image terms).
    m = BoidsModel(n=200, L=50.0, seed=3)
    before = [(a.x, a.y) for a in m.agent_list]
    m.step()
    for (x0, y0), a in zip(before, m.agent_list):
        dx = periodic_delta(a.x, x0, m.L)
        dy = periodic_delta(a.y, y0, m.L)
        assert dx == pytest.approx(a.vx, abs=1e-9)
        assert dy == pytest.approx(a.vy, abs=1e-9)


# -- the three steering rules (isolated, faithful) ----------------------------

def test_separation_steers_away_from_a_close_neighbour():
    # Two boids, separation only (no alignment, no cohesion), within r_sep. The focal
    # boid's steering must have a positive component pointing AWAY from the neighbour.
    m = BoidsModel(n=2, L=50.0, r=7.0, r_sep=3.0, w_sep=1.0, w_align=0.0, w_coh=0.0,
                   align=False, seed=0)
    a, b = m.agent_list
    a.x, a.y, a.vx, a.vy = 10.0, 10.0, 0.0, 0.0
    b.x, b.y, b.vx, b.vy = 11.0, 10.0, 0.0, 0.0   # neighbour 1 unit to the +x of a
    cells = m._build_cells()
    neigh = m._neighbours(a, cells)
    ax, ay = m._steering(a, neigh)
    assert ax < 0.0                # steers a in -x (away from b at +x)
    assert ay == pytest.approx(0.0, abs=1e-9)


def test_cohesion_steers_toward_a_distant_neighbour():
    # Cohesion only: focal boid should steer TOWARD a neighbour that is within
    # perception r but outside the separation radius (no separation, no alignment).
    m = BoidsModel(n=2, L=50.0, r=7.0, r_sep=2.0, w_sep=0.0, w_align=0.0, w_coh=1.0,
                   align=False, seed=0)
    a, b = m.agent_list
    a.x, a.y, a.vx, a.vy = 10.0, 10.0, 0.5, 0.0
    b.x, b.y, b.vx, b.vy = 15.0, 10.0, 0.5, 0.0   # 5 units +x: inside r, outside r_sep
    cells = m._build_cells()
    neigh = m._neighbours(a, cells)
    ax, ay = m._steering(a, neigh)
    assert ax > 0.0                # steers a in +x (toward b)
    assert ay == pytest.approx(0.0, abs=1e-9)


def test_alignment_steers_toward_neighbour_velocity():
    # Alignment only: a boid moving +x next to a boid moving +y should gain a +y
    # steering component (toward the neighbour's heading). Place the neighbour outside
    # r_sep so separation does not fire, and zero cohesion.
    m = BoidsModel(n=2, L=50.0, r=7.0, r_sep=2.0, w_sep=0.0, w_align=1.0, w_coh=0.0,
                   align=True, seed=0)
    a, b = m.agent_list
    a.x, a.y, a.vx, a.vy = 10.0, 10.0, 1.0, 0.0   # moving +x
    b.x, b.y, b.vx, b.vy = 14.0, 10.0, 0.0, 1.0   # moving +y, 4 units away (>r_sep)
    cells = m._build_cells()
    neigh = m._neighbours(a, cells)
    ax, ay = m._steering(a, neigh)
    assert ay > 0.0                # alignment pulls a's velocity toward +y


def test_alignment_off_removes_the_alignment_contribution():
    # With align=False the very same configuration produces NO +y alignment pull.
    m = BoidsModel(n=2, L=50.0, r=7.0, r_sep=2.0, w_sep=0.0, w_align=1.0, w_coh=0.0,
                   align=False, seed=0)
    a, b = m.agent_list
    a.x, a.y, a.vx, a.vy = 10.0, 10.0, 1.0, 0.0
    b.x, b.y, b.vx, b.vy = 14.0, 10.0, 0.0, 1.0
    cells = m._build_cells()
    neigh = m._neighbours(a, cells)
    ax, ay = m._steering(a, neigh)
    # no separation (r_sep), no cohesion (w_coh=0), no alignment (off) -> zero steering.
    assert ax == pytest.approx(0.0, abs=1e-12)
    assert ay == pytest.approx(0.0, abs=1e-12)


def test_isolated_boid_has_no_steering_and_keeps_velocity():
    m = BoidsModel(n=1, L=50.0, seed=0)
    a = m.agent_list[0]
    a.vx, a.vy = 0.7, 0.2
    v0 = (a.vx, a.vy)
    m.step()
    # no neighbours -> no steering -> velocity unchanged (within the speed clamp).
    assert (a.vx, a.vy) == pytest.approx(v0)


# -- cell list == brute force -------------------------------------------------

def test_cell_list_neighbours_match_bruteforce():
    m = BoidsModel(n=200, L=50.0, r=7.0, seed=7)
    cells = m._build_cells()
    for a in m.agent_list:
        fast = set(id(b) for b in m._neighbours(a, cells))
        slow = set(id(b) for b in m._neighbours_bruteforce(a))
        assert fast == slow


def test_cell_list_neighbours_match_bruteforce_after_motion():
    m = BoidsModel(n=200, L=50.0, r=7.0, seed=8)
    for _ in range(15):
        m.step()
    cells = m._build_cells()
    for a in m.agent_list:
        fast = set(id(b) for b in m._neighbours(a, cells))
        slow = set(id(b) for b in m._neighbours_bruteforce(a))
        assert fast == slow


def test_mean_nn_distance_matches_bruteforce():
    # The expanding-ring nearest-neighbour search must equal an O(N^2) reference.
    m = BoidsModel(n=200, L=50.0, r=7.0, seed=9)
    for _ in range(10):
        m.step()
    fast = m.mean_nearest_neighbour_distance()
    # brute-force reference
    total = 0.0
    for a in m.agent_list:
        best = float("inf")
        for b in m.agent_list:
            if b is a:
                continue
            d2 = periodic_dist2(a.x, a.y, b.x, b.y, m.L)
            if d2 < best:
                best = d2
        total += math.sqrt(best)
    slow = total / m.n
    assert fast == pytest.approx(slow, abs=1e-9)


# -- steady-state estimator ---------------------------------------------------

def test_tail_mean_is_trailing_window_mean():
    series = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert tail_mean(series, window=2) == pytest.approx(0.45)   # mean(0.4, 0.5)
    assert tail_mean(series, window=100) == pytest.approx(0.3)  # whole series
    assert tail_mean([], window=5) == 0.0


def test_run_summary_shape():
    res = run_single(n=200, seed=0, n_ticks=30, measure_last=10)
    assert res["n"] == 200 and res["align"] is True
    assert len(res["phi_series"]) == 31          # t=0 baseline + 30 ticks
    assert len(res["mean_nn_series"]) == 31
    assert 0.0 <= res["steady_phi"] <= 1.0
    assert res["steady_mean_nn"] >= 0.0


def test_run_rejects_bad_measure_window():
    m = BoidsModel(n=10, seed=0)
    with pytest.raises(ValueError):
        m.run(10, measure_last=0)
    with pytest.raises(ValueError):
        m.run(10, measure_last=50)


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(n=200, seed=42, n_ticks=60, measure_last=20)
    b = run_single(n=200, seed=42, n_ticks=60, measure_last=20)
    assert a["phi_series"] == b["phi_series"]
    assert a["mean_nn_series"] == b["mean_nn_series"]
    assert a["steady_phi"] == b["steady_phi"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(n=200, seed=1, n_ticks=60, measure_last=20)
    b = run_single(n=200, seed=2, n_ticks=60, measure_last=20)
    for res in (a, b):
        assert all(0.0 <= x <= 1.0 for x in res["phi_series"])
        assert all(d >= 0.0 for d in res["mean_nn_series"])


# -- qualitative sanity (the locked grade lives in run.py) --------------------

def test_full_flocks_more_than_alignment_off():
    # Faithfulness sanity, not the locked grade: the 3-rule model reaches a far higher
    # order parameter than the alignment-OFF control, and stays cohesive.
    full = run_single(align=True, seed=0, n_ticks=300, measure_last=100)
    off = run_single(align=False, seed=0, n_ticks=300, measure_last=100)
    assert full["steady_phi"] > off["steady_phi"] + 0.3
    assert off["steady_phi"] < 0.3            # control has no common heading
    # cohesion holds in both arms (mean NN distance well below the box scale).
    assert full["steady_mean_nn"] < 5.0
    assert off["steady_mean_nn"] < 5.0
