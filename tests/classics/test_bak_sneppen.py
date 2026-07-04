"""Faithful-rule + determinism + analytic-anchor tests for the Bak-Sneppen evolution
(SOC) reproduction.

These pin the extremal-update rule (replace the GLOBAL-min site + its two periodic
ring-neighbours with fresh U[0,1) draws), the avalanche definition (maximal below-f_c
run), the f_c percentile estimator, the discrete-MLE tau estimator on a synthetic power
law, and determinism (same seed -> identical active-min sequence). They are faithfulness
tests, NOT prediction tests (the locked predictions P1-P3 are evaluated by
examples/repro_bak_sneppen/run.py).

NOTE: this is EXTREMAL DYNAMICS / an SOC model, not an agent-stepping ABM — the
global-min selection is centralized/model-orchestrated, so there is no scheduler/agent
roster to test, only the deterministic extremal-update rule.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from abm_auto.classics.bak_sneppen import (
    BakSneppenRing,
    avalanche_size_histogram,
    avalanches_below,
    estimate_fc,
    fit_tau,
    fitness_histogram,
    heavy_tail_stats,
    punctuation_stats,
    run_bak_sneppen,
)


# -- extremal update rule -----------------------------------------------------

def test_step_updates_argmin_and_two_neighbours():
    # Hand-set fitnesses so the global min is at a known interior index; after one step
    # exactly that site and its two ring-neighbours must change, all others fixed.
    rng = np.random.default_rng(0)
    ring = BakSneppenRing(10, rng)
    ring.fitness[:] = 0.9
    ring.fitness[4] = 0.01  # unique global minimum at index 4
    before = ring.fitness.copy()
    active = ring.step()
    assert active == pytest.approx(0.01)  # returned the min that was acted on
    changed = np.flatnonzero(~np.isclose(ring.fitness, before))
    assert set(changed.tolist()) == {3, 4, 5}  # site + its two neighbours


def test_step_wraps_periodic_boundary():
    # Global min at index 0 -> neighbours are N-1 and 1 (periodic ring).
    rng = np.random.default_rng(0)
    ring = BakSneppenRing(8, rng)
    ring.fitness[:] = 0.9
    ring.fitness[0] = 0.02
    before = ring.fitness.copy()
    ring.step()
    changed = set(np.flatnonzero(~np.isclose(ring.fitness, before)).tolist())
    assert changed == {7, 0, 1}  # wraps: left neighbour of 0 is 7


def test_step_replacements_are_in_unit_interval():
    rng = np.random.default_rng(1)
    ring = BakSneppenRing(50, rng)
    for _ in range(2000):
        ring.step()
    assert ring.fitness.min() >= 0.0
    assert ring.fitness.max() < 1.0


def test_rejects_small_n():
    with pytest.raises(ValueError):
        BakSneppenRing(2, np.random.default_rng(0))


# -- determinism --------------------------------------------------------------

def test_same_seed_identical_active_min_sequence():
    a = run_bak_sneppen(n=50, transient=500, n_steps=3000, seed=7, fitness_samples=500)
    b = run_bak_sneppen(n=50, transient=500, n_steps=3000, seed=7, fitness_samples=500)
    assert np.array_equal(a["active_min"], b["active_min"])
    assert np.array_equal(a["pooled_fitness"], b["pooled_fitness"])


def test_different_seeds_can_differ():
    a = run_bak_sneppen(n=50, transient=500, n_steps=3000, seed=1, fitness_samples=500)
    b = run_bak_sneppen(n=50, transient=500, n_steps=3000, seed=2, fitness_samples=500)
    assert not np.array_equal(a["active_min"], b["active_min"])


# -- avalanche definition -----------------------------------------------------

def test_avalanches_below_counts_maximal_runs():
    # Below-threshold runs of lengths 2, then 1, then 3.
    series = [0.9, 0.1, 0.1, 0.9, 0.9, 0.1, 0.9, 0.1, 0.1, 0.1]
    sizes = avalanches_below(series, f_c=0.5)
    assert sizes == [2, 1, 3]


def test_avalanches_below_handles_trailing_run():
    series = [0.9, 0.1, 0.1]  # ends while still below threshold
    assert avalanches_below(series, f_c=0.5) == [2]


def test_avalanches_below_none_below():
    series = [0.9, 0.8, 0.7]
    assert avalanches_below(series, f_c=0.5) == []


def test_avalanches_below_all_below_is_one_avalanche():
    series = [0.1, 0.2, 0.3, 0.4]
    assert avalanches_below(series, f_c=0.5) == [4]


# -- f_c estimator ------------------------------------------------------------

def test_estimate_fc_is_low_percentile():
    # On a synthetic distribution uniform on (0.667, 1) the 5th percentile sits just
    # above the lower edge.
    rng = np.random.default_rng(0)
    pooled = 0.667 + 0.333 * rng.random(200_000)
    fc = estimate_fc(pooled, low_percentile=5.0)
    assert fc == pytest.approx(0.667 + 0.05 * 0.333, abs=0.01)


def test_estimate_fc_empty_is_nan():
    assert math.isnan(estimate_fc([]))


# -- punctuation stats --------------------------------------------------------

def test_punctuation_counts_dips_and_recoveries():
    # below, above, below, above  -> 2 dips, 2 above-runs (recoveries / quiet spells)
    series = [0.1, 0.1, 0.9, 0.1, 0.9, 0.9]
    st = punctuation_stats(series, f_c=0.5)
    assert st["n_below_runs"] == 2
    assert st["n_recoveries"] == 2
    assert st["frac_below"] == pytest.approx(3 / 6)
    assert st["longest_below_run"] == 2
    assert st["longest_above_run"] == 2


# -- discrete-MLE tau estimator (analytic anchor) -----------------------------

@pytest.mark.parametrize("alpha_true", [2.0, 2.5, 3.0])
def test_fit_tau_recovers_known_exponent(alpha_true):
    # Synthetic GENUINE discrete power law with a known exponent (numpy zipf draws
    # P(k) ~ k^{-alpha}, k = 1, 2, ...). The exact discrete MLE must recover alpha at
    # kmin=1 within sampling error. (Validates the estimator, NOT the model.)
    rng = np.random.default_rng(0)
    samples = rng.zipf(alpha_true, size=400_000)
    res = fit_tau(samples, kmin=1)
    assert res["tau"] == pytest.approx(alpha_true, abs=0.05)
    assert res["n_tail"] == int(samples.size)


def test_fit_tau_empty_tail_is_nan():
    res = fit_tau([], kmin=1)
    assert math.isnan(res["tau"])
    assert res["n_tail"] == 0


# -- heavy-tail + histogram helpers -------------------------------------------

def test_heavy_tail_stats_basic():
    sizes = [1, 1, 2, 10, 100, 1000]
    st = heavy_tail_stats(sizes)
    assert st["n"] == 6
    assert st["max"] == 1000.0
    assert st["min"] == 1.0
    assert st["decades"] == pytest.approx(3.0)  # log10(1000) - log10(1)


def test_avalanche_size_histogram_covers_all():
    sizes = list(range(1, 1000))
    hist = avalanche_size_histogram(sizes, n_bins=20)
    total = sum(b["count"] for b in hist)
    assert total == len(sizes)


def test_fitness_histogram_density_integrates_to_one():
    rng = np.random.default_rng(0)
    pooled = rng.random(100_000)  # U[0,1)
    hist = fitness_histogram(pooled, n_bins=50)
    width = hist[0]["hi"] - hist[0]["lo"]
    integral = sum(b["density"] * width for b in hist)
    assert integral == pytest.approx(1.0, abs=1e-9)


# -- SOC sanity (small ring, qualitative) -------------------------------------

def test_self_organizes_above_zero_cutoff():
    # Even on a short run the stationary fitness distribution develops a lower cutoff
    # well above 0 (self-organization), and avalanches of varied size appear.
    res = run_bak_sneppen(n=100, transient=20_000, n_steps=50_000, seed=0,
                          fitness_samples=5_000)
    fc = estimate_fc(res["pooled_fitness"], low_percentile=5.0)
    assert fc > 0.3  # a clear nonzero lower cutoff has emerged
    sizes = avalanches_below(res["active_min"], fc)
    assert len(sizes) > 0
    assert max(sizes) > 1
