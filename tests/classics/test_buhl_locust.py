"""Faithful-rule + determinism tests for the Buhl et al. (2006) marching-locust
reproduction (the Czirok 1D self-propelled-particle variant).

These pin the RULES, not the locked predictions: the periodic ring geometry, the local
neighbour average over the real ring (bucket grid == brute force), the Czirok alignment
response and sign update, the fixed-speed move + wrap, the order parameter and net-sign,
the direction-flip counter, the density = N/Lr control, the parameter guards, and
determinism. The locked clauses P1-P3 (density crossover, intermittent near-critical
switching, monotone ordering) are graded by examples/repro_buhl_locust/run.py, not here.
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.buhl_locust import (
    LocustModel,
    count_sign_flips,
    ring_delta,
    ring_dist,
    run_single,
    tail_mean,
)


# -- periodic ring geometry ---------------------------------------------------

def test_ring_delta_minimum_image():
    L = 10.0
    # short way round is negative/positive minimum image, not the long way
    assert ring_delta(1.0, 9.0, L) == pytest.approx(2.0)     # 1-9 = -8 -> +2 (wrap)
    assert ring_delta(9.0, 1.0, L) == pytest.approx(-2.0)
    assert ring_delta(2.0, 1.0, L) == pytest.approx(1.0)     # no wrap needed
    assert abs(ring_delta(0.0, 5.0, L)) == pytest.approx(5.0)  # exactly half


def test_ring_dist_is_symmetric_and_wraps():
    L = 8.0
    assert ring_dist(0.5, 7.5, L) == pytest.approx(1.0)      # across the 0/L seam
    assert ring_dist(7.5, 0.5, L) == pytest.approx(1.0)
    assert ring_dist(3.0, 3.0, L) == pytest.approx(0.0)
    assert ring_dist(0.0, 4.0, L) == pytest.approx(4.0)      # half the ring


# -- local neighbour average: bucket grid == brute force ----------------------

def test_local_mean_matches_bruteforce_over_all_agents():
    # The O(N) bucket-grid neighbour average must equal the brute-force all-pairs average
    # (including self) for every agent, on a moderately dense ring.
    m = LocustModel(n=80, Lr=40.0, R=1.5, eta=1.0, beta=2.0, speed=0.1, seed=3)
    cells = m._build_cells()
    for a in m.agent_list:
        assert m._local_mean(a, cells) == pytest.approx(m._local_mean_bruteforce(a))


def test_local_mean_includes_self_and_is_in_range():
    # An isolated agent (empty neighbourhood except itself) has local mean = its own
    # heading exactly, and every local mean lies in [-1, +1].
    m = LocustModel(n=6, Lr=600.0, R=0.5, eta=1.0, beta=2.0, speed=0.1, seed=1)
    cells = m._build_cells()
    for a in m.agent_list:
        u = m._local_mean(a, cells)
        assert -1.0 <= u <= 1.0
    # Force a genuinely isolated agent: put one far from all others.
    a0 = m.agent_list[0]
    a0.x = 0.0
    for b in m.agent_list[1:]:
        b.x = 300.0                    # half a ring away, well beyond R
    cells = m._build_cells()
    assert m._local_mean(a0, cells) == pytest.approx(float(a0.s))


def test_local_mean_of_unanimous_cluster_is_plus_or_minus_one():
    m = LocustModel(n=10, Lr=20.0, R=2.0, eta=1.0, beta=2.0, speed=0.1, seed=0)
    for a in m.agent_list:
        a.x = 5.0                      # all within R of each other
        a.s = 1
    cells = m._build_cells()
    for a in m.agent_list:
        assert m._local_mean(a, cells) == pytest.approx(1.0)
    for a in m.agent_list:
        a.s = -1
    cells = m._build_cells()
    for a in m.agent_list:
        assert m._local_mean(a, cells) == pytest.approx(-1.0)


# -- Czirok alignment response ------------------------------------------------

def test_response_is_signed_monotone_saturating():
    m = LocustModel(n=4, Lr=100.0, R=1.0, eta=1.0, beta=2.0, speed=0.1, seed=0)
    assert m.response(0.0) == pytest.approx(0.0)
    assert m.response(1.0) == pytest.approx(math.tanh(2.0))
    assert m.response(-1.0) == pytest.approx(-math.tanh(2.0))
    # monotone increasing and sign-preserving
    assert m.response(0.5) > m.response(0.2) > 0.0
    assert m.response(-0.5) < m.response(-0.2) < 0.0
    # saturates: |G| < 1 always
    assert abs(m.response(1.0)) < 1.0


def test_zero_noise_locks_a_unanimous_group_forever():
    # With eta=0 a unanimous group has u=+1 (or -1); response is +tanh(beta)>0, so the
    # sign update reproduces the same heading for every agent every tick: the band never
    # loses its perfect order and its direction never reverses.
    m = LocustModel(n=12, Lr=6.0, R=2.0, eta=0.0, beta=3.0, speed=0.05, seed=0)
    for a in m.agent_list:
        a.x = 3.0
        a.s = 1
    for _ in range(50):
        m.step()
    assert m.order_parameter() == pytest.approx(1.0)
    assert all(a.s == 1 for a in m.agent_list)


def test_new_heading_sign_follows_local_mean_without_noise():
    # eta=0: the new heading is exactly sign(G(u)) = sign(u). A unanimous -1 cluster ->
    # every new heading is -1; a unanimous +1 cluster -> +1.
    m = LocustModel(n=8, Lr=20.0, R=2.0, eta=0.0, beta=2.0, speed=0.1, seed=0)
    for a in m.agent_list:
        a.x = 5.0
        a.s = -1
    cells = m._build_cells()
    for a in m.agent_list:
        assert m._new_heading(a, cells) == -1
    for a in m.agent_list:
        a.s = 1
    cells = m._build_cells()
    for a in m.agent_list:
        assert m._new_heading(a, cells) == 1


# -- fixed-speed move + periodic wrap -----------------------------------------

def test_step_moves_at_fixed_speed_in_heading_direction():
    # With eta=0 and a unanimous +1 cluster, every agent advances by exactly +speed per
    # tick (mod Lr); a unanimous -1 cluster advances by -speed.
    speed = 0.1
    m = LocustModel(n=5, Lr=10.0, R=3.0, eta=0.0, beta=3.0, speed=speed, seed=0)
    for a in m.agent_list:
        a.x = 2.0
        a.s = 1
    x0 = [a.x for a in m.agent_list]
    m.step()
    for a, x_before in zip(m.agent_list, x0):
        assert a.x == pytest.approx((x_before + speed) % m.Lr)
    # now flip to -1 and check the move is -speed
    for a in m.agent_list:
        a.s = -1
        a._next_s = -1
    x1 = [a.x for a in m.agent_list]
    # do one raw move by stepping with eta=0 (headings stay -1)
    m.step()
    for a, x_before in zip(m.agent_list, x1):
        assert a.x == pytest.approx((x_before - speed) % m.Lr)


def test_positions_stay_on_ring():
    m = LocustModel(n=30, Lr=15.0, R=1.0, eta=1.5, beta=2.0, speed=0.3, seed=2)
    for _ in range(200):
        m.step()
    for a in m.agent_list:
        assert 0.0 <= a.x < m.Lr


# -- order parameter + net sign -----------------------------------------------

def test_order_parameter_and_net_sign_on_hand_state():
    m = LocustModel(n=10, Lr=100.0, R=1.0, eta=1.0, beta=2.0, speed=0.1, seed=0)
    for a in m.agent_list:
        a.s = 1
    assert m.order_parameter() == pytest.approx(1.0)
    assert m.net_sign() == 1
    # split 6 +1 / 4 -1 -> net = +2, phi = 2/10
    for a in m.agent_list[:4]:
        a.s = -1
    assert m.order_parameter() == pytest.approx(0.2)
    assert m.net_sign() == 1
    assert m.net_direction() == 2
    # exact tie -> phi 0, sign 0
    for a in m.agent_list[:5]:
        a.s = -1
    for a in m.agent_list[5:]:
        a.s = 1
    assert m.order_parameter() == pytest.approx(0.0)
    assert m.net_sign() == 0


# -- direction-flip counter ---------------------------------------------------

def test_count_sign_flips_counts_reversals_and_skips_ties():
    assert count_sign_flips([1, 1, 1], window=10) == 0
    assert count_sign_flips([1, -1, 1], window=10) == 2       # + -> - -> +
    assert count_sign_flips([1, 0, 1], window=10) == 0        # tie skipped, no reversal
    assert count_sign_flips([1, 0, -1], window=10) == 1       # tie skipped, real reversal
    assert count_sign_flips([-1, -1, 1, 1, -1], window=10) == 2
    # window restricts to the trailing slice
    assert count_sign_flips([1, -1, 1, -1, 1, 1, 1], window=2) == 0


def test_tail_mean_averages_trailing_window():
    assert tail_mean([0.0, 0.0, 1.0, 1.0], window=2) == pytest.approx(1.0)
    assert tail_mean([2.0, 4.0], window=10) == pytest.approx(3.0)
    assert tail_mean([], window=5) == 0.0


# -- density control + parameter guards ---------------------------------------

def test_density_is_n_over_ring_length():
    m = LocustModel(n=60, Lr=120.0, R=1.0, eta=1.0, beta=2.0, speed=0.1, seed=0)
    assert m.density == pytest.approx(0.5)
    m2 = LocustModel(n=60, Lr=60.0, R=1.0, eta=1.0, beta=2.0, speed=0.1, seed=0)
    assert m2.density == pytest.approx(1.0)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        LocustModel(n=0, Lr=10.0)
    with pytest.raises(ValueError):
        LocustModel(n=10, Lr=0.0)
    with pytest.raises(ValueError):
        LocustModel(n=10, Lr=10.0, R=0.0)
    with pytest.raises(ValueError):
        LocustModel(n=10, Lr=10.0, eta=-0.1)
    with pytest.raises(ValueError):
        LocustModel(n=10, Lr=10.0, beta=0.0)
    with pytest.raises(ValueError):
        LocustModel(n=10, Lr=10.0, speed=0.0)
    # ring must be bigger than one neighbourhood diameter (2R)
    with pytest.raises(ValueError):
        LocustModel(n=10, Lr=1.5, R=1.0)


def test_run_summary_shape():
    res = run_single(n=40, Lr=80.0, R=1.0, eta=1.0, beta=2.0, speed=0.1, seed=0,
                     n_steps=200, measure_last=100)
    assert res["density"] == pytest.approx(40.0 / 80.0)
    assert len(res["phi_series"]) == len(res["net_sign_series"]) == 201  # includes t=0
    assert 0.0 <= res["steady_phi"] <= 1.0
    assert res["n_direction_flips"] >= 0
    assert res["final_phi"] == pytest.approx(res["phi_series"][-1])


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed():
    a = run_single(n=40, Lr=120.0, R=1.0, eta=1.5, beta=2.0, speed=0.1, seed=7,
                   n_steps=400, measure_last=200)
    b = run_single(n=40, Lr=120.0, R=1.0, eta=1.5, beta=2.0, speed=0.1, seed=7,
                   n_steps=400, measure_last=200)
    assert a["phi_series"] == b["phi_series"]
    assert a["net_sign_series"] == b["net_sign_series"]
    assert a["n_direction_flips"] == b["n_direction_flips"]


def test_different_seed_differs():
    a = run_single(n=40, Lr=120.0, R=1.0, eta=1.5, beta=2.0, speed=0.1, seed=1,
                   n_steps=400, measure_last=200)
    b = run_single(n=40, Lr=120.0, R=1.0, eta=1.5, beta=2.0, speed=0.1, seed=2,
                   n_steps=400, measure_last=200)
    assert a["phi_series"] != b["phi_series"]
