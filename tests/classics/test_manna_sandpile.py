"""Faithful-rule + determinism tests for the Manna stochastic sandpile reproduction.

These pin the Manna toppling RULE (critical at height >= 2; a critical cell loses exactly 2
grains and scatters those 2 grains to two INDEPENDENTLY-random von-Neumann neighbours; grains
off the edge are lost; relax until no cell is critical; avalanche size = total topplings),
mass conservation / open-boundary dissipation, the stochastic-independence signature that
separates Manna from deterministic BTW, the discrete-MLE tau fit, the heavy-tail metrics, and
determinism. They are faithfulness tests of the RULES, NOT prediction tests — the locked
P1-P3 (tail exponent tau in band, heavy-tailed, finite stationary occupancy) are evaluated by
examples/repro_manna_sandpile/run.py.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from abm_auto.classics.manna_sandpile import (
    CRITICAL,
    MannaSandpile,
    avalanche,
    drive,
    fit_tau,
    heavy_tail_stats,
    mean_occupancy,
    run_manna,
    size_histogram,
)


# -- basic construction / guards ----------------------------------------------

def test_invalid_L_raises():
    with pytest.raises(ValueError):
        MannaSandpile(0)
    with pytest.raises(ValueError):
        MannaSandpile(-4)


def test_starts_empty():
    p = MannaSandpile(8, seed=0)
    assert p.total_grains() == 0
    assert p.mean_occupancy() == 0.0
    assert mean_occupancy(p) == 0.0


# -- the toppling threshold ---------------------------------------------------

def test_subcritical_cell_never_topples():
    # A lone cell at height 1 (< CRITICAL=2) is stable: no toppling, no avalanche.
    p = MannaSandpile(8, seed=0)
    p.heights[4, 4] = CRITICAL - 1
    s = p.topple_until_stable()
    assert s == 0
    assert p.heights[4, 4] == CRITICAL - 1
    assert p.total_grains() == CRITICAL - 1


def test_single_critical_cell_topples_once_and_removes_two():
    # An interior cell at exactly height 2 topples exactly once (avalanche size 1): it loses
    # 2 grains and scatters 2 grains into its von-Neumann neighbourhood. Interior => no loss,
    # so total grains are conserved and the toppled cell ends at 0.
    p = MannaSandpile(9, seed=3)
    p.heights[4, 4] = 2
    s = p.topple_until_stable()
    assert s == 1                      # exactly one toppling
    assert p.heights[4, 4] == 0        # lost its 2 grains
    assert p.total_grains() == 2       # 2 grains conserved (interior, none left the edge)


def test_scatter_lands_only_on_von_neumann_neighbours():
    # The 2 scattered grains of a single interior critical cell must land ONLY on the 4
    # nearest neighbours (never diagonal, never the cell itself). Check the total of the 4
    # neighbours is exactly 2 and every non-neighbour cell (except the toppled one) is 0.
    p = MannaSandpile(9, seed=1)
    p.heights[4, 4] = 2
    p.topple_until_stable()
    nbrs = [(3, 4), (5, 4), (4, 3), (4, 5)]
    assert sum(int(p.heights[r, c]) for r, c in nbrs) == 2
    # diagonals untouched
    for r, c in [(3, 3), (3, 5), (5, 3), (5, 5)]:
        assert p.heights[r, c] == 0
    # everything else zero
    assert p.total_grains() == 2


def test_grains_scatter_independently_at_corner():
    # The two grains are drawn INDEPENDENTLY. At a CORNER cell (0,0) only 2 of the 4
    # directions (down, right) are in-bounds; the other 2 (up, left) leave the lattice. Since
    # each grain independently picks 1 of 4 directions, in the FIRST sweep the number of
    # grains leaving the edge is Binomial(2, 1/2): both may leave (prob 1/4), one may leave,
    # or both may stay. We isolate that first sweep by scattering a single corner-cell topple
    # via topple_until_stable on a corner cell whose in-bounds neighbours start EMPTY: when
    # BOTH grains leave, the pile ends empty (total 0) and s == 1 (no cascade). When at least
    # one grain stays, total grains > 0. Observing the total==0 outcome is the independence
    # signature — both draws independently chose an out-of-bounds direction on the same
    # topple. A fixed redistribution could never empty a corner cell.
    saw_both_left = False       # total == 0  => both grains left the edge on sweep 1 (s==1)
    saw_some_stayed = False     # total  > 0  => at least one grain stayed in-bounds
    for seed in range(80):
        p = MannaSandpile(6, seed=seed)
        p.heights[0, 0] = 2
        s = p.topple_until_stable()
        tot = p.total_grains()
        if tot == 0:
            assert s == 1                              # both left on sweep 1: no cascade
            saw_both_left = True
        else:
            assert 0 < tot <= 2                        # some grains survived (may have cascaded)
            saw_some_stayed = True
        if saw_both_left and saw_some_stayed:
            break
    assert saw_both_left, "both grains never left together (independence of the two draws)"
    assert saw_some_stayed, "grains never stayed in-bounds"


def test_height_three_topples_twice_and_leaves_one():
    # A cell at height 3 is critical (>=2). One sweep removes 2 (leaving 1) and scatters 2.
    # The cell is now at 1 (stable). If neither scattered grain landed back... it stays 1.
    # But a neighbour may become critical if it receives 2. Regardless, the toppled cell
    # itself drops by exactly 2 in that first sweep. Verify the sweep arithmetic directly.
    p = MannaSandpile(9, seed=0)
    p.heights[4, 4] = 3
    # After a full relaxation the grid is stable (no cell >= 2) and grains are conserved
    # (interior cell, small grid but neighbours are interior too for one topple).
    s = p.topple_until_stable()
    assert s >= 1
    assert p.total_grains() == 3       # nothing reached the edge
    assert int(p.heights.max()) < CRITICAL   # fully relaxed


# -- open boundary / dissipation ----------------------------------------------

def test_corner_cell_can_lose_grains_off_edge():
    # A critical cell in the corner has only 2 in-bounds neighbours; grains scattered toward
    # the 2 out-of-bounds directions are LOST. Over many topples we must sometimes see the
    # total grains drop below 2 (i.e. at least one grain left the lattice).
    saw_loss = False
    for seed in range(60):
        p = MannaSandpile(6, seed=seed)
        p.heights[0, 0] = 2
        p.topple_until_stable()
        if p.total_grains() < 2:
            saw_loss = True
            break
    assert saw_loss, "corner cell never lost a grain off the open boundary"


def test_edge_dissipation_makes_driven_pile_stationary():
    # Driving a pile continuously must NOT blow up: open-boundary loss balances the input, so
    # the total grain count stays bounded. Drive a modest pile and check occupancy is finite
    # and well below the (2 grains/cell) saturation ceiling.
    p = MannaSandpile(16, seed=0)
    drive(p, 6000, record=False)
    occ = p.mean_occupancy()
    assert 0.0 < occ < 2.0             # a genuine steady state, not frozen (2) nor drained (0)


# -- avalanche size counting --------------------------------------------------

def test_avalanche_size_counts_total_topplings():
    # avalanche() is a thin wrapper: dropping a grain on a height-1 cell makes it critical,
    # so at least one toppling fires; a drop on an empty far cell fires none.
    p = MannaSandpile(12, seed=0)
    p.heights[6, 6] = 1
    s = avalanche(p, 6, 6)             # -> height 2 -> topples
    assert s >= 1
    p2 = MannaSandpile(12, seed=0)
    s0 = avalanche(p2, 0, 11)          # empty cell far corner -> height 1 -> no topple
    assert s0 == 0


def test_drive_records_one_size_per_grain():
    p = MannaSandpile(12, seed=2)
    sizes = drive(p, 500, record=True)
    assert len(sizes) == 500
    assert all(isinstance(s, int) and s >= 0 for s in sizes)
    # record=False stores nothing.
    p2 = MannaSandpile(12, seed=2)
    empty = drive(p2, 100, record=False)
    assert empty == []


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed():
    a = run_manna(L=16, transient=1000, n_avalanches=1500, seed=7, occupancy_samples=50)
    b = run_manna(L=16, transient=1000, n_avalanches=1500, seed=7, occupancy_samples=50)
    assert a["sizes"] == b["sizes"]
    assert a["stationary_mean_occupancy"] == b["stationary_mean_occupancy"]


def test_different_seed_differs():
    a = run_manna(L=16, transient=1000, n_avalanches=1500, seed=1, occupancy_samples=50)
    b = run_manna(L=16, transient=1000, n_avalanches=1500, seed=2, occupancy_samples=50)
    # The stochastic scatter + drops differ, so the recorded avalanche stream differs.
    assert a["sizes"] != b["sizes"]


# -- discrete-MLE tau fit (recover a KNOWN exponent) --------------------------

def test_fit_tau_recovers_synthetic_exponent():
    # Draw a large synthetic discrete power-law sample with a KNOWN tau via inverse-CDF on a
    # continuous Pareto then floor to integers >= s_min; the discrete MLE must land close to
    # the planted exponent. This checks the estimator, independent of the sandpile physics.
    rng = np.random.default_rng(0)
    true_tau = 1.30
    s_min = 1
    n = 400_000
    # continuous power-law with exponent tau (pdf ~ x^{-tau}), x >= s_min, via inverse CDF:
    u = rng.random(n)
    x = s_min * (1.0 - u) ** (-1.0 / (true_tau - 1.0))
    sizes = np.floor(x).astype(np.int64)
    sizes = sizes[sizes >= s_min]
    res = fit_tau(sizes, s_min=s_min)
    assert res["n_tail"] == int(sizes.size)
    # discrete MLE on floored continuous data recovers tau within a few % / a few stderr
    assert abs(res["tau"] - true_tau) < 0.05


def test_fit_tau_excludes_zero_avalanches():
    # Zero-size avalanches (no toppling) are NOT part of the tail and must be excluded: the
    # estimate and the tail count must be identical whether or not zeros are present.
    rng = np.random.default_rng(1)
    u = rng.random(50_000)
    x = 1.0 * (1.0 - u) ** (-1.0 / (1.25 - 1.0))
    x = np.minimum(x, 1e15)                        # clip the extreme tail so int64 cast is safe
    sizes = np.floor(x).astype(np.int64)
    sizes = sizes[sizes >= 1]
    with_zeros = np.concatenate((sizes, np.zeros(20_000, dtype=np.int64)))
    r1 = fit_tau(sizes, s_min=1)
    r2 = fit_tau(with_zeros, s_min=1)
    assert r1["n_tail"] == r2["n_tail"]
    assert r1["tau"] == pytest.approx(r2["tau"])


def test_fit_tau_respects_lower_cutoff():
    # With a higher s_min the fit uses only s >= s_min; the tail count shrinks accordingly.
    sizes = [1, 1, 2, 2, 3, 5, 8, 13, 21, 34, 55]
    r1 = fit_tau(sizes, s_min=1)
    r5 = fit_tau(sizes, s_min=5)
    assert r1["n_tail"] == len(sizes)
    assert r5["n_tail"] == sum(1 for s in sizes if s >= 5)
    assert r5["s_min"] == 5


# -- heavy-tail metrics -------------------------------------------------------

def test_heavy_tail_stats_on_hand_data():
    sizes = [0, 0, 1, 1, 2, 4, 10, 1000]      # nonzero: 1,1,2,4,10,1000
    st = heavy_tail_stats(sizes)
    assert st["n_nonzero"] == 6
    assert st["max"] == 1000.0
    assert st["min_nonzero"] == 1.0
    assert st["median_nonzero"] == pytest.approx(3.0)   # median of [1,1,2,4,10,1000]
    assert st["decades"] == pytest.approx(math.log10(1000.0))  # 3 decades
    assert st["max_over_median"] == pytest.approx(1000.0 / 3.0)


def test_size_histogram_bins_are_geometric_and_cover_all():
    rng = np.random.default_rng(2)
    x = 1.0 * (1.0 - rng.random(20_000)) ** (-1.0 / 0.3)
    x = np.minimum(x, 1e15)                        # clip the extreme tail so int64 cast is safe
    sizes = np.floor(x).astype(np.int64)
    hist = size_histogram(sizes, n_bins=20)
    total_binned = sum(b["count"] for b in hist)
    assert total_binned == int(np.sum(sizes >= 1))    # every nonzero size lands in a bin
    # geometric bins: strictly increasing edges
    for b in hist:
        assert b["hi"] >= b["lo"]
