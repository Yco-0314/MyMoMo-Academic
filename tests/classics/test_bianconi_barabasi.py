"""Faithful-rule + determinism tests for the Bianconi-Barabasi (2001) fitness model.

These pin the fitness-weighted preferential-attachment mechanics (weight = eta*k,
no-multi-edge, m edges per arrival, exact final node/edge count), the seed network,
the condensing fitness law's sampling, the fit-get-richer coupling helper, the CSN
discrete-MLE fit, the condensate fraction, and determinism (same seed -> identical
degree + fitness sequence). They are FAITHFULNESS tests, NOT prediction tests (the
locked predictions P1-P3 are graded by examples/repro_bianconi_barabasi/run.py).
"""
from __future__ import annotations

import math
import random

import pytest

from abm_auto.classics.bianconi_barabasi import (
    BianconiBarabasiModel,
    CONDENSING_THETA,
    condensing_fitness,
    discrete_powerlaw_mle,
    degree_histogram,
    fit_gamma,
    fit_get_richer,
    make_condensing_fitness,
    run_bb,
    run_bb_seeds,
    spearman,
    uniform_fitness,
)


# -- construction / seed network ----------------------------------------------

def test_seed_network_is_clique_on_m_plus_1_with_fitness():
    model = BianconiBarabasiModel(n=20, m=2, seed=0)
    # Seed = m+1 = 3 nodes, each connected to the other 2 (degree 2 each).
    assert len(model.node_ids) == 3
    for i in range(3):
        assert model.degree[i] == 2
        assert 0.0 < model.fitness[i] <= 1.0
    # weight_i = eta_i * k_i; total_weight is their sum.
    expected = sum(model.fitness[i] * model.degree[i] for i in range(3))
    assert model.total_weight == pytest.approx(expected)


def test_invalid_params_rejected():
    with pytest.raises(ValueError):
        BianconiBarabasiModel(n=10, m=0, seed=0)
    with pytest.raises(ValueError):
        BianconiBarabasiModel(n=2, m=2, seed=0)  # n must be > m
    with pytest.raises(ValueError):
        make_condensing_fitness(0.0)             # theta must be > 0


# -- attachment mechanics -----------------------------------------------------

def test_each_arrival_adds_exactly_m_edges_and_final_counts():
    n, m = 500, 2
    model = BianconiBarabasiModel(n=n, m=m, seed=1)
    model.grow()
    assert len(model.node_ids) == n
    # seed clique on m+1 nodes -> C(m+1,2) edges; each arrival adds m edges.
    expected_edges = (m + 1) * m // 2 + (n - (m + 1)) * m
    assert model.num_edges() == expected_edges


def test_no_self_loops_and_no_multi_edges_and_symmetry():
    model = BianconiBarabasiModel(n=800, m=2, seed=2)
    model.grow()
    for node, nbrs in enumerate(model.adjacency):
        assert node not in nbrs                      # no self-loop
        for nb in nbrs:
            assert node in model.adjacency[nb]       # symmetric
    # every arriving node was born with exactly m edges (>= m thereafter).
    for node in model.node_ids[model.m + 1:]:
        assert model.degree[node] >= model.m


def test_min_degree_equals_m():
    r = run_bb(n=2000, m=2, seed=3)
    assert r["min_degree"] == 2
    assert min(r["degrees"]) == 2


def test_running_weight_matches_bruteforce_eta_times_degree():
    model = BianconiBarabasiModel(n=1000, m=2, seed=4)
    model.grow()
    # the incrementally maintained total_weight equals a fresh recompute of sum(eta*k).
    brute = sum(model.fitness[i] * model.degree[i] for i in model.node_ids)
    assert model.total_weight == pytest.approx(brute, rel=1e-9)
    for i in model.node_ids:
        assert model.weight[i] == pytest.approx(model.fitness[i] * model.degree[i])


def test_choose_targets_distinct_and_count():
    from abm_auto.classics.bianconi_barabasi import NodeAgent
    model = BianconiBarabasiModel(n=20, m=2, seed=5)
    for _ in range(5):
        new_id = len(model.node_ids)
        eta = model._draw_fitness()
        model._register_node(new_id, eta)
        ag = NodeAgent(new_id, model, m=model.m, eta=eta)
        targets = ag.choose_targets()
        assert len(targets) == len(set(targets))     # distinct (no replacement)
        assert len(targets) == model.m
        model.attach(new_id, targets)


# -- fitness laws -------------------------------------------------------------

def test_uniform_fitness_in_unit_interval():
    rng = random.Random(0)
    vals = [uniform_fitness(rng) for _ in range(1000)]
    assert all(0.0 <= v <= 1.0 for v in vals)


def test_condensing_law_samples_unit_interval_and_biases_low():
    # rho(eta)=(theta+1)(1-eta)^theta piles mass toward LOW fitness -> mean well below 0.5.
    rng = random.Random(0)
    vals = [condensing_fitness(rng) for _ in range(5000)]
    assert all(0.0 <= v <= 1.0 for v in vals)
    assert CONDENSING_THETA == 10.0
    mean = sum(vals) / len(vals)
    # theoretical mean of Beta(1, theta+1) = 1/(theta+2) ~= 0.083 for theta=10.
    assert mean < 0.2


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_sequences():
    a = run_bb(n=2000, m=2, seed=7)
    b = run_bb(n=2000, m=2, seed=7)
    assert a["degrees"] == b["degrees"]
    assert a["fitness"] == b["fitness"]
    assert a["max_degree"] == b["max_degree"]


def test_different_seeds_differ():
    a = run_bb(n=2000, m=2, seed=7)
    b = run_bb(n=2000, m=2, seed=8)
    assert a["degrees"] != b["degrees"]


# -- fit method (discrete MLE) ------------------------------------------------

def test_discrete_mle_matches_csn_formula_on_known_input():
    degrees = [5, 6, 8, 10]   # all >= kmin=5
    kmin = 5
    s = sum(math.log(k / (kmin - 0.5)) for k in degrees)
    expected = 1.0 + 4 / s
    gamma, n_tail = discrete_powerlaw_mle(degrees, kmin=kmin)
    assert n_tail == 4
    assert gamma == pytest.approx(expected, rel=1e-12)


def test_fit_gamma_uses_kmin_m_plus_1():
    r = run_bb(n=3000, m=2, seed=0)
    f = fit_gamma(r["degrees"], m=2)
    assert f["kmin"] == 3                       # m + 1, fixed (not tuned)
    assert f["n_tail"] > 0
    assert math.isfinite(f["gamma_mle"])


def test_degree_histogram_sums_to_node_count():
    r = run_bb(n=1000, m=2, seed=0)
    hist = degree_histogram(r["degrees"])
    assert sum(h["count"] for h in hist) == 1000
    assert hist[0]["degree"] == 2                # minimum-degree (=m) spike


# -- fit-get-richer coupling + condensate helpers -----------------------------

def test_spearman_perfect_monotone():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)


def test_fit_get_richer_reports_both_spearmans_and_bins():
    r = run_bb(n=5000, m=2, seed=1)
    p1 = fit_get_richer(r["fitness"], r["degrees"], r["birth"])
    assert p1["n_bins"] == 4
    assert 0.0 <= p1["aged_frac"] <= 1.0
    assert len(p1["bin_ratios"]) == 4
    # aged-cohort Spearman >= whole-population Spearman (dilution by late arrivals).
    assert p1["spearman_aged"] >= p1["spearman_all"] - 1e-9
    # fitness genuinely couples to degree (positive), not zero.
    assert p1["spearman_aged"] > 0.2


def test_no_fitness_control_kills_the_coupling():
    # A pure-BA rerun (use_fitness=False) correlated with an INDEPENDENT random label
    # shows no fit-get-richer: Spearman ~ 0 and no bin passes the 2x ratio.
    r = run_bb(n=5000, m=2, use_fitness=False, seed=1)
    rng = random.Random(999)
    labels = [rng.random() for _ in range(len(r["degrees"]))]
    p1 = fit_get_richer(labels, r["degrees"], r["birth"])
    assert abs(p1["spearman_aged"]) < 0.15
    assert p1["n_bins_pass_2x"] == 0


def test_condensate_fraction_bounds_and_condensing_exceeds_uniform():
    # f_max is a fraction in [0,1]; the condensing law concentrates the top hub far
    # more than the uniform law at the same N (faithfulness sanity; the locked P2
    # grades the exact contrast + N-scaling in the runner).
    uni = run_bb(n=10000, m=2, fitness_fn=uniform_fitness, seed=0)
    con = run_bb(n=10000, m=2, fitness_fn=condensing_fitness, seed=0)
    assert 0.0 <= uni["f_max"] <= 1.0
    assert 0.0 <= con["f_max"] <= 1.0
    assert con["f_max"] > uni["f_max"]


def test_run_bb_seeds_aggregates():
    agg = run_bb_seeds(n=2000, m=2, n_seeds=3, seed_base=0)
    assert agg["n_seeds"] == 3
    assert len(agg["per_seed_f_max"]) == 3
    assert len(agg["per_seed_gamma"]) == 3
    assert agg["min_f_max"] <= agg["mean_f_max"] <= agg["max_f_max"]
