"""Faithful-rule + determinism tests for the Kuramoto (1975) reproduction.

These pin the synchronous Euler update, the mean-field coupling identity (the O(N)
path must equal the brute-force O(N^2) all-pairs sum), the fixed natural-frequency
draw, the order parameter, the analytic K_c, and determinism (same seed -> identical
result). They are faithfulness tests, NOT prediction tests (the predictions P1-P3 are
evaluated by examples/repro_kuramoto/run.py).
"""
from __future__ import annotations

import cmath
import math

import pytest

from abm_auto.classics.kuramoto import (
    KuramotoModel,
    OscillatorAgent,
    critical_coupling_normal,
    run_many_seeds,
    run_single,
    steady_r,
)


def test_order_parameter_all_in_phase_is_one():
    # All phases equal -> perfectly coherent -> r = 1.
    m = KuramotoModel(8, K=0.0, dt=0.05, seed=0)
    for a in m.agent_list:
        a.theta = 1.234
    assert m.order_parameter() == pytest.approx(1.0, abs=1e-12)


def test_order_parameter_uniform_phases_is_near_zero():
    # N phases spread evenly around the circle -> the unit vectors cancel -> r ~ 0.
    m = KuramotoModel(12, K=0.0, dt=0.05, seed=0)
    for i, a in enumerate(m.agent_list):
        a.theta = 2.0 * math.pi * i / m.n
    assert m.order_parameter() == pytest.approx(0.0, abs=1e-12)


def test_mean_field_coupling_equals_bruteforce():
    # The O(N) mean-field coupling term used in step() must equal the brute-force
    # all-pairs sum_j sin(theta_j - theta_i) for every agent, on an arbitrary phase set.
    m = KuramotoModel(40, K=2.0, dt=0.05, seed=3)
    z = sum(cmath.exp(1j * a.theta) for a in m.agent_list)
    for a in m.agent_list:
        mean_field_term = (cmath.exp(-1j * a.theta) * z).imag
        brute = m._coupling_bruteforce(a)
        assert mean_field_term == pytest.approx(brute, abs=1e-9)


def test_zero_coupling_each_oscillator_drifts_at_its_own_omega():
    # With K=0 there is no coupling: theta_i(t) = theta_i(0) + omega_i * t * dt exactly.
    m = KuramotoModel(5, K=0.0, dt=0.05, seed=1)
    theta0 = [a.theta for a in m.agent_list]
    omega = [a.omega for a in m.agent_list]
    n_steps = 10
    for _ in range(n_steps):
        m.step()
    for a, t0, w in zip(m.agent_list, theta0, omega):
        expected = t0 + w * n_steps * m.dt
        assert a.theta == pytest.approx(expected, abs=1e-9)


def test_natural_frequencies_are_fixed_over_the_run():
    # omega is drawn once at construction and never changes during stepping.
    m = KuramotoModel(20, K=3.0, dt=0.05, seed=2)
    omega_before = [a.omega for a in m.agent_list]
    for _ in range(50):
        m.step()
    omega_after = [a.omega for a in m.agent_list]
    assert omega_before == omega_after


def test_single_step_matches_explicit_euler_formula():
    # One synchronous Euler tick must reproduce the textbook update exactly for every
    # oscillator, computed independently from the start-of-tick snapshot.
    m = KuramotoModel(6, K=1.5, dt=0.05, seed=7)
    theta0 = [a.theta for a in m.agent_list]
    omega = [a.omega for a in m.agent_list]
    n = m.n
    m.step()
    for i, a in enumerate(m.agent_list):
        coupling = math.fsum(math.sin(theta0[j] - theta0[i]) for j in range(n))
        expected = theta0[i] + (omega[i] + (m.K / n) * coupling) * m.dt
        assert a.theta == pytest.approx(expected, abs=1e-9)


def test_synchronous_update_reads_one_snapshot():
    # The new phase of agent 0 must be computed from the OLD phases of all agents, not
    # the already-updated phase of agent 0 (or any earlier-committed agent). Verify by
    # comparing against a hand-rolled snapshot computation.
    m = KuramotoModel(10, K=4.0, dt=0.05, seed=5)
    snap = [a.theta for a in m.agent_list]
    omega = [a.omega for a in m.agent_list]
    n = m.n
    m.step()
    # Reconstruct expected next phases purely from the snapshot.
    for i, a in enumerate(m.agent_list):
        coupling = math.fsum(math.sin(snap[j] - snap[i]) for j in range(n))
        expected = snap[i] + (omega[i] + (m.K / n) * coupling) * m.dt
        assert a.theta == pytest.approx(expected, abs=1e-9)


def test_determinism_same_seed_identical_result():
    a = run_single(n=200, K=2.0, dt=0.05, seed=42, n_steps=300, measure_last=100)
    b = run_single(n=200, K=2.0, dt=0.05, seed=42, n_steps=300, measure_last=100)
    assert a["steady_r"] == b["steady_r"]
    assert a["final_r"] == b["final_r"]
    assert a["r_series"] == b["r_series"]


def test_different_seed_different_omega_draw():
    m1 = KuramotoModel(50, K=1.0, dt=0.05, seed=1)
    m2 = KuramotoModel(50, K=1.0, dt=0.05, seed=2)
    o1 = [a.omega for a in m1.agent_list]
    o2 = [a.omega for a in m2.agent_list]
    assert o1 != o2


def test_critical_coupling_normal_value():
    # K_c = 2 * sigma * sqrt(2/pi); for sigma=1 this is ~1.5958.
    assert critical_coupling_normal(1.0) == pytest.approx(1.5957691, abs=1e-6)
    # Scales linearly in sigma.
    assert critical_coupling_normal(2.0) == pytest.approx(2 * 1.5957691, abs=1e-6)


def test_steady_r_averages_the_tail():
    series = [0.0] * 10 + [0.5] * 5
    # Tail of 5 -> mean 0.5; tail longer than series -> mean of whole.
    assert steady_r(series, window=5) == pytest.approx(0.5)
    assert steady_r(series, window=100) == pytest.approx(sum(series) / len(series))
    assert steady_r([], window=5) == 0.0


def test_run_many_seeds_is_deterministic_and_shaped():
    a = run_many_seeds(n=120, K=3.0, dt=0.05, n_seeds=4, seed_base=0,
                       n_steps=200, measure_last=80)
    b = run_many_seeds(n=120, K=3.0, dt=0.05, n_seeds=4, seed_base=0,
                       n_steps=200, measure_last=80)
    assert a["per_seed_steady"] == b["per_seed_steady"]
    assert a["mean_steady_r"] == b["mean_steady_r"]
    assert len(a["per_seed_steady"]) == 4
    assert 0.0 <= a["mean_steady_r"] <= 1.0
    assert a["std_steady_r"] >= 0.0


def test_order_parameter_in_unit_interval_over_a_run():
    m = KuramotoModel(100, K=2.0, dt=0.05, seed=9)
    for _ in range(50):
        m.step()
        r = m.order_parameter()
        assert 0.0 <= r <= 1.0 + 1e-12


def test_strong_coupling_synchronizes_weak_coupling_does_not():
    # Sanity (not a locked prediction): a large K drives r high; K=0 leaves r ~ 1/sqrt(N).
    strong = run_single(n=300, K=6.0, dt=0.05, seed=0, n_steps=2000, measure_last=1000)
    none = run_single(n=300, K=0.0, dt=0.05, seed=0, n_steps=2000, measure_last=1000)
    assert strong["steady_r"] > 0.6
    assert none["steady_r"] < 0.3


def test_invalid_construction_args_rejected():
    with pytest.raises(ValueError):
        KuramotoModel(0, K=1.0)
    with pytest.raises(ValueError):
        KuramotoModel(10, K=-1.0)
    with pytest.raises(ValueError):
        KuramotoModel(10, dt=0.0)
    with pytest.raises(ValueError):
        run_single(n=10, n_steps=100, measure_last=200)


def test_agent_step_is_noop():
    # The per-agent step is a no-op; the tick lives on the model.
    m = KuramotoModel(4, K=1.0, dt=0.05, seed=0)
    a: OscillatorAgent = m.agent_list[0]
    before = a.theta
    a.step()
    assert a.theta == before
