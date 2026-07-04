"""Faithful-rule + determinism tests for the Stag Hunt coordination game (Skyrms 2004;
Maynard Smith lineage) reproduction.

These pin the coordination-game payoff matrix, the payoff-proportional imitation
micro-rule, the interior-fixed-point x* anchor, fixation/absorption, the steady-state
estimator, and determinism (same seed -> identical result). They are faithfulness tests,
NOT prediction tests (the locked predictions P1-P3 are evaluated by
examples/repro_stag_hunt/run.py).
"""
from __future__ import annotations

import pytest

from abm_auto.classics.stag_hunt import (
    HARE,
    STAG,
    StagHuntModel,
    StrategyAgent,
    interior_fixed_point,
    payoff,
    run_single,
    steady_value,
)


# -- payoff matrix (the symmetric coordination game) --------------------------

def test_payoff_matrix_coordination_game():
    R, T, P, S_ = 4.0, 3.0, 2.0, 0.0
    # (S,S)=R, (S,H)=S_, (H,S)=T, (H,H)=P
    assert payoff(STAG, STAG, R=R, T=T, P=P, S_=S_) == pytest.approx(R)
    assert payoff(STAG, HARE, R=R, T=T, P=P, S_=S_) == pytest.approx(S_)
    assert payoff(HARE, STAG, R=R, T=T, P=P, S_=S_) == pytest.approx(T)
    assert payoff(HARE, HARE, R=R, T=T, P=P, S_=S_) == pytest.approx(P)


def test_payoff_ordering_makes_both_pure_states_stable():
    # R>T>P>S_: stag-stag is the best outcome; hare is safe; the lone stag-hunter is
    # worst. Both (S,S) and (H,H) are strict Nash — no unilateral deviation gains.
    R, T, P, S_ = 4.0, 3.0, 2.0, 0.0
    # In an all-Stag world a Hare deviant earns T=3 < R=4 -> (S,S) is a strict ESS.
    assert payoff(STAG, STAG, R=R, T=T, P=P, S_=S_) > payoff(HARE, STAG, R=R, T=T, P=P, S_=S_)
    # In an all-Hare world a Stag deviant earns S_=0 < P=2 -> (H,H) is a strict ESS.
    assert payoff(HARE, HARE, R=R, T=T, P=P, S_=S_) > payoff(STAG, HARE, R=R, T=T, P=P, S_=S_)


# -- interior fixed point (analytic anchor) -----------------------------------

def test_interior_fixed_point_formula():
    # Canonical (4,3,2,0) -> (2-0)/((4-3)+(2-0)) = 2/3.
    assert interior_fixed_point(4.0, 3.0, 2.0, 0.0) == pytest.approx(2.0 / 3.0)
    # (4,2,2,0) -> (2)/((2)+(2)) = 0.5.
    assert interior_fixed_point(4.0, 2.0, 2.0, 0.0) == pytest.approx(0.5)
    # (5,3,2,1.5) -> (0.5)/((2)+(0.5)) = 0.2.
    assert interior_fixed_point(5.0, 3.0, 2.0, 1.5) == pytest.approx(0.2)


def test_interior_fixed_point_is_hare_basin_probability():
    # x* is also the fraction of (0,1) below it, i.e. P(random x0 lands in Hare basin).
    # Canonical x*=0.667 -> risk-dominant Hare owns the majority basin.
    assert interior_fixed_point(4.0, 3.0, 2.0, 0.0) > 0.5


# -- model construction + invariants ------------------------------------------

def test_requires_strict_payoff_ordering():
    with pytest.raises(ValueError):
        StagHuntModel(100, R=4.0, T=4.0, P=2.0, S_=0.0, x0=0.5, seed=0)   # R not > T
    with pytest.raises(ValueError):
        StagHuntModel(100, R=4.0, T=3.0, P=3.0, S_=0.0, x0=0.5, seed=0)   # T not > P
    with pytest.raises(ValueError):
        StagHuntModel(100, R=4.0, T=3.0, P=2.0, S_=2.0, x0=0.5, seed=0)   # P not > S_


def test_initial_stag_fraction_matches_x0():
    for x0 in (0.1, 0.25, 0.5, 0.9):
        m = StagHuntModel(1000, x0=x0, seed=0)
        assert m.stag_fraction() == pytest.approx(x0, abs=1e-9)
        assert m.n_stags() == round(x0 * 1000)


def test_population_is_strategy_agents():
    m = StagHuntModel(50, x0=0.5, seed=0)
    assert len(m.agent_list) == 50
    assert all(isinstance(a, StrategyAgent) for a in m.agent_list)
    assert all(a.strategy in (STAG, HARE) for a in m.agent_list)


# -- the elementary mechanics: pairing + imitation ----------------------------

def test_play_round_assigns_consistent_pair_payoffs():
    # Two agents (one Stag, one Hare) -> paired together, matching row-payoffs.
    m = StagHuntModel(2, R=4.0, T=3.0, P=2.0, S_=0.0, x0=0.5, seed=0)
    m.agent_list[0].strategy = STAG
    m.agent_list[1].strategy = HARE
    m.play_round()
    payoffs = {a.strategy: a.payoff for a in m.agent_list}
    assert payoffs[STAG] == pytest.approx(0.0)   # Stag vs Hare = S_ = 0 (the sucker)
    assert payoffs[HARE] == pytest.approx(3.0)   # Hare vs Stag = T = 3


def test_imitation_copies_strictly_better_model_when_draw_succeeds():
    # A Stag that got suckered (payoff S_=0) meeting a Hare model that earned T=3 switches
    # to Hare with probability gap/span; force the RNG draw to succeed -> it copies Hare.
    m = StagHuntModel(2, R=4.0, T=3.0, P=2.0, S_=0.0, x0=0.5, seed=0)
    learner, model_agent = m.agent_list
    learner.strategy = STAG
    learner.payoff = 0.0
    model_agent.strategy = HARE
    model_agent.payoff = 3.0
    draws = iter([1, 0])
    m.rng.randrange = lambda *_a, **_k: next(draws)  # each agent draws the other
    m.rng.random = lambda: 0.0                       # 0.0 < p_switch -> switch
    m.imitate()
    assert learner.strategy == HARE


def test_imitation_never_copies_worse_or_equal_model():
    # A coordinated Stag (payoff R=4) meeting a worse Hare model (payoff P=2) never
    # imitates, regardless of the RNG draw (gap <= 0 -> no switch).
    m = StagHuntModel(2, R=4.0, T=3.0, P=2.0, S_=0.0, x0=0.5, seed=0)
    learner, model_agent = m.agent_list
    learner.strategy = STAG
    learner.payoff = 4.0
    model_agent.strategy = HARE
    model_agent.payoff = 2.0
    draws = iter([1, 0])
    m.rng.randrange = lambda *_a, **_k: next(draws)
    m.rng.random = lambda: 0.0
    m.imitate()
    assert learner.strategy == STAG


def test_imitation_skips_switch_when_draw_fails():
    # Same favourable gap as the copy test, but the probability draw fails -> no switch.
    m = StagHuntModel(2, R=4.0, T=3.0, P=2.0, S_=0.0, x0=0.5, seed=0)
    learner, model_agent = m.agent_list
    learner.strategy = STAG
    learner.payoff = 0.0
    model_agent.strategy = HARE
    model_agent.payoff = 3.0
    draws = iter([1, 0])
    m.rng.randrange = lambda *_a, **_k: next(draws)
    m.rng.random = lambda: 1.0                       # 1.0 < p_switch is False -> no switch
    m.imitate()
    assert learner.strategy == STAG


# -- fixation / absorption ----------------------------------------------------

def test_pure_states_are_absorbing():
    # An all-Hare (and all-Stag) population is fixated and cannot leave (no strictly
    # better model to copy) -> a full run stays put.
    lo = run_single(200, x0=0.0, seed=0)
    hi = run_single(200, x0=1.0, seed=0)
    assert lo["fixated"] and lo["fixed_on"] == HARE
    assert hi["fixated"] and hi["fixed_on"] == STAG
    assert lo["steady_stag_fraction"] == pytest.approx(0.0)
    assert hi["steady_stag_fraction"] == pytest.approx(1.0)


def test_is_fixated_flag_tracks_uniform_population():
    m = StagHuntModel(10, x0=0.5, seed=0)
    assert not m.is_fixated()
    for a in m.agent_list:
        a.strategy = HARE
    assert m.is_fixated()


# -- steady-state estimator ---------------------------------------------------

def test_steady_value_is_tail_mean():
    series = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert steady_value(series, window=2) == pytest.approx(0.45)   # mean(0.4, 0.5)
    assert steady_value(series, window=100) == pytest.approx(0.3)  # whole series
    assert steady_value([], window=5) == 0.0


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(300, x0=0.7, seed=42)
    b = run_single(300, x0=0.7, seed=42)
    assert a["stag_fraction_series"] == b["stag_fraction_series"]
    assert a["steady_stag_fraction"] == b["steady_stag_fraction"]
    assert a["generations"] == b["generations"]
    assert a["fixed_on"] == b["fixed_on"]


def test_different_seed_stays_shaped():
    for seed in (1, 2):
        res = run_single(300, x0=0.5, seed=seed)
        assert all(0.0 <= x <= 1.0 for x in res["stag_fraction_series"])
        assert 0.0 <= res["steady_stag_fraction"] <= 1.0
        assert res["fixed_on"] in (STAG, HARE)


# -- basin selection (sanity; the locked grading is in run.py) -----------------

def test_low_start_fixates_hare_high_start_fixates_stag():
    # Canonical x*=0.667: a start well below fixates Hare; a start well above fixates
    # Stag. This is the bistable signature (NOT convergence to an interior mix).
    lo = run_single(1000, x0=0.3, seed=0)
    hi = run_single(1000, x0=0.9, seed=0)
    assert lo["fixed_on"] == HARE
    assert hi["fixed_on"] == STAG
    assert lo["steady_stag_fraction"] < 0.1
    assert hi["steady_stag_fraction"] > 0.9


def test_distinct_from_hawk_dove_fixates_not_mixes():
    # Distinctness: the stag hunt fixates on a PURE state (0 or 1), unlike Hawk-Dove which
    # settles at an interior mix. From a high start the steady fraction is ~1, not ~x*.
    hi = run_single(1000, x0=0.85, seed=1)
    assert hi["fixated"]
    assert hi["steady_stag_fraction"] > 0.95 or hi["steady_stag_fraction"] < 0.05
