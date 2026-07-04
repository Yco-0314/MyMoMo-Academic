"""Faithful-rule + determinism tests for the Bikhchandani-Hirshleifer-Welch (1992)
informational-cascade reproduction.

These pin the Bayesian follow-own-signal decision rule (posterior sign = sign(d + s)
with the tie broken by one's own signal), the +-2 cascade barrier and its herding
(later agents ignore their own signal), the pairing structure of the +-1 walk on the
net action difference d, the closed-form references (P(no cascade after k pairs),
P(incorrect | cascade), E[agents before cascade], social-accuracy gain), the queue
summary shape, the Monte-Carlo aggregation, and determinism (same seed -> identical).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3 are
graded by examples/repro_bikhchandani_information_cascade/run.py against a >=200k-queue
Monte Carlo.
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.bikhchandani_information_cascade import (
    HIGH,
    LOW,
    CascadeAgent,
    CascadeModel,
    expected_agents_before_cascade,
    prob_incorrect_given_cascade,
    prob_no_cascade_after_pairs,
    run_monte_carlo,
    run_single,
    social_accuracy_gain,
)


# -- the Bayesian follow-own-signal decision rule -----------------------------

def _agent(signal: str) -> CascadeAgent:
    """A lone agent carrying a given signal (model state irrelevant to decide)."""
    m = CascadeModel(n=1, p=0.7, seed=0)
    return CascadeAgent(0, m, signal=signal)


def test_first_agent_follows_own_signal():
    # d = 0 (no predecessors): posterior sign = sign(0 + s) = s -> follow own signal.
    assert _agent("h").decide(0) == HIGH
    assert _agent("l").decide(0) == LOW


def test_balanced_history_follows_own_signal():
    # d = 0 with a balanced history behaves identically: follow own signal.
    assert _agent("h").decide(0) == HIGH
    assert _agent("l").decide(0) == LOW


def test_lead_of_one_against_own_signal_is_a_tie_broken_by_signal():
    # d = +1, low signal -> score 0 -> tie -> follow own signal (act L, against lead).
    a = _agent("l")
    assert a.decide(1) == LOW
    assert a.signal_revealed is True and a.in_cascade is False
    # d = -1, high signal -> tie -> follow own signal (act H, against lead).
    b = _agent("h")
    assert b.decide(-1) == HIGH


def test_lead_of_one_with_agreeing_signal_follows_lead():
    # d = +1, high signal -> score +2 -> act H (agrees, pushes to a cascade next).
    assert _agent("h").decide(1) == HIGH
    assert _agent("l").decide(-1) == LOW


def test_cascade_barrier_overrides_own_signal():
    # |d| >= 2: the public lead outweighs a single signal -> herd, ignore own signal.
    up = _agent("l")          # low signal, but public lead is +2 (H)
    assert up.decide(2) == HIGH
    assert up.in_cascade is True and up.signal_revealed is False
    down = _agent("h")        # high signal, but public lead is -2 (L)
    assert down.decide(-2) == LOW
    assert down.in_cascade is True and down.signal_revealed is False


def test_agent_rejects_bad_signal():
    m = CascadeModel(n=1, p=0.7, seed=0)
    with pytest.raises(ValueError):
        CascadeAgent(0, m, signal="x")


# -- model construction + invariants ------------------------------------------

def test_model_rejects_bad_params():
    with pytest.raises(ValueError):
        CascadeModel(n=0)
    with pytest.raises(ValueError):
        CascadeModel(n=10, p=0.5)     # precision must exceed 1/2
    with pytest.raises(ValueError):
        CascadeModel(n=10, p=1.0)     # and be strictly < 1
    with pytest.raises(ValueError):
        CascadeModel(n=10, p=0.3)


def test_population_size_and_signals():
    m = CascadeModel(n=30, p=0.7, seed=1)
    assert len(m.agent_list) == 30
    assert all(isinstance(a, CascadeAgent) for a in m.agent_list)
    assert all(a.signal in ("h", "l") for a in m.agent_list)
    assert m.true_state in (HIGH, LOW)


def test_signal_precision_matches_p_empirically():
    # Across many agents the fraction of correct signals should be ~ p.
    correct = 0
    total = 0
    for seed in range(400):
        m = CascadeModel(n=30, p=0.7, seed=seed)
        correct_symbol = "h" if m.true_state == HIGH else "l"
        for a in m.agent_list:
            total += 1
            if a.signal == correct_symbol:
                correct += 1
    frac = correct / total
    assert frac == pytest.approx(0.7, abs=0.02)


# -- the cascade mechanism (a realised queue) ---------------------------------

def test_first_two_actions_reveal_signals():
    # The first agent always reveals its signal; the second reveals unless it is a
    # cascade already (it never is at agent 2, since d in {-1,0,1} before it acts).
    m = CascadeModel(n=30, p=0.7, seed=3)
    a0, a1 = m.agent_list[0], m.agent_list[1]
    m.act_one(a0)
    assert a0.action == (HIGH if a0.signal == "h" else LOW)   # follows own signal
    assert not m.cascade_active()
    m.act_one(a1)
    # after two agents d in {-2, 0, 2}: cascade iff the two agreed.
    if a0.signal == a1.signal:
        assert m.cascade_active()
    else:
        assert m.d == 0 and not m.cascade_active()


def test_once_cascade_active_it_stays_and_d_is_frozen():
    # Force a +2 lead, then every later agent copies regardless of its signal, so |d|
    # never leaves the barrier region and the direction is frozen.
    m = CascadeModel(n=30, p=0.7, seed=7)
    m.n_high, m.n_low = 2, 0          # public lead +2 (a cascade is active)
    assert m.cascade_active()
    for a in m.agent_list[2:]:
        before_dir = 1 if m.d > 0 else -1
        m.act_one(a)
        assert a.action == HIGH        # herd up regardless of own signal
        assert (1 if m.d > 0 else -1) == before_dir


def test_run_summary_shape_and_consistency():
    res = run_single(n=30, p=0.7, seed=5)
    assert res["n"] == 30 and res["p"] == 0.7
    assert res["true_state"] in (HIGH, LOW)
    assert isinstance(res["cascade_formed"], bool)
    if res["cascade_formed"]:
        assert res["cascade_direction"] in (HIGH, LOW)
        assert isinstance(res["cascade_correct"], bool)
        assert res["cascade_correct"] == (res["cascade_direction"] == res["true_state"])
        assert 1 <= res["cascade_start_index"] <= 30
        # agents acting on private info before a cascade is a small even/odd count >= 2
        assert res["agents_before_cascade"] >= 2
    assert res["n_high"] + res["n_low"] == 30


def test_agents_before_cascade_is_even_when_formed_within_queue():
    # The +-1 walk absorbs only from a balanced state at an even step, so the number of
    # agents that revealed private info before a (within-queue) cascade is even.
    for seed in range(200):
        res = run_single(n=200, p=0.7, seed=seed)
        if res["cascade_formed"]:
            assert res["agents_before_cascade"] % 2 == 0


def test_cascade_almost_always_forms_in_a_long_queue():
    # With N=200 a cascade essentially always forms (P(no cascade) ~ (2p(1-p))^100).
    formed = sum(run_single(n=200, p=0.7, seed=s)["cascade_formed"] for s in range(300))
    assert formed == 300


# -- closed-form references ---------------------------------------------------

def test_prob_no_cascade_after_pairs_matches_formula():
    assert prob_no_cascade_after_pairs(0.7, 1) == pytest.approx(2 * 0.7 * 0.3)
    assert prob_no_cascade_after_pairs(0.7, 10) == pytest.approx((2 * 0.7 * 0.3) ** 10)
    # the locked analytic value P(no cascade by agent 20) at p=0.7
    assert prob_no_cascade_after_pairs(0.7, 10) == pytest.approx(1.71e-4, rel=0.02)


def test_prob_incorrect_given_cascade_locked_values():
    assert prob_incorrect_given_cascade(0.7) == pytest.approx(0.1552, abs=1e-4)
    assert prob_incorrect_given_cascade(0.6) == pytest.approx(0.3077, abs=1e-4)
    assert prob_incorrect_given_cascade(0.8) == pytest.approx(0.0588, abs=1e-4)


def test_expected_agents_before_cascade_locked_value():
    assert expected_agents_before_cascade(0.7) == pytest.approx(3.45, abs=0.01)
    # < 4 for all p in (0.5, 1): 2/(p^2+(1-p)^2) is maximised at p->1/2 where it -> 4.
    for p in (0.55, 0.6, 0.7, 0.8, 0.9, 0.95):
        assert expected_agents_before_cascade(p) < 4.0


def test_social_accuracy_gain_small_at_p07():
    # gain = p^2/(p^2+(1-p)^2) - p = 0.49/0.58 - 0.7 = 0.1448 at p=0.7 (NOT the same
    # quantity as P(incorrect|cascade)=0.1552). The locked clause is gain <= 0.16.
    assert social_accuracy_gain(0.7) == pytest.approx(0.1448, abs=1e-3)
    assert social_accuracy_gain(0.7) <= 0.16


# -- Monte-Carlo aggregation --------------------------------------------------

def test_monte_carlo_shape_and_references():
    mc = run_monte_carlo(n=30, p=0.7, n_queues=2000, seed_base=0)
    assert mc["n_queues"] == 2000
    assert 0.0 <= mc["frac_cascade_formed"] <= 1.0
    assert mc["cf_p_incorrect_given_cascade"] == pytest.approx(0.1552, abs=1e-4)
    assert mc["cf_expected_agents_before_cascade"] == pytest.approx(3.45, abs=0.01)
    # even at 2k queues the estimates should sit near the closed forms (loose tol)
    assert mc["p_incorrect_given_cascade"] == pytest.approx(0.1552, abs=0.03)
    assert mc["mean_agents_before_cascade"] == pytest.approx(3.45, abs=0.2)
    assert mc["frac_cascade_formed_by_agent_20"] > 0.99


def test_monte_carlo_rejects_bad_count():
    with pytest.raises(ValueError):
        run_monte_carlo(n=30, p=0.7, n_queues=0)


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_queue():
    a = run_single(n=30, p=0.7, seed=42)
    b = run_single(n=30, p=0.7, seed=42)
    assert a == b


def test_determinism_same_seed_identical_monte_carlo():
    a = run_monte_carlo(n=30, p=0.7, n_queues=1000, seed_base=0)
    b = run_monte_carlo(n=30, p=0.7, n_queues=1000, seed_base=0)
    for key in ("frac_cascade_formed", "p_incorrect_given_cascade",
                "mean_agents_before_cascade", "frac_cascade_formed_by_agent_20"):
        assert a[key] == b[key]


def test_different_seed_can_differ():
    a = run_single(n=30, p=0.7, seed=1)
    b = run_single(n=30, p=0.7, seed=2)
    # at least the seed field differs; the realised queues are (almost surely) not
    # both identical across every field
    assert a["seed"] != b["seed"]
