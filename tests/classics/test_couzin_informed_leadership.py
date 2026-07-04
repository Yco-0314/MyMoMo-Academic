"""Faithful-rule + determinism tests for the Couzin et al. (2005) informed-leadership repro.

These pin the RULES of the model — the bounded-turn geometry, the 3-zone social direction
(repulsion override, orientation+attraction blend), the informed goal-weighting
d_desired = normalize(d_soc + omega*g_hat), the accuracy/offset metrics, the informed/naive
split, and determinism — NOT the locked predictions. The locked P1/P2/P3 (leader economy,
fraction-vs-N, averaging-vs-commitment) are graded by
examples/repro_couzin_informed_leadership/run.py.
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.couzin_informed_leadership import (
    InformedLeadershipModel,
    _n_informed_for_fraction,
    angular_difference,
    fraction_to_reach_accuracy,
    rotate_toward,
    run_single,
)


# -- rotate_toward geometry ---------------------------------------------------

def test_rotate_toward_snaps_when_within_theta_max():
    # target only 0.1 rad away, theta_max 0.5 -> snap exactly to target.
    dx, dy = 1.0, 0.0
    tx, ty = math.cos(0.1), math.sin(0.1)
    nx, ny = rotate_toward(dx, dy, tx, ty, 0.5)
    assert nx == pytest.approx(tx)
    assert ny == pytest.approx(ty)


def test_rotate_toward_is_bounded_by_theta_max():
    # target 1.5 rad CCW away, theta_max 0.3 -> rotate exactly 0.3 rad CCW, not all the way.
    dx, dy = 1.0, 0.0
    tx, ty = math.cos(1.5), math.sin(1.5)
    nx, ny = rotate_toward(dx, dy, tx, ty, 0.3)
    ang = math.atan2(ny, nx)
    assert ang == pytest.approx(0.3, abs=1e-9)
    assert math.hypot(nx, ny) == pytest.approx(1.0)


def test_rotate_toward_picks_shorter_direction():
    # target at -1.0 rad (CW). Bounded turn must go CW (negative angle), not CW the long way.
    dx, dy = 1.0, 0.0
    tx, ty = math.cos(-1.0), math.sin(-1.0)
    nx, ny = rotate_toward(dx, dy, tx, ty, 0.4)
    assert math.atan2(ny, nx) == pytest.approx(-0.4, abs=1e-9)


def test_rotate_toward_zero_target_keeps_heading():
    nx, ny = rotate_toward(0.6, 0.8, 0.0, 0.0, 0.5)
    assert (nx, ny) == (0.6, 0.8)


# -- angular difference -------------------------------------------------------

def test_angular_difference_wraps():
    assert angular_difference(0.1, 0.0) == pytest.approx(0.1)
    # 350deg vs 10deg -> -20deg (shortest signed way), not +340deg.
    assert angular_difference(math.radians(350), math.radians(10)) == pytest.approx(
        math.radians(-20), abs=1e-9)
    assert angular_difference(math.pi, 0.0) == pytest.approx(math.pi)


# -- informed / naive split ---------------------------------------------------

def test_informed_are_first_agents_and_carry_unit_goal():
    m = InformedLeadershipModel(n=10, n_informed=3, omega=0.5, goal_angle=0.0, seed=0)
    informed = [a for a in m.agent_list if a.informed]
    naive = [a for a in m.agent_list if not a.informed]
    assert len(informed) == 3
    assert len(naive) == 7
    assert [a.id for a in informed] == [0, 1, 2]           # first ids are informed
    for a in informed:
        assert math.hypot(a.gx, a.gy) == pytest.approx(1.0)  # unit goal
    for a in naive:
        assert (a.gx, a.gy) == (0.0, 0.0)                    # naive: no goal


def test_fraction_to_n_informed_rounds_and_clamps():
    assert _n_informed_for_fraction(100, 0.10) == 10
    assert _n_informed_for_fraction(30, 0.02) == 1          # round(0.6) = 1
    assert _n_informed_for_fraction(30, 0.0) == 0
    assert _n_informed_for_fraction(30, 1.5) == 30          # clamp to n
    assert _n_informed_for_fraction(100, 0.049) == 5        # round(4.9)


# -- social direction: repulsion override -------------------------------------

def test_repulsion_overrides_and_steers_away():
    # Two agents inside the repulsion zone: the focal one must steer directly AWAY from the
    # neighbour, ignoring orientation/attraction. Neighbour to the +x of the focal agent ->
    # social direction points -x.
    m = InformedLeadershipModel(n=2, n_informed=0, zor=2.0, dzoo=6.0, zoa_width=8.0, seed=0)
    a, b = m.agent_list
    a.x, a.y, a.dx, a.dy = 0.0, 0.0, 1.0, 0.0
    b.x, b.y, b.dx, b.dy = 0.5, 0.0, 1.0, 0.0     # inside zor of a
    sx, sy, repelling = m.social_direction(a)
    assert repelling is True
    assert sx == pytest.approx(-1.0)
    assert sy == pytest.approx(0.0)


def test_orientation_aligns_with_neighbour_heading():
    # One neighbour in the ORIENTATION zone (zor..zor+dzoo). No repulsion. Social direction
    # should align with the neighbour's heading (pointing +y here).
    m = InformedLeadershipModel(n=2, n_informed=0, zor=1.0, dzoo=6.0, zoa_width=8.0, seed=0)
    a, b = m.agent_list
    a.x, a.y, a.dx, a.dy = 0.0, 0.0, 1.0, 0.0
    b.x, b.y, b.dx, b.dy = 3.0, 0.0, 0.0, 1.0     # in orientation zone; heading +y
    sx, sy, repelling = m.social_direction(a)
    assert repelling is False
    assert sx == pytest.approx(0.0, abs=1e-12)
    assert sy == pytest.approx(1.0)


def test_attraction_steers_toward_far_neighbour():
    # One neighbour ONLY in the ATTRACTION zone (beyond zor+dzoo, within zor+dzoo+width).
    # Social direction should point TOWARD it (+x here), regardless of its heading.
    m = InformedLeadershipModel(n=2, n_informed=0, zor=1.0, dzoo=2.0, zoa_width=10.0, seed=0)
    a, b = m.agent_list
    a.x, a.y, a.dx, a.dy = 0.0, 0.0, 0.0, 1.0
    b.x, b.y, b.dx, b.dy = 8.0, 0.0, 0.0, -1.0    # in attraction zone (3 < 8 < 13); heading -y
    sx, sy, repelling = m.social_direction(a)
    assert repelling is False
    assert sx == pytest.approx(1.0)               # toward b (+x), ignoring b's heading
    assert sy == pytest.approx(0.0, abs=1e-12)


def test_no_neighbours_gives_no_social_preference():
    # A neighbour far outside all zones -> zero social direction (keep current heading).
    m = InformedLeadershipModel(n=2, n_informed=0, zor=1.0, dzoo=2.0, zoa_width=3.0, seed=0)
    a, b = m.agent_list
    a.x, a.y, a.dx, a.dy = 0.0, 0.0, 1.0, 0.0
    b.x, b.y, b.dx, b.dy = 100.0, 0.0, 0.0, 1.0   # far outside (r_attract = 6)
    sx, sy, repelling = m.social_direction(a)
    assert (sx, sy, repelling) == (0.0, 0.0, False)


# -- informed goal weighting: d_desired = normalize(d_soc + omega*g_hat) ------

def test_informed_blends_social_and_goal():
    # Informed focal agent, one attraction neighbour pulling +x (d_soc = +x). Goal g_hat = +y.
    # With omega=1 the desired direction should be the 45-degree bisector normalize((1,1)).
    m = InformedLeadershipModel(n=2, n_informed=1, omega=1.0, goal_angle=math.pi / 2,
                                zor=1.0, dzoo=2.0, zoa_width=10.0, seed=0)
    a = m.agent_list[0]                            # informed, goal +y
    b = m.agent_list[1]
    a.x, a.y, a.dx, a.dy = 0.0, 0.0, 1.0, 0.0
    a.gx, a.gy = 0.0, 1.0                          # goal +y
    b.x, b.y, b.dx, b.dy = 8.0, 0.0, 1.0, 0.0     # attraction neighbour toward +x
    dx, dy = m.desired_direction(a)
    inv = 1.0 / math.sqrt(2.0)
    assert dx == pytest.approx(inv)
    assert dy == pytest.approx(inv)


def test_naive_ignores_goal_even_if_it_had_one():
    # A naive agent with the SAME social neighbour keeps only the social direction (+x).
    m = InformedLeadershipModel(n=2, n_informed=0, omega=1.0,
                                zor=1.0, dzoo=2.0, zoa_width=10.0, seed=0)
    a, b = m.agent_list
    a.x, a.y, a.dx, a.dy = 0.0, 0.0, 1.0, 0.0
    b.x, b.y, b.dx, b.dy = 8.0, 0.0, 1.0, 0.0
    dx, dy = m.desired_direction(a)
    assert dx == pytest.approx(1.0)
    assert dy == pytest.approx(0.0, abs=1e-12)


def test_informed_goal_suppressed_under_repulsion():
    # Under active repulsion the informed agent just avoids (goal is NOT blended in).
    m = InformedLeadershipModel(n=2, n_informed=1, omega=5.0, goal_angle=math.pi / 2,
                                zor=2.0, dzoo=6.0, zoa_width=8.0, seed=0)
    a, b = m.agent_list
    a.x, a.y, a.dx, a.dy = 0.0, 0.0, 1.0, 0.0
    a.gx, a.gy = 0.0, 1.0
    b.x, b.y = 0.5, 0.0                            # inside zor -> repulsion
    dx, dy = m.desired_direction(a)
    assert dx == pytest.approx(-1.0)               # pure avoidance (-x), goal +y ignored
    assert dy == pytest.approx(0.0, abs=1e-12)


def test_informed_with_no_neighbours_steers_by_goal_alone():
    # No social neighbour, informed -> desired direction is exactly the goal direction.
    m = InformedLeadershipModel(n=2, n_informed=1, omega=0.5, goal_angle=math.pi / 2,
                                zor=1.0, dzoo=2.0, zoa_width=3.0, seed=0)
    a, b = m.agent_list
    a.x, a.y, a.dx, a.dy = 0.0, 0.0, 1.0, 0.0
    a.gx, a.gy = 0.0, 1.0
    b.x, b.y = 100.0, 0.0                          # far outside all zones
    dx, dy = m.desired_direction(a)
    assert dx == pytest.approx(0.0, abs=1e-12)
    assert dy == pytest.approx(1.0)


# -- accuracy / offset metrics ------------------------------------------------

def test_accuracy_is_cos_of_heading_vs_goal():
    # All headings = +x; goal = +x -> accuracy 1. Goal = +y -> accuracy 0. Goal = -x -> -1.
    m = InformedLeadershipModel(n=4, n_informed=2, goal_angle=0.0, seed=0)
    for a in m.agent_list:
        a.dx, a.dy = 1.0, 0.0
    assert m.accuracy() == pytest.approx(1.0)
    m.ref_gx, m.ref_gy, m.ref_goal_angle = 0.0, 1.0, math.pi / 2
    assert m.accuracy() == pytest.approx(0.0, abs=1e-12)
    m.ref_gx, m.ref_gy = -1.0, 0.0
    assert m.accuracy() == pytest.approx(-1.0)


def test_reference_goal_is_bisector_of_two_subgroups():
    # Two informed goals at +40deg and -40deg -> bisector (circular mean) is 0deg (+x).
    goals = [math.radians(40), math.radians(-40)]
    m = InformedLeadershipModel(n=4, n_informed=2, informed_goal_angles=goals, seed=0)
    assert m.ref_goal_angle == pytest.approx(0.0, abs=1e-9)
    assert m.ref_gx == pytest.approx(1.0)


def test_signed_offset_measures_departure_from_bisector():
    # Bisector at 0; force all headings to +30deg -> signed offset ~ +30deg.
    goals = [math.radians(60), math.radians(-60)]
    m = InformedLeadershipModel(n=4, n_informed=2, informed_goal_angles=goals, seed=0)
    for a in m.agent_list:
        a.dx, a.dy = math.cos(math.radians(30)), math.sin(math.radians(30))
    assert m.signed_heading_offset() == pytest.approx(math.radians(30), abs=1e-9)


def test_incoherent_group_has_zero_accuracy():
    # Perfectly opposed headings -> zero mean vector -> accuracy 0 (no defined direction).
    m = InformedLeadershipModel(n=2, n_informed=1, goal_angle=0.0, seed=0)
    m.agent_list[0].dx, m.agent_list[0].dy = 1.0, 0.0
    m.agent_list[1].dx, m.agent_list[1].dy = -1.0, 0.0
    assert m.accuracy() == pytest.approx(0.0)
    assert m.polarization() == pytest.approx(0.0)


# -- constant speed / motion --------------------------------------------------

def test_agents_move_at_constant_speed_along_heading():
    m = InformedLeadershipModel(n=5, n_informed=1, s=2.0, sigma=0.0, seed=1)
    before = [(a.x, a.y) for a in m.agent_list]
    m.step()
    for (x0, y0), a in zip(before, m.agent_list):
        d = math.hypot(a.x - x0, a.y - y0)
        assert d == pytest.approx(m.s, abs=1e-9)   # displacement == speed each step
        assert math.hypot(a.dx, a.dy) == pytest.approx(1.0)  # heading stays unit


# -- validation ---------------------------------------------------------------

def test_invalid_params_raise():
    with pytest.raises(ValueError):
        InformedLeadershipModel(n=0)
    with pytest.raises(ValueError):
        InformedLeadershipModel(n=10, n_informed=11)      # more informed than agents
    with pytest.raises(ValueError):
        InformedLeadershipModel(n=10, omega=-0.1)
    with pytest.raises(ValueError):
        InformedLeadershipModel(n=10, theta_max=0.0)
    with pytest.raises(ValueError):
        InformedLeadershipModel(n=10, n_informed=2,
                                informed_goal_angles=[0.0])  # wrong length


# -- run summary shape --------------------------------------------------------

def test_run_summary_shape_and_realised_fraction():
    r = run_single(n=100, p_inf=0.10, omega=0.5, n_steps=200, measure_last=80, seed=0)
    assert r["n"] == 100 and r["n_informed"] == 10
    assert r["p_inf"] == pytest.approx(0.10)
    assert len(r["accuracy_series"]) == 201          # t=0 baseline + 200 steps
    assert -1.0 <= r["steady_accuracy"] <= 1.0
    assert 0.0 <= r["steady_polarization"] <= 1.0


def test_fraction_to_reach_accuracy_scans_ascending():
    sweep = {
        "realised_p_inf": [0.02, 0.05, 0.10, 0.20],
        "mean_accuracy": [0.40, 0.70, 0.92, 0.98],
    }
    assert fraction_to_reach_accuracy(sweep, 0.9) == 0.10
    assert fraction_to_reach_accuracy(sweep, 0.99) is None    # never reached in the sweep
    assert fraction_to_reach_accuracy(sweep, 0.3) == 0.02     # first fraction already clears


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed():
    a = run_single(n=80, p_inf=0.1, omega=0.5, n_steps=200, measure_last=80, seed=7)
    b = run_single(n=80, p_inf=0.1, omega=0.5, n_steps=200, measure_last=80, seed=7)
    assert a["accuracy_series"] == b["accuracy_series"]
    assert a["steady_accuracy"] == b["steady_accuracy"]


def test_different_seed_differs():
    a = run_single(n=80, p_inf=0.1, omega=0.5, n_steps=200, measure_last=80, seed=1)
    b = run_single(n=80, p_inf=0.1, omega=0.5, n_steps=200, measure_last=80, seed=2)
    assert a["accuracy_series"] != b["accuracy_series"]
