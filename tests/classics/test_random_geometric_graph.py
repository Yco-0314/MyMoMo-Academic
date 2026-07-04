"""Faithful-rule + determinism tests for the Random Geometric Graph (Gilbert disk
model, 2D) reproduction.

These pin the hard-boundary Euclidean geometry, the mean-degree relation
<k> = N*pi*r^2 (r = sqrt(<k>/(N*pi))), the disk connection rule, the non-wrapped
cell-grid neighbour lookup (== brute force), the three structural measurements
(clustering / giant-component fraction / measured mean degree), the sweep helpers, and
determinism (same seed -> identical graph).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3 (high
clustering far above ER, high-<k> giant component, mean-degree relation) are evaluated by
examples/repro_random_geometric_graph/run.py.
"""
from __future__ import annotations

import math

import networkx as nx
import pytest

from abm_auto.classics.random_geometric_graph import (
    RandomGeometricGraph,
    clustering_coefficient,
    euclid_dist2,
    ideal_mean_degree,
    largest_component_fraction,
    measured_mean_degree,
    radius_for_mean_degree,
    run_many_seeds,
    run_single,
    sweep,
)


# -- hard-boundary geometry ---------------------------------------------------

def test_euclid_dist2_is_hard_boundary_no_wrap():
    # Plain Euclidean squared distance; points near opposite edges are FAR (no torus).
    assert euclid_dist2(0.1, 0.1, 0.4, 0.5) == pytest.approx(0.09 + 0.16)
    # (0.05,0.05) and (0.95,0.95): the hard-boundary distance is the long diagonal
    # (~0.9*sqrt(2))^2, NOT the short toroidal 0.1*sqrt(2) — this is what distinguishes
    # the disk model from the torus variant.
    assert euclid_dist2(0.05, 0.05, 0.95, 0.95) == pytest.approx(0.9 ** 2 + 0.9 ** 2)


# -- mean-degree relation -----------------------------------------------------

def test_radius_for_mean_degree_inverts_the_relation():
    n, k = 1500, 8.0
    r = radius_for_mean_degree(n, k)
    # r = sqrt(<k>/(N*pi)) and the ideal mean degree N*pi*r^2 round-trips to <k>.
    assert r == pytest.approx(math.sqrt(k / (n * math.pi)))
    assert ideal_mean_degree(n, r) == pytest.approx(k)


def test_radius_grows_with_target_degree_and_shrinks_with_n():
    assert radius_for_mean_degree(1000, 8.0) > radius_for_mean_degree(1000, 4.0)
    assert radius_for_mean_degree(2000, 8.0) < radius_for_mean_degree(1000, 8.0)


def test_radius_for_mean_degree_rejects_bad_args():
    with pytest.raises(ValueError):
        radius_for_mean_degree(0, 4.0)
    with pytest.raises(ValueError):
        radius_for_mean_degree(1000, -1.0)


# -- model construction + invariants ------------------------------------------

def test_points_are_uniform_in_the_unit_square():
    m = RandomGeometricGraph(n=1000, r=0.05, seed=0)
    assert len(m.xs) == 1000 and len(m.ys) == 1000
    for x, y in zip(m.xs, m.ys):
        assert 0.0 <= x < 1.0 and 0.0 <= y < 1.0


def test_from_mean_degree_sets_the_right_radius():
    m = RandomGeometricGraph.from_mean_degree(n=1500, k=8.0, seed=1)
    assert m.r == pytest.approx(radius_for_mean_degree(1500, 8.0))
    # the cell grid uses a NON-wrapped side >= r.
    assert m.cell_size >= m.r - 1e-12
    assert m.n_cells == max(1, int(math.floor(1.0 / m.r)))


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        RandomGeometricGraph(n=0, r=0.05)
    with pytest.raises(ValueError):
        RandomGeometricGraph(n=100, r=0.0)
    with pytest.raises(ValueError):
        RandomGeometricGraph(n=100, r=1.5)   # r > 1 in the unit square


# -- the disk connection rule -------------------------------------------------

def test_edge_exists_iff_within_radius():
    # Two hand-placed points: connected iff their distance <= r.
    m = RandomGeometricGraph(n=2, r=0.1, seed=0)
    m.xs, m.ys = [0.20, 0.28], [0.20, 0.20]   # 0.08 apart (<= 0.1): connected
    g = m.build()
    assert g.has_edge(0, 1)

    m2 = RandomGeometricGraph(n=2, r=0.1, seed=0)
    m2.xs, m2.ys = [0.20, 0.35], [0.20, 0.20]  # 0.15 apart (> 0.1): NOT connected
    g2 = m2.build()
    assert not g2.has_edge(0, 1)


def test_graph_has_all_nodes_even_when_isolated():
    m = RandomGeometricGraph(n=50, r=0.001, seed=0)  # tiny r -> essentially no edges
    g = m.build()
    assert g.number_of_nodes() == 50


# -- cell grid == brute force -------------------------------------------------

def test_cell_grid_edges_match_bruteforce():
    m = RandomGeometricGraph.from_mean_degree(n=1200, k=6.0, seed=7)
    fast = set(m._edges_cell_grid())
    slow = set(m._edges_bruteforce())
    assert fast == slow


def test_cell_grid_edges_match_bruteforce_high_degree():
    # A denser graph (more neighbours per cell) still matches all-pairs exactly.
    m = RandomGeometricGraph.from_mean_degree(n=1000, k=12.0, seed=3)
    fast = set(m._edges_cell_grid())
    slow = set(m._edges_bruteforce())
    assert fast == slow


def test_cell_grid_neighbours_match_bruteforce_per_node():
    m = RandomGeometricGraph.from_mean_degree(n=800, k=8.0, seed=5)
    cells = m._build_cells()
    for i in range(m.n):
        fast = set(m._neighbours(i, cells))
        slow = {
            j for j in range(m.n)
            if j != i and euclid_dist2(m.xs[i], m.ys[i], m.xs[j], m.ys[j]) <= m.r2
        }
        assert fast == slow


# -- structural measurements --------------------------------------------------

def test_clustering_matches_networkx_reference():
    m = RandomGeometricGraph.from_mean_degree(n=800, k=8.0, seed=2)
    g = m.build()
    assert clustering_coefficient(g) == pytest.approx(nx.average_clustering(g))


def test_largest_component_fraction_on_known_graphs():
    # A single triangle across 4 nodes: 3/4 in the largest component.
    g = nx.Graph()
    g.add_nodes_from(range(4))
    g.add_edges_from([(0, 1), (1, 2), (0, 2)])
    assert largest_component_fraction(g) == pytest.approx(0.75)
    # Fully connected path over 5 nodes: all 5 in one component.
    p = nx.path_graph(5)
    assert largest_component_fraction(p) == pytest.approx(1.0)


def test_measured_mean_degree_is_twice_edges_over_n():
    g = nx.Graph()
    g.add_nodes_from(range(10))
    g.add_edges_from([(0, 1), (1, 2), (2, 3)])   # 3 edges, N=10
    assert measured_mean_degree(g) == pytest.approx(2.0 * 3 / 10)


# -- qualitative structural sanity (the locked grade lives in run.py) ---------

def test_measured_mean_degree_close_to_ideal_with_boundary_loss():
    # <k>_meas should sit modestly BELOW the ideal N*pi*r^2 (hard-boundary loss <= 15%),
    # not above it and not wildly off. Faithfulness sanity, not the locked P3 grade.
    res = run_many_seeds(1500, 8.0, n_seeds=5, seed_base=0)
    ideal = res["ideal_mean_degree"]
    meas = res["mean_measured_mean_degree"]
    assert 0.85 * ideal <= meas <= 1.02 * ideal


def test_clustering_far_exceeds_er_expectation():
    # RGG clustering at high <k> is O(0.5), vastly above ER's <k>/N ~ 0.005. Sanity only.
    res = run_many_seeds(1500, 8.0, n_seeds=3, seed_base=0)
    er_expectation = 8.0 / 1500
    assert res["mean_clustering"] > 0.4
    assert res["mean_clustering"] / er_expectation > 30


def test_giant_component_grows_with_mean_degree():
    # S is small at low <k> and near-spanning at high <k> (monotone-ish). Sanity only.
    low = run_many_seeds(1500, 2.0, n_seeds=3, seed_base=0)
    high = run_many_seeds(1500, 8.0, n_seeds=3, seed_base=0)
    assert low["mean_largest_component_fraction"] < 0.30
    assert high["mean_largest_component_fraction"] > 0.85


# -- sweep helpers ------------------------------------------------------------

def test_run_single_summary_shape():
    res = run_single(1000, 8.0, seed=0)
    assert res["n"] == 1000 and res["k_target"] == 8.0
    assert res["r"] == pytest.approx(radius_for_mean_degree(1000, 8.0))
    assert 0.0 <= res["clustering"] <= 1.0
    assert 0.0 < res["largest_component_fraction"] <= 1.0
    assert res["measured_mean_degree"] >= 0.0
    assert res["n_edges"] >= 0


def test_sweep_runs_every_k_once():
    grid = [1.0, 4.0, 8.0]
    out = sweep(1000, grid, n_seeds=2, seed_base=0)
    assert [r["k_target"] for r in out] == grid
    for r in out:
        assert r["n_seeds"] == 2
        assert len(r["per_seed_clustering"]) == 2


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_graph():
    a = run_single(1200, 6.0, seed=42)
    b = run_single(1200, 6.0, seed=42)
    assert a["n_edges"] == b["n_edges"]
    assert a["clustering"] == b["clustering"]
    assert a["largest_component_fraction"] == b["largest_component_fraction"]
    assert a["measured_mean_degree"] == b["measured_mean_degree"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(1200, 6.0, seed=1)
    b = run_single(1200, 6.0, seed=2)
    for res in (a, b):
        assert 0.0 <= res["clustering"] <= 1.0
        assert 0.0 < res["largest_component_fraction"] <= 1.0
