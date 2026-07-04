"""Faithful-rule + determinism tests for the Vicsek flocking (Vicsek et al. 1995)
reproduction.

These pin the periodic geometry, the order parameter phi, the synchronous align+move
micro-rule (constant speed, mean-neighbour heading + bounded noise, periodic wrap), the
cell-list neighbour lookup (== brute force), the steady-state estimator, and determinism
(same seed -> identical result). They are faithfulness tests, NOT prediction tests (the
locked predictions P1-P3 are evaluated by examples/repro_vicsek_flocking/run.py).
"""
from __future__ import annotations

import cmath
import math

import pytest

from abm_auto.classics.vicsek import (
    ParticleAgent,
    VicsekModel,
    periodic_delta,
    periodic_dist2,
    run_single,
    steady_phi,
)


# -- periodic geometry --------------------------------------------------------

def test_periodic_delta_minimum_image():
    L = 10.0
    assert periodic_delta(1.0, 2.0, L) == pytest.approx(-1.0)
    assert periodic_delta(2.0, 1.0, L) == pytest.approx(1.0)
    # wrapping: 9 and 1 are 2 apart across the boundary, not 8.
    assert periodic_delta(9.0, 1.0, L) == pytest.approx(-2.0)
    assert periodic_delta(1.0, 9.0, L) == pytest.approx(2.0)
    # within (-L/2, L/2]
    assert abs(periodic_delta(0.0, 7.3, L)) <= L / 2 + 1e-9


def test_periodic_dist2_is_toroidal():
    L = 10.0
    # straight-line interior distance
    assert periodic_dist2(1.0, 1.0, 4.0, 5.0, L) == pytest.approx(9.0 + 16.0)
    # across the seam: (0.5,0.5) and (9.5,9.5) are sqrt(0.5^2+0.5^2)*... apart, not huge.
    assert periodic_dist2(0.5, 0.5, 9.5, 9.5, L) == pytest.approx(1.0 + 1.0)


# -- order parameter ----------------------------------------------------------

def test_order_parameter_perfectly_aligned_is_one():
    m = VicsekModel(n=50, L=12.0, eta=0.5, seed=0)
    for a in m.agent_list:
        a.theta = 0.7   # all identical heading
    assert m.order_parameter() == pytest.approx(1.0)


def test_order_parameter_opposed_pair_is_zero():
    m = VicsekModel(n=2, L=12.0, eta=0.5, seed=0)
    m.agent_list[0].theta = 0.0
    m.agent_list[1].theta = math.pi   # opposite directions cancel
    assert m.order_parameter() == pytest.approx(0.0, abs=1e-12)


def test_order_parameter_in_unit_interval():
    m = VicsekModel(n=300, L=12.0, eta=3.0, seed=1)
    phi = m.order_parameter()
    assert 0.0 <= phi <= 1.0


# -- model construction + invariants ------------------------------------------

def test_population_is_particle_agents_in_box():
    m = VicsekModel(n=300, L=12.0, v=0.03, r=1.0, eta=0.5, seed=0)
    assert len(m.agent_list) == 300
    assert all(isinstance(a, ParticleAgent) for a in m.agent_list)
    for a in m.agent_list:
        assert 0.0 <= a.x < m.L and 0.0 <= a.y < m.L
        assert 0.0 <= a.theta < 2.0 * math.pi


def test_density_matches_n_over_L_squared():
    m = VicsekModel(n=300, L=12.0, eta=0.5, seed=0)
    assert m.density == pytest.approx(300 / 144.0)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        VicsekModel(n=0, eta=0.5)
    with pytest.raises(ValueError):
        VicsekModel(n=10, r=0.0, eta=0.5)
    with pytest.raises(ValueError):
        VicsekModel(n=10, eta=-0.1)


# -- the elementary mechanics: constant speed + neighbour alignment -----------

def test_speed_is_constant_each_move():
    # Every particle displaces exactly v per tick (in minimum-image terms).
    m = VicsekModel(n=300, L=12.0, v=0.03, r=1.0, eta=1.0, seed=2)
    before = [(a.x, a.y) for a in m.agent_list]
    m.step()
    for (x0, y0), a in zip(before, m.agent_list):
        dx = periodic_delta(a.x, x0, m.L)
        dy = periodic_delta(a.y, y0, m.L)
        assert math.hypot(dx, dy) == pytest.approx(m.v, abs=1e-9)


def test_positions_wrap_into_box():
    m = VicsekModel(n=300, L=12.0, eta=2.0, seed=4)
    for _ in range(20):
        m.step()
    for a in m.agent_list:
        assert 0.0 <= a.x < m.L and 0.0 <= a.y < m.L


def test_zero_noise_aligned_flock_stays_aligned():
    # With eta=0 and all headings identical, the mean-neighbour heading equals theta and
    # there is no noise, so a perfectly ordered flock stays perfectly ordered (phi==1).
    m = VicsekModel(n=300, L=12.0, eta=0.0, seed=5)
    for a in m.agent_list:
        a.theta = 1.234
    for _ in range(10):
        m.step()
    assert m.order_parameter() == pytest.approx(1.0, abs=1e-9)


def test_new_heading_is_mean_neighbour_angle_plus_bounded_noise():
    # Force eta and check a single particle's staged heading equals arg(neighbour sum)
    # plus a noise term inside [-eta/2, eta/2].
    m = VicsekModel(n=300, L=12.0, eta=0.8, seed=6)
    cells = m._build_cells()
    a = m.agent_list[0]
    expected_mean = cmath.phase(m._neighbor_sum(a, cells))
    # Re-run the heading stage deterministically by stepping once and recovering noise.
    # Instead, verify the rule directly: stage headings, then for each agent the deviation
    # from its mean neighbour angle is within the noise bound.
    means = {ag.id: cmath.phase(m._neighbor_sum(ag, cells)) for ag in m.agent_list}
    m.step()  # consumes one noise draw per agent; positions/headings now updated
    # After step, theta_i = mean_i + noise_i with |noise| <= eta/2 (mod 2pi wrap).
    for ag in m.agent_list:
        dev = ag.theta - means[ag.id]
        # bring into (-pi, pi]
        dev = (dev + math.pi) % (2 * math.pi) - math.pi
        assert abs(dev) <= m.eta / 2.0 + 1e-9
    assert isinstance(expected_mean, float)


def test_neighbour_sum_includes_self():
    # An isolated particle (no others within r) has neighbour sum = its own unit vector,
    # so its mean heading equals its current heading.
    m = VicsekModel(n=1, L=12.0, eta=0.0, seed=0)
    a = m.agent_list[0]
    a.theta = 0.9
    cells = m._build_cells()
    s = m._neighbor_sum(a, cells)
    assert cmath.phase(s) == pytest.approx(0.9)
    assert abs(s) == pytest.approx(1.0)


# -- cell list == brute force -------------------------------------------------

def test_cell_list_matches_bruteforce():
    m = VicsekModel(n=300, L=12.0, r=1.0, eta=0.5, seed=7)
    cells = m._build_cells()
    for a in m.agent_list:
        fast = m._neighbor_sum(a, cells)
        slow = m._neighbor_sum_bruteforce(a)
        assert abs(fast - slow) < 1e-12


def test_cell_list_matches_bruteforce_after_motion():
    # Still exact after particles have moved and re-bucketed across the run.
    m = VicsekModel(n=300, L=12.0, r=1.0, eta=2.0, seed=8)
    for _ in range(15):
        m.step()
    cells = m._build_cells()
    for a in m.agent_list:
        assert abs(m._neighbor_sum(a, cells) - m._neighbor_sum_bruteforce(a)) < 1e-12


# -- steady-state estimator ---------------------------------------------------

def test_steady_phi_is_tail_mean():
    series = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert steady_phi(series, window=2) == pytest.approx(0.45)   # mean(0.4, 0.5)
    assert steady_phi(series, window=100) == pytest.approx(0.3)  # whole series
    assert steady_phi([], window=5) == 0.0


def test_run_summary_shape():
    res = run_single(n=300, eta=1.0, seed=0, n_ticks=30, measure_last=10)
    assert res["n"] == 300 and res["eta"] == 1.0
    assert len(res["phi_series"]) == 31              # t=0 baseline + 30 ticks
    assert 0.0 <= res["steady_phi"] <= 1.0
    assert 0.0 <= res["final_phi"] <= 1.0


def test_run_rejects_bad_measure_window():
    m = VicsekModel(n=10, eta=0.5, seed=0)
    with pytest.raises(ValueError):
        m.run(10, measure_last=0)
    with pytest.raises(ValueError):
        m.run(10, measure_last=50)


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(n=300, eta=2.0, seed=42, n_ticks=60, measure_last=20)
    b = run_single(n=300, eta=2.0, seed=42, n_ticks=60, measure_last=20)
    assert a["phi_series"] == b["phi_series"]
    assert a["steady_phi"] == b["steady_phi"]
    assert a["final_phi"] == b["final_phi"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(n=300, eta=3.0, seed=1, n_ticks=60, measure_last=20)
    b = run_single(n=300, eta=3.0, seed=2, n_ticks=60, measure_last=20)
    for res in (a, b):
        assert all(0.0 <= x <= 1.0 for x in res["phi_series"])
        assert 0.0 <= res["steady_phi"] <= 1.0


# -- qualitative sanity (the locked grading lives in run.py) -------------------

def test_low_noise_orders_high_noise_disorders():
    # Faithfulness sanity, not the locked grade: low noise -> high phi, high noise -> low.
    lo = run_single(n=300, eta=0.1, seed=0, n_ticks=300, measure_last=100)
    hi = run_single(n=300, eta=5.0, seed=0, n_ticks=300, measure_last=100)
    assert lo["steady_phi"] > 0.8
    assert hi["steady_phi"] < 0.2
    assert lo["steady_phi"] > hi["steady_phi"]
