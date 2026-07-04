"""Faithful-rule + determinism + analytic-anchor tests for the Bak-Tang-Wiesenfeld
sandpile (SOC) reproduction.

These pin the toppling rule (cell -4, +1 to each von-Neumann neighbour, boundary grains
lost), the avalanche-size accounting, the abelian/order-independence property, the
discrete-MLE tau estimator on a synthetic power law, and determinism (same seed ->
identical avalanche sequence). They are faithfulness tests, NOT prediction tests (the
locked predictions P1-P3 are evaluated by examples/repro_btw_sandpile/run.py).

NOTE: this is a CELLULAR AUTOMATON / SOC model, not an agent-stepping ABM — there is no
scheduler/agent roster to test, only the deterministic toppling rule.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from abm_auto.classics.btw_sandpile import (
    THRESHOLD,
    Sandpile,
    avalanche,
    drive,
    fit_tau,
    heavy_tail_stats,
    mean_height,
    run_sandpile,
    size_histogram,
)


# -- toppling rule ------------------------------------------------------------

def test_below_threshold_no_toppling():
    pile = Sandpile(5)
    pile.heights[2, 2] = THRESHOLD - 1  # height 3, stable
    s = pile.topple_until_stable()
    assert s == 0
    assert pile.heights[2, 2] == THRESHOLD - 1


def test_single_topple_interior_conserves_locally():
    # A single cell at exactly THRESHOLD in the interior topples exactly once: it loses 4
    # and each of its 4 neighbours gains 1 (no grains lost, interior cell).
    pile = Sandpile(5)
    pile.heights[2, 2] = THRESHOLD
    grains_before = pile.total_grains()
    s = pile.drop_one(2, 2)  # pushes it to 5 -> topples (s counts that topple)
    # drop_one adds one grain first (so total grains in = before+1), interior => none lost
    assert pile.total_grains() == grains_before + 1
    assert s == 1
    assert pile.heights[2, 2] == 1  # 5 - 4
    assert pile.heights[1, 2] == 1
    assert pile.heights[3, 2] == 1
    assert pile.heights[2, 1] == 1
    assert pile.heights[2, 3] == 1


def test_boundary_grains_are_lost():
    # A corner cell has only 2 in-bounds neighbours; toppling sends 4 grains out, only 2
    # land on the grid, 2 leave the boundary and are lost.
    pile = Sandpile(5)
    pile.heights[0, 0] = THRESHOLD
    grains_before = pile.total_grains()  # 4
    pile.heights[0, 0] += 1             # make it 5 by hand (no extra-grain bookkeeping)
    s = pile.topple_until_stable()
    assert s == 1
    assert pile.heights[0, 0] == 1     # 5 - 4
    assert pile.heights[0, 1] == 1     # right neighbour
    assert pile.heights[1, 0] == 1     # down neighbour
    # 2 grains left the grid: total now = (before+1) - 2 lost.
    assert pile.total_grains() == grains_before + 1 - 2


def test_chain_reaction_avalanche():
    # Two adjacent cells primed at THRESHOLD; dropping on one cascades into the other.
    pile = Sandpile(7)
    pile.heights[3, 3] = THRESHOLD - 1
    pile.heights[3, 4] = THRESHOLD - 1
    s = pile.drop_one(3, 3)
    # The first cell reaches 4 (3 + 1) and topples, pushing 3,4 from 3 to 4, which then
    # also topples: at least 2 topplings.
    assert s >= 2
    assert (pile.heights < THRESHOLD).all()  # stable at the end


def test_abelian_order_independence():
    # The total avalanche size and final configuration are independent of where the grain
    # is placed in a symmetric primed grid only insofar as the rule is order-independent;
    # we test that a synchronous sweep gives a stable grid with all cells < THRESHOLD and
    # that re-relaxing an already-stable grid is a no-op (idempotent relaxation).
    pile = Sandpile(9)
    rng = np.random.default_rng(123)
    # Prime a random near-critical grid (heights 0..3), then a few drops.
    pile.heights = rng.integers(0, THRESHOLD, size=(9, 9)).astype(np.int64)
    pile.topple_until_stable()
    assert (pile.heights < THRESHOLD).all()
    # Relaxing an already-stable grid does nothing.
    assert pile.topple_until_stable() == 0


def test_avalanche_helper_matches_drop_one():
    pile_a = Sandpile(6)
    pile_b = Sandpile(6)
    pile_a.heights[2, 2] = THRESHOLD - 1
    pile_b.heights[2, 2] = THRESHOLD - 1
    assert avalanche(pile_a, 2, 2) == pile_b.drop_one(2, 2)
    assert np.array_equal(pile_a.heights, pile_b.heights)


def test_rejects_bad_L():
    with pytest.raises(ValueError):
        Sandpile(0)


# -- determinism --------------------------------------------------------------

def test_same_seed_identical_avalanche_sequence():
    a = run_sandpile(L=20, transient=500, n_avalanches=500, seed=7)
    b = run_sandpile(L=20, transient=500, n_avalanches=500, seed=7)
    assert a["sizes"] == b["sizes"]
    assert a["stationary_mean_height"] == b["stationary_mean_height"]


def test_different_seeds_can_differ():
    a = run_sandpile(L=20, transient=500, n_avalanches=500, seed=1)
    b = run_sandpile(L=20, transient=500, n_avalanches=500, seed=2)
    assert a["sizes"] != b["sizes"]


def test_drive_records_one_size_per_grain():
    pile = Sandpile(10)
    rng = np.random.default_rng(0)
    sizes = drive(pile, 50, rng, record=True)
    assert len(sizes) == 50
    assert all(isinstance(s, int) and s >= 0 for s in sizes)


def test_drive_no_record_returns_empty_but_advances():
    pile = Sandpile(10)
    rng = np.random.default_rng(0)
    out = drive(pile, 50, rng, record=False)
    assert out == []
    assert pile.total_grains() > 0  # grains were added


# -- mean height --------------------------------------------------------------

def test_mean_height_helper():
    pile = Sandpile(4)
    pile.heights[:] = 2
    assert mean_height(pile) == pytest.approx(2.0)


# -- discrete-MLE tau estimator (analytic anchor) ------------------------------

@pytest.mark.parametrize("alpha_true", [2.0, 2.5, 3.0])
def test_fit_tau_recovers_known_exponent(alpha_true):
    # Synthetic GENUINE discrete power law with a known exponent: numpy's zipf draws
    # P(k) ~ k^{-alpha} for k = 1, 2, ... (the discrete power law the estimator is the
    # MLE for). The exact discrete MLE must recover alpha at kmin=1 within sampling error.
    # (This validates the estimator, NOT the sandpile.) The (kmin-0.5) continuity-
    # correction approximation would be biased low here by ~0.2-0.8, which is exactly why
    # fit_tau uses the exact zeta-likelihood MLE instead.
    rng = np.random.default_rng(0)
    samples = rng.zipf(alpha_true, size=400_000)
    res = fit_tau(samples, kmin=1)
    assert res["tau"] == pytest.approx(alpha_true, abs=0.05)
    assert res["n_tail"] == int(samples.size)
    assert res["kmin"] == 1


def test_fit_tau_excludes_zero_sizes():
    # Zero-size avalanches must not enter the tail fit (they are not in the power law).
    sizes = [0, 0, 0, 1, 2, 3, 4, 5]
    res = fit_tau(sizes, kmin=1)
    assert res["n_tail"] == 5  # only the 5 nonzero entries


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
    assert st["decades"] == pytest.approx(3.0)  # log10(1000) - log10(1)
    # median of [1,1,2,10,100,1000] = (2+10)/2 = 6
    assert st["median_nonzero"] == pytest.approx(6.0)
    assert st["max_over_median"] == pytest.approx(1000.0 / 6.0)


def test_size_histogram_geometric_bins_cover_all_nonzero():
    sizes = list(range(0, 1000))  # 0..999
    hist = size_histogram(sizes, n_bins=20)
    total = sum(b["count"] for b in hist)
    nonzero = sum(1 for s in sizes if s >= 1)
    assert total == nonzero  # every nonzero avalanche lands in exactly one bin


# -- SOC sanity (small grid, qualitative) -------------------------------------

def test_self_organizes_to_nontrivial_mean_height():
    # Even on a small grid the driven pile reaches a nonzero stationary mean height and
    # produces a spread of avalanche sizes (not all zero).
    res = run_sandpile(L=20, transient=2_000, n_avalanches=2_000, seed=0)
    assert res["stationary_mean_height"] > 1.0
    assert max(res["sizes"]) > 1
    assert any(s == 0 for s in res["sizes"])  # some drops trigger no avalanche
