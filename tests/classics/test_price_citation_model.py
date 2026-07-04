"""Faithful-rule + determinism tests for the Price (1976) cumulative-advantage
citation-model reproduction.

These pin the DIRECTED preferential-attachment mechanics (each arrival emits exactly m
distinct out-edges to EXISTING/older papers only — a DAG; only in-degree grows), the
additive-constant cumulative-advantage draw (weight ∝ in-degree + a), the running
Newman O(1) target list, the discrete-MLE + KS-selected tail fit on hand-computable
cases, the analytic p_0 / gamma formulas, and determinism (same seed -> identical
in-degree sequence). They are FAITHFULNESS tests, NOT prediction tests (the locked
predictions P1-P3 are graded by examples/repro_price_citation_model/run.py).
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.price_citation_model import (
    PaperAgent,
    PriceModel,
    analytic_gamma,
    analytic_p0,
    discrete_powerlaw_mle,
    fit_tail_exponent,
    in_degree_histogram,
    run_price,
    variance,
)


# -- construction / seed network ----------------------------------------------

def test_seed_network_has_no_citations_and_only_additive_weight():
    model = PriceModel(n=100, m=3, a=1, n_seeds=20, seed=0)
    assert len(model.existing_ids) == 20
    # Seeds start uncited (in-degree 0) and citing nothing (out-degree 0).
    for i in range(20):
        assert model.in_degree[i] == 0
        assert model.out_degree[i] == 0
    # Target list holds a=1 copy of each seed (pure additive weight) => length 20.
    assert len(model.target_list) == 20 * model.a


def test_invalid_params_rejected():
    with pytest.raises(ValueError):
        PriceModel(n=100, m=0, seed=0)                 # m must be >= 1
    with pytest.raises(ValueError):
        PriceModel(n=100, m=3, a=0, seed=0)            # a must be >= 1
    with pytest.raises(ValueError):
        PriceModel(n=100, m=3, n_seeds=3, seed=0)      # n_seeds must be >= m+1
    with pytest.raises(ValueError):
        PriceModel(n=20, m=3, n_seeds=20, seed=0)      # n must be > n_seeds


# -- directed preferential-attachment mechanics -------------------------------

def test_each_arrival_emits_exactly_m_out_edges():
    n, m, seeds = 500, 3, 20
    r = run_price(n=n, m=m, a=1, n_seeds=seeds, seed=1)
    # Every NON-SEED paper has out-degree exactly m (it cites m references, forever).
    for k in r["out_degrees"][seeds:]:
        assert k == m
    # Seeds cite nothing.
    for k in r["out_degrees"][:seeds]:
        assert k == 0
    assert r["nonseed_out_all_equal_m"] is True


def test_edges_are_a_dag_only_cite_older_papers():
    # Structural invariant: a citation always points from a younger id to an older
    # (strictly smaller) id. Drive arrivals and check every chosen target is older.
    model = PriceModel(n=200, m=3, a=1, n_seeds=20, seed=2)
    while len(model.existing_ids) < model.target_n:
        new_id = len(model.existing_ids)
        model._register_node(new_id)
        agent = PaperAgent(new_id, model)
        targets = agent.choose_targets()
        # every reference is an existing (older) paper: id strictly less than new_id
        assert all(t < new_id for t in targets)
        assert len(targets) == len(set(targets))       # distinct references
        assert len(targets) == model.m
        model.attach(new_id, targets)
        model._make_citable(new_id)
    assert model.is_dag() is True


def test_no_self_citation():
    # A paper never cites itself: during its step it is not yet in existing_ids.
    model = PriceModel(n=300, m=3, a=1, n_seeds=20, seed=3)
    model.grow()
    # Reconstruct is unnecessary — the DAG test above proves target < new_id, so a
    # self-citation (target == new_id) is impossible. Here assert out-degree bound.
    assert all(model.out_degree[i] == 3 for i in model.existing_ids[20:])


def test_in_degree_conservation_matches_total_citations():
    # Total in-degree == total out-degree == m * (number of non-seed papers).
    n, m, seeds = 1000, 3, 20
    r = run_price(n=n, m=m, a=1, n_seeds=seeds, seed=4)
    total_in = sum(r["in_degrees"])
    total_out = sum(r["out_degrees"])
    assert total_in == total_out
    assert total_out == m * (n - seeds)


def test_min_out_degree_zero_and_in_degree_can_be_zero():
    r = run_price(n=2000, m=3, a=1, n_seeds=20, seed=5)
    assert min(r["out_degrees"]) == 0            # seeds cite nothing
    assert min(r["in_degrees"]) == 0             # never-cited papers exist


# -- cumulative-advantage weighting -------------------------------------------

def test_target_list_encodes_in_degree_plus_a():
    # After growth, node j should appear (in_degree[j] + a) times in the running list.
    model = PriceModel(n=400, m=3, a=1, n_seeds=20, seed=6)
    model.grow()
    counts = {}
    for nid in model.target_list:
        counts[nid] = counts.get(nid, 0) + 1
    for nid in model.existing_ids:
        assert counts.get(nid, 0) == model.in_degree[nid] + model.a


def test_high_in_degree_node_is_preferentially_cited():
    # Statistical faithfulness: with a strongly seeded head start, the most-cited early
    # paper attracts far more citations than a typical late paper (rich-get-richer).
    r = run_price(n=20000, m=3, a=1, n_seeds=20, seed=7)
    max_in = r["max_in_degree"]
    mean_in = r["mean_in_degree"]
    # The hub's citation count vastly exceeds the mean (heavy tail / cumulative adv.).
    assert max_in > 20 * mean_in


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_in_degree_sequence():
    a = run_price(n=3000, m=3, a=1, n_seeds=20, seed=11)
    b = run_price(n=3000, m=3, a=1, n_seeds=20, seed=11)
    assert a["in_degrees"] == b["in_degrees"]
    assert a["max_in_degree"] == b["max_in_degree"]
    assert a["zero_in_degree_fraction"] == b["zero_in_degree_fraction"]


def test_different_seeds_differ():
    a = run_price(n=3000, m=3, a=1, n_seeds=20, seed=11)
    b = run_price(n=3000, m=3, a=1, n_seeds=20, seed=12)
    assert a["in_degrees"] != b["in_degrees"]


# -- analytic formulas --------------------------------------------------------

def test_analytic_gamma_is_2_plus_a_over_m():
    assert analytic_gamma(3, 1) == pytest.approx(2 + 1 / 3)     # 2.333...
    assert analytic_gamma(1, 1) == pytest.approx(3.0)           # degenerate w/ BA
    assert analytic_gamma(3, 3) == pytest.approx(3.0)           # Price's a=m => 3


def test_analytic_p0_is_m_plus_a_over_2m_plus_a():
    assert analytic_p0(3, 1) == pytest.approx(4 / 7)            # 0.571...
    assert analytic_p0(1, 1) == pytest.approx(2 / 3)            # 0.666...


# -- fit method (discrete MLE + KS-selected kmin) -----------------------------

def test_discrete_mle_matches_csn_formula_on_known_input():
    degrees = [5, 6, 8, 10]
    kmin = 5
    s = sum(math.log(k / (kmin - 0.5)) for k in degrees)
    expected = 1.0 + 4 / s
    gamma, n_tail = discrete_powerlaw_mle(degrees, kmin=kmin)
    assert n_tail == 4
    assert gamma == pytest.approx(expected, rel=1e-12)


def test_discrete_mle_only_counts_tail_above_kmin():
    degrees = [1, 2, 3, 10, 20, 30]
    gamma, n_tail = discrete_powerlaw_mle(degrees, kmin=10)
    assert n_tail == 3


def test_fit_tail_exponent_selects_kmin_by_ks_and_returns_gamma_below_3():
    # On a genuine Price m=3,a=1 run the KS-selected gamma-hat is finite and < 3.
    r = run_price(n=50000, m=3, a=1, n_seeds=20, seed=0)
    f = fit_tail_exponent(r["in_degrees"])
    assert f["kmin"] is not None and f["kmin"] >= 2
    assert math.isfinite(f["gamma_mle"])
    assert 1.5 < f["gamma_mle"] < 3.0
    assert f["n_tail"] >= 50


def test_in_degree_histogram_sums_to_node_count():
    r = run_price(n=1000, m=3, a=1, n_seeds=20, seed=0)
    hist = in_degree_histogram(r["in_degrees"])
    assert sum(h["count"] for h in hist) == 1000
    assert hist[0]["degree"] == 0            # the never-cited spike at in-degree 0


def test_variance_matches_population_formula():
    vals = [1.0, 2.0, 3.0, 4.0]
    mean = 2.5
    expected = sum((v - mean) ** 2 for v in vals) / 4
    assert variance(vals) == pytest.approx(expected)
    assert variance([7.0]) == 0.0


# -- structural signatures (P1) -----------------------------------------------

def test_out_degree_variance_is_zero_but_in_degree_variance_is_large():
    # P1 signature (graded in the runner): out-degree is constant (var 0 among
    # non-seeds), in-degree is heavy-tailed (var ratio huge).
    r = run_price(n=20000, m=3, a=1, n_seeds=20, seed=0)
    assert r["var_nonseed_out_degree"] == pytest.approx(0.0, abs=1e-12)
    assert r["var_in_degree"] > 0.0
    # in/out variance ratio (over the whole graph) is large.
    assert r["var_ratio_in_over_out"] > 50.0
