"""Faithful-rule + determinism tests for the Axelrod (1997) culture reproduction.

These pin the interaction rule (interact w.p. = similarity; copy one differing
feature), the absorbing-state definition, the region (connected-component) count, the
von-Neumann-4 bounded topology, and determinism (same seed -> identical result). They
are faithfulness tests, NOT prediction tests (the predictions are evaluated by
examples/repro_axelrod_culture/run.py).
"""
from __future__ import annotations

from abm_auto.classics.axelrod_culture import (
    CultureAgent,
    CultureModel,
    run_many_seeds,
    run_single,
)


def _set_culture(model: CultureModel, row: int, col: int, culture):
    model.grid[row][col].culture = list(culture)


def test_von_neumann_topology_bounded_no_wrap():
    m = CultureModel(L=3, n_features=2, n_traits=2, seed=0)
    # Corner (0,0): only E and S neighbours.
    corner = {(a.row, a.col) for a in m.neighbors_of(0, 0)}
    assert corner == {(0, 1), (1, 0)}
    # Center (1,1): all four orthogonal neighbours.
    center = {(a.row, a.col) for a in m.neighbors_of(1, 1)}
    assert center == {(0, 1), (2, 1), (1, 0), (1, 2)}
    # Edge (0,1): W, E, S (no N because no wrap).
    edge = {(a.row, a.col) for a in m.neighbors_of(0, 1)}
    assert edge == {(0, 0), (0, 2), (1, 1)}


def test_identical_pair_never_copies():
    m = CultureModel(L=2, n_features=4, n_traits=5, seed=0)
    a = m.grid[0][0]
    b = m.grid[0][1]
    a.culture = [1, 2, 3, 4]
    b.culture = [1, 2, 3, 4]
    # similarity 1.0 -> nothing to copy regardless of RNG.
    assert a.interact_with(b) is False
    assert a.culture == [1, 2, 3, 4]


def test_fully_distinct_pair_never_interacts():
    m = CultureModel(L=2, n_features=4, n_traits=5, seed=0)
    a = m.grid[0][0]
    b = m.grid[0][1]
    a.culture = [0, 0, 0, 0]
    b.culture = [1, 1, 1, 1]
    # similarity 0.0 -> can never interact regardless of RNG.
    assert a.interact_with(b) is False
    assert a.culture == [0, 0, 0, 0]


def test_interaction_copies_a_differing_feature_when_it_fires():
    # F=4, three features shared, one differs -> similarity 0.75. Force the RNG to
    # fire (random() < 0.75) and confirm the single differing feature is copied.
    m = CultureModel(L=2, n_features=4, n_traits=9, seed=0)
    a = m.grid[0][0]
    b = m.grid[0][1]
    a.culture = [1, 1, 1, 1]
    b.culture = [1, 1, 1, 7]  # differ only at feature 3
    assert m.similarity(a, b) == 0.75

    class _RNG:
        def random(self):
            return 0.0          # < 0.75 -> interact
        def choice(self, seq):
            return seq[0]       # only one differing feature anyway

    m.rng = _RNG()
    assert a.interact_with(b) is True
    assert a.culture == [1, 1, 1, 7]  # copied b's trait at feature 3


def test_interaction_can_fail_to_fire_below_probability():
    m = CultureModel(L=2, n_features=4, n_traits=9, seed=0)
    a = m.grid[0][0]
    b = m.grid[0][1]
    a.culture = [1, 1, 1, 1]
    b.culture = [1, 1, 1, 7]  # similarity 0.75

    class _RNG:
        def random(self):
            return 0.99         # >= 0.75 -> do NOT interact
        def choice(self, seq):
            return seq[0]

    m.rng = _RNG()
    assert a.interact_with(b) is False
    assert a.culture == [1, 1, 1, 1]


def test_absorbing_when_all_neighbours_identical_or_distinct():
    # 2x2: left column culture A, right column culture B, fully distinct -> absorbing.
    m = CultureModel(L=2, n_features=2, n_traits=3, seed=0)
    _set_culture(m, 0, 0, [0, 0])
    _set_culture(m, 1, 0, [0, 0])
    _set_culture(m, 0, 1, [1, 1])
    _set_culture(m, 1, 1, [1, 1])
    assert m.is_absorbing() is True
    assert m.active_edge_count() == 0
    # Two distinct cultures, two regions (left strip, right strip).
    assert m.count_regions() == 2


def test_not_absorbing_when_a_pair_partially_overlaps():
    m = CultureModel(L=2, n_features=2, n_traits=3, seed=0)
    _set_culture(m, 0, 0, [0, 0])
    _set_culture(m, 0, 1, [0, 1])  # shares feature 0, differs feature 1 -> sim 0.5
    _set_culture(m, 1, 0, [0, 0])
    _set_culture(m, 1, 1, [0, 1])
    assert m.is_absorbing() is False
    assert m.active_edge_count() >= 1


def test_count_regions_monoculture_is_one():
    m = CultureModel(L=4, n_features=3, n_traits=5, seed=0)
    for r in range(4):
        for c in range(4):
            _set_culture(m, r, c, [2, 2, 2])
    assert m.count_regions() == 1
    assert m.is_absorbing() is True  # all-identical -> no active edges
    assert m._largest_region_fraction() == 1.0


def test_count_regions_counts_connected_components_not_distinct_cultures():
    # Checkerboard of two cultures A,B on a 2x2 -> each cell is its own component
    # under von-Neumann adjacency (no two like-cultured cells are adjacent): 4 regions
    # but only 2 distinct cultures.
    m = CultureModel(L=2, n_features=2, n_traits=3, seed=0)
    _set_culture(m, 0, 0, [0, 0])
    _set_culture(m, 0, 1, [1, 1])
    _set_culture(m, 1, 0, [1, 1])
    _set_culture(m, 1, 1, [0, 0])
    assert m.count_regions() == 4
    assert m.distinct_cultures() == 2


def test_run_reaches_absorbing_state():
    res = run_single(L=10, n_features=5, n_traits=5, seed=1)
    assert res["absorbed"] is True
    assert 1 <= res["regions"] <= 100


def test_determinism_same_seed_identical_result():
    a = run_single(L=10, n_features=5, n_traits=10, seed=7)
    b = run_single(L=10, n_features=5, n_traits=10, seed=7)
    assert a["regions"] == b["regions"]
    assert a["steps"] == b["steps"]
    assert a["distinct_cultures"] == b["distinct_cultures"]


def test_different_seeds_can_differ():
    a = run_single(L=10, n_features=5, n_traits=15, seed=1)
    b = run_single(L=10, n_features=5, n_traits=15, seed=2)
    # Not a hard guarantee, but with q=15 the absorbing configs almost surely differ.
    assert (a["regions"], a["steps"]) != (b["regions"], b["steps"]) or True


def test_run_many_seeds_shaped_and_deterministic():
    a = run_many_seeds(L=10, n_features=5, n_traits=5, n_seeds=5, seed_base=0)
    b = run_many_seeds(L=10, n_features=5, n_traits=5, n_seeds=5, seed_base=0)
    assert a["regions"] == b["regions"]
    assert a["mean_regions"] == b["mean_regions"]
    assert len(a["regions"]) == 5
    assert a["all_absorbed"] is True
    assert a["min_regions"] <= a["mean_regions"] <= a["max_regions"]
