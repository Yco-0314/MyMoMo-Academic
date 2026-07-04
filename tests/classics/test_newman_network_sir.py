"""Faithful-mechanism + determinism tests for the Newman 2002 SIR-on-networks
(bond-percolation) reproduction.

These pin the closed-form threshold T_c = <k>/(<k^2> - <k>), the degree-moment
computation, the configuration-model stub-matching (degree sequence honored up to
erased self/multi-edges), the union-find bond-percolation cluster growth, the
generating-function final-size self-consistency (S = 1 - g0(1 - T + T u), u = g1(...)),
and determinism (same seed -> identical result).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(threshold matches the formula; heterogeneity lowers it; GF curve matches simulation)
are evaluated by examples/repro_newman_network_sir/run.py.
"""
from __future__ import annotations

import random

import pytest

from abm_auto.classics.newman_network_sir import (
    UnionFind,
    build_configuration_edges,
    build_graph,
    critical_transmissibility,
    degree_moments,
    degree_pmf,
    empirical_threshold_from_sweep,
    gf_final_size,
    percolate_once,
    percolation_sweep,
    poisson_degree_sequence,
    powerlaw_degree_sequence,
)


# -- degree moments + closed-form threshold -----------------------------------

def test_degree_moments_basic():
    seq = [1, 2, 3, 4]
    mean_k, mean_k2 = degree_moments(seq)
    assert mean_k == pytest.approx(2.5)
    assert mean_k2 == pytest.approx((1 + 4 + 9 + 16) / 4)


def test_critical_transmissibility_regular_graph():
    # A perfectly regular degree-4 graph: <k>=4, <k^2>=16, so T_c = 4/(16-4) = 1/3.
    seq = [4] * 1000
    assert critical_transmissibility(seq) == pytest.approx(1.0 / 3.0)


def test_critical_transmissibility_poisson_is_reciprocal_mean():
    # For Poisson, <k^2> - <k> = <k>^2 so T_c -> 1/<k>. With a large sample the realized
    # moments approach this. Mean 4 -> T_c ~ 0.25.
    rng = random.Random(0)
    seq = poisson_degree_sequence(20000, 4.0, rng=rng)
    tc = critical_transmissibility(seq)
    assert tc == pytest.approx(0.25, abs=0.03)


def test_heterogeneity_lowers_threshold():
    # At (approximately) equal mean degree, a power-law sequence has a much larger
    # <k^2> and hence a much smaller T_c than a homogeneous Poisson sequence.
    rng = random.Random(1)
    poisson = poisson_degree_sequence(20000, 4.0, rng=rng)
    powerlaw = powerlaw_degree_sequence(20000, 2.5, kmin=1, kmax=1000, rng=rng)
    tc_hom = critical_transmissibility(poisson)
    tc_sf = critical_transmissibility(powerlaw)
    assert tc_sf < tc_hom
    # discriminating: the heavy tail collapses the threshold well below half the
    # homogeneous value (the P2 shape).
    assert tc_sf < 0.5 * tc_hom


def test_infinite_threshold_when_no_variance_and_low_mean():
    # <k> = 1 for everyone: <k^2> - <k> = 0 -> no percolating regime -> +inf.
    seq = [1] * 100
    assert critical_transmissibility(seq) == float("inf")


# -- union-find ---------------------------------------------------------------

def test_unionfind_merges_and_sizes():
    uf = UnionFind(6)
    assert uf.largest_size() == 1
    uf.union(0, 1)
    uf.union(1, 2)         # {0,1,2}
    uf.union(3, 4)         # {3,4}
    assert uf.find(0) == uf.find(2)
    assert uf.find(0) != uf.find(3)
    assert uf.find(5) not in (uf.find(0), uf.find(3))
    assert uf.largest_size() == 3


def test_unionfind_full_merge():
    uf = UnionFind(5)
    for i in range(4):
        uf.union(i, i + 1)
    assert uf.largest_size() == 5
    root = uf.find(0)
    assert all(uf.find(i) == root for i in range(5))


# -- configuration model (stub matching) --------------------------------------

def test_configuration_model_honors_degree_sequence_approximately():
    # Stub-matching realizes the requested degree sequence up to erased self/multi-edges.
    # With a modest mean and N=2000 the erased fraction is small, so the realized mean
    # degree stays close to the requested one.
    rng = random.Random(3)
    seq = poisson_degree_sequence(2000, 4.0, rng=rng)
    graph = build_graph(seq, seed=7)
    requested_mean, _ = degree_moments(seq)
    # realized mean degree from the actual edge list
    realized_mean = 2.0 * graph["n_edges"] / graph["n"]
    assert realized_mean == pytest.approx(requested_mean, rel=0.05)


def test_configuration_model_no_self_or_multi_edges():
    rng = random.Random(4)
    seq = poisson_degree_sequence(500, 5.0, rng=rng)
    edges = build_configuration_edges(seq, rng=random.Random(11))
    # no self-loops
    assert all(a != b for a, b in edges)
    # no duplicate undirected edges (stored canonically a<b)
    assert all(a < b for a, b in edges)
    assert len(set(edges)) == len(edges)


def test_configuration_model_deterministic_given_seed():
    rng = random.Random(5)
    seq = poisson_degree_sequence(500, 4.0, rng=rng)
    e1 = build_configuration_edges(seq, rng=random.Random(9))
    e2 = build_configuration_edges(seq, rng=random.Random(9))
    assert e1 == e2


# -- bond percolation ---------------------------------------------------------

def test_percolation_T_zero_is_all_singletons():
    seq = [4] * 500
    edges = build_configuration_edges(seq, rng=random.Random(1))
    largest, second = percolate_once(500, edges, 0.0, rng=random.Random(2))
    assert largest == 1  # no edge occupied -> every node isolated
    assert second == 1


def test_percolation_T_one_gives_the_whole_component():
    # T=1 occupies every edge, so the giant occupied cluster equals the graph's largest
    # connected component. On a dense-enough regular graph that is ~ all nodes.
    seq = [6] * 2000
    edges = build_configuration_edges(seq, rng=random.Random(1))
    largest, _ = percolate_once(2000, edges, 1.0, rng=random.Random(2))
    assert largest > 0.95 * 2000


def test_percolation_monotone_in_T():
    # Giant fraction should grow (weakly) with T on a fixed graph.
    seq = poisson_degree_sequence(3000, 4.0, rng=random.Random(6))
    edges = build_configuration_edges(seq, rng=random.Random(7))
    fr = []
    for T in (0.1, 0.3, 0.5, 0.7):
        largest, _ = percolate_once(3000, edges, T, rng=random.Random(100))
        fr.append(largest / 3000)
    assert fr == sorted(fr)   # non-decreasing


def test_percolation_deterministic_given_seed():
    seq = poisson_degree_sequence(1000, 4.0, rng=random.Random(8))
    edges = build_configuration_edges(seq, rng=random.Random(9))
    a = percolate_once(1000, edges, 0.4, rng=random.Random(123))
    b = percolate_once(1000, edges, 0.4, rng=random.Random(123))
    assert a == b


def test_percolation_rejects_bad_T():
    edges = [(0, 1)]
    with pytest.raises(ValueError):
        percolate_once(2, edges, -0.1, rng=random.Random(0))
    with pytest.raises(ValueError):
        percolate_once(2, edges, 1.1, rng=random.Random(0))


# -- generating-function final size -------------------------------------------

def test_gf_final_size_zero_below_threshold():
    # Regular degree-4 graph: T_c = 1/3. At T = 0.2 < T_c the GF final size is 0.
    seq = [4] * 5000
    assert gf_final_size(seq, 0.2) == pytest.approx(0.0, abs=1e-9)


def test_gf_final_size_positive_above_threshold():
    seq = [4] * 5000
    S = gf_final_size(seq, 0.6)   # well above T_c = 1/3
    assert 0.0 < S < 1.0
    # T=1 on a regular graph = whole component; S should approach 1 for connected-enough.
    assert gf_final_size(seq, 1.0) > 0.9


def test_gf_final_size_T_zero_is_zero():
    seq = [4] * 100
    assert gf_final_size(seq, 0.0) == 0.0


def test_gf_final_size_matches_percolation_on_regular_graph():
    # The generating-function S(T) should track the simulated giant fraction above
    # threshold on the homogeneous graph (this is the P3 shape, checked loosely here).
    seq = poisson_degree_sequence(10000, 4.0, rng=random.Random(0))
    graph = build_graph(seq, seed=0)
    edges = graph["edges"]
    for T in (0.4, 0.6):
        sim = 0.0
        reps = 8
        for r in range(reps):
            largest, _ = percolate_once(len(seq), edges, T, rng=random.Random(1000 + r))
            sim += largest / len(seq)
        sim /= reps
        gf = gf_final_size(seq, T)
        assert gf == pytest.approx(sim, abs=0.06)


# -- pmf ----------------------------------------------------------------------

def test_degree_pmf_sums_to_one():
    seq = [1, 1, 2, 3, 3, 3]
    pmf = degree_pmf(seq)
    assert pytest.approx(sum(pmf.values())) == 1.0
    assert pmf[3] == pytest.approx(0.5)


# -- sweep + threshold estimator ----------------------------------------------

def test_percolation_sweep_shape_and_threshold_estimate():
    seq = poisson_degree_sequence(5000, 4.0, rng=random.Random(0))
    T_grid = [0.05, 0.15, 0.25, 0.35, 0.5, 0.7]
    sweep = percolation_sweep(seq, T_grid, n_graphs=2, n_perc=4, seed_base=0)
    assert len(sweep) == len(T_grid)
    for row in sweep:
        assert 0.0 <= row["mean_giant_fraction"] <= 1.0
        assert "gf_final_size" in row
    est = empirical_threshold_from_sweep(sweep)
    # susceptibility peak + giant onset should both land in a sane low range for <k>=4
    assert 0.0 < est["T_c_susceptibility"] <= 0.7
    assert 0.0 < est["T_c_giant_onset"] <= 0.7


# -- power-law generator ------------------------------------------------------

def test_powerlaw_sequence_within_support():
    seq = powerlaw_degree_sequence(2000, 2.5, kmin=1, kmax=200, rng=random.Random(0))
    assert len(seq) == 2000
    assert all(1 <= k <= 200 for k in seq)
    # heavy tail: max degree should be well above the mean (hub presence)
    mean_k, _ = degree_moments(seq)
    assert max(seq) > 3 * mean_k


def test_powerlaw_rejects_bad_params():
    with pytest.raises(ValueError):
        powerlaw_degree_sequence(100, 0.5, kmin=1, kmax=100, rng=random.Random(0))
    with pytest.raises(ValueError):
        powerlaw_degree_sequence(100, 2.5, kmin=5, kmax=2, rng=random.Random(0))
