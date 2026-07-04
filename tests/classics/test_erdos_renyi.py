"""Faithful-rule + determinism + analytic-anchor tests for the Erdos-Renyi giant
component reproduction.

These pin the graph construction (exact mean degree via gnm), the largest-component
fraction measurement, the self-consistent S = 1 - exp(-z*S) solver, and determinism
(same seed -> identical graph -> identical fraction). They are faithfulness tests, NOT
prediction tests (the locked predictions P1-P3 are evaluated by
examples/repro_erdos_renyi/run.py).

NOTE: this is a network-GENERATION model, not an agent-stepping ABM — there is no
scheduler/tick to test, only the static structural rules.
"""
from __future__ import annotations

import math

import networkx as nx
import pytest

from abm_auto.classics.erdos_renyi import (
    build_graph,
    edges_for_mean_degree,
    largest_component_fraction,
    run_many_seeds,
    sweep,
    theoretical_S,
)


# -- graph construction -------------------------------------------------------

def test_edges_for_mean_degree_is_exact():
    # z = 2m/n => m = z*n/2.
    assert edges_for_mean_degree(10_000, 2.0) == 10_000
    assert edges_for_mean_degree(10_000, 1.0) == 5_000
    assert edges_for_mean_degree(10_000, 0.5) == 2_500
    assert edges_for_mean_degree(10_000, 0.0) == 0


def test_edges_clamped_to_feasible_range():
    # Cannot exceed n(n-1)/2 complete-graph edges.
    n = 5
    assert edges_for_mean_degree(n, 1_000.0) == n * (n - 1) // 2
    assert edges_for_mean_degree(n, -1.0) == 0  # round(neg) clamped up to 0


def test_build_graph_has_exact_node_and_edge_count():
    n, z = 1000, 2.0
    g = build_graph(n, z, seed=0)
    assert g.number_of_nodes() == n
    assert g.number_of_edges() == edges_for_mean_degree(n, z)
    # Realised mean degree is exactly z (gnm controls it, not just in expectation).
    mean_degree = 2 * g.number_of_edges() / n
    assert mean_degree == pytest.approx(z)
    # Node labels are 0..n-1.
    assert set(g.nodes()) == set(range(n))


def test_build_graph_rejects_bad_params():
    with pytest.raises(ValueError):
        build_graph(0, 1.0, seed=0)
    with pytest.raises(ValueError):
        build_graph(100, -1.0, seed=0)


# -- largest-component fraction -----------------------------------------------

def test_largest_component_fraction_complete_graph():
    g = nx.complete_graph(50)
    assert largest_component_fraction(g) == 1.0


def test_largest_component_fraction_empty_graph_is_single_node():
    # n isolated nodes: the largest component is one node => 1/n.
    g = nx.empty_graph(10)
    assert largest_component_fraction(g) == pytest.approx(1.0 / 10)


def test_largest_component_fraction_hand_example():
    # Two components: {0,1,2} and {3,4}. Largest = 3/5.
    g = nx.Graph()
    g.add_edges_from([(0, 1), (1, 2), (3, 4)])
    assert largest_component_fraction(g) == pytest.approx(3 / 5)


def test_largest_component_fraction_zero_node_graph():
    assert largest_component_fraction(nx.Graph()) == 0.0


# -- determinism --------------------------------------------------------------

def test_same_seed_identical_graph_and_fraction():
    a = build_graph(2000, 1.5, seed=7)
    b = build_graph(2000, 1.5, seed=7)
    assert set(a.edges()) == set(b.edges())
    assert largest_component_fraction(a) == largest_component_fraction(b)


def test_different_seeds_can_differ():
    fracs = {largest_component_fraction(build_graph(2000, 1.2, seed=s))
             for s in range(8)}
    assert len(fracs) > 1  # near the transition, seed-to-seed variation is real


def test_run_many_seeds_deterministic_and_well_shaped():
    a = run_many_seeds(2000, 1.5, n_seeds=10, seed_base=0)
    b = run_many_seeds(2000, 1.5, n_seeds=10, seed_base=0)
    assert a["fractions"] == b["fractions"]
    assert a["mean_fraction"] == b["mean_fraction"]
    assert len(a["fractions"]) == 10
    assert a["min_fraction"] <= a["mean_fraction"] <= a["max_fraction"]
    assert a["variance"] >= 0.0
    assert a["stdev"] == pytest.approx(math.sqrt(a["variance"]))


def test_sweep_returns_one_row_per_z():
    rows = sweep(1000, [0.5, 1.0, 2.0], n_seeds=3, seed_base=0)
    assert [r["z"] for r in rows] == [0.5, 1.0, 2.0]
    assert all(r["n"] == 1000 and r["n_seeds"] == 3 for r in rows)


# -- analytic anchor: S = 1 - exp(-z*S) ---------------------------------------

def test_theoretical_S_is_zero_at_or_below_threshold():
    assert theoretical_S(0.5) == 0.0
    assert theoretical_S(0.8) == 0.0
    assert theoretical_S(1.0) == 0.0


def test_theoretical_S_solves_the_self_consistency():
    for z in (1.5, 2.0, 3.0):
        s = theoretical_S(z)
        assert 0.0 < s < 1.0
        assert s == pytest.approx(1.0 - math.exp(-z * s), abs=1e-9)


def test_theoretical_S_known_reference_values():
    # Classic references: same fixed-point relation as SIR final size.
    assert theoretical_S(1.5) == pytest.approx(0.583, abs=1e-3)
    assert theoretical_S(2.0) == pytest.approx(0.7968, abs=1e-3)
    assert theoretical_S(3.0) == pytest.approx(0.9405, abs=1e-3)


def test_theoretical_S_monotone_in_z():
    assert theoretical_S(1.2) < theoretical_S(1.5) < theoretical_S(2.0) < theoretical_S(3.0)


# -- end-to-end sanity: measured matches theory above threshold ---------------

def test_measured_fraction_tracks_theory_at_large_n():
    # At n=10k the measured giant fraction is close to the self-consistent S.
    for z in (2.0, 3.0):
        row = run_many_seeds(10_000, z, n_seeds=5, seed_base=0)
        assert row["mean_fraction"] == pytest.approx(theoretical_S(z), abs=0.05)


def test_below_threshold_no_giant_component():
    row = run_many_seeds(10_000, 0.5, n_seeds=5, seed_base=0)
    assert row["mean_fraction"] < 0.05
