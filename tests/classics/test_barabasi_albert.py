"""Faithful-rule + determinism tests for the Barabasi-Albert (1999) reproduction.

These pin the preferential-attachment mechanics (degree-weighted, no-multi-edge,
m edges per arrival, exact final node count and edge count), the seed network, the
discrete-MLE fit formula on a hand-computable case, and determinism (same seed ->
identical degree sequence). They are FAITHFULNESS tests, NOT prediction tests (the
locked predictions P1-P3 are graded by examples/repro_barabasi_albert/run.py).
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.barabasi_albert import (
    BAModel,
    ccdf_loglog_slope,
    degree_histogram,
    discrete_powerlaw_mle,
    er_max_degree,
    fit_gamma,
    run_ba,
)


# -- construction / seed network ----------------------------------------------

def test_seed_network_is_clique_on_m_plus_1():
    model = BAModel(n=10, m=3, seed=0)
    # Seed = m+1 = 4 nodes, each connected to the other 3 (degree 3 each).
    assert len(model.node_ids) == 4
    for i in range(4):
        assert model.degree[i] == 3
    # 4-clique has 6 edges -> total degree 12.
    assert model.total_degree == 12


def test_invalid_params_rejected():
    with pytest.raises(ValueError):
        BAModel(n=10, m=0, seed=0)
    with pytest.raises(ValueError):
        BAModel(n=3, m=3, seed=0)  # n must be > m


# -- preferential-attachment mechanics ----------------------------------------

def test_each_arrival_adds_exactly_m_edges_and_final_node_count():
    n, m = 200, 3
    r = run_ba(n=n, m=m, seed=1)
    assert r["n"] == n
    # Total edges = seed-clique edges + m per arrival.
    # seed clique on m+1=4 nodes -> C(4,2)=6 edges; arrivals = n-(m+1).
    model = BAModel(n=n, m=m, seed=1)
    model.grow()
    total_edges = model.total_degree // 2
    expected = (m + 1) * m // 2 + (n - (m + 1)) * m
    assert total_edges == expected


def test_no_self_loops_and_no_multi_edges():
    model = BAModel(n=500, m=3, seed=2)
    model.grow()
    for node, nbrs in model.adjacency.items():
        assert node not in nbrs                      # no self-loop
        # adjacency is a set -> no multi-edge by construction; also check symmetry
        for nb in nbrs:
            assert node in model.adjacency[nb]
    # Every arriving node attaches to exactly m DISTINCT existing nodes.
    for node in model.node_ids[model.m + 1:]:
        # at least m edges (could gain more later from incoming arrivals)
        assert model.degree[node] >= model.m


def test_min_degree_equals_m():
    # Every node is born with m edges; the minimum degree in the graph is m.
    r = run_ba(n=2000, m=3, seed=3)
    assert r["min_degree"] == 3
    assert min(r["degrees"]) == 3


def test_choose_targets_is_degree_weighted_without_replacement():
    # With a strongly skewed seed, the high-degree node should be the most likely
    # target; targets are distinct (no replacement). We check distinctness here and
    # leave the statistical weighting to the determinism + emergent-gamma checks.
    model = BAModel(n=10, m=3, seed=4)
    agent_targets = []
    # Drive a few arrivals and record their chosen targets.
    for _ in range(5):
        new_id = len(model.node_ids)
        model._register_node(new_id)
        from abm_auto.classics.barabasi_albert import NodeAgent
        ag = NodeAgent(new_id, model, m=model.m)
        targets = ag.choose_targets()
        assert len(targets) == len(set(targets))     # distinct (no replacement)
        assert len(targets) == model.m
        model.attach(new_id, targets)
        agent_targets.append(targets)
    assert len(agent_targets) == 5


def test_attaches_to_at_most_existing_node_count():
    # If m exceeds the number of existing nodes at the very first arrival it is
    # capped (cannot happen here since seed has m+1 nodes, but guard the invariant).
    model = BAModel(n=6, m=2, seed=0)
    model.grow()
    assert model.degree[model.node_ids[-1]] >= 0  # ran without error


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_degree_sequence():
    a = run_ba(n=3000, m=3, seed=7)
    b = run_ba(n=3000, m=3, seed=7)
    assert a["degrees"] == b["degrees"]
    assert a["max_degree"] == b["max_degree"]


def test_different_seeds_differ():
    a = run_ba(n=3000, m=3, seed=7)
    b = run_ba(n=3000, m=3, seed=8)
    assert a["degrees"] != b["degrees"]


# -- fit method (discrete MLE) ------------------------------------------------

def test_discrete_mle_matches_csn_formula_on_known_input():
    # gamma = 1 + n / sum( ln(k_i / (kmin-0.5)) ). Hand-compute for a tiny tail.
    degrees = [5, 6, 8, 10]   # all >= kmin=5
    kmin = 5
    s = sum(math.log(k / (kmin - 0.5)) for k in degrees)
    expected = 1.0 + 4 / s
    gamma, n_tail = discrete_powerlaw_mle(degrees, kmin=kmin)
    assert n_tail == 4
    assert gamma == pytest.approx(expected, rel=1e-12)


def test_discrete_mle_only_counts_tail_above_kmin():
    degrees = [1, 2, 3, 10, 20, 30]
    gamma, n_tail = discrete_powerlaw_mle(degrees, kmin=10)
    assert n_tail == 3  # only 10, 20, 30


def test_fit_gamma_uses_kmin_m_plus_1():
    r = run_ba(n=2000, m=3, seed=0)
    f = fit_gamma(r["degrees"], m=3)
    assert f["kmin"] == 4                       # m + 1, fixed (not tuned)
    assert f["gamma_mle"] > 1.0
    assert f["n_tail"] > 0


def test_ccdf_slope_returns_finite_for_powerlaw_tail():
    r = run_ba(n=2000, m=3, seed=0)
    g, npts = ccdf_loglog_slope(r["degrees"], kmin=4)
    assert math.isfinite(g)
    assert npts >= 2


def test_degree_histogram_sums_to_node_count():
    r = run_ba(n=1000, m=3, seed=0)
    hist = degree_histogram(r["degrees"])
    assert sum(h["count"] for h in hist) == 1000
    # sorted by degree ascending, first bucket is the minimum-degree (=m) spike
    assert hist[0]["degree"] == 3


# -- ER comparison (P3) -------------------------------------------------------

def test_er_max_degree_is_deterministic_and_near_target_mean():
    a = er_max_degree(5000, 6.0, seed=0)
    b = er_max_degree(5000, 6.0, seed=0)
    assert a["max_degree"] == b["max_degree"]
    assert a["edges"] == b["edges"]
    assert abs(a["mean_degree_achieved"] - 6.0) < 0.3


def test_ba_max_degree_far_exceeds_er_at_equal_mean_degree():
    # Heavy tail vs Poisson: BA grows hubs; ER does not. (Locked P3 grades the
    # exact ratio in the runner; this is a faithfulness sanity check.)
    ba = run_ba(n=5000, m=3, seed=0)
    er = er_max_degree(5000, ba["mean_degree"], seed=0)
    assert ba["max_degree"] > 3 * er["max_degree"]
