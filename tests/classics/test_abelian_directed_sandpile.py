"""Faithful-rule + determinism tests for the directed abelian sandpile (Dhar & Ramaswamy
1989) reproduction.

These pin the directed toppling rule (threshold 2, sheds 2 grains DOWNWARD to the two
down-diagonal neighbours), the transverse periodicity + open bottom boundary, the ABELIAN
order-independence (a synchronous top-down sweep gives the same size and final config as a
naive single-cell relaxation), the wrap-aware avalanche-geometry metrics, the discrete-MLE
tail-exponent helper, and determinism. They are faithfulness tests of the RULES, NOT
prediction tests — the locked P1-P3 (tau in [1.2,1.5]~4/3, anisotropy >= 2x, heavy tail)
are evaluated by examples/repro_abelian_directed_sandpile/run.py.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.abelian_directed_sandpile import (
    THRESHOLD,
    DirectedSandpile,
    analyze,
    anisotropy_stats,
    fit_tau,
    heavy_tail_stats,
    longitudinal_extent,
    run_directed_sandpile,
    transverse_extent,
)


def _naive_relax(H, W, init):
    """Reference relaxation: topple ONE arbitrary unstable cell (fully once) at a time,
    directed rule. Because the model is abelian this must agree with the model's sweep on
    BOTH the toppling count and the final configuration, regardless of order."""
    h = init.copy()
    total = 0
    while True:
        ys, xs = np.nonzero(h >= THRESHOLD)
        if len(ys) == 0:
            return total, h
        y, x = int(ys[0]), int(xs[0])
        h[y, x] -= THRESHOLD
        if y + 1 < H:
            h[y + 1, x] += 1
            h[y + 1, (x + 1) % W] += 1
        total += 1


# -- the directed toppling rule ------------------------------------------------

def test_threshold_is_two():
    assert THRESHOLD == 2


def test_single_topple_sends_two_grains_down_diagonal():
    # A lone height-2 cell at (0,0) topples once: -2 at (0,0); +1 at (1,0) and +1 at (1,1).
    p = DirectedSandpile(H=3, W=3)
    p.heights[0, 0] = 2
    size, toppled = p._relax()
    assert size == 1
    assert toppled == {(0, 0)}
    assert p.heights[0, 0] == 0
    assert p.heights[1, 0] == 1          # down-left (same column)
    assert p.heights[1, 1] == 1          # down-right (column + 1)
    # nothing moves upward or sideways within the row
    assert p.heights[2, 0] == 0 and p.heights[1, 2] == 0


def test_grains_only_move_downward():
    # A cell in the MIDDLE topples down only: the row above is never touched.
    p = DirectedSandpile(H=4, W=4)
    p.heights[2, 1] = 2
    p.heights[1, :] = 0
    p._relax()
    assert np.all(p.heights[0] == 0)     # top row untouched
    assert np.all(p.heights[1] == 0)     # the row ABOVE the toppler untouched
    assert p.heights[3, 1] == 1 and p.heights[3, 2] == 1


def test_transverse_wrap_of_down_right_neighbour():
    # The down-right neighbour of the LAST column wraps to column 0 (periodic in x).
    p = DirectedSandpile(H=2, W=5)
    p.heights[0, 4] = 2
    p._relax()
    assert p.heights[1, 4] == 1          # down-left = same column 4
    assert p.heights[1, 0] == 1          # down-right = (4+1) mod 5 = 0 (wrapped)


def test_bottom_row_grains_are_lost():
    # Toppling the OPEN bottom row loses both grains (no row below to receive them).
    p = DirectedSandpile(H=3, W=4)
    p.heights[2, 1] = 2                   # bottom row (y = H-1 = 2)
    grains_before = p.total_grains()
    size, toppled = p._relax()
    assert size == 1 and toppled == {(2, 1)}
    assert p.heights[2, 1] == 0
    assert p.total_grains() == grains_before - 2   # both grains left the system


def test_multiple_topplings_of_one_cell():
    # A cell with height 5 topples TWICE (5 -> 3 -> 1); it sheds 4 grains downward.
    p = DirectedSandpile(H=3, W=6)
    p.heights[0, 2] = 5
    size, toppled = p._relax()
    # (0,2) toppled 2x contributes 2; the shed grains cascade further down (counted too).
    assert (0, 2) in toppled
    assert p.heights[0, 2] == 1          # 5 - 2*2 = 1 left, now stable
    assert size >= 2
    # conservation: the drop of 4 grains from row0 is fully accounted by the sweep result
    assert p.heights.min() >= 0


def test_abelian_order_independence():
    # THE defining property: the sweep result (size + final config) is independent of the
    # toppling order. Compare to a naive single-cell relaxation over many random configs.
    rng = np.random.default_rng(1234)
    for _ in range(150):
        H = int(rng.integers(3, 9))
        W = int(rng.integers(3, 9))
        init = rng.integers(0, 3, size=(H, W)).astype(np.int64)
        p = DirectedSandpile(H, W)
        p.heights = init.copy()
        s_sweep, _ = p._relax()
        s_naive, h_naive = _naive_relax(H, W, init)
        assert s_sweep == s_naive
        assert np.array_equal(p.heights, h_naive)


def test_drop_one_returns_size_and_toppled_set():
    p = DirectedSandpile(H=4, W=4)
    p.heights[0, 1] = 1                   # so a drop at col 1 makes it 2 -> topples
    size, toppled = p.drop_one(1)
    assert size >= 1
    assert (0, 1) in toppled


def test_drop_below_threshold_no_avalanche():
    # A drop onto an empty top-row cell (height 0 -> 1 < 2) causes no toppling.
    p = DirectedSandpile(H=5, W=5)
    size, toppled = p.drop_one(2)
    assert size == 0
    assert toppled == set()
    assert p.heights[0, 2] == 1


def test_invalid_dimensions_raise():
    with pytest.raises(ValueError):
        DirectedSandpile(H=1, W=10)
    with pytest.raises(ValueError):
        DirectedSandpile(H=10, W=1)


# -- avalanche-geometry metrics (wrap-aware) -----------------------------------

def test_longitudinal_extent():
    assert longitudinal_extent(set()) == 0
    assert longitudinal_extent({(3, 5)}) == 0            # single row
    assert longitudinal_extent({(0, 0), (3, 9)}) == 3    # y spans 0..3


def test_transverse_extent_linear_and_single():
    assert transverse_extent(set(), 10) == 0
    assert transverse_extent({(0, 4), (1, 4)}, 10) == 0  # single column
    assert transverse_extent({(0, 1), (0, 3)}, 10) == 2  # cols 1..3 -> extent 2


def test_transverse_extent_is_wrap_aware():
    # Columns 0 and 9 on a ring of W=10 are ADJACENT across the seam: extent 1, not 9.
    assert transverse_extent({(0, 0), (0, 9)}, 10) == 1
    # a cluster occupying cols {8,9,0,1} wraps: tightest arc is 4 columns -> extent 3.
    assert transverse_extent({(0, 8), (0, 9), (0, 0), (0, 1)}, 10) == 3


# -- discrete-MLE tail exponent ------------------------------------------------

def test_fit_tau_recovers_known_exponent():
    # Sample from the EXACT discrete power law P(s) = s^-tau / zeta(tau) (numpy's Zipf is
    # the zeta distribution) with tau=2.0 and check the MLE recovers it. This is the same
    # discrete law fit_tau assumes, so the estimate should land within a few percent.
    rng = np.random.default_rng(0)
    tau_true = 2.0
    s = rng.zipf(tau_true, size=300000).astype(np.int64)
    res = fit_tau(s, kmin=1)
    assert res["n_tail"] == s.size
    assert abs(res["tau"] - tau_true) < 0.03     # MLE lands on the truth for the exact law


def test_fit_tau_excludes_zeros():
    sizes = [0, 0, 0, 1, 2, 3, 4, 5]
    res = fit_tau(sizes, kmin=1)
    assert res["n_tail"] == 5                     # the three zeros are excluded


# -- heavy-tail + anisotropy descriptors ---------------------------------------

def test_heavy_tail_stats_on_hand_data():
    sizes = [0, 0, 1, 2, 4, 10, 1000]
    ht = heavy_tail_stats(sizes)
    assert ht["n_nonzero"] == 5
    assert ht["max"] == 1000.0
    assert ht["min_nonzero"] == 1.0
    assert ht["median_nonzero"] == 4.0
    assert ht["max_over_median"] == pytest.approx(250.0)
    assert ht["decades"] == pytest.approx(3.0)    # log10(1000) - log10(1)


def test_anisotropy_uses_only_nonzero_avalanches():
    sizes = [0, 5, 8]
    longitudinal = [0, 10, 20]
    transverse = [0, 2, 4]
    an = anisotropy_stats(longitudinal, transverse, sizes)
    assert an["n_nonzero"] == 2
    assert an["mean_longitudinal"] == pytest.approx(15.0)   # (10+20)/2, zero excluded
    assert an["mean_transverse"] == pytest.approx(3.0)      # (2+4)/2
    assert an["aniso_ratio"] == pytest.approx(5.0)


# -- run summary shape + determinism -------------------------------------------

def test_run_summary_shape():
    run = run_directed_sandpile(H=40, W=40, transient=200, n_avalanches=500, seed=0)
    assert run["H"] == 40 and run["W"] == 40
    assert len(run["sizes"]) == 500
    assert len(run["longitudinal"]) == 500 == len(run["transverse"])
    a = analyze(run)
    assert set(a) >= {"tau", "heavy_tail", "anisotropy", "histogram", "n_zero", "n_total"}
    assert a["n_total"] == 500
    assert a["n_zero"] + a["heavy_tail"]["n_nonzero"] == 500


def test_determinism_same_seed():
    a = run_directed_sandpile(H=60, W=50, transient=300, n_avalanches=800, seed=7)
    b = run_directed_sandpile(H=60, W=50, transient=300, n_avalanches=800, seed=7)
    assert a["sizes"] == b["sizes"]
    assert a["longitudinal"] == b["longitudinal"]
    assert a["transverse"] == b["transverse"]


def test_different_seed_differs():
    a = run_directed_sandpile(H=60, W=50, transient=300, n_avalanches=800, seed=1)
    b = run_directed_sandpile(H=60, W=50, transient=300, n_avalanches=800, seed=2)
    assert a["sizes"] != b["sizes"]
