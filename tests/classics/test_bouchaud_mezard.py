"""Faithful-rule + determinism tests for the Bouchaud-Mézard wealth-condensation
(2000) reproduction.

These pin the inequality + tail statistics (Gini, normalisation, heavy-tail ratios,
the CCDF top-decile slope, the Hill tail-exponent estimate, and the power-law-vs-
exponential AIC), the vectorised Euler-Maruyama SDE micro-rule (the physics noise
normalisation ⟨dη²⟩ = 2σ²·dt that yields μ = 1 + J/σ², the all-to-all exchange
conserving ⟨W⟩ in expectation, strictly-positive wealth), the explicit agent roster,
the steady-state estimator, and determinism (same seed → identical result).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(Gini bands, heavy power-law tail, μ̂ ordering) are evaluated by
examples/repro_bouchaud_mezard/run.py against the full N≈3000, long-run sweep.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from abm_auto.classics.bouchaud_mezard import (
    BouchaudMezardModel,
    WealthAgent,
    J_for_mu,
    gini,
    hill_tail_exponent,
    max_over_mean,
    normalise,
    percentile_over_mean,
    powerlaw_beats_exponential_aic,
    run_single,
    tail_mean,
    top_decile_ccdf_slope,
)


# -- Gini ---------------------------------------------------------------------

def test_gini_equal_is_zero():
    assert gini([5.0, 5.0, 5.0, 5.0]) == pytest.approx(0.0)


def test_gini_of_one_rich_all_poor_approaches_one():
    # n-1 zeros and one positive value -> Gini = (n-1)/n.
    vals = [0.0] * 99 + [100.0]
    assert gini(vals) == pytest.approx(99.0 / 100.0, abs=1e-9)


def test_gini_is_scale_invariant():
    xs = [1.0, 2.0, 3.0, 10.0, 40.0]
    assert gini(xs) == pytest.approx(gini([7.0 * x for x in xs]), abs=1e-12)


def test_gini_empty_and_all_zero_are_zero():
    assert gini([]) == 0.0
    assert gini([0.0, 0.0, 0.0]) == 0.0


def test_gini_matches_known_uniform_value():
    # Gini of {1,2,3,4} = 0.25 (classic small example).
    assert gini([1.0, 2.0, 3.0, 4.0]) == pytest.approx(0.25, abs=1e-9)


# -- normalisation + heavy-tail ratios ----------------------------------------

def test_normalise_divides_by_mean():
    w = normalise([1.0, 2.0, 3.0])   # mean 2 -> [0.5, 1.0, 1.5]
    assert np.allclose(w, [0.5, 1.0, 1.5])
    assert float(np.mean(w)) == pytest.approx(1.0)


def test_max_over_mean_of_flat_is_one():
    assert max_over_mean([3.0, 3.0, 3.0]) == pytest.approx(1.0)


def test_max_over_mean_picks_the_top():
    # one big value dominates: max/mean is large.
    vals = [1.0] * 99 + [1000.0]
    mean = (99 * 1.0 + 1000.0) / 100.0
    assert max_over_mean(vals) == pytest.approx(1000.0 / mean)


def test_percentile_over_mean_monotone_in_q():
    xs = list(range(1, 1001))
    lo = percentile_over_mean(xs, 50.0)
    hi = percentile_over_mean(xs, 99.9)
    assert hi > lo > 0.0


# -- tail estimators on a KNOWN Pareto -----------------------------------------

def _pareto_sample(alpha: float, n: int, seed: int = 0) -> np.ndarray:
    """Exact Pareto(alpha) tail sample: P(W>w) = w^{-alpha} for w>=1, via inverse-CDF."""
    rng = np.random.default_rng(seed)
    u = rng.random(n)
    return (1.0 - u) ** (-1.0 / alpha)   # W = (1-U)^{-1/alpha}, W>=1


def test_ccdf_slope_recovers_pareto_exponent():
    # A Pareto(alpha=2) tail has CCDF log-log slope ~ -alpha over its top decile.
    xs = _pareto_sample(2.0, 50000, seed=1)
    slope = top_decile_ccdf_slope(xs)
    assert slope is not None
    assert -2.6 < slope < -1.4          # near -2


def test_hill_recovers_pareto_exponent():
    # Hill estimator of a Pareto(alpha=2.5) tail returns ~2.5.
    xs = _pareto_sample(2.5, 80000, seed=2)
    mu_hat = hill_tail_exponent(xs, tail_frac=0.1)
    assert mu_hat is not None
    assert 2.1 < mu_hat < 2.9


def test_powerlaw_beats_exponential_on_pareto():
    # On a genuine Pareto tail, the power-law fit wins the AIC comparison.
    xs = _pareto_sample(2.0, 50000, seed=3)
    wins, aic_pl, aic_exp = powerlaw_beats_exponential_aic(xs, tail_frac=0.1)
    assert wins is True
    assert aic_pl < aic_exp


def test_exponential_data_does_not_prefer_powerlaw():
    # On EXPONENTIAL data (the Dragulescu-Yakovenko-style thin tail), the power law
    # must NOT win — this is the discriminating control that keeps P2 honest.
    rng = np.random.default_rng(4)
    xs = rng.exponential(1.0, size=50000)
    wins, aic_pl, aic_exp = powerlaw_beats_exponential_aic(xs, tail_frac=0.1)
    assert wins is False
    assert aic_exp <= aic_pl


def test_tail_estimators_return_none_on_tiny_input():
    assert top_decile_ccdf_slope([1.0, 2.0, 3.0]) is None
    assert hill_tail_exponent([1.0, 2.0, 3.0]) is None


# -- model construction + invariants ------------------------------------------

def test_population_is_wealth_agents_at_w0():
    m = BouchaudMezardModel(n=500, sigma=0.1, J=0.01, dt=0.01, w0=1.0, seed=0)
    assert len(m.agent_list) == 500
    assert all(isinstance(a, WealthAgent) for a in m.agent_list)
    assert all(a.wealth == pytest.approx(1.0) for a in m.agent_list)
    assert np.allclose(m.W, 1.0)


def test_mu_theory_is_one_plus_J_over_sigma2():
    m = BouchaudMezardModel(n=100, sigma=0.1, J=0.02, dt=0.01, seed=0)
    # mu = 1 + J/sigma^2 = 1 + 0.02/0.01 = 3.
    assert m.mu_theory == pytest.approx(3.0)


def test_J_for_mu_inverts_the_exponent_formula():
    sigma = 0.1
    for mu in (1.4, 2.0, 3.0, 5.0):
        J = J_for_mu(mu, sigma)
        m = BouchaudMezardModel(n=50, sigma=sigma, J=J, dt=0.01, seed=0)
        assert m.mu_theory == pytest.approx(mu)


def test_physics_noise_normalisation_is_two_sigma2_dt():
    # The load-bearing convention: Var(d eta) = 2 sigma^2 dt (NOT sigma^2 dt), which is
    # what makes mu = 1 + J/sigma^2 hold. The Ito->log drift is -1/2 of that.
    sigma, dt = 0.1, 0.01
    m = BouchaudMezardModel(n=10, sigma=sigma, J=0.01, dt=dt, seed=0)
    assert m.noise_var_per_step == pytest.approx(2.0 * sigma * sigma * dt)
    assert m._noise_std == pytest.approx(sigma * math.sqrt(2.0 * dt))
    assert m._drift == pytest.approx(-sigma * sigma * dt)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        BouchaudMezardModel(n=1)                 # need n > 1
    with pytest.raises(ValueError):
        BouchaudMezardModel(n=10, sigma=0.0)     # sigma > 0
    with pytest.raises(ValueError):
        BouchaudMezardModel(n=10, J=-1.0)        # J >= 0
    with pytest.raises(ValueError):
        BouchaudMezardModel(n=10, dt=0.0)        # dt > 0
    with pytest.raises(ValueError):
        BouchaudMezardModel(n=10, w0=0.0)        # w0 > 0


# -- the elementary SDE mechanics ---------------------------------------------

def test_wealth_stays_strictly_positive():
    m = BouchaudMezardModel(n=2000, sigma=0.2, J=0.02, dt=0.01, seed=1)
    for _ in range(200):
        m.step()
    assert np.all(m.W > 0.0)


def test_zero_noise_zero_exchange_is_frozen():
    # With sigma tiny and J=0 the multiplicative factor is ~1 and there is no exchange,
    # so wealth barely moves (the delta start is (near) a fixed point). We use a small
    # sigma (sigma>0 is required) and check the spread stays negligible.
    m = BouchaudMezardModel(n=1000, sigma=1e-6, J=0.0, dt=0.01, seed=0)
    for _ in range(50):
        m.step()
    assert np.allclose(m.W, 1.0, atol=1e-3)


def test_exchange_pulls_toward_the_mean():
    # With NO noise (sigma->0) the exchange term alone contracts any spread toward the
    # common mean: an initially unequal vector becomes MORE equal after stepping.
    m = BouchaudMezardModel(n=4, sigma=1e-9, J=1.0, dt=0.05, seed=0)
    m.W = np.array([1.0, 1.0, 1.0, 5.0])         # one rich agent
    g0 = gini(m.W)
    for _ in range(20):
        m.step()
    g1 = gini(m.W)
    assert g1 < g0                                # redistribution reduces inequality
    assert float(m.W.mean()) == pytest.approx(2.0, abs=1e-6)   # mean conserved


def test_mean_conserved_in_expectation_without_exchange():
    # The Ito->log correction keeps E[W(t+dt)/W(t)] = 1 for the noise part: over many
    # agents the sample mean stays ~ w0 even with J=0 (pure multiplicative noise).
    m = BouchaudMezardModel(n=20000, sigma=0.1, J=0.0, dt=0.01, seed=7)
    for _ in range(100):
        m.step()
    # mean should hover near 1 (no systematic drift up or down from the noise).
    assert float(m.W.mean()) == pytest.approx(1.0, rel=0.15)


def test_roster_is_synced_to_the_vector():
    m = BouchaudMezardModel(n=100, sigma=0.1, J=0.01, dt=0.01, seed=3)
    for _ in range(10):
        m.step()
    for a, w in zip(m.agent_list, m.W):
        assert a.wealth == pytest.approx(float(w))


# -- steady-state estimator ---------------------------------------------------

def test_tail_mean_is_trailing_window_mean():
    series = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert tail_mean(series, window=2) == pytest.approx(0.45)   # mean(0.4, 0.5)
    assert tail_mean(series, window=100) == pytest.approx(0.3)  # whole series
    assert tail_mean([], window=5) == 0.0


def test_run_summary_shape():
    res = run_single(n=500, sigma=0.1, J=0.01, dt=0.02, seed=0,
                     n_steps=200, measure_last=100, measure_every=20)
    assert res["n"] == 500
    assert res["mu_theory"] == pytest.approx(2.0)
    assert len(res["gini_series"]) == 201            # t=0 baseline + 200 ticks
    assert len(res["max_over_mean_series"]) == 201
    assert 0.0 <= res["steady_gini"] <= 1.0
    assert res["steady_max_over_mean"] >= 1.0
    assert res["n_pooled_snapshots"] >= 1


def test_run_rejects_bad_windows():
    m = BouchaudMezardModel(n=50, seed=0)
    with pytest.raises(ValueError):
        m.run(10, measure_last=0)
    with pytest.raises(ValueError):
        m.run(10, measure_last=50)
    with pytest.raises(ValueError):
        m.run(10, measure_last=5, measure_every=0)


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(n=500, sigma=0.1, J=0.01, dt=0.02, seed=42,
                   n_steps=300, measure_last=100, measure_every=20)
    b = run_single(n=500, sigma=0.1, J=0.01, dt=0.02, seed=42,
                   n_steps=300, measure_last=100, measure_every=20)
    assert a["gini_series"] == b["gini_series"]
    assert a["max_over_mean_series"] == b["max_over_mean_series"]
    assert a["steady_gini"] == b["steady_gini"]
    assert a["hill_mu_hat"] == b["hill_mu_hat"]


def test_different_seed_differs_but_stays_shaped():
    a = run_single(n=500, sigma=0.1, J=0.01, dt=0.02, seed=1,
                   n_steps=300, measure_last=100, measure_every=20)
    b = run_single(n=500, sigma=0.1, J=0.01, dt=0.02, seed=2,
                   n_steps=300, measure_last=100, measure_every=20)
    assert a["gini_series"] != b["gini_series"]
    for res in (a, b):
        assert all(0.0 <= g <= 1.0 for g in res["gini_series"])
        assert all(m >= 1.0 - 1e-9 for m in res["max_over_mean_series"])


# -- qualitative sanity (the locked grade lives in run.py) --------------------

def test_more_redistribution_lowers_inequality():
    # Faithfulness sanity, not the locked grade: a larger J (larger mu) yields a LOWER
    # steady Gini than a smaller J on the same short run. Uses a modest N + short horizon
    # so the ordering is already visible without the full production run.
    sigma = 0.1
    low_J = run_single(n=2000, sigma=sigma, J=J_for_mu(1.5, sigma), dt=0.02, seed=0,
                       n_steps=4000, measure_last=2000, measure_every=100)
    high_J = run_single(n=2000, sigma=sigma, J=J_for_mu(5.0, sigma), dt=0.02, seed=0,
                        n_steps=4000, measure_last=2000, measure_every=100)
    assert low_J["steady_gini"] > high_J["steady_gini"]
    # and the heavier-redistribution arm has a lighter tail (bigger Hill mu-hat).
    assert high_J["hill_mu_hat"] > low_J["hill_mu_hat"]
