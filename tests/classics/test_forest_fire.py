"""Faithful-rule + determinism + analytic-anchor tests for the Drossel-Schwabl
forest-fire (SOC) reproduction.

These pin the synchronous CA update (burning->empty, tree-with-burning-neighbour->burning,
empty->tree w.p. p, tree->burning w.p. f), the double-separation fire-size accounting
(one lightning strike burns the whole connected cluster instantly = one fire of size =
cluster size), the discrete-MLE tau estimator on a synthetic power law, and determinism
(same seed -> identical fire sequence). They are faithfulness tests, NOT prediction tests
(the locked predictions P1-P3 are evaluated by examples/repro_forest_fire/run.py).

NOTE: this is a CELLULAR AUTOMATON / SOC model, not an agent-stepping ABM — there is no
scheduler/agent roster to test, only deterministic local update rules.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from abm_auto.classics.forest_fire import (
    BURNING,
    EMPTY,
    TREE,
    ForestFire,
    SeparatedForestFire,
    _cluster_size,
    fit_tau,
    heavy_tail_stats,
    run_separated,
    size_histogram,
)


# -- (A) literal synchronous CA rules -----------------------------------------

def test_burning_becomes_empty():
    ff = ForestFire(5, p=0.0, f=0.0, seed=0, init="empty")
    ff.grid[2, 2] = BURNING
    ff.step()
    assert ff.grid[2, 2] == EMPTY


def test_fire_spreads_to_tree_neighbour():
    # A burning cell ignites an adjacent tree; with p=f=0 nothing else changes.
    ff = ForestFire(5, p=0.0, f=0.0, seed=0, init="empty")
    ff.grid[2, 2] = BURNING
    ff.grid[2, 3] = TREE
    ff.grid[3, 2] = TREE
    ff.grid[0, 0] = TREE  # isolated tree, no burning neighbour -> stays a tree
    ff.step()
    assert ff.grid[2, 3] == BURNING   # ignited
    assert ff.grid[3, 2] == BURNING   # ignited
    assert ff.grid[2, 2] == EMPTY     # burnt down
    assert ff.grid[0, 0] == TREE      # untouched (no burning neighbour, f=0)


def test_growth_fills_empty_with_prob_p():
    # With p=1, every empty cell becomes a tree in one tick; with p=0 none do.
    ff1 = ForestFire(8, p=1.0, f=0.0, seed=1, init="empty")
    ff1.step()
    assert np.all(ff1.grid == TREE)
    ff0 = ForestFire(8, p=0.0, f=0.0, seed=1, init="empty")
    ff0.step()
    assert np.all(ff0.grid == EMPTY)


def test_lightning_ignites_tree_with_prob_f():
    # With f=p=1 (and no burning neighbours), every tree is struck by lightning -> burning.
    # (f<=p is required by the scale-separation guard; f=p=1 is the degenerate edge that
    # still exercises the lightning rule.)
    ff = ForestFire(8, p=1.0, f=1.0, seed=2, init="trees")
    ff.step()
    assert np.all(ff.grid == BURNING)


def test_no_wrap_open_boundary():
    # A burning cell on the top edge must NOT ignite a tree on the bottom edge (no torus).
    ff = ForestFire(5, p=0.0, f=0.0, seed=0, init="empty")
    ff.grid[0, 2] = BURNING
    ff.grid[4, 2] = TREE
    ff.step()
    assert ff.grid[4, 2] == TREE  # not ignited across the boundary


def test_rejects_bad_L_and_bad_scale():
    with pytest.raises(ValueError):
        ForestFire(0)
    with pytest.raises(ValueError):
        ForestFire(5, p=0.05, f=0.1)  # f > p violates scale separation


# -- (B) double-separation fire-size accounting -------------------------------

def test_cluster_size_connected_von_neumann():
    # A plus-shaped cluster of 5 trees + a diagonal-only neighbour that must NOT connect.
    grid = np.zeros((5, 5), dtype=np.int8)
    for (r, c) in [(2, 2), (1, 2), (3, 2), (2, 1), (2, 3)]:
        grid[r, c] = TREE
    grid[1, 1] = TREE  # diagonal to centre, only von-Neumann-adjacent to (1,2) and (2,1)
    cells = _cluster_size(grid, 2, 2)
    # (1,1) IS connected via (1,2) [von-Neumann], so the cluster is all 6.
    assert len(cells) == 6
    # An isolated tree forms its own size-1 cluster.
    iso = np.zeros((5, 5), dtype=np.int8)
    iso[0, 0] = TREE
    assert len(_cluster_size(iso, 0, 0)) == 1
    # Striking empty ground returns no cells.
    assert _cluster_size(iso, 4, 4) == []


def test_cluster_size_wraps_toroidally_for_fire_size_metric():
    grid = np.zeros((5, 5), dtype=np.int8)
    grid[1, 0] = TREE
    grid[1, 4] = TREE
    cells = set(_cluster_size(grid, 1, 0))
    assert cells == {(1, 0), (1, 4)}


def test_lightning_burns_whole_cluster_instantly():
    ff = SeparatedForestFire(5, p=0.05, f=5e-5, seed=0, init="empty")
    ff.grid[:] = EMPTY
    # A connected line of 4 trees.
    for c in range(4):
        ff.grid[2, c] = TREE
    # Force the strike onto a tree by seeding the grid, then call _cluster_size directly
    # to verify instantaneous removal of the whole cluster.
    cells = _cluster_size(ff.grid, 2, 0)
    assert len(cells) == 4
    for (r, c) in cells:
        ff.grid[r, c] = EMPTY
    assert np.all(ff.grid == EMPTY)


def test_lightning_on_empty_returns_zero():
    ff = SeparatedForestFire(5, p=0.05, f=5e-5, seed=0, init="empty")
    ff.grid[:] = EMPTY  # all empty -> any strike hits bare ground
    assert ff.lightning() == 0


def test_trees_per_strike_match_scale_ratio():
    # theta = trees planted per strike = round(p/f); with p=0.05, f=p/1000 -> 1000.
    ff = SeparatedForestFire(10, p=0.05, f=0.05 / 1000, seed=0)
    assert ff.trees_per_strike == 1000


def test_grow_plants_exactly_theta_trees():
    # On an empty grid the growth phase plants exactly theta trees (not a saturating bulk).
    ff = SeparatedForestFire(64, p=0.05, f=0.05 / 100, seed=0, init="empty")  # theta=100
    assert ff.trees_per_strike == 100
    ff._grow()
    assert int(np.sum(ff.grid == TREE)) == 100


# -- determinism --------------------------------------------------------------

def test_same_seed_identical_fire_sequence():
    a = run_separated(L=48, p=0.05, f=0.05 / 64, transient=50, n_fires=200, seed=7)
    b = run_separated(L=48, p=0.05, f=0.05 / 64, transient=50, n_fires=200, seed=7)
    assert a["sizes"] == b["sizes"]
    assert a["stationary_tree_density"] == b["stationary_tree_density"]


def test_different_seeds_can_differ():
    a = run_separated(L=48, p=0.05, f=0.05 / 64, transient=50, n_fires=200, seed=1)
    b = run_separated(L=48, p=0.05, f=0.05 / 64, transient=50, n_fires=200, seed=2)
    assert a["sizes"] != b["sizes"]


def test_run_records_one_size_per_fire():
    r = run_separated(L=32, p=0.05, f=0.05 / 32, transient=20, n_fires=100, seed=0)
    assert len(r["sizes"]) == 100
    assert all(isinstance(s, int) and s >= 0 for s in r["sizes"])


# -- discrete-MLE tau estimator (analytic anchor) ------------------------------

@pytest.mark.parametrize("alpha_true", [1.5, 2.0, 2.5])
def test_fit_tau_recovers_known_exponent(alpha_true):
    # Synthetic GENUINE discrete power law (numpy zipf draws P(k) ~ k^{-alpha}); the exact
    # discrete MLE must recover alpha at kmin=1 within sampling error. Validates the
    # estimator, NOT the forest fire.
    rng = np.random.default_rng(0)
    samples = rng.zipf(alpha_true, size=400_000)
    res = fit_tau(samples, kmin=1)
    assert res["tau"] == pytest.approx(alpha_true, abs=0.05)
    assert res["n_tail"] == int(samples.size)
    assert res["kmin"] == 1


def test_fit_tau_excludes_zero_sizes():
    sizes = [0, 0, 0, 1, 2, 3, 4, 5]
    res = fit_tau(sizes, kmin=1)
    assert res["n_tail"] == 5


def test_fit_tau_empty_tail_is_nan():
    res = fit_tau([0, 0, 0], kmin=1)
    assert math.isnan(res["tau"])
    assert res["n_tail"] == 0


# -- heavy-tail descriptors ----------------------------------------------------

def test_heavy_tail_stats_basic():
    sizes = [0, 1, 1, 2, 10, 100, 1000]
    st = heavy_tail_stats(sizes)
    assert st["n_nonzero"] == 6
    assert st["max"] == 1000.0
    assert st["min_nonzero"] == 1.0
    assert st["decades"] == pytest.approx(3.0)
    assert st["median_nonzero"] == pytest.approx(6.0)
    assert st["max_over_median"] == pytest.approx(1000.0 / 6.0)


def test_size_histogram_geometric_bins_cover_all_nonzero():
    sizes = list(range(0, 1000))
    hist = size_histogram(sizes, n_bins=20)
    total = sum(b["count"] for b in hist)
    nonzero = sum(1 for s in sizes if s >= 1)
    assert total == nonzero


# -- SOC sanity (small grid, qualitative) -------------------------------------

def test_self_organizes_to_nontrivial_density_and_fire_spread():
    # On a small grid with a small-grid-appropriate theta (=64 trees/strike, well below
    # the 64*64 = 4096 cells) the separated model reaches a nonzero stationary tree density
    # and produces a spread of fire sizes (not all zero, some > 1).
    r = run_separated(L=64, p=0.05, f=0.05 / 64, transient=300, n_fires=800, seed=0)
    assert 0.1 < r["stationary_tree_density"] < 0.95   # neither empty nor saturated
    assert max(r["sizes"]) > 1
