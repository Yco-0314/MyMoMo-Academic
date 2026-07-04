"""Faithful-rule + determinism tests for the Cont-Bouchaud percolation market
(Cont & Bouchaud 2000) reproduction.

These pin the union-find, the Erdos-Renyi cluster-size generation (G(N, p=c/N)), the
trading micro-rule (per-cluster Bernoulli(a) activation + fair-coin sign, aggregate
return = sum of signed active cluster sizes), the standardization, the tail / kurtosis
statistics, and determinism (same seed -> identical result).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(fat tails at criticality, heavy tails vs Gaussian, activity-driven crossover to
Gaussian) are evaluated by examples/repro_cont_bouchaud/run.py.
"""
from __future__ import annotations

import math
import random

import pytest

from abm_auto.classics.cont_bouchaud import (
    UnionFind,
    activity_sweep,
    cluster_sizes,
    excess_kurtosis,
    gaussian_tail_prob,
    run_many_seeds,
    run_regime,
    sample_returns,
    standardize,
    tail_exponent,
    tail_prob,
)


# -- union-find ---------------------------------------------------------------

def test_union_find_merges_into_one_component():
    uf = UnionFind(5)
    uf.union(0, 1)
    uf.union(1, 2)
    uf.union(3, 4)
    roots = {uf.find(i) for i in range(5)}
    assert len(roots) == 2                    # {0,1,2} and {3,4}
    assert uf.find(0) == uf.find(2)
    assert uf.find(3) == uf.find(4)
    assert uf.find(0) != uf.find(3)


def test_union_find_size_tracks_component():
    uf = UnionFind(4)
    uf.union(0, 1)
    uf.union(2, 3)
    uf.union(1, 2)
    assert uf.size[uf.find(0)] == 4           # all four merged


# -- Erdos-Renyi cluster sizes ------------------------------------------------

def test_cluster_sizes_partition_the_nodes():
    # The component sizes must sum to N and be a valid partition (no lost nodes).
    for c in (0.0, 0.5, 1.0, 2.0):
        rng = random.Random(3)
        sizes = cluster_sizes(200, c, rng=rng)
        assert sum(sizes) == 200
        assert all(s >= 1 for s in sizes)


def test_cluster_sizes_c_zero_is_all_singletons():
    # c = 0 means no edges: every node is its own cluster.
    sizes = cluster_sizes(500, 0.0, rng=random.Random(0))
    assert len(sizes) == 500
    assert all(s == 1 for s in sizes)


def test_cluster_sizes_criticality_grows_the_largest_cluster():
    # At/above the percolation threshold c = 1 the largest cluster is far bigger than
    # the tiny clusters of a well-below-threshold graph (c = 0.2), at the same N.
    n = 5000
    sub = cluster_sizes(n, 0.2, rng=random.Random(1))
    crit = cluster_sizes(n, 1.0, rng=random.Random(1))
    assert max(crit) > max(sub) * 3           # criticality yields a much larger cluster


def test_cluster_sizes_invalid_params_raise():
    with pytest.raises(ValueError):
        cluster_sizes(0, 1.0, rng=random.Random(0))
    with pytest.raises(ValueError):
        cluster_sizes(10, -1.0, rng=random.Random(0))


def test_cluster_sizes_deterministic_given_seed():
    a = cluster_sizes(1000, 1.0, rng=random.Random(7))
    b = cluster_sizes(1000, 1.0, rng=random.Random(7))
    assert sorted(a) == sorted(b)


# -- trading micro-rule -------------------------------------------------------

def test_sample_returns_zero_activity_is_all_zero():
    # a = 0: no cluster ever active, every return is exactly 0.
    r = sample_returns([1, 2, 3, 10], 0.0, 50, rng=random.Random(0))
    assert r == [0.0] * 50


def test_sample_returns_bounded_by_total_size():
    # |r| can never exceed the total number of agents (all clusters active, same sign).
    sizes = [1, 1, 2, 5, 20]
    total = sum(sizes)
    r = sample_returns(sizes, 1.0, 100, rng=random.Random(2))
    assert all(abs(x) <= total for x in r)


def test_sample_returns_full_activity_return_is_signed_size_sum():
    # a = 1: every cluster active every step, so |r| is a sum of +/- sizes; its parity
    # matches the total-size parity and it never exceeds the total.
    sizes = [3, 4, 5]
    r = sample_returns(sizes, 1.0, 200, rng=random.Random(9))
    total = sum(sizes)
    for x in r:
        assert abs(x) <= total
        assert (int(abs(x)) - total) % 2 == 0     # r = total - 2*(sum of sold sizes)


def test_sample_returns_single_cluster_is_plus_or_minus_size():
    # One cluster of size 7 at a = 1: each step is +7 or -7.
    r = sample_returns([7], 1.0, 300, rng=random.Random(4))
    assert set(r) <= {7.0, -7.0}
    assert 7.0 in r and -7.0 in r                 # both signs occur over 300 draws


def test_sample_returns_invalid_params_raise():
    with pytest.raises(ValueError):
        sample_returns([1, 2], -0.1, 10, rng=random.Random(0))
    with pytest.raises(ValueError):
        sample_returns([1, 2], 1.5, 10, rng=random.Random(0))
    with pytest.raises(ValueError):
        sample_returns([1, 2], 0.5, 0, rng=random.Random(0))


# -- standardization + statistics ---------------------------------------------

def test_standardize_zero_mean_unit_std():
    std = standardize([1.0, 2.0, 3.0, 4.0, 5.0])
    mean = sum(std) / len(std)
    var = sum((x - mean) ** 2 for x in std) / len(std)
    assert mean == pytest.approx(0.0, abs=1e-12)
    assert var == pytest.approx(1.0, abs=1e-9)


def test_standardize_constant_series_is_zeros():
    assert standardize([5.0, 5.0, 5.0]) == [0.0, 0.0, 0.0]


def test_excess_kurtosis_gaussian_is_near_zero():
    rng = random.Random(11)
    sample = [rng.gauss(0.0, 1.0) for _ in range(200000)]
    ek = excess_kurtosis(sample)
    assert abs(ek) < 0.15                          # Gaussian excess kurtosis ~ 0


def test_excess_kurtosis_leptokurtic_is_positive():
    # A spiky mixture (mostly tiny, rare huge) is fat-tailed: excess kurtosis >> 0.
    rng = random.Random(12)
    sample = []
    for _ in range(100000):
        sample.append(rng.gauss(0, 1) if rng.random() > 0.02 else rng.gauss(0, 12))
    assert excess_kurtosis(sample) > 3.0


def test_excess_kurtosis_is_scale_invariant():
    rng = random.Random(13)
    sample = [rng.gauss(0, 1) for _ in range(5000)]
    ek_raw = excess_kurtosis(sample)
    ek_scaled = excess_kurtosis([100.0 * x + 7.0 for x in sample])
    assert ek_raw == pytest.approx(ek_scaled, abs=1e-9)


def test_tail_prob_counts_exceedances():
    # 10 values, two beyond 1.0 in magnitude.
    vals = [0.0, 0.5, -0.5, 0.9, -0.9, 0.1, -0.1, 0.2, 2.0, -3.0]
    assert tail_prob(vals, 1.0) == pytest.approx(0.2)
    assert tail_prob(vals, 5.0) == pytest.approx(0.0)


def test_gaussian_tail_prob_known_values():
    # P(|Z| > 3) ~ 0.0027, P(|Z| > 5) ~ 5.7e-7.
    assert gaussian_tail_prob(3.0) == pytest.approx(0.0026998, abs=1e-6)
    assert gaussian_tail_prob(5.0) == pytest.approx(5.733e-7, abs=1e-9)


def test_tail_exponent_recovers_a_power_law():
    # Sample |x| from a Pareto with tail exponent alpha; the Hill-style log-log fit on
    # the standardized values should recover an exponent in a sensible band.
    rng = random.Random(21)
    alpha_true = 3.0
    raw = []
    for _ in range(50000):
        u = rng.random()
        x = (1.0 - u) ** (-1.0 / alpha_true)       # Pareto(alpha) on [1, inf)
        raw.append(x if rng.random() < 0.5 else -x)
    std = standardize(raw)
    alpha = tail_exponent(std)
    assert not math.isnan(alpha)
    assert 1.5 <= alpha <= 5.0                      # recovers the right ballpark


def test_tail_exponent_nan_on_tiny_sample():
    assert math.isnan(tail_exponent([0.1, 0.2, 0.3]))


# -- run_regime shape ---------------------------------------------------------

def test_run_regime_shape_and_ranges():
    res = run_regime(2000, 1.0, 0.05, n_steps=2000, seed=0)
    assert res["n"] == 2000 and res["c"] == 1.0 and res["a"] == 0.05
    assert 0.0 <= res["largest_cluster_fraction"] <= 1.0
    assert res["n_clusters"] >= 1
    assert res["p_gt_3sigma"] >= 0.0
    assert res["p_gt_5sigma"] >= 0.0


# -- determinism --------------------------------------------------------------

def test_run_regime_deterministic_same_seed():
    a = run_regime(2000, 1.0, 0.05, n_steps=1000, seed=42)
    b = run_regime(2000, 1.0, 0.05, n_steps=1000, seed=42)
    assert a["excess_kurtosis"] == b["excess_kurtosis"]
    assert a["p_gt_3sigma"] == b["p_gt_3sigma"]
    assert a["largest_cluster"] == b["largest_cluster"]


def test_run_many_seeds_deterministic():
    a = run_many_seeds(2000, 1.0, 0.05, n_steps=800, n_seeds=3, seed_base=0)
    b = run_many_seeds(2000, 1.0, 0.05, n_steps=800, n_seeds=3, seed_base=0)
    assert a["pooled_excess_kurtosis"] == b["pooled_excess_kurtosis"]
    assert a["per_seed_excess_kurtosis"] == b["per_seed_excess_kurtosis"]
    assert a["total_samples"] == b["total_samples"]


def test_run_many_seeds_pools_all_samples():
    res = run_many_seeds(1000, 1.0, 0.05, n_steps=500, n_seeds=4, seed_base=0)
    assert res["total_samples"] == 500 * 4
    assert len(res["per_seed_excess_kurtosis"]) == 4


# -- qualitative sanity (the locked grade lives in run.py) --------------------

def test_criticality_low_activity_is_fatter_than_high_activity_control():
    # Faithfulness sanity, not the locked grade: at c = 1 the low-activity (herding)
    # regime has a much larger excess kurtosis than the high-activity control (which
    # averages many independent clusters toward Gaussian).
    n = 4000
    herd = run_many_seeds(n, 1.0, 0.05, n_steps=3000, n_seeds=3, seed_base=0)
    control = run_many_seeds(n, 1.0, 0.49, n_steps=3000, n_seeds=3, seed_base=0)
    assert herd["pooled_excess_kurtosis"] > 3.0
    assert herd["pooled_excess_kurtosis"] > control["pooled_excess_kurtosis"] * 3.0


def test_criticality_is_fatter_than_below_threshold_control():
    # c = 1 (critical) vs c = 0.2 (well below threshold), same small activity: the
    # critical regime is markedly fatter-tailed (a bigger excess kurtosis).
    n = 4000
    crit = run_many_seeds(n, 1.0, 0.05, n_steps=3000, n_seeds=3, seed_base=0)
    sub = run_many_seeds(n, 0.2, 0.05, n_steps=3000, n_seeds=3, seed_base=0)
    assert crit["pooled_excess_kurtosis"] > sub["pooled_excess_kurtosis"] * 3.0


def test_activity_sweep_kurtosis_decreases():
    # Excess kurtosis should fall as activity rises (herding -> Gaussian). Check the
    # endpoints of a coarse sweep at criticality.
    n = 3000
    sweep = activity_sweep(n, 1.0, [0.05, 0.2, 0.49], n_steps=2500, n_seeds=3,
                           seed_base=0)
    kurts = [row["pooled_excess_kurtosis"] for row in sweep]
    assert kurts[0] > kurts[-1]                    # low activity fatter than high
    assert kurts[0] > 3.0
