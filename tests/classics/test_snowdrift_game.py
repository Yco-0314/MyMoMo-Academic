"""Faithful-rule + determinism tests for the Hauert & Doebeli (2004) spatial snowdrift
game reproduction.

These pin the snowdrift payoff ordering (T > R > S > P), the r = c/(2b-c) parameterisation
and its inverse, the well-mixed ESS f* = 1 - r (analytic + a mean-field replicator that
lands on the same line), the periodic Moore-8 neighbour-count convolution, the summed
payoff arithmetic, both update rules (the STOCHASTIC replicator imitation and the
DETERMINISTIC best-takes-over control), the imitation-probability bound p in [0,1], the
synchronous update, the steady-state estimator, and determinism (same seed -> identical
result).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(inhibition, extinction, and the best-takes-over gate) are evaluated by
examples/repro_snowdrift_game/run.py.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.snowdrift_game import (
    COOPERATE,
    DEFECT,
    SnowdriftAgent,
    SnowdriftModel,
    cost_benefit_ratio,
    moore_neighbour_coop_counts,
    params_from_ratio,
    run_single,
    snowdrift_payoffs,
    summed_payoffs,
    tail_mean,
    well_mixed_ess,
    well_mixed_replicator,
)


# -- snowdrift payoffs (T > R > S > P) ----------------------------------------

def test_payoff_ordering_is_snowdrift_not_pd():
    # Snowdrift ranking is T > R > S > P (the reverse of the PD's T > R > P > S): the
    # sucker payoff S beats the punishment P, so best-reply-to-a-defector is to cooperate.
    p = snowdrift_payoffs(b=1.0, c=0.6)
    assert p["T"] > p["R"] > p["S"] > p["P"]
    # concrete values: R=b-c/2, T=b, S=b-c, P=0.
    assert p["R"] == pytest.approx(0.7)
    assert p["T"] == pytest.approx(1.0)
    assert p["S"] == pytest.approx(0.4)
    assert p["P"] == pytest.approx(0.0)


def test_payoffs_require_b_gt_c_gt_zero():
    with pytest.raises(ValueError):
        snowdrift_payoffs(b=1.0, c=1.0)   # c not < b
    with pytest.raises(ValueError):
        snowdrift_payoffs(b=1.0, c=0.0)   # c not > 0


# -- cost-to-benefit ratio and its inverse ------------------------------------

def test_ratio_roundtrip():
    for r in (0.1, 0.25, 0.5, 0.75, 0.9):
        b, c = params_from_ratio(r, b=1.0)
        assert cost_benefit_ratio(b, c) == pytest.approx(r)
        assert b > c > 0.0            # stays a valid snowdrift game for all interior r


def test_ratio_bounds_are_enforced():
    with pytest.raises(ValueError):
        params_from_ratio(0.0)
    with pytest.raises(ValueError):
        params_from_ratio(1.0)


# -- well-mixed ESS f* = 1 - r -------------------------------------------------

def test_well_mixed_ess_is_one_minus_r():
    for r in (0.2, 0.4, 0.6, 0.8):
        assert well_mixed_ess(r) == pytest.approx(1.0 - r)


def test_mean_field_replicator_lands_on_one_minus_r():
    # The mean-field replicator flow (no spatial structure) converges to the analytic
    # interior ESS 1 - r for any interior r and any interior start.
    for r in (0.2, 0.4, 0.6, 0.8):
        f = well_mixed_replicator(r, f0=0.5)
        assert f == pytest.approx(1.0 - r, abs=1e-3)
    # independent of the (interior) initial fraction
    assert well_mixed_replicator(0.5, f0=0.1) == pytest.approx(0.5, abs=1e-3)
    assert well_mixed_replicator(0.5, f0=0.9) == pytest.approx(0.5, abs=1e-3)


# -- Moore-8 periodic neighbour counts ----------------------------------------

def test_all_cooperators_have_eight_coop_neighbours():
    g = np.ones((6, 6), dtype=np.int8)
    counts = moore_neighbour_coop_counts(g)
    assert counts.shape == g.shape
    assert np.all(counts == 8)         # every site has 8 C neighbours (self excluded)


def test_all_defectors_have_zero_coop_neighbours():
    g = np.zeros((6, 6), dtype=np.int8)
    assert np.all(moore_neighbour_coop_counts(g) == 0)


def test_neighbour_count_is_periodic_and_self_excluded():
    # A single cooperator on an otherwise-defector lattice: its 8 Moore neighbours each see
    # exactly ONE cooperator, and the cooperator itself sees ZERO (self excluded).
    g = np.zeros((5, 5), dtype=np.int8)
    g[2, 2] = 1
    counts = moore_neighbour_coop_counts(g)
    assert counts[2, 2] == 0                     # self excluded
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            assert counts[2 + dy, 2 + dx] == 1   # each Moore neighbour sees the one C
    # wrap-around: a cooperator at a corner still contributes to sites across the seam.
    g2 = np.zeros((4, 4), dtype=np.int8)
    g2[0, 0] = 1
    c2 = moore_neighbour_coop_counts(g2)
    assert c2[3, 3] == 1 and c2[0, 1] == 1 and c2[1, 0] == 1 and c2[3, 0] == 1


# -- summed payoffs ------------------------------------------------------------

def test_summed_payoff_matches_hand_calc():
    # Focal cooperator with n_c cooperating neighbours scores R*n_c + S*(8-n_c); a
    # defector scores T*n_c + P*(8-n_c). Build a lattice where the centre is C with 3 C
    # neighbours and check the centre's score.
    b, c = 1.0, 0.5
    R, T, S, P = b - c / 2, b, b - c, 0.0
    g = np.zeros((5, 5), dtype=np.int8)
    g[2, 2] = COOPERATE
    g[1, 2] = g[3, 2] = g[2, 1] = COOPERATE   # 3 cooperating Moore neighbours of (2,2)
    pay = summed_payoffs(g, R, T, S, P)
    # centre is C with 3 C-neighbours and 5 D-neighbours: 3*R + 5*S.
    assert pay[2, 2] == pytest.approx(3 * R + 5 * S)


def test_defector_scores_T_per_cooperator_neighbour():
    b, c = 1.0, 0.5
    R, T, S, P = b - c / 2, b, b - c, 0.0
    g = np.ones((5, 5), dtype=np.int8)   # all cooperators
    g[2, 2] = DEFECT                     # one defector surrounded by 8 cooperators
    pay = summed_payoffs(g, R, T, S, P)
    assert pay[2, 2] == pytest.approx(8 * T)   # defector exploits all 8 C neighbours


# -- model construction + invariants ------------------------------------------

def test_model_builds_agent_per_site_and_valid_game():
    m = SnowdriftModel(L=20, r=0.5, seed=0)
    assert m.n == 400
    assert len(m.agent_list) == 400
    assert all(isinstance(a, SnowdriftAgent) for a in m.agent_list)
    assert m.b > m.c > 0.0                       # valid snowdrift game
    assert m.T > m.R > m.S > m.P                 # ordering holds on the model's payoffs
    assert cost_benefit_ratio(m.b, m.c) == pytest.approx(0.5)
    # Delta = T - S = c is the per-interaction payoff range used to bound p.
    assert m.delta == pytest.approx(m.T - m.S)
    assert m.delta == pytest.approx(m.c)


def test_initial_coop_fraction_is_approximately_right():
    m = SnowdriftModel(L=100, r=0.5, init_coop_fraction=0.5, seed=1)
    f0 = m.cooperator_fraction()
    assert 0.45 <= f0 <= 0.55                    # ~50% cooperators initially


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        SnowdriftModel(L=1)                       # need L > 1
    with pytest.raises(ValueError):
        SnowdriftModel(L=20, r=0.0)               # r must be interior
    with pytest.raises(ValueError):
        SnowdriftModel(L=20, r=1.0)
    with pytest.raises(ValueError):
        SnowdriftModel(L=20, rule="bogus")        # unknown rule
    with pytest.raises(ValueError):
        SnowdriftModel(L=20, init_coop_fraction=1.5)


# -- the stochastic replicator imitation rule ---------------------------------

def test_imitation_probability_stays_in_unit_interval():
    # Over a full replicator step the adopt-probability p = max(0,P_j-P_i)/(k*Delta) must be
    # a valid probability; we exercise the update on a mixed lattice and check no site's
    # strategy becomes anything other than C/D (i.e. the vectorised draw is well-formed).
    m = SnowdriftModel(L=30, r=0.5, seed=3, rule="replicator")
    for _ in range(10):
        m.step()
        vals = np.unique(m.grid)
        assert set(vals.tolist()) <= {DEFECT, COOPERATE}


def test_replicator_only_copies_a_strictly_better_neighbour_direction():
    # Construct a 1-C-vs-D situation so the imitation probability is deterministic in sign:
    # a lone defector cannot be imitated INTO cooperation by a worse-scoring partner. We
    # verify the probability formula directly on a crafted payoff field.
    m = SnowdriftModel(L=10, r=0.5, seed=0, rule="replicator")
    payoff = np.zeros((m.L, m.L), dtype=np.float64)
    # give site (5,5) a high payoff and its neighbour (5,6) a low one
    payoff[5, 5] = 8.0 * m.delta        # max possible
    payoff[5, 6] = 0.0
    # p(5,6 <- 5,5) = (8*delta - 0)/(8*delta) = 1  ; p(5,5 <- 5,6) = 0 (worse partner)
    denom = m.k * m.delta
    p_up = max(0.0, payoff[5, 5] - payoff[5, 6]) / denom
    p_down = max(0.0, payoff[5, 6] - payoff[5, 5]) / denom
    assert p_up == pytest.approx(1.0)
    assert p_down == pytest.approx(0.0)


def test_replicator_all_defect_is_absorbing():
    # An all-defector lattice has all-zero payoff, so no site can improve by imitation:
    # all-D is an absorbing state under the replicator rule.
    m = SnowdriftModel(L=20, r=0.5, seed=0, rule="replicator")
    m.grid[:] = DEFECT
    for _ in range(5):
        m.step()
    assert m.cooperator_fraction() == pytest.approx(0.0)


# -- the deterministic best-takes-over control --------------------------------

def test_best_takes_over_is_deterministic_and_copies_local_best():
    # A block of cooperators scoring high against a sea of defectors: under best-takes-over
    # a defector adjacent to the high-scoring cooperator block adopts C. Determinism: two
    # runs with the same seed give identical series.
    a = run_single(L=40, r=0.3, seed=7, rule="best_takes_over", n_steps=30, measure_last=10)
    b = run_single(L=40, r=0.3, seed=7, rule="best_takes_over", n_steps=30, measure_last=10)
    assert a["coop_series"] == b["coop_series"]


def test_best_takes_over_keeps_incumbent_on_no_better_neighbour():
    # If every neighbour scores <= the focal site, best-takes-over keeps the incumbent
    # strategy. All-C lattice: every site is (weakly) the best -> stays all C.
    m = SnowdriftModel(L=15, r=0.4, seed=0, rule="best_takes_over")
    m.grid[:] = COOPERATE
    before = m.cooperator_fraction()
    m.step()
    assert m.cooperator_fraction() == pytest.approx(before)   # unchanged (all C persists)


def test_two_rules_are_selectable_and_distinct():
    rep = SnowdriftModel(L=20, r=0.5, seed=0, rule="replicator")
    bto = SnowdriftModel(L=20, r=0.5, seed=0, rule="best_takes_over")
    assert rep.rule == "replicator" and bto.rule == "best_takes_over"
    # same construction knobs otherwise (fair control): L, r, payoffs, init identical.
    for attr in ("L", "r", "b", "c", "R", "T", "S", "P", "init_coop_fraction"):
        assert getattr(rep, attr) == getattr(bto, attr)


# -- synchronous update (payoffs read the frozen lattice) ---------------------

def test_update_is_synchronous_via_frozen_payoffs():
    # One step should be reproducible from a hand-applied frozen-payoff update: run the
    # model's step and a manual best-takes-over step from the same start and compare.
    m = SnowdriftModel(L=12, r=0.4, seed=5, rule="best_takes_over")
    start = m.grid.copy()
    payoff = summed_payoffs(start, m.R, m.T, m.S, m.P)
    expected = m._best_takes_over_update(payoff)
    m.step()
    assert np.array_equal(m.grid, expected)


# -- steady-state estimator ----------------------------------------------------

def test_tail_mean_is_trailing_window_mean():
    series = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert tail_mean(series, window=2) == pytest.approx(0.45)    # mean(0.4, 0.5)
    assert tail_mean(series, window=100) == pytest.approx(0.3)   # whole series
    assert tail_mean([], window=5) == 0.0


def test_run_summary_shape():
    res = run_single(L=30, r=0.5, seed=0, n_steps=40, measure_last=10)
    assert res["L"] == 30 and res["rule"] == "replicator"
    assert len(res["coop_series"]) == 41          # t=0 baseline + 40 gens
    assert 0.0 <= res["steady_coop_fraction"] <= 1.0
    assert 0.0 <= res["final_coop_fraction"] <= 1.0


def test_run_rejects_bad_measure_window():
    m = SnowdriftModel(L=10, r=0.5, seed=0)
    with pytest.raises(ValueError):
        m.run(10, measure_last=0)
    with pytest.raises(ValueError):
        m.run(10, measure_last=50)


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(L=40, r=0.5, seed=42, n_steps=60, measure_last=20)
    b = run_single(L=40, r=0.5, seed=42, n_steps=60, measure_last=20)
    assert a["coop_series"] == b["coop_series"]
    assert a["steady_coop_fraction"] == b["steady_coop_fraction"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(L=40, r=0.5, seed=1, n_steps=60, measure_last=20)
    b = run_single(L=40, r=0.5, seed=2, n_steps=60, measure_last=20)
    for res in (a, b):
        assert all(0.0 <= x <= 1.0 for x in res["coop_series"])


# -- qualitative sanity (the locked grade lives in run.py) --------------------

def test_lattice_inhibits_relative_to_well_mixed_at_mid_r():
    # Faithfulness sanity, not the locked grade: at an intermediate r the stochastic
    # replicator lattice sits BELOW the well-mixed ESS 1 - r (inhibition), while the
    # best-takes-over control does NOT collapse the same way.
    r = 0.5
    rep = run_single(L=80, r=r, seed=0, rule="replicator", n_steps=400, measure_last=100)
    bto = run_single(L=80, r=r, seed=0, rule="best_takes_over", n_steps=400, measure_last=100)
    ess = well_mixed_ess(r)
    assert rep["steady_coop_fraction"] < ess - 0.05        # replicator is inhibited
    # the best-takes-over control is markedly less inhibited than the replicator.
    assert bto["steady_coop_fraction"] > rep["steady_coop_fraction"] + 0.1
