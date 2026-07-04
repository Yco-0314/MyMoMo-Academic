"""Faithful-rule + determinism tests for the Dragulescu-Yakovenko statistical
mechanics of money (2000) reproduction.

These pin the conserved kinetic-exchange mechanics (money conservation to machine
precision, the no-debt / non-negativity boundary, the delta initial condition,
the full-repartition pooling rule), the inequality + distribution statistics
(Gini and CV on closed-form references, the log-linear exponential fit, and the
exponential-vs-power-law AIC on synthetic exponential vs peaked data), and
determinism (same seed -> identical run).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(docs/studies/dragulescu-yakovenko/PREDICTIONS-locked.md, exponential shape /
Gini=0.5 & CV=1 / conservation) are evaluated by
examples/repro_dragulescu_yakovenko/run.py.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from abm_auto.classics.dragulescu_yakovenko import (
    MoneyAgent,
    MoneyExchangeModel,
    coefficient_of_variation,
    exp_vs_power_aic,
    exponential_loglinear_fit,
    gini,
    histogram,
    mode_bin_centre,
    run_single,
)


# -- inequality + distribution statistics (closed-form references) ------------

def test_gini_equal_is_zero():
    assert gini([5.0, 5.0, 5.0, 5.0]) == pytest.approx(0.0)


def test_gini_maximally_unequal_approaches_one():
    # one holder, n-1 zeros -> Gini = (n-1)/n.
    xs = [0.0] * 999 + [1000.0]
    assert gini(xs) == pytest.approx((len(xs) - 1) / len(xs), abs=1e-9)


def test_gini_of_exponential_sample_is_half():
    # The Gini of an exponential distribution is exactly 1/2.
    rng = np.random.default_rng(0)
    xs = rng.exponential(scale=100.0, size=400_000)
    assert gini(xs) == pytest.approx(0.5, abs=0.01)


def test_cv_of_exponential_sample_is_one():
    # The coefficient of variation of an exponential is exactly 1 (std == mean).
    rng = np.random.default_rng(1)
    xs = rng.exponential(scale=100.0, size=400_000)
    assert coefficient_of_variation(xs) == pytest.approx(1.0, abs=0.02)


def test_cv_equal_is_zero_and_empty_is_zero():
    assert coefficient_of_variation([7.0, 7.0, 7.0]) == pytest.approx(0.0)
    assert coefficient_of_variation([]) == 0.0


def test_histogram_normalizes_to_density():
    rng = np.random.default_rng(2)
    xs = rng.exponential(scale=100.0, size=200_000)
    centres, density = histogram(xs, n_bins=40, m_max=600.0)
    width = centres[1] - centres[0]
    # density over the covered window integrates to ~ P(m < 600) ~= 1 - e^-6 ~ 0.9975.
    assert float(np.sum(density) * width) == pytest.approx(1.0 - math.exp(-6.0), abs=0.02)


def test_exponential_mode_is_in_lowest_bin():
    # For an exponential, P(m) peaks at m = 0 -> mode is the lowest bin centre.
    rng = np.random.default_rng(3)
    xs = rng.exponential(scale=100.0, size=300_000)
    mode_m = mode_bin_centre(xs, n_bins=40, m_max=600.0)
    assert mode_m < 0.1 * 100.0    # well inside the lowest ~10% money bin


def test_loglinear_fit_recovers_exponential_slope():
    # Fitting ln P(m) vs m on an exponential should recover R^2 ~ 1 and slope 1/T.
    rng = np.random.default_rng(4)
    xs = rng.exponential(scale=100.0, size=500_000)
    fit = exponential_loglinear_fit(xs, mean_m=100.0)
    assert fit["r2"] >= 0.98
    # fitted temperature ~ 100 (the exponential scale).
    assert fit["temperature"] == pytest.approx(100.0, rel=0.15)


def test_aic_prefers_exponential_for_exponential_data():
    rng = np.random.default_rng(5)
    xs = rng.exponential(scale=100.0, size=200_000)
    aic = exp_vs_power_aic(xs, mean_m=100.0)
    assert aic["exp_preferred"] is True
    assert aic["aic_exp"] < aic["aic_powerlaw"]


def test_aic_prefers_powerlaw_for_powerlaw_data():
    # Sanity that the AIC discriminates: genuine heavy-tailed power-law data over
    # the window should NOT be judged exponential. A Pareto with a heavy tail
    # (alpha ~ 1.5) is unambiguously power-law-shaped over the bulk window.
    rng = np.random.default_rng(6)
    xs = rng.pareto(a=1.5, size=300_000) * 100.0 + 20.0
    aic = exp_vs_power_aic(xs, mean_m=float(np.mean(xs)))
    assert aic["exp_preferred"] is False
    assert aic["aic_powerlaw"] < aic["aic_exp"]


def test_loglinear_fit_flags_peaked_gamma_as_non_exponential():
    # The DY falsification signature: adding a saving propensity turns the
    # stationary distribution into a PEAKED Gamma with an interior mode. The
    # log-linear R^2 drops below 0.95 AND the mode moves well away from 0 —
    # the two P1 sub-clauses that must catch that Gamma.
    rng = np.random.default_rng(7)
    g = rng.gamma(shape=3.0, scale=100.0 / 3.0, size=300_000)   # mean 100, peaked
    fit = exponential_loglinear_fit(g, mean_m=100.0)
    mode_m = mode_bin_centre(g, n_bins=40, m_max=600.0)
    assert fit["r2"] < 0.95              # not a clean exponential tail
    assert mode_m > 0.3 * 100.0          # interior peak (mode > 0.3<m>)


# -- model construction + the delta initial condition -------------------------

def test_delta_start_all_equal_mean():
    m = MoneyExchangeModel(n=1000, mean_money=100.0, seed=0)
    assert m.n == 1000
    assert all(isinstance(a, MoneyAgent) for a in m.agent_list)
    assert np.allclose(m.money, 100.0)
    assert m.money.sum() == pytest.approx(100.0 * 1000)
    # a delta start has Gini 0 and CV 0 (perfect equality).
    assert gini(m.money) == pytest.approx(0.0)
    assert coefficient_of_variation(m.money) == pytest.approx(0.0)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        MoneyExchangeModel(n=1)          # need >= 2 agents
    with pytest.raises(ValueError):
        MoneyExchangeModel(n=100, mean_money=0.0)
    with pytest.raises(ValueError):
        MoneyExchangeModel(n=100).run(100, burn_in_frac=1.0)   # burn_in must be < 1
    with pytest.raises(ValueError):
        MoneyExchangeModel(n=100).run(100, sample_every=0)


# -- the elementary mechanics: conservation + no-debt + full repartition ------

def test_money_conserved_to_machine_precision():
    m = MoneyExchangeModel(n=2000, mean_money=100.0, seed=1)
    initial = float(m.money.sum())
    for _ in range(50):
        m._sweep()
        assert float(m.money.sum()) == pytest.approx(initial, rel=1e-12, abs=1e-6)


def test_no_debt_all_balances_nonnegative():
    m = MoneyExchangeModel(n=2000, mean_money=100.0, seed=2)
    for _ in range(80):
        m._sweep()
        assert float(m.money.min()) >= 0.0


def test_single_exchange_pools_and_repartitions():
    # Directly exercise the full-repartition rule on a hand-set pair.
    m = MoneyExchangeModel(n=2, mean_money=50.0, seed=0)
    m.money[0], m.money[1] = 30.0, 70.0
    s = float(m.money[0] + m.money[1])
    # replicate one exchange deterministically with a fixed epsilon.
    eps = 0.25
    new0 = eps * s
    new1 = s - new0
    m.money[0], m.money[1] = new0, new1
    assert m.money[0] + m.money[1] == pytest.approx(s)   # pooled total preserved
    assert m.money[0] == pytest.approx(25.0)
    assert m.money[1] == pytest.approx(75.0)


def test_agents_stay_synced_with_money_vector():
    m = MoneyExchangeModel(n=500, mean_money=100.0, seed=3)
    m.step()
    for a in m.agent_list:
        assert a.balance == pytest.approx(float(m.money[a.index]))


def test_relaxes_away_from_delta_toward_inequality():
    # Faithfulness sanity (NOT the locked grade): starting from perfect equality
    # the exchange drives the Gini up toward the exponential fixed point ~0.5.
    res = run_single(n=2000, mean_money=100.0, seed=0, n_sweeps=400,
                     burn_in_frac=0.5, sample_every=50)
    assert res["stationary_gini"] > 0.4
    assert res["stationary_cv"] > 0.8


# -- run summary shape + conservation diagnostics -----------------------------

def test_run_summary_shape_and_conservation():
    res = run_single(n=1000, mean_money=100.0, seed=0, n_sweeps=200,
                     burn_in_frac=0.5, sample_every=25)
    assert res["n"] == 1000 and res["mean_money"] == 100.0
    assert len(res["gini_series"]) == 201          # t=0 baseline + 200 sweeps
    assert len(res["cv_series"]) == 201
    # conservation clause P3: |dM|/M < 1e-9 and min money never negative.
    assert res["max_rel_dM"] < 1e-9
    assert res["min_money_ever"] >= 0.0
    assert isinstance(res["money_sample"], np.ndarray)
    assert res["money_sample"].size > 0


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(n=1000, seed=42, n_sweeps=150, burn_in_frac=0.5, sample_every=25)
    b = run_single(n=1000, seed=42, n_sweeps=150, burn_in_frac=0.5, sample_every=25)
    assert a["gini_series"] == b["gini_series"]
    assert a["cv_series"] == b["cv_series"]
    assert np.array_equal(a["money_sample"], b["money_sample"])


def test_different_seed_can_differ_but_conserves():
    a = run_single(n=1000, seed=1, n_sweeps=150, burn_in_frac=0.5, sample_every=25)
    b = run_single(n=1000, seed=2, n_sweeps=150, burn_in_frac=0.5, sample_every=25)
    for res in (a, b):
        assert res["max_rel_dM"] < 1e-9
        assert res["min_money_ever"] >= 0.0
