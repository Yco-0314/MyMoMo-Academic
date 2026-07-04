"""Faithful-rule + determinism tests for the Couzin et al. (2002) zonal reproduction.

These pin the RULES of the 3-zone self-propelled-particle model (Couzin, Krause, James,
Ruxton & Franks 2002): the bounded turn-toward, the repulsion override, the
orientation/attraction combination, the blind angle, the synchronous update, the constant
speed, the polarization / angular-momentum order parameters, ``from_state`` carry-forward,
parameter validation, and determinism. They are faithfulness tests of the MECHANISM, NOT
prediction tests — the locked clauses P1 (mill), P2 (parallel flock) and P3 (hysteresis)
are graded by examples/repro_couzin_zonal/run.py.

Framing: genuine-agent (3-zone self-propelled particles, 2D, disclosed).
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.couzin_zonal import (
    CouzinZonalModel,
    FishAgent,
    _first_crossing,
    rotate_toward,
    run_single,
    sweep_dzoo,
    tail_mean,
)


# -- rotate_toward: the bounded turn ------------------------------------------

def test_rotate_toward_snaps_within_theta_max():
    # target only a small angle away (< theta_max): heading snaps exactly onto it.
    dx, dy = 1.0, 0.0
    tx, ty = math.cos(0.1), math.sin(0.1)
    nx, ny = rotate_toward(dx, dy, tx, ty, theta_max=0.35)
    assert nx == pytest.approx(tx)
    assert ny == pytest.approx(ty)


def test_rotate_toward_caps_at_theta_max():
    # target is pi/2 away but theta_max is 0.3: heading turns exactly 0.3 rad (CCW), no more.
    nx, ny = rotate_toward(1.0, 0.0, 0.0, 1.0, theta_max=0.3)
    ang = math.atan2(ny, nx)
    assert ang == pytest.approx(0.3)
    assert math.hypot(nx, ny) == pytest.approx(1.0)     # stays a unit heading


def test_rotate_toward_turns_shortest_way():
    # target just clockwise of current heading: the turn must go CW (negative angle), not
    # the long way around.
    nx, ny = rotate_toward(1.0, 0.0, math.cos(-0.2), math.sin(-0.2), theta_max=0.35)
    assert math.atan2(ny, nx) == pytest.approx(-0.2)


def test_rotate_toward_zero_target_keeps_heading():
    # a (0,0) desired direction means "no preference": heading is unchanged.
    nx, ny = rotate_toward(0.6, 0.8, 0.0, 0.0, theta_max=0.35)
    assert (nx, ny) == (0.6, 0.8)


# -- desired direction: repulsion overrides -----------------------------------

def test_repulsion_overrides_and_steers_away():
    # Two agents; b sits just to a's +x within the repulsion radius. a must steer AWAY (-x),
    # ignoring any orientation/attraction. b is at distance 0.5 < zor=1.0.
    m = CouzinZonalModel(
        2, zor=1.0, dzoo=6.0, zoa_width=8.0, seed=0,
        _positions=[(0.0, 0.0), (0.5, 0.0)],
        _headings=[(1.0, 0.0), (1.0, 0.0)])
    a, b = m.agent_list
    tx, ty = m.desired_direction(a)
    assert tx == pytest.approx(-1.0)
    assert ty == pytest.approx(0.0)


def test_orientation_aligns_with_neighbour_heading():
    # b is in a's ORIENTATION zone (zor<=r<zor+dzoo) and has NO attraction/repulsion pull;
    # with only one orientation neighbour the desired direction equals b's heading.
    m = CouzinZonalModel(
        2, zor=1.0, dzoo=6.0, zoa_width=8.0, seed=0,
        _positions=[(0.0, 0.0), (3.0, 0.0)],       # r=3.0 in [1.0, 7.0): orientation zone
        _headings=[(1.0, 0.0), (0.0, 1.0)])        # b points +y
    a, _ = m.agent_list
    tx, ty = m.desired_direction(a)
    assert tx == pytest.approx(0.0)
    assert ty == pytest.approx(1.0)                # a wants to align with b's +y heading


def test_attraction_steers_toward_distant_neighbour():
    # b is in a's ATTRACTION zone only (r beyond orientation but within attraction). With no
    # orientation term, the desired direction is the unit vector TOWARD b.
    m = CouzinZonalModel(
        2, zor=1.0, dzoo=6.0, zoa_width=8.0, seed=0,
        _positions=[(0.0, 0.0), (10.0, 0.0)],      # r=10 in [7.0, 15.0): attraction zone
        _headings=[(1.0, 0.0), (0.0, 1.0)])        # b's heading is irrelevant to attraction
    a, _ = m.agent_list
    tx, ty = m.desired_direction(a)
    assert tx == pytest.approx(1.0)                # steer toward b (+x)
    assert ty == pytest.approx(0.0)


def test_no_neighbours_in_range_keeps_heading():
    # b is beyond the attraction radius: no zone fires, desired direction is (0,0).
    m = CouzinZonalModel(
        2, zor=1.0, dzoo=6.0, zoa_width=8.0, seed=0,
        _positions=[(0.0, 0.0), (100.0, 0.0)],     # r=100 > r_attract=15
        _headings=[(1.0, 0.0), (0.0, 1.0)])
    a, _ = m.agent_list
    assert m.desired_direction(a) == (0.0, 0.0)


def test_blind_angle_excludes_rear_neighbour():
    # b is directly BEHIND a (a faces +x, b at -x in the orientation zone). With a wide rear
    # blind angle, a cannot see b, so no zone fires. With full perception (blind=0) it does.
    common = dict(_positions=[(0.0, 0.0), (-3.0, 0.0)],
                  _headings=[(1.0, 0.0), (0.0, 1.0)])
    seen = CouzinZonalModel(2, zor=1.0, dzoo=6.0, zoa_width=8.0, blind=0.0, seed=0, **common)
    assert seen.desired_direction(seen.agent_list[0]) != (0.0, 0.0)
    # blind angle of pi (rear 180 deg hidden): the directly-behind neighbour is unseen.
    blindm = CouzinZonalModel(2, zor=1.0, dzoo=6.0, zoa_width=8.0, blind=math.pi, seed=0, **common)
    assert blindm.desired_direction(blindm.agent_list[0]) == (0.0, 0.0)


# -- order parameters ---------------------------------------------------------

def test_polarization_all_aligned_is_one():
    # all headings identical -> perfect polarization p = 1.
    m = CouzinZonalModel(
        3, seed=0, _positions=[(0.0, 0.0), (5.0, 0.0), (-5.0, 0.0)],
        _headings=[(1.0, 0.0), (1.0, 0.0), (1.0, 0.0)])
    assert m.polarization() == pytest.approx(1.0)


def test_polarization_opposed_pair_is_zero():
    # two opposed unit headings cancel -> p = 0.
    m = CouzinZonalModel(
        2, seed=0, _positions=[(0.0, 0.0), (5.0, 0.0)],
        _headings=[(1.0, 0.0), (-1.0, 0.0)])
    assert m.polarization() == pytest.approx(0.0)


def test_angular_momentum_perfect_mill_is_one():
    # Four agents on a ring, each heading exactly tangential (CCW): a perfect torus has
    # angular momentum m = 1 while polarization is 0 (headings point every which way).
    pos = [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)]
    tang = [(0.0, 1.0), (-1.0, 0.0), (0.0, -1.0), (1.0, 0.0)]   # r_hat rotated +90 deg
    m = CouzinZonalModel(4, seed=0, _positions=pos, _headings=tang)
    assert m.angular_momentum() == pytest.approx(1.0)
    assert m.polarization() == pytest.approx(0.0, abs=1e-12)


def test_angular_momentum_radial_headings_is_zero():
    # headings pointing radially outward have no tangential component -> m = 0.
    pos = [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)]
    rad = [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)]
    m = CouzinZonalModel(4, seed=0, _positions=pos, _headings=rad)
    assert m.angular_momentum() == pytest.approx(0.0, abs=1e-12)


# -- constant speed + synchronous update --------------------------------------

def test_constant_speed_move_distance():
    # Every agent moves exactly distance s along its heading each step (constant speed).
    m = CouzinZonalModel(
        1, s=2.0, sigma=0.0, seed=0, _positions=[(0.0, 0.0)], _headings=[(1.0, 0.0)])
    a = m.agent_list[0]
    x0, y0 = a.x, a.y
    m.step()
    assert math.hypot(a.x - x0, a.y - y0) == pytest.approx(2.0)


def test_synchronous_update_uses_start_of_step_snapshot():
    # Two mutually-attracting agents move symmetrically because both desired directions are
    # computed from the SAME start-of-step snapshot; after one noise-free step their gap
    # shrinks by 2*s and they stay mirror images about the midpoint.
    m = CouzinZonalModel(
        2, s=1.0, zor=1.0, dzoo=2.0, zoa_width=8.0, sigma=0.0, theta_max=math.pi, seed=0,
        _positions=[(-5.0, 0.0), (5.0, 0.0)],       # r=10 in attraction zone
        _headings=[(1.0, 0.0), (-1.0, 0.0)])        # already facing each other
    a, b = m.agent_list
    m.step()
    assert a.x == pytest.approx(-4.0)
    assert b.x == pytest.approx(4.0)
    assert a.y == pytest.approx(0.0)
    assert b.y == pytest.approx(0.0)


def test_headings_stay_unit_after_noisy_step():
    # After a step with noise, every heading remains a unit vector.
    m = CouzinZonalModel(30, sigma=0.1, seed=3)
    m.step()
    for a in m.agent_list:
        assert math.hypot(a.dx, a.dy) == pytest.approx(1.0)


# -- from_state carry-forward (needed for hysteresis) -------------------------

def test_from_state_carries_positions_and_headings():
    # from_state must copy positions + headings exactly and apply the new dzoo (so the
    # hysteresis ramp continues the SAME swarm, not a fresh one).
    base = CouzinZonalModel(20, dzoo=3.0, seed=1)
    for _ in range(10):
        base.step()
    cont = CouzinZonalModel.from_state(base, dzoo=9.0)
    assert cont.dzoo == 9.0
    assert cont.n == base.n
    for a, b in zip(cont.agent_list, base.agent_list):
        assert (a.x, a.y) == (b.x, b.y)
        assert a.dx == pytest.approx(b.dx)
        assert a.dy == pytest.approx(b.dy)


def test_sweep_returns_final_model_for_carry_forward():
    # sweep_dzoo must expose its final swarm so a down-branch can continue it (the
    # carry-forward that makes hysteresis observable).
    res = sweep_dzoo([2.0, 4.0], n=20, sigma=0.02, seed=0, equilibrate=20,
                     measure_last=10, warmup=20)
    assert "_final_model" in res
    assert isinstance(res["_final_model"], CouzinZonalModel)
    assert res["_final_model"].dzoo == pytest.approx(4.0)
    assert len(res["dzoo"]) == len(res["polarization"]) == len(res["angular_momentum"]) == 2


# -- crossing detector (locates the hysteresis switches) ----------------------

def test_first_crossing_up_and_down():
    dz = [1.0, 2.0, 3.0, 4.0, 5.0]
    vals = [0.1, 0.2, 0.3, 0.9, 0.95]
    # ascending: first dzoo where value crosses 0.65 upward is 4.0.
    assert _first_crossing(dz, vals, 0.65, ascending=True) == 4.0
    # descending on the reversed branch: first place it drops below 0.65.
    dzr = list(reversed(dz))
    valsr = [0.95, 0.9, 0.3, 0.2, 0.1]
    assert _first_crossing(dzr, valsr, 0.65, ascending=False) == 3.0
    # never crosses -> None.
    assert _first_crossing(dz, [0.1, 0.1, 0.1, 0.1, 0.1], 0.65, ascending=True) is None


# -- parameter validation -----------------------------------------------------

def test_invalid_params_raise():
    with pytest.raises(ValueError):
        CouzinZonalModel(0)
    with pytest.raises(ValueError):
        CouzinZonalModel(10, zor=0.0)
    with pytest.raises(ValueError):
        CouzinZonalModel(10, dzoo=-1.0)
    with pytest.raises(ValueError):
        CouzinZonalModel(10, theta_max=0.0)
    with pytest.raises(ValueError):
        CouzinZonalModel(10, sigma=-1.0)
    with pytest.raises(ValueError):
        CouzinZonalModel(10, blind=2 * math.pi)


def test_nested_radii_derivation():
    # r_orient = zor + dzoo; r_attract = r_orient + zoa_width.
    m = CouzinZonalModel(5, zor=1.0, dzoo=6.0, zoa_width=8.0, seed=0)
    assert m.r_orient == pytest.approx(7.0)
    assert m.r_attract == pytest.approx(15.0)


# -- summary helpers ----------------------------------------------------------

def test_tail_mean_averages_trailing_window():
    assert tail_mean([0.0, 0.0, 1.0, 1.0], window=2) == pytest.approx(1.0)
    assert tail_mean([2.0, 4.0], window=10) == pytest.approx(3.0)   # window > len uses all
    assert tail_mean([]) == 0.0


def test_run_summary_shape_and_ranges():
    res = run_single(n=25, dzoo=6.0, n_steps=120, measure_last=40, seed=0)
    assert len(res["polarization_series"]) == len(res["angular_momentum_series"]) == 121
    assert 0.0 <= res["steady_polarization"] <= 1.0
    assert 0.0 <= res["steady_angular_momentum"] <= 1.0
    assert res["dzoo"] == 6.0


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed():
    a = run_single(n=40, dzoo=6.0, n_steps=200, measure_last=60, seed=7)
    b = run_single(n=40, dzoo=6.0, n_steps=200, measure_last=60, seed=7)
    assert a["polarization_series"] == b["polarization_series"]
    assert a["angular_momentum_series"] == b["angular_momentum_series"]


def test_different_seed_differs():
    a = run_single(n=40, dzoo=6.0, n_steps=200, measure_last=60, seed=1)
    b = run_single(n=40, dzoo=6.0, n_steps=200, measure_last=60, seed=2)
    assert a["polarization_series"] != b["polarization_series"]


def test_agent_is_fishagent_and_step_is_noop():
    # the tick lives on the model; the per-agent step is intentionally a no-op that leaves
    # position + heading untouched (faithfulness to the synchronous model-level update).
    m = CouzinZonalModel(3, seed=0)
    a = m.agent_list[0]
    assert isinstance(a, FishAgent)
    x0, y0, dx0, dy0 = a.x, a.y, a.dx, a.dy
    a.step()
    assert (a.x, a.y, a.dx, a.dy) == (x0, y0, dx0, dy0)
