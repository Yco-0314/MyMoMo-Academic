"""Faithful-construction + determinism tests for the Watts-Strogatz (1998)
small-world NETWORK-GENERATION reproduction.

These pin the ring-lattice construction (n*k/2 edges, k-regular, analytic lattice
clustering C = 3(k-2)/(4(k-1))), the giant-component path-length convention, the
p=0 / p=1 endpoint qualitative behaviour, normalisation to the lattice baseline, the
half-drop crossing helper, and determinism (same seed -> identical graph/metrics).

They are construction/faithfulness tests, NOT the locked prediction tests (P1-P3 are
evaluated by examples/repro_watts_strogatz/run.py against the full n=1000 grid).
"""
from __future__ import annotations

import networkx as nx
import pytest

from abm_auto.classics.watts_strogatz import (
    build_ws_graph,
    characteristic_path_length,
    clustering_coefficient,
    first_p_below_half,
    giant_component,
    metrics_for,
    normalize_to_lattice,
    run_many_seeds,
    sweep,
)


def test_ring_lattice_is_k_regular_with_nk_over_2_edges():
    n, k = 50, 6
    g = build_ws_graph(n, k, 0.0, seed=0)
    assert g.number_of_nodes() == n
    assert g.number_of_edges() == n * k // 2
    # p=0 lattice: every node has exactly degree k.
    assert set(dict(g.degree()).values()) == {k}


def test_lattice_clustering_matches_analytic_formula():
    # For a ring lattice with k>=2 nearest neighbours per side, the analytic local
    # clustering coefficient is C_lattice = 3(k-2) / (4(k-1)) (Watts-Strogatz 1998).
    for k in (4, 6, 10):
        g = build_ws_graph(100, k, 0.0, seed=0)
        analytic = 3 * (k - 2) / (4 * (k - 1))
        assert clustering_coefficient(g) == pytest.approx(analytic, abs=1e-9)


def test_lattice_is_seed_independent():
    # p=0 means no rewiring -> the graph is the pristine lattice regardless of seed.
    g1 = build_ws_graph(60, 4, 0.0, seed=1)
    g2 = build_ws_graph(60, 4, 0.0, seed=999)
    assert clustering_coefficient(g1) == clustering_coefficient(g2)
    assert characteristic_path_length(g1) == characteristic_path_length(g2)


def test_odd_k_rejected():
    with pytest.raises(ValueError):
        build_ws_graph(50, 5, 0.1, seed=0)


def test_endpoints_lattice_long_high_vs_random_short_low():
    # Qualitative endpoint behaviour at a small size: the p=0 lattice has a much LONGER
    # characteristic path length and MUCH HIGHER clustering than the p=1 random graph.
    n, k = 200, 10
    lat = metrics_for(n, k, 0.0, seed=0)
    rnd = metrics_for(n, k, 1.0, seed=0)
    assert lat["L"] > rnd["L"]          # lattice path length is longer
    assert lat["C"] > rnd["C"]          # lattice clustering is higher
    # At p=1 the clustering collapses toward the random-graph value (~k/n).
    assert rnd["C"] < 0.2


def test_path_length_uses_giant_component_when_disconnected():
    # A deliberately disconnected graph: two triangles with no edge between them.
    g = nx.Graph()
    g.add_edges_from([(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3)])
    assert not nx.is_connected(g)
    # L is computed on the giant component (here size 3), so it is finite (not inf).
    L = characteristic_path_length(g)
    assert L == pytest.approx(1.0, abs=1e-9)  # complete triangle: all pairs distance 1
    assert giant_component(g).number_of_nodes() == 3


def test_metrics_are_deterministic_for_a_seed():
    a = metrics_for(120, 6, 0.1, seed=7)
    b = metrics_for(120, 6, 0.1, seed=7)
    assert a == b
    # Different seed -> generally different rewiring (so different L/C); at least the
    # graph object differs.
    c = metrics_for(120, 6, 0.1, seed=8)
    assert (c["L"], c["C"]) != (a["L"], a["C"])


def test_run_many_seeds_averages_and_reports_variance():
    seeds = [0, 1, 2, 3]
    r = run_many_seeds(120, 6, 0.1, seeds=seeds)
    assert r["p"] == 0.1 and r["k"] == 6 and r["n"] == 120
    assert r["seeds"] == seeds
    assert len(r["per_seed"]) == 4
    assert r["L_std"] >= 0.0 and r["C_std"] >= 0.0
    # mean L is within the [min, max] of the per-seed values.
    Ls = [s["L"] for s in r["per_seed"]]
    assert min(Ls) <= r["L_mean"] <= max(Ls)


def test_run_many_seeds_is_reproducible():
    a = run_many_seeds(100, 6, 0.2, seeds=[0, 1, 2])
    b = run_many_seeds(100, 6, 0.2, seeds=[0, 1, 2])
    assert a["L_mean"] == b["L_mean"]
    assert a["C_mean"] == b["C_mean"]
    assert a["per_seed"] == b["per_seed"]


def test_normalize_to_lattice_sets_ratios_to_one_at_p0():
    rows = sweep(150, 6, [0.0, 0.1, 1.0], seeds=[0, 1])
    norm = normalize_to_lattice(rows)
    base = next(r for r in norm if r["p"] == 0.0)
    assert base["L_over_L0"] == pytest.approx(1.0, abs=1e-12)
    assert base["C_over_C0"] == pytest.approx(1.0, abs=1e-12)
    # By p=1 both ratios should have dropped well below 1.
    top = next(r for r in norm if r["p"] == 1.0)
    assert top["L_over_L0"] < 1.0
    assert top["C_over_C0"] < 1.0


def test_normalize_requires_p0_baseline():
    rows = sweep(80, 6, [0.1, 1.0], seeds=[0])
    with pytest.raises(ValueError):
        normalize_to_lattice(rows)


def test_first_p_below_half_finds_grid_crossing():
    norm = [
        {"p": 0.0, "L_over_L0": 1.0, "C_over_C0": 1.0},
        {"p": 0.01, "L_over_L0": 0.6, "C_over_C0": 0.95},
        {"p": 0.1, "L_over_L0": 0.3, "C_over_C0": 0.7},
        {"p": 1.0, "L_over_L0": 0.1, "C_over_C0": 0.05},
    ]
    # L drops below 0.5 first at p=0.1; C only at p=1.0.
    assert first_p_below_half(norm, "L_over_L0") == 0.1
    assert first_p_below_half(norm, "C_over_C0") == 1.0
    # Never-crossing key returns None.
    flat = [{"p": 0.0, "x": 1.0}, {"p": 1.0, "x": 0.9}]
    assert first_p_below_half(flat, "x") is None
