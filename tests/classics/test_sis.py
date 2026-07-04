"""Faithful-rule + determinism tests for the SIS endemic-threshold reproduction.

These pin the mass-action force of infection, the synchronous start-of-tick update,
the I->S recovery (NO immunity / no R state), the i0 seeding, determinism (same seed ->
identical run), the late-window prevalence measurement, and the analytic endemic
formula i* = 1 - 1/R0. They are faithfulness tests, NOT prediction tests (the locked
predictions P1-P3 are evaluated by examples/repro_sis_endemic/run.py).
"""
from __future__ import annotations

import pytest

from abm_auto.classics.sis import (
    I,
    S,
    PersonAgent,
    SISModel,
    beta_for_r0,
    endemic_prevalence,
    run_many_seeds,
    run_single,
)


def test_initial_seeding_and_baseline_counts():
    m = SISModel(n=1000, beta=0.2, gamma=0.1, i0=10, ticks=10, tail=5, seed=0)
    assert m.count(I) == 10
    assert m.count(S) == 990
    # SIS has only two states; every agent is S or I.
    assert m.count(S) + m.count(I) == 1000


def test_no_R_state_only_S_and_I():
    # The module must NOT define a recovered state; the only constants are S and I.
    import abm_auto.classics.sis as sis
    assert not hasattr(sis, "R")
    assert sis.S == "S" and sis.I == "I"


def test_force_of_infection_formula():
    # p_infect = 1 - (1 - beta/N)^I_count.
    m = SISModel(n=10_000, beta=0.3, gamma=0.1, i0=10, ticks=10, tail=5, seed=0)
    per_contact = 0.3 / 10_000
    assert m.force_of_infection(0) == 0.0
    assert m.force_of_infection(1) == pytest.approx(per_contact)
    assert m.force_of_infection(50) == pytest.approx(1 - (1 - per_contact) ** 50)
    # small beta*I/N limit ~ beta*I/N
    assert m.force_of_infection(50) == pytest.approx(0.3 * 50 / 10_000, rel=1e-2)


def test_recovery_returns_to_S_no_immunity():
    # gamma=1 => every infective recovers in exactly one tick; with beta=0 there is no
    # transmission, so after one tick every I returns to S (NOT to a recovered state).
    m = SISModel(n=100, beta=0.0, gamma=1.0, i0=5, ticks=3, tail=1, seed=0)
    res = m.run()
    # All infections die out (beta=0, all recover to S); prevalence -> 0, all back to S.
    assert m.count(I) == 0
    assert m.count(S) == 100               # everyone is Susceptible again (no immunity)
    assert res["extinct"] is True
    # I_series: 5 -> 0 -> 0 -> 0 (t=0 baseline then 3 ticks).
    assert res["I_series"][0] == 5
    assert all(v == 0 for v in res["I_series"][1:])


def test_zero_beta_means_die_out():
    m = SISModel(n=1000, beta=0.0, gamma=0.1, i0=10, ticks=200, tail=50, seed=3)
    res = m.run()
    # No transmission => infection eventually dies out => prevalence -> 0.
    assert res["prevalence"] == pytest.approx(0.0)
    assert res["extinct"] is True


def test_synchronous_update_uses_start_of_tick_I_count():
    # Hand check one tick: p_infect is frozen from the start-of-tick I_count, and a
    # newly-infected S does not recover in the same tick (committed from start state).
    m = SISModel(n=4, beta=4.0, gamma=1.0, i0=1, ticks=1, tail=1, seed=0)
    i_count = m.count(I)
    assert i_count == 1
    m.p_infect = m.force_of_infection(i_count)
    # With beta=4, N=4 => per_contact = 1.0 => p_infect = 1.0 for I_count=1 => all S->I.
    assert m.p_infect == 1.0
    m.agents.step()
    for p in m.persons:
        p.state = p._next_state
    # All 3 S became I; the original I (gamma=1) recovered -> S. No agent both infected
    # and recovered in the same tick.
    assert m.count(I) == 3
    assert m.count(S) == 1


def test_population_conserved_S_plus_I():
    m = SISModel(n=2000, beta=0.3, gamma=0.1, i0=10, ticks=100, tail=20, seed=1)
    m.run()
    assert m.count(S) + m.count(I) == 2000   # two-state conservation every tick
    assert 0 <= m.count(I) <= 2000


def test_endemic_prevalence_formula():
    # i* = 1 - 1/R0 for R0 > 1, else 0.
    assert endemic_prevalence(0.8) == 0.0
    assert endemic_prevalence(1.0) == 0.0
    assert endemic_prevalence(1.5) == pytest.approx(1 - 1 / 1.5)
    assert endemic_prevalence(2.0) == pytest.approx(0.5)
    assert endemic_prevalence(3.0) == pytest.approx(2 / 3)


def test_prevalence_is_late_window_mean():
    # The reported prevalence equals the mean of the last `tail` I/N values directly.
    res = run_single(n=2000, r0=2.0, gamma=0.1, i0=10, ticks=300, tail=50, seed=0)
    tail_I = res["I_series"][-50:]
    expected = (sum(tail_I) / len(tail_I)) / 2000
    assert res["prevalence"] == pytest.approx(expected)


def test_determinism_same_seed_identical_run():
    a = run_single(n=3000, r0=2.0, gamma=0.1, i0=10, ticks=300, tail=50, seed=7)
    b = run_single(n=3000, r0=2.0, gamma=0.1, i0=10, ticks=300, tail=50, seed=7)
    assert a["prevalence"] == b["prevalence"]
    assert a["I_series"] == b["I_series"]
    assert a["S_series"] == b["S_series"]


def test_different_seeds_can_differ():
    # At a stable R0 the late-window prevalence fluctuates seed to seed (stochastic).
    prevs = {run_single(n=3000, r0=2.0, gamma=0.1, i0=10, ticks=300, tail=50, seed=s)["prevalence"]
             for s in range(8)}
    assert len(prevs) > 1


def test_beta_for_r0():
    assert beta_for_r0(2.0, 0.1) == pytest.approx(0.2)
    assert beta_for_r0(0.8, 0.1) == pytest.approx(0.08)


def test_below_threshold_dies_out():
    # R0=0.8 < 1 => sub-critical => prevalence collapses to ~0.
    res = run_single(n=10_000, r0=0.8, gamma=0.1, i0=10, ticks=500, tail=50, seed=0)
    assert res["prevalence"] < 0.02


def test_above_threshold_endemic_near_i_star():
    # R0=2.0 => endemic prevalence near i* = 0.5 (single seed; large N is self-averaging).
    res = run_single(n=10_000, r0=2.0, gamma=0.1, i0=10, ticks=500, tail=50, seed=0)
    assert abs(res["prevalence"] - 0.5) < 0.05


def test_run_many_seeds_shape_and_determinism():
    a = run_many_seeds(n=2000, r0=2.0, gamma=0.1, i0=10, ticks=200, tail=50,
                       n_seeds=10, seed_base=0)
    b = run_many_seeds(n=2000, r0=2.0, gamma=0.1, i0=10, ticks=200, tail=50,
                       n_seeds=10, seed_base=0)
    assert a["prevalences"] == b["prevalences"]
    assert a["mean_prevalence"] == b["mean_prevalence"]
    assert a["i_star"] == pytest.approx(0.5)
    assert 0.0 <= a["extinction_frequency"] <= 1.0
    assert a["std_prevalence"] == pytest.approx(a["var_prevalence"] ** 0.5)
