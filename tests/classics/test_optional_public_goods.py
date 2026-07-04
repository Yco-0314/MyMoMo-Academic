"""Faithful-rule + determinism tests for the Optional Public Goods game with loners
(Hauert, De Monte, Hofbauer & Sigmund 2002) reproduction.

These pin the exact optional-PGG payoffs (all-C, all-D, all-L corners; the social-dilemma
gap P_D > P_C; the lone-participant-forced-to-sigma term; the closed form == a Monte-Carlo
group-sampling estimate), the strategy bookkeeping, the imitation-with-mutation update, the
compulsory control (loner removed, nothing else changed), the cyclic-dominance qualitative
sanity, the burn-in estimator, and determinism (same seed -> identical result).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(RPS coexistence, voluntary-vs-compulsory, regime flip) are evaluated by
examples/repro_optional_public_goods/run.py.
"""
from __future__ import annotations

import random

import pytest

from abm_auto.classics.optional_public_goods import (
    C,
    D,
    L,
    OptionalPGGModel,
    PlayerAgent,
    expected_payoffs,
    run_single,
)


# -- payoffs at the corners (Hauert et al. 2002 exact) ------------------------

def test_all_cooperators_earn_r_minus_one():
    # A population of all cooperators: every cooperator earns r-1 (pot r*n_c split N ways
    # minus its own cost 1 = r*N/N - 1 = r - 1); a loner would earn sigma; a lone
    # defector inserted would earn r (free-ride on N-1 cooperators). P_L = sigma.
    r, sigma, N = 3.0, 1.0, 5
    p_c, p_d, p_l = expected_payoffs(1.0, 0.0, 0.0, r=r, sigma=sigma, N=N)
    assert p_c == pytest.approx(r - 1.0)          # 2.0
    assert p_l == pytest.approx(sigma)            # 1.0
    # a defector among all-C free-rides on N-1 cooperators split over N: r*(N-1)/N
    assert p_d == pytest.approx(r * (N - 1) / N)  # 3*4/5 = 2.4


def test_all_defectors_earn_zero_and_loner_beats_them():
    # All defectors: the pot is empty, everyone earns 0. A loner earns sigma > 0, so
    # opting out beats staying (L beats D — the arm that rescues cooperation).
    r, sigma, N = 3.0, 1.0, 5
    p_c, p_d, p_l = expected_payoffs(0.0, 1.0, 0.0, r=r, sigma=sigma, N=N)
    assert p_d == pytest.approx(0.0)
    assert p_l == pytest.approx(sigma)
    assert p_l > p_d                              # loner strictly beats a sea of defectors


def test_all_loners_everyone_forced_to_sigma():
    # If everyone abstains, every focal player is alone in its sampled group and is forced
    # to the loner payoff sigma — all three strategies yield sigma at this corner.
    r, sigma, N = 3.0, 1.0, 5
    p_c, p_d, p_l = expected_payoffs(0.0, 0.0, 1.0, r=r, sigma=sigma, N=N)
    assert p_c == pytest.approx(sigma)
    assert p_d == pytest.approx(sigma)
    assert p_l == pytest.approx(sigma)


def test_social_dilemma_defectors_beat_cooperators_when_mixed():
    # In any mixed population with cooperators present, a defector out-earns a cooperator
    # (the free-rider advantage) — the dilemma that makes the compulsory game collapse.
    for (x_c, x_d, x_l) in [(0.5, 0.4, 0.1), (0.3, 0.3, 0.4), (0.8, 0.1, 0.1)]:
        p_c, p_d, p_l = expected_payoffs(x_c, x_d, x_l, r=3.0, sigma=1.0, N=5)
        assert p_d > p_c


def test_loner_release_valve_when_defectors_dominate():
    # When defectors dominate (few cooperators), the pot is nearly worthless, so the loner
    # payoff sigma exceeds both participant payoffs — L is the release valve that invades.
    p_c, p_d, p_l = expected_payoffs(0.02, 0.9, 0.08, r=3.0, sigma=1.0, N=5)
    assert p_l > p_d
    assert p_l > p_c


def test_closed_form_matches_monte_carlo_group_sampling():
    # The analytic payoff (exact expectation over the binomial group sampling) must match a
    # brute-force Monte-Carlo estimate that literally forms random groups of N and plays.
    rng = random.Random(12345)
    r, sigma, N = 3.0, 1.0, 5
    x_c, x_d, x_l = 0.4, 0.35, 0.25
    p_c, p_d, p_l = expected_payoffs(x_c, x_d, x_l, r=r, sigma=sigma, N=N)

    def sample_strategy():
        u = rng.random()
        if u < x_c:
            return C
        if u < x_c + x_d:
            return D
        return L

    # Monte-Carlo: focal player of a given type, sample N-1 co-players, play, average.
    trials = 200_000
    for focal, analytic in ((C, p_c), (D, p_d)):
        total = 0.0
        for _ in range(trials):
            others = [sample_strategy() for _ in range(N - 1)]
            participants = [s for s in others if s != L] + [focal]
            S = len(participants)
            if S == 1:
                total += sigma            # lone participant forced to sigma
                continue
            n_c = sum(1 for s in participants if s == C)
            share = r * n_c / S           # pot r*n_c*c split over S participants (c=1)
            if focal == D:
                total += share
            else:                          # cooperator paid the cost
                total += share - 1.0
        mc = total / trials
        assert mc == pytest.approx(analytic, abs=0.02)


def test_payoffs_reject_bad_group_size():
    with pytest.raises(ValueError):
        expected_payoffs(0.5, 0.3, 0.2, r=3.0, sigma=1.0, N=1)


# -- model construction + invariants ------------------------------------------

def test_population_is_player_agents_with_valid_strategies():
    m = OptionalPGGModel(pop=500, r=3.0, sigma=1.0, N=5, seed=0)
    assert len(m.agent_list) == 500
    assert all(isinstance(a, PlayerAgent) for a in m.agent_list)
    assert all(a.strategy in (C, D, L) for a in m.agent_list)
    # frequencies sum to 1.
    x_c, x_d, x_l = m.frequencies()
    assert x_c + x_d + x_l == pytest.approx(1.0)


def test_compulsory_removes_the_loner_strategy():
    vol = OptionalPGGModel(pop=500, r=3.0, sigma=1.0, N=5, compulsory=False, seed=0)
    comp = OptionalPGGModel(pop=500, r=3.0, sigma=1.0, N=5, compulsory=True, seed=0)
    assert vol.strategy_set == (C, D, L)
    assert comp.strategy_set == (C, D)
    # the control changes ONLY availability of the loner: every other knob identical.
    for attr in ("pop", "r", "sigma", "N", "mu"):
        assert getattr(vol, attr) == getattr(comp, attr)
    # compulsory population has NO loners at initialisation.
    assert comp.strategy_count(L) == 0


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        OptionalPGGModel(pop=0)
    with pytest.raises(ValueError):
        OptionalPGGModel(pop=10, N=1)
    with pytest.raises(ValueError):
        OptionalPGGModel(pop=10, r=1.0)                 # need r > 1
    with pytest.raises(ValueError):
        OptionalPGGModel(pop=10, r=3.0, sigma=0.0)       # need sigma > 0
    with pytest.raises(ValueError):
        OptionalPGGModel(pop=10, r=3.0, sigma=2.5)       # need sigma < r-1 = 2
    with pytest.raises(ValueError):
        OptionalPGGModel(pop=10, mu=1.5)                 # need mu <= 1


# -- the imitation-with-mutation micro-rule -----------------------------------

def test_frequencies_stay_normalised_each_generation():
    m = OptionalPGGModel(pop=1000, r=3.0, sigma=1.0, N=5, mu=1e-3, seed=1)
    for _ in range(20):
        m.step()
        x_c, x_d, x_l = m.frequencies()
        assert x_c + x_d + x_l == pytest.approx(1.0)
        assert 0.0 <= x_c <= 1.0 and 0.0 <= x_d <= 1.0 and 0.0 <= x_l <= 1.0


def test_compulsory_arm_never_produces_a_loner():
    # With the loner strategy unavailable, no update (imitation or mutation) can ever
    # introduce a loner — the population stays on the C/D edge.
    m = OptionalPGGModel(pop=1000, r=3.0, sigma=1.0, N=5, mu=0.05, compulsory=True, seed=2)
    for _ in range(30):
        m.step()
        assert m.strategy_count(L) == 0


def test_mutation_off_imitation_only_lets_best_strategy_take_over():
    # With mu=0 (pure imitation) starting mostly-defect, defectors — the strategy with the
    # highest payoff when cooperators are present — spread; cooperators do not take over.
    m = OptionalPGGModel(pop=2000, r=3.0, sigma=1.0, N=5, mu=0.0, compulsory=True,
                         init="mostly_defect", seed=3)
    fC0 = m.strategy_fraction(C)
    for _ in range(50):
        m.step()
    # in the compulsory game defectors dominate; cooperators are driven down.
    assert m.strategy_fraction(D) > 0.5
    assert m.strategy_fraction(C) <= fC0 + 1e-9


def test_all_defect_is_absorbing_without_mutation_and_loner():
    # A pure-defector compulsory population with no mutation stays all-defect (nothing can
    # invade). This is the sterile Nash outcome the loner option later rescues.
    m = OptionalPGGModel(pop=500, r=3.0, sigma=1.0, N=5, mu=0.0, compulsory=True, seed=0)
    for a in m.agent_list:
        a.strategy = D
    for _ in range(20):
        m.step()
    assert m.strategy_fraction(D) == pytest.approx(1.0)


# -- burn-in / summary estimator ----------------------------------------------

def test_run_summary_shape_and_measure_window():
    res = run_single(pop=400, r=3.0, sigma=1.0, N=5, seed=0, n_gen=60, measure_from=20)
    assert res["pop"] == 400 and res["compulsory"] is False
    assert len(res["fC_series"]) == 61          # gen-0 baseline + 60 generations
    assert len(res["fD_series"]) == 61
    assert len(res["fL_series"]) == 61
    # time-averaged frequencies are valid probabilities summing to ~1.
    s = res["timeavg_fC"] + res["timeavg_fD"] + res["timeavg_fL"]
    assert s == pytest.approx(1.0, abs=1e-9)
    assert 0.0 <= res["coop_amplitude"] <= 1.0


def test_run_rejects_bad_measure_window():
    m = OptionalPGGModel(pop=100, seed=0)
    with pytest.raises(ValueError):
        m.run(50, measure_from=-1)
    with pytest.raises(ValueError):
        m.run(50, measure_from=100)


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(pop=800, r=3.0, sigma=1.0, N=5, seed=42, n_gen=80, measure_from=20)
    b = run_single(pop=800, r=3.0, sigma=1.0, N=5, seed=42, n_gen=80, measure_from=20)
    assert a["fC_series"] == b["fC_series"]
    assert a["fD_series"] == b["fD_series"]
    assert a["fL_series"] == b["fL_series"]
    assert a["timeavg_fC"] == b["timeavg_fC"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(pop=800, r=3.0, sigma=1.0, N=5, seed=1, n_gen=80, measure_from=20)
    b = run_single(pop=800, r=3.0, sigma=1.0, N=5, seed=2, n_gen=80, measure_from=20)
    for res in (a, b):
        for series in (res["fC_series"], res["fD_series"], res["fL_series"]):
            assert all(0.0 <= x <= 1.0 for x in series)


# -- qualitative sanity (the locked grade lives in run.py) --------------------

def test_voluntary_sustains_cooperation_more_than_compulsory():
    # Faithfulness sanity, not the locked grade: at r=3, sigma=1 the voluntary game keeps a
    # meaningfully positive time-averaged cooperator frequency while the compulsory control
    # collapses to near-zero cooperation.
    vol = run_single(pop=3000, r=3.0, sigma=1.0, N=5, mu=1e-3, compulsory=False,
                     seed=0, n_gen=1500, measure_from=500)
    comp = run_single(pop=3000, r=3.0, sigma=1.0, N=5, mu=1e-3, compulsory=True,
                      seed=0, n_gen=1500, measure_from=500)
    assert comp["timeavg_fC"] < 0.05                 # compulsory collapses to all-D
    assert vol["timeavg_fC"] > comp["timeavg_fC"] + 0.05
    # all three strategies are present on time-average in the voluntary game (coexistence).
    assert vol["timeavg_fC"] > 0.05
    assert vol["timeavg_fD"] > 0.05
    assert vol["timeavg_fL"] > 0.05
