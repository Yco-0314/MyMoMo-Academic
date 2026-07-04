"""Faithful-rule + determinism tests for the Huth & Wissel (1992) fish-schooling reproduction.

These pin the RULES of the zonal SPP core — the bounded-turn geometry, the nested
repulsion/orientation/attraction zones, the repulsion override (identical in both arms), the
two INTEGRATION rules (averaging-all-neighbours vs decide-on-the-single-nearest), the
polarization / NND / CV(NND) metrics, the synchronous update, and determinism. They are
faithfulness tests of the mechanism, NOT prediction tests — the locked P1-P3 (averaging beats
decision on polarization; averaging's CV(NND) smaller; both rules school) are graded by
examples/repro_huth_wissel_fish/run.py against the actual numbers.
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.huth_wissel_fish import (
    AVERAGING,
    DECISION,
    FishAgent,
    HuthWisselModel,
    rotate_toward,
    run_single,
)


# -- bounded-turn geometry ----------------------------------------------------

def test_rotate_toward_snaps_when_within_theta_max():
    # Target within theta_max: the heading snaps exactly to the (unit) target.
    nx, ny = rotate_toward(1.0, 0.0, 0.0, 1.0, theta_max=10.0)
    assert nx == pytest.approx(0.0, abs=1e-12)
    assert ny == pytest.approx(1.0, abs=1e-12)


def test_rotate_toward_caps_at_theta_max_and_stays_unit():
    # Target 90 deg away, but theta_max=0.1 rad: rotate exactly 0.1 rad CCW, stay unit length.
    nx, ny = rotate_toward(1.0, 0.0, 0.0, 1.0, theta_max=0.1)
    assert math.hypot(nx, ny) == pytest.approx(1.0)
    assert math.atan2(ny, nx) == pytest.approx(0.1, abs=1e-9)


def test_rotate_toward_zero_target_leaves_heading():
    # No preference (zero target) -> heading unchanged.
    nx, ny = rotate_toward(0.6, 0.8, 0.0, 0.0, theta_max=0.5)
    assert (nx, ny) == (0.6, 0.8)


def test_rotate_toward_picks_shorter_direction():
    # Target 90 deg CW (below) should rotate CW (negative angle), not CW the long way.
    nx, ny = rotate_toward(1.0, 0.0, 0.0, -1.0, theta_max=0.1)
    assert math.atan2(ny, nx) == pytest.approx(-0.1, abs=1e-9)


# -- repulsion override (identical in both arms) ------------------------------

def _two_fish(rule, *, sep, a_heading=(1.0, 0.0), b_heading=(0.0, 1.0), zor=1.0,
              dzoo=3.0, zoa_width=6.0):
    """Two fish separated by `sep` along +x; b at the origin's right of a. Returns the model
    and a's desired direction under `rule` (no noise, single tick geometry)."""
    m = HuthWisselModel(2, zor=zor, dzoo=dzoo, zoa_width=zoa_width, sigma=0.0, rule=rule,
                        _positions=[(0.0, 0.0), (sep, 0.0)],
                        _headings=[a_heading, b_heading])
    return m, m.desired_direction(m.agent_list[0])


def test_repulsion_overrides_and_steers_away_both_rules():
    # b is INSIDE a's repulsion zone (sep < zor). Both rules must steer a AWAY from b
    # (-x direction), ignoring orientation/attraction — identical override.
    for rule in (AVERAGING, DECISION):
        _, (dx, dy) = _two_fish(rule, sep=0.5, zor=1.0)
        assert dx == pytest.approx(-1.0)
        assert dy == pytest.approx(0.0, abs=1e-12)


def test_orientation_zone_averaging_aligns_to_neighbour_heading():
    # b is in a's ORIENTATION zone (zor <= sep < zor+dzoo). Averaging with a single neighbour
    # aligns a's desired direction to b's heading (0,1).
    _, (dx, dy) = _two_fish(AVERAGING, sep=2.0, zor=1.0, dzoo=3.0)
    assert dx == pytest.approx(0.0, abs=1e-12)
    assert dy == pytest.approx(1.0)


def test_attraction_zone_averaging_steers_toward_neighbour():
    # b is in a's ATTRACTION zone (zor+dzoo <= sep < zor+dzoo+zoa_width). Averaging steers a
    # TOWARD b (b is along +x from a), i.e. desired direction ~ (+1, 0).
    _, (dx, dy) = _two_fish(AVERAGING, sep=6.0, zor=1.0, dzoo=3.0, zoa_width=6.0)
    assert dx == pytest.approx(1.0)
    assert dy == pytest.approx(0.0, abs=1e-12)


def test_no_neighbour_gives_no_preference():
    # b is OUTSIDE all zones (sep > zor+dzoo+zoa_width): desired direction is (0,0) meaning
    # "keep heading" for both rules.
    for rule in (AVERAGING, DECISION):
        _, (dx, dy) = _two_fish(rule, sep=50.0)
        assert (dx, dy) == (0.0, 0.0)


# -- the integration rules diverge on 3+ neighbours ---------------------------

def test_decision_follows_single_nearest_not_the_average():
    # Three fish: a at origin; a NEAR orientation neighbour b just past zor heading +y; and a
    # FAR orientation neighbour c heading -y (opposite). Averaging cancels the two headings
    # (=> falls back / near-zero), but DECISION follows only the NEAREST (b), giving +y.
    zor, dzoo = 1.0, 6.0
    positions = [(0.0, 0.0), (1.5, 0.0), (5.0, 0.0)]     # b nearer than c, both in zoo
    headings = [(1.0, 0.0), (0.0, 1.0), (0.0, -1.0)]     # b:+y, c:-y
    dec = HuthWisselModel(3, zor=zor, dzoo=dzoo, sigma=0.0, rule=DECISION,
                          _positions=positions, _headings=headings)
    ddx, ddy = dec.desired_direction(dec.agent_list[0])
    assert ddy == pytest.approx(1.0)                     # follows nearest b's +y heading
    assert ddx == pytest.approx(0.0, abs=1e-12)

    avg = HuthWisselModel(3, zor=zor, dzoo=dzoo, sigma=0.0, rule=AVERAGING,
                          _positions=positions, _headings=headings)
    adx, ady = avg.desired_direction(avg.agent_list[0])
    # averaging the two opposite headings cancels -> no preference (0,0), the opposite of DEC.
    assert (adx, ady) == (0.0, 0.0)


def test_decision_nearest_attraction_when_no_orientation():
    # Two attraction-zone neighbours at different distances (none in orientation). DECISION
    # steers toward the NEAREST one; here the nearer is along +y so desired ~ (0,+1).
    zor, dzoo, zoa = 1.0, 1.0, 20.0                      # tiny orientation zone
    positions = [(0.0, 0.0), (0.0, 3.0), (10.0, 0.0)]    # nearer neighbour along +y
    headings = [(1.0, 0.0), (1.0, 0.0), (1.0, 0.0)]
    dec = HuthWisselModel(3, zor=zor, dzoo=dzoo, zoa_width=zoa, sigma=0.0, rule=DECISION,
                          _positions=positions, _headings=headings)
    ddx, ddy = dec.desired_direction(dec.agent_list[0])
    assert ddy == pytest.approx(1.0)
    assert ddx == pytest.approx(0.0, abs=1e-12)


# -- metrics ------------------------------------------------------------------

def test_polarization_all_aligned_is_one():
    # All headings identical -> polarization 1.
    m = HuthWisselModel(4, sigma=0.0,
                        _positions=[(0, 0), (2, 0), (0, 2), (2, 2)],
                        _headings=[(1, 0)] * 4)
    assert m.polarization() == pytest.approx(1.0)


def test_polarization_opposed_is_zero():
    # Two +x, two -x -> polarization 0 (headings cancel).
    m = HuthWisselModel(4, sigma=0.0,
                        _positions=[(0, 0), (2, 0), (0, 2), (2, 2)],
                        _headings=[(1, 0), (1, 0), (-1, 0), (-1, 0)])
    assert m.polarization() == pytest.approx(0.0, abs=1e-12)


def test_nnd_and_cv_on_hand_placed_fish():
    # Fish on a line at x=0,1,3: NND(0)=1, NND(1)=1, NND(2 at x=3)=2. mean=4/3.
    m = HuthWisselModel(3, sigma=0.0,
                        _positions=[(0.0, 0.0), (1.0, 0.0), (3.0, 0.0)],
                        _headings=[(1, 0)] * 3)
    nnds = m.nearest_neighbour_distances()
    assert nnds == pytest.approx([1.0, 1.0, 2.0])
    assert m.mean_nnd() == pytest.approx(4.0 / 3.0)
    # CV = std/mean with std over {1,1,2}
    mean = 4.0 / 3.0
    var = ((1 - mean) ** 2 + (1 - mean) ** 2 + (2 - mean) ** 2) / 3.0
    assert m.cv_nnd() == pytest.approx(math.sqrt(var) / mean)


def test_cv_zero_for_uniform_spacing():
    # Equilateral triangle: every fish's nearest neighbour is at distance 1 -> CV = 0.
    h = math.sqrt(3.0) / 2.0
    m = HuthWisselModel(3, sigma=0.0,
                        _positions=[(0.0, 0.0), (1.0, 0.0), (0.5, h)],
                        _headings=[(1, 0)] * 3)
    assert m.cv_nnd() == pytest.approx(0.0, abs=1e-12)


# -- movement + synchronous update --------------------------------------------

def test_fish_moves_by_speed_along_heading_no_noise():
    # A lone fish (no neighbours, sigma=0) keeps its heading and moves exactly s per step.
    m = HuthWisselModel(1, s=0.5, sigma=0.0,
                        _positions=[(0.0, 0.0)], _headings=[(1.0, 0.0)])
    m.step()
    assert (m.agent_list[0].x, m.agent_list[0].y) == pytest.approx((0.5, 0.0))
    m.step()
    assert (m.agent_list[0].x, m.agent_list[0].y) == pytest.approx((1.0, 0.0))


def test_heading_stays_unit_after_step():
    m = HuthWisselModel(20, dzoo=6.0, sigma=0.1, rule=AVERAGING, seed=3)
    for _ in range(30):
        m.step()
    for a in m.agent_list:
        assert math.hypot(a.dx, a.dy) == pytest.approx(1.0, abs=1e-9)


# -- parameter validation -----------------------------------------------------

def test_invalid_params_raise():
    with pytest.raises(ValueError):
        HuthWisselModel(0)
    with pytest.raises(ValueError):
        HuthWisselModel(10, zor=0.0)
    with pytest.raises(ValueError):
        HuthWisselModel(10, theta_max=0.0)
    with pytest.raises(ValueError):
        HuthWisselModel(10, sigma=-1.0)
    with pytest.raises(ValueError):
        HuthWisselModel(10, rule="follow-the-crowd")     # unknown integration rule


# -- run summary shape --------------------------------------------------------

def test_run_summary_shape():
    res = run_single(AVERAGING, n=20, n_steps=60, measure_last=20, seed=0)
    assert res["rule"] == AVERAGING
    assert len(res["polarization_series"]) == len(res["cv_nnd_series"]) == 61  # incl t=0
    assert 0.0 <= res["steady_polarization"] <= 1.0
    assert res["steady_cv_nnd"] >= 0.0
    assert res["steady_mean_nnd"] >= 0.0


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_same_rule():
    a = run_single(AVERAGING, n=30, dzoo=6.0, n_steps=120, measure_last=40, seed=7)
    b = run_single(AVERAGING, n=30, dzoo=6.0, n_steps=120, measure_last=40, seed=7)
    assert a["polarization_series"] == b["polarization_series"]
    assert a["cv_nnd_series"] == b["cv_nnd_series"]
    assert a["steady_polarization"] == b["steady_polarization"]


def test_different_seed_differs():
    a = run_single(AVERAGING, n=30, dzoo=6.0, n_steps=120, measure_last=40, seed=1)
    b = run_single(AVERAGING, n=30, dzoo=6.0, n_steps=120, measure_last=40, seed=2)
    assert a["polarization_series"] != b["polarization_series"]


def test_rules_diverge_at_matched_seed():
    # Same seed, same params, only the integration rule differs: the trajectories must differ
    # (this is the whole locked A/B — averaging vs deciding on one neighbour).
    avg = run_single(AVERAGING, n=40, dzoo=6.0, n_steps=200, measure_last=80, seed=0)
    dec = run_single(DECISION, n=40, dzoo=6.0, n_steps=200, measure_last=80, seed=0)
    assert avg["polarization_series"] != dec["polarization_series"]
