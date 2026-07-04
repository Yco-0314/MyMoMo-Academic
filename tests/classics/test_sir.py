"""Faithful-rule + determinism tests for the SIR threshold reproduction.

These pin the mass-action force of infection, the synchronous start-of-tick update,
the absorbing R state, the i0 seeding, determinism (same seed -> identical run), and
the analytic final-size solver. They are faithfulness tests, NOT prediction tests
(the locked predictions P1-P3 are evaluated by examples/repro_sir_threshold/run.py).
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.sir import (
    I,
    R,
    S,
    PersonAgent,
    SIRModel,
    analytic_final_size,
    beta_for_r0,
    run_many_seeds,
    run_single,
)


def test_initial_seeding_and_baseline_counts():
    m = SIRModel(n=1000, beta=0.2, gamma=0.1, i0=10, seed=0)
    assert m.count(I) == 10
    assert m.count(S) == 990
    assert m.count(R) == 0


def test_force_of_infection_formula():
    # p_infect = 1 - (1 - beta/N)^I_count.
    m = SIRModel(n=10_000, beta=0.3, gamma=0.1, i0=10, seed=0)
    per_contact = 0.3 / 10_000
    assert m.force_of_infection(0) == 0.0
    assert m.force_of_infection(1) == pytest.approx(per_contact)
    assert m.force_of_infection(50) == pytest.approx(1 - (1 - per_contact) ** 50)
    # small beta*I/N limit ~ beta*I/N
    assert m.force_of_infection(50) == pytest.approx(0.3 * 50 / 10_000, rel=1e-2)


def test_recovery_is_probabilistic_and_R_is_absorbing():
    # gamma=1 => every infective recovers in exactly one tick; with beta=0 there is no
    # transmission, so after one tick: I->R, S unchanged, and R never leaves R.
    m = SIRModel(n=100, beta=0.0, gamma=1.0, i0=5, seed=0)
    res = m.run()
    assert res["attack_rate"] == pytest.approx(5 / 100)  # only the seeds ever infected
    assert res["S_final"] == 95
    assert res["R_final"] == 5
    # I extinct after one update tick (t=1), run stops.
    assert res["steps"] == 1
    # R is absorbing: I_series goes 5 -> 0 and stays 0; R_series 0 -> 5.
    assert res["I_series"] == [5, 0]
    assert res["R_series"] == [0, 5]


def test_zero_beta_means_no_secondary_infections():
    m = SIRModel(n=1000, beta=0.0, gamma=0.1, i0=10, seed=3)
    res = m.run()
    # No transmission => only the original 10 are ever infected => attack rate = 10/1000.
    assert res["attack_rate"] == pytest.approx(10 / 1000)
    assert res["S_final"] == 990


def test_synchronous_update_uses_start_of_tick_I_count():
    # Hand check one tick: p_infect is frozen from the start-of-tick I_count, and a
    # newly-infected S does not recover in the same tick (committed from start state).
    m = SIRModel(n=4, beta=4.0, gamma=1.0, i0=1, seed=0)
    # start: 1 I, 3 S. Force a deterministic single tick by hand.
    i_count = m.count(I)
    assert i_count == 1
    m.p_infect = m.force_of_infection(i_count)
    # With beta=4, N=4 => per_contact = 1.0 => p_infect = 1.0 for I_count=1 => all S->I.
    assert m.p_infect == 1.0
    m.agents.step()
    for p in m.persons:
        p.state = p._next_state
    # All 3 S became I; the original I (gamma=1) recovered -> R. No agent both infected
    # and recovered in the same tick.
    assert m.count(I) == 3
    assert m.count(R) == 1
    assert m.count(S) == 0


def test_run_reaches_extinction_and_conserves_population():
    m = SIRModel(n=2000, beta=0.3, gamma=0.1, i0=10, seed=1)
    res = m.run()
    assert m.count(I) == 0  # ran to extinction
    assert res["S_final"] + res["R_final"] == 2000  # S + R = N at the end (I=0)
    assert 0.0 <= res["attack_rate"] <= 1.0


def test_determinism_same_seed_identical_run():
    a = run_single(n=3000, r0=2.0, gamma=0.1, i0=10, seed=7)
    b = run_single(n=3000, r0=2.0, gamma=0.1, i0=10, seed=7)
    assert a["attack_rate"] == b["attack_rate"]
    assert a["S_series"] == b["S_series"]
    assert a["I_series"] == b["I_series"]
    assert a["steps"] == b["steps"]


def test_different_seeds_can_differ():
    # Near/above threshold, different seeds give different trajectories (stochastic).
    rates = {run_single(n=3000, r0=1.5, gamma=0.1, i0=5, seed=s)["attack_rate"]
             for s in range(8)}
    assert len(rates) > 1


def test_beta_for_r0():
    assert beta_for_r0(2.0, 0.1) == pytest.approx(0.2)
    assert beta_for_r0(0.8, 0.1) == pytest.approx(0.08)


def test_run_many_seeds_shape_and_determinism():
    a = run_many_seeds(n=2000, r0=2.0, gamma=0.1, i0=10, n_seeds=10, seed_base=0)
    b = run_many_seeds(n=2000, r0=2.0, gamma=0.1, i0=10, n_seeds=10, seed_base=0)
    assert a["attack_rates"] == b["attack_rates"]
    assert a["mean_attack_rate"] == b["mean_attack_rate"]
    assert len(a["attack_rates"]) == 10
    assert a["min_attack_rate"] <= a["mean_attack_rate"] <= a["max_attack_rate"]
    assert 0.0 <= a["takeoff_frequency"] <= 1.0


def test_analytic_final_size_below_threshold_is_zero():
    assert analytic_final_size(0.8) == 0.0
    assert analytic_final_size(1.0) == 0.0


def test_analytic_final_size_solves_the_relation():
    # The returned attack rate a must satisfy a = 1 - exp(-R0 * a).
    for r0 in (1.5, 2.0, 3.0):
        a = analytic_final_size(r0)
        assert 0.0 < a < 1.0
        assert a == pytest.approx(1.0 - math.exp(-r0 * a), abs=1e-6)
    # Known reference value: R0=2.0 -> attack rate ~ 0.7968.
    assert analytic_final_size(2.0) == pytest.approx(0.7968, abs=1e-3)
    # Monotone in R0.
    assert analytic_final_size(1.5) < analytic_final_size(2.0) < analytic_final_size(3.0)


def test_invalid_params_rejected():
    with pytest.raises(ValueError):
        SIRModel(n=100, beta=0.2, gamma=0.0, i0=10)
    with pytest.raises(ValueError):
        SIRModel(n=100, beta=-1.0, gamma=0.1, i0=10)
    with pytest.raises(ValueError):
        SIRModel(n=100, beta=0.2, gamma=0.1, i0=0)
    with pytest.raises(ValueError):
        SIRModel(n=100, beta=0.2, gamma=0.1, i0=100)
