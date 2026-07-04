"""Faithful-rule + determinism tests for the Hawk-Dove ESS (Maynard Smith & Price
1973) reproduction.

These pin the contest payoff matrix, the payoff-proportional imitation micro-rule, the
ESS p*=V/C anchor, the steady-state estimator, and determinism (same seed -> identical
result). They are faithfulness tests, NOT prediction tests (the locked predictions
P1-P3 are evaluated by examples/repro_hawk_dove_ess/run.py).
"""
from __future__ import annotations

import pytest

from abm_auto.classics.hawk_dove import (
    DOVE,
    HAWK,
    HawkDoveModel,
    StrategyAgent,
    ess_hawk_fraction,
    payoff,
    run_single,
    steady_value,
)


# -- payoff matrix (the classic cost model) -----------------------------------

def test_payoff_matrix_cost_model():
    V, C = 2.0, 4.0
    # (H,H) = (V-C)/2 = -1 ; (H,D) = V = 2 ; (D,H) = 0 ; (D,D) = V/2 = 1
    assert payoff(HAWK, HAWK, V=V, C=C) == pytest.approx((V - C) / 2.0)
    assert payoff(HAWK, DOVE, V=V, C=C) == pytest.approx(V)
    assert payoff(DOVE, HAWK, V=V, C=C) == pytest.approx(0.0)
    assert payoff(DOVE, DOVE, V=V, C=C) == pytest.approx(V / 2.0)


def test_payoff_hawk_beats_dove_but_hawk_fight_is_costly():
    # With V<C a Hawk-Hawk clash is negative (escalation cost outweighs the half
    # resource), while exploiting a Dove is the best single payoff.
    V, C = 2.0, 4.0
    assert payoff(HAWK, DOVE, V=V, C=C) > payoff(DOVE, DOVE, V=V, C=C) > payoff(DOVE, HAWK, V=V, C=C)
    assert payoff(HAWK, HAWK, V=V, C=C) < 0.0


# -- ESS analytic anchor ------------------------------------------------------

def test_ess_hawk_fraction_is_V_over_C():
    assert ess_hawk_fraction(2.0, 4.0) == pytest.approx(0.5)
    assert ess_hawk_fraction(1.0, 4.0) == pytest.approx(0.25)
    assert ess_hawk_fraction(3.0, 4.0) == pytest.approx(0.75)


# -- model construction + invariants ------------------------------------------

def test_requires_V_less_than_C():
    with pytest.raises(ValueError):
        HawkDoveModel(100, V=4.0, C=4.0, x0=0.5, seed=0)
    with pytest.raises(ValueError):
        HawkDoveModel(100, V=5.0, C=4.0, x0=0.5, seed=0)


def test_initial_hawk_fraction_matches_x0():
    for x0 in (0.1, 0.25, 0.5, 0.9):
        m = HawkDoveModel(1000, V=2.0, C=4.0, x0=x0, seed=0)
        assert m.hawk_fraction() == pytest.approx(x0, abs=1e-9)
        assert m.n_hawks() == round(x0 * 1000)


def test_population_is_strategy_agents():
    m = HawkDoveModel(50, V=2.0, C=4.0, x0=0.5, seed=0)
    assert len(m.agent_list) == 50
    assert all(isinstance(a, StrategyAgent) for a in m.agent_list)
    assert all(a.strategy in (HAWK, DOVE) for a in m.agent_list)


# -- the elementary mechanics: pairing + imitation ----------------------------

def test_play_round_assigns_consistent_pair_payoffs():
    # Two agents -> they must be paired against each other and get the matching
    # row-payoffs for their strategies.
    m = HawkDoveModel(2, V=2.0, C=4.0, x0=0.5, seed=0)
    m.agent_list[0].strategy = HAWK
    m.agent_list[1].strategy = DOVE
    m.play_round()
    payoffs = {a.strategy: a.payoff for a in m.agent_list}
    assert payoffs[HAWK] == pytest.approx(2.0)   # Hawk vs Dove = V
    assert payoffs[DOVE] == pytest.approx(0.0)   # Dove vs Hawk = 0


def test_imitation_copies_strictly_better_model_when_draw_succeeds():
    # A Dove (payoff 0) meeting a Hawk model (payoff V=2) switches to Hawk with
    # probability gap/span; force the RNG draw to succeed -> it copies Hawk.
    m = HawkDoveModel(2, V=2.0, C=4.0, x0=0.5, seed=0)
    learner, model_agent = m.agent_list
    learner.strategy = DOVE
    learner.payoff = 0.0
    model_agent.strategy = HAWK
    model_agent.payoff = 2.0
    # Force the random model to be agent 1 and the switch draw to succeed.
    draws = iter([1, 0])
    m.rng.randrange = lambda *_a, **_k: next(draws)  # each agent draws the other
    m.rng.random = lambda: 0.0                     # 0.0 < p_switch -> switch
    m.imitate()
    assert learner.strategy == HAWK


def test_imitation_never_copies_worse_or_equal_model():
    # A Hawk-exploiter (payoff 2) meeting a worse Dove model (payoff 0) never imitates,
    # regardless of the RNG draw (gap <= 0 -> no switch).
    m = HawkDoveModel(2, V=2.0, C=4.0, x0=0.5, seed=0)
    learner, model_agent = m.agent_list
    learner.strategy = HAWK
    learner.payoff = 2.0
    model_agent.strategy = DOVE
    model_agent.payoff = 0.0
    draws = iter([1, 0])
    m.rng.randrange = lambda *_a, **_k: next(draws)
    m.rng.random = lambda: 0.0                      # even a "succeed" draw can't flip a non-positive gap
    m.imitate()
    assert learner.strategy == HAWK


def test_imitation_skips_switch_when_draw_fails():
    # Same favourable gap as the copy test, but the probability draw fails -> no switch.
    m = HawkDoveModel(2, V=2.0, C=4.0, x0=0.5, seed=0)
    learner, model_agent = m.agent_list
    learner.strategy = DOVE
    learner.payoff = 0.0
    model_agent.strategy = HAWK
    model_agent.payoff = 2.0
    draws = iter([1, 0])
    m.rng.randrange = lambda *_a, **_k: next(draws)
    m.rng.random = lambda: 1.0                      # 1.0 < p_switch is False -> no switch
    m.imitate()
    assert learner.strategy == DOVE


# -- steady-state estimator ---------------------------------------------------

def test_steady_value_is_tail_mean():
    series = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert steady_value(series, window=2) == pytest.approx(0.45)   # mean(0.4, 0.5)
    assert steady_value(series, window=100) == pytest.approx(0.3)  # whole series
    assert steady_value([], window=5) == 0.0


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(300, V=2.0, C=4.0, x0=0.3, seed=42)
    b = run_single(300, V=2.0, C=4.0, x0=0.3, seed=42)
    assert a["hawk_fraction_series"] == b["hawk_fraction_series"]
    assert a["steady_hawk_fraction"] == b["steady_hawk_fraction"]
    assert a["generations"] == b["generations"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(300, V=2.0, C=4.0, x0=0.3, seed=1)
    b = run_single(300, V=2.0, C=4.0, x0=0.3, seed=2)
    for res in (a, b):
        assert all(0.0 <= x <= 1.0 for x in res["hawk_fraction_series"])
        assert 0.0 <= res["steady_hawk_fraction"] <= 1.0


# -- convergence toward the ESS (sanity; the locked grading is in run.py) ------

def test_converges_near_ess_from_both_starts():
    # Faithfulness sanity, not the locked grade: from a low and a high start the
    # steady hawk fraction lands near p*=V/C=0.5 for V=2,C=4 (loose tol here).
    lo = run_single(1000, V=2.0, C=4.0, x0=0.1, seed=0)
    hi = run_single(1000, V=2.0, C=4.0, x0=0.9, seed=0)
    assert abs(lo["steady_hawk_fraction"] - 0.5) < 0.07
    assert abs(hi["steady_hawk_fraction"] - 0.5) < 0.07


def test_steady_fraction_tracks_V_over_C():
    # Lower V/C ratio -> lower steady hawk fraction (the ESS tracks the ratio).
    half = run_single(1000, V=2.0, C=4.0, x0=0.5, seed=0)   # p*=0.5
    quarter = run_single(1000, V=1.0, C=4.0, x0=0.5, seed=0)  # p*=0.25
    assert half["steady_hawk_fraction"] > quarter["steady_hawk_fraction"]
    assert abs(quarter["steady_hawk_fraction"] - 0.25) < 0.07
