"""Faithful-rule + determinism tests for the Seceder model (Dittrich, Liljeros,
Soulier & Banzhaf 2000) reproduction.

These pin the locked cluster-counting rule (gap-cut + minimum occupancy), the
population-variance computation, the seceder selection (the farthest-from-the-
3-mean entity of a sampled triple reproduces), the offspring micro-rule
(offspring = seceder value + gaussian, replacing exactly one entity so N is
constant), and determinism (same seed -> identical run).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(>=2 clusters; variance >> mutation floor; cluster count stable over the late
run) are evaluated by examples/repro_seceder/run.py.
"""
from __future__ import annotations

import pytest

from abm_auto.classics.seceder import (
    EntityAgent,
    SecederModel,
    count_clusters,
    population_variance,
    run_single,
)


# -- locked cluster-counting rule (hand-built arrays) -------------------------

def test_one_tight_blob_is_one_cluster():
    # 20 values all within a tiny spread (no gap exceeds 3*sigma_mut=0.6) -> 1 cluster.
    blob = [0.0 + 0.01 * i for i in range(20)]   # spread 0.19, all gaps 0.01
    assert count_clusters(blob, sigma_mut=0.2) == 1


def test_three_well_separated_blobs_is_three_clusters():
    # Three tight blobs centred at -5, 0, +5 (huge gaps between them) -> 3 clusters.
    a = [-5.0 + 0.01 * i for i in range(10)]
    b = [0.0 + 0.01 * i for i in range(10)]
    c = [5.0 + 0.01 * i for i in range(10)]
    assert count_clusters(a + b + c, sigma_mut=0.2) == 3


def test_cluster_count_is_order_invariant():
    # Counting sorts internally: a shuffled mix of three blobs still counts 3.
    a = [-5.0 + 0.01 * i for i in range(10)]
    b = [0.0 + 0.01 * i for i in range(10)]
    c = [5.0 + 0.01 * i for i in range(10)]
    mixed = [a[0], c[3], b[7], a[9], c[0], b[1], a[5], c[8], b[4], a[2],
             c[5], b[9], a[7], c[1], b[6], a[4], c[9], b[2], a[8], c[6],
             b[0], a[1], c[2], b[3], a[3], c[4], b[5], a[6], c[7], b[8]]
    assert count_clusters(mixed, sigma_mut=0.2) == 3


def test_gap_threshold_is_locked_at_three_sigma():
    # Two blobs separated by EXACTLY 0.6 (= 3*sigma_mut) do NOT split (gap must
    # EXCEED the threshold); separated by more than 0.6 they do.
    left = [0.0] * 10
    just_at = [0.6] * 10            # consecutive gap exactly 0.6 -> not a boundary
    assert count_clusters(left + just_at, sigma_mut=0.2) == 1
    just_over = [0.61] * 10        # gap 0.61 > 0.6 -> a boundary -> 2 clusters
    assert count_clusters(left + just_over, sigma_mut=0.2) == 2


def test_min_occupancy_drops_noise_stragglers():
    # A lone far-away straggler (occupancy 1 < min_occupancy 5) is NOT a cluster:
    # one big blob + one isolated point -> still 1 cluster.
    blob = [0.0 + 0.01 * i for i in range(30)]
    straggler = [100.0]
    assert count_clusters(blob + straggler, sigma_mut=0.2, min_occupancy=5) == 1
    # A separated group AT the occupancy floor (5) DOES count -> 2 clusters.
    group = [100.0 + 0.01 * i for i in range(5)]
    assert count_clusters(blob + group, sigma_mut=0.2, min_occupancy=5) == 2


def test_cluster_count_empty_is_zero():
    assert count_clusters([], sigma_mut=0.2) == 0


# -- variance -----------------------------------------------------------------

def test_population_variance_matches_definition():
    vals = [1.0, 2.0, 3.0, 4.0, 5.0]      # mean 3, var = (4+1+0+1+4)/5 = 2.0
    assert population_variance(vals) == pytest.approx(2.0)


def test_population_variance_of_constant_is_zero():
    assert population_variance([7.0] * 10) == pytest.approx(0.0)
    assert population_variance([3.0]) == 0.0    # <2 entities -> 0
    assert population_variance([]) == 0.0


# -- model construction + invariants ------------------------------------------

def test_population_is_entity_agents_with_traits():
    m = SecederModel(n=200, sigma_mut=0.2, init_sigma=1.0, seed=0)
    assert len(m.agent_list) == 200
    assert all(isinstance(a, EntityAgent) for a in m.agent_list)
    assert all(isinstance(a.x, float) for a in m.agent_list)
    # Initial blob: roughly unit spread, single cluster.
    assert m.cluster_count() == 1


def test_mutation_floor_is_sigma_squared():
    m = SecederModel(n=200, sigma_mut=0.2, seed=0)
    assert m.mutation_floor == pytest.approx(0.04)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        SecederModel(n=2)                   # need >=3 to sample a triple
    with pytest.raises(ValueError):
        SecederModel(n=10, sigma_mut=0.0)
    with pytest.raises(ValueError):
        SecederModel(n=10, init_sigma=-1.0)
    with pytest.raises(ValueError):
        SecederModel(n=10, gap_factor=0.0)
    with pytest.raises(ValueError):
        SecederModel(n=10, min_occupancy=0)


# -- the seceder selection rule (hand-built triple) ---------------------------

def test_seceder_is_farthest_from_triple_mean():
    # Triple {0, 1, 10}: mean = 11/3 ~= 3.667; distances |0-m|=3.667, |1-m|=2.667,
    # |10-m|=6.333 -> the seceder is the entity with value 10 (the outlier).
    m = SecederModel(n=3, sigma_mut=0.2, seed=0)
    m.agent_list[0].x = 0.0
    m.agent_list[1].x = 1.0
    m.agent_list[2].x = 10.0
    sec_idx, rep_idx = m.reproduction_event()
    # With n=3 the sampled triple is all three; the outlier (value 10) is index 2.
    assert sec_idx == 2


def test_seceder_picks_low_outlier_too():
    # Triple {-10, 0, 1}: mean = -3; |-10-(-3)|=7 is the max -> seceder is value -10.
    m = SecederModel(n=3, sigma_mut=0.2, seed=1)
    m.agent_list[0].x = -10.0
    m.agent_list[1].x = 0.0
    m.agent_list[2].x = 1.0
    sec_idx, _ = m.reproduction_event()
    assert sec_idx == 0


def test_offspring_is_seceder_value_plus_gaussian_and_replaces_one_entity():
    # n=3 so the triple is fixed; with sigma_mut tiny the offspring ~= seceder value.
    # Exactly ONE entity changes (the replaced one) and the population size is constant.
    m = SecederModel(n=3, sigma_mut=1e-9, seed=2)
    m.agent_list[0].x = 0.0
    m.agent_list[1].x = 1.0
    m.agent_list[2].x = 10.0          # the seceder
    before = [a.x for a in m.agent_list]
    sec_idx, rep_idx = m.reproduction_event()
    after = [a.x for a in m.agent_list]
    assert len(m.agent_list) == 3                       # N constant
    # The replaced slot now holds (approximately) the seceder's value + ~0 mutation.
    assert after[rep_idx] == pytest.approx(before[sec_idx], abs=1e-6)
    # Every OTHER slot is unchanged.
    for i in range(3):
        if i != rep_idx:
            assert after[i] == before[i]


def test_reproduction_keeps_population_size_constant_over_many_events():
    m = SecederModel(n=50, sigma_mut=0.2, seed=3)
    for _ in range(500):
        m.reproduction_event()
        assert len(m.agent_list) == 50


# -- run summary + late-window series -----------------------------------------

def test_run_summary_shape():
    res = run_single(n=200, sigma_mut=0.2, seed=0, generations=30, measure_last=10)
    assert res["n"] == 200 and res["sigma_mut"] == 0.2
    assert len(res["cluster_series"]) == 31          # t=0 baseline + 30 ticks
    assert len(res["variance_series"]) == 31
    assert len(res["late_cluster_counts"]) == 10
    assert res["final_clusters"] >= 1
    assert res["final_variance"] >= 0.0
    assert res["mutation_floor"] == pytest.approx(0.04)
    assert len(res["final_traits"]) == 200


def test_run_rejects_bad_args():
    m = SecederModel(n=10, sigma_mut=0.2, seed=0)
    with pytest.raises(ValueError):
        m.run(0)
    m2 = SecederModel(n=10, sigma_mut=0.2, seed=0)
    with pytest.raises(ValueError):
        m2.run(10, measure_last=0)
    m3 = SecederModel(n=10, sigma_mut=0.2, seed=0)
    with pytest.raises(ValueError):
        m3.run(10, measure_last=50)


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(n=200, sigma_mut=0.2, seed=42, generations=60, measure_last=20)
    b = run_single(n=200, sigma_mut=0.2, seed=42, generations=60, measure_last=20)
    assert a["final_traits"] == b["final_traits"]
    assert a["cluster_series"] == b["cluster_series"]
    assert a["variance_series"] == b["variance_series"]
    assert a["steady_clusters"] == b["steady_clusters"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(n=200, sigma_mut=0.2, seed=1, generations=60, measure_last=20)
    b = run_single(n=200, sigma_mut=0.2, seed=2, generations=60, measure_last=20)
    for res in (a, b):
        assert all(c >= 1 for c in res["cluster_series"][1:])   # never 0 once running
        assert all(v >= 0.0 for v in res["variance_series"])


# -- qualitative sanity (the locked grade lives in run.py) --------------------

def test_diversification_emerges_from_initial_blob():
    # Faithfulness sanity, not the locked grade: the population starts as a single
    # blob and, under the seceder rule, ends up with MORE than one cluster while
    # variance stays well above the mutation floor.
    res = run_single(n=200, sigma_mut=0.2, seed=0, generations=400, measure_last=100)
    assert res["cluster_series"][0] == 1                  # starts as one blob
    assert res["steady_clusters"] >= 2                    # splits into groups
    assert res["steady_variance"] > 10 * res["mutation_floor"]  # diversity persists
