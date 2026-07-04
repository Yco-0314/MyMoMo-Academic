"""Faithful-rule + determinism tests for the cyclic cellular automaton reproduction
(Fisch, Gravner & Griffeath 1991).

These pin the threshold-1 Moore-8 cyclic advancement rule, the toroidal wrap, the
synchronous update, the change-fraction activity metric, the per-cell colour-return-period
statistic, and determinism. They are FAITHFULNESS tests, NOT prediction tests — the locked
P1 (spiral plateau at n=8), P2 (fixation at n=16), and P3 (colour-return period = n) are
evaluated by examples/repro_cyclic_ca/run.py against the locked thresholds.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.cyclic_ca import (
    change_fraction_series,
    colour_history,
    dominant_active_period,
    has_successor_neighbour,
    random_grid,
    run,
    run_single,
    step,
)


# -- the advancement rule (threshold 1, cyclic) -------------------------------

def test_cell_advances_when_a_neighbour_holds_the_successor_colour():
    # A 3x3 patch on a larger grid: a centre cell in colour 0 with one neighbour in colour 1
    # must advance to 1; a lone cell in colour 0 with no successor neighbour must stay 0.
    n = 4
    g = np.zeros((5, 5), dtype=np.int64)     # everything colour 0
    g[2, 2] = 0
    g[2, 3] = 1                              # a successor (0 -> 1) neighbour of (2,2)
    nxt = step(g, n)
    assert nxt[2, 2] == 1                    # advanced 0 -> 1 (threshold 1 met)
    # a colour-0 cell far from any colour-1 cell keeps its colour.
    assert nxt[0, 0] == 0
    # the successor cell (2,3) is colour 1; it advances only if a neighbour is colour 2.
    assert nxt[2, 3] == 1                    # no colour-2 neighbour -> stays 1


def test_advance_is_strictly_plus_one_mod_n_never_skips():
    # A colour-0 cell surrounded by BOTH colour-1 and colour-2 neighbours still only goes to
    # 1 (it advances by exactly +1; it never jumps straight to 2).
    n = 5
    g = np.zeros((5, 5), dtype=np.int64)
    g[2, 2] = 0
    g[2, 3] = 1
    g[2, 1] = 2                              # a colour-2 neighbour is irrelevant to a 0-cell
    nxt = step(g, n)
    assert nxt[2, 2] == 1                    # +1 only, not +2


def test_wraparound_top_row_advances_from_successor_across_the_torus():
    # A colour-0 cell in the top row whose ONLY successor neighbour is across the toroidal
    # wrap (bottom row) must still advance — the neighbourhood wraps.
    n = 3
    g = np.zeros((4, 4), dtype=np.int64)     # all colour 0
    g[0, 0] = 0
    g[3, 0] = 1                              # directly "above" (0,0) across the wrap
    nxt = step(g, n)
    assert nxt[0, 0] == 1                    # advanced via the toroidal neighbour


def test_no_advance_when_all_uniform():
    # A completely uniform grid has no successor colour anywhere -> nothing ever changes,
    # for any n (a fixed point).
    for n in (2, 3, 8):
        g = np.full((6, 6), 2 % n, dtype=np.int64)
        nxt = step(g, n)
        assert np.array_equal(nxt, g)


def test_two_colour_checkerboard_flips_everywhere():
    # With n=2 a checkerboard of 0/1: EVERY cell has a Moore neighbour of the opposite
    # colour, so 0-cells advance to 1 and 1-cells advance to 0 -> the board inverts each step
    # (period 2). This nails the threshold-1 synchronous flip.
    n = 2
    idx = np.indices((6, 6)).sum(axis=0)
    g = (idx % 2).astype(np.int64)
    g1 = step(g, n)
    assert np.array_equal(g1, 1 - g)         # fully inverted
    g2 = step(g1, n)
    assert np.array_equal(g2, g)             # back to start: period 2


# -- has_successor_neighbour mask ---------------------------------------------

def test_has_successor_neighbour_matches_the_rule_mask():
    n = 4
    g = np.array([[0, 1, 0],
                  [2, 0, 3],
                  [0, 0, 1]], dtype=np.int64)
    mask = has_successor_neighbour(g, n)
    # cell (0,0)=0 has neighbour (0,1)=1 -> successor present -> True
    assert mask[0, 0]
    # cell (1,1)=0 has neighbour (0,1)=1 -> True
    assert mask[1, 1]
    # cell (0,1)=1: needs a neighbour of colour 2; (1,0)=2 is a Moore neighbour -> True
    assert mask[0, 1]
    # the step must advance exactly the masked cells by +1.
    nxt = step(g, n)
    advanced = nxt != g
    assert np.array_equal(advanced, mask)


# -- synchronous (not sequential) update --------------------------------------

def test_update_is_synchronous_uses_current_grid_only():
    # A colour-1 cell next to a colour-2 cell that itself advances this step: the 1-cell must
    # advance based on the CURRENT (pre-update) colour of its neighbour (2), not the neighbour's
    # post-update colour. Set up a 0->1->2 chain and check both advance simultaneously by +1.
    n = 3
    g = np.zeros((4, 4), dtype=np.int64)
    g[1, 1] = 0
    g[1, 2] = 1
    g[1, 3] = 2                              # 2's successor is 0; needs a neighbour colour 0
    nxt = step(g, n)
    assert nxt[1, 1] == 1                    # 0 -> 1 (saw current 1 at (1,2))
    assert nxt[1, 2] == 2                    # 1 -> 2 (saw current 2 at (1,3))
    # (1,3)=2 advances to 0 iff a Moore neighbour is 0; (1,1) and others are 0 -> yes
    assert nxt[1, 3] == 0


# -- run / orbit --------------------------------------------------------------

def test_run_zero_steps_is_identity_and_does_not_mutate():
    g = random_grid(8, 5, seed=3)
    g_copy = g.copy()
    out = run(g, 5, 0)
    assert np.array_equal(out, g_copy)
    step(g, 5)                               # a step must not mutate the input either
    assert np.array_equal(g, g_copy)


def test_colour_history_shape_and_first_frame():
    g = random_grid(10, 6, seed=1)
    frames = colour_history(g, 6, 12)
    assert frames.shape == (13, 10, 10)
    assert np.array_equal(frames[0], g)
    # each successive frame must equal one step of the previous.
    assert np.array_equal(frames[1], step(g, 6))


# -- change-fraction metric ---------------------------------------------------

def test_change_fraction_series_length_and_range():
    g = random_grid(32, 8, seed=0)
    res = change_fraction_series(g, 8, 50)
    cs = res["change_fraction"]
    assert len(cs) == 50
    assert all(0.0 <= c <= 1.0 for c in cs)
    assert res["final_grid"].shape == (32, 32)


def test_change_fraction_is_one_for_inverting_checkerboard():
    # The n=2 checkerboard flips every cell each step -> change fraction is exactly 1.0.
    n = 2
    idx = np.indices((8, 8)).sum(axis=0)
    g = (idx % 2).astype(np.int64)
    res = change_fraction_series(g, n, 4)
    assert all(c == pytest.approx(1.0) for c in res["change_fraction"])


# -- colour-return-period statistic (P3 machinery) ----------------------------

def test_dominant_active_period_equals_n_for_steady_checkerboard_cycle():
    # A cell that advances by +1 EVERY step returns to its start colour every n steps. Build
    # an n=2 checkerboard (every cell advances every step): the colour-return period must be
    # exactly n=2, active fraction 1.0.
    n = 2
    idx = np.indices((16, 16)).sum(axis=0)
    g = (idx % 2).astype(np.int64)
    res = dominant_active_period(g, n, window=20, active_frac=0.9)
    assert res["active_fraction"] == pytest.approx(1.0)
    assert res["median_return_period"] == pytest.approx(2.0)


def test_dominant_active_period_no_active_cells_on_frozen_grid():
    # A uniform grid never changes -> no active cells -> NaN period, zero active fraction.
    n = 5
    g = np.full((12, 12), 3, dtype=np.int64)
    res = dominant_active_period(g, n, window=15)
    assert res["n_active"] == 0
    assert np.isnan(res["median_return_period"])
    assert res["active_fraction"] == 0.0


# -- invalid params -----------------------------------------------------------

def test_invalid_params_raise():
    with pytest.raises(ValueError):
        random_grid(0, 8)
    with pytest.raises(ValueError):
        random_grid(16, 1)                   # need >= 2 colours
    with pytest.raises(ValueError):
        run(random_grid(8, 4, seed=0), 4, -1)
    with pytest.raises(ValueError):
        change_fraction_series(random_grid(8, 4, seed=0), 4, -1)


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_evolution():
    a = run_single(L=48, n=8, steps=60, seed=11, period_window=20)
    b = run_single(L=48, n=8, steps=60, seed=11, period_window=20)
    assert a["change_fraction"] == b["change_fraction"]
    assert a["tail_mean_change"] == b["tail_mean_change"]
    assert a["median_return_period"] == b["median_return_period"]


def test_random_grid_same_seed_identical_field():
    g1 = random_grid(64, 8, seed=7)
    g2 = random_grid(64, 8, seed=7)
    assert np.array_equal(g1, g2)


def test_different_seed_differs():
    a = run_single(L=48, n=8, steps=60, seed=1, period_window=20)
    b = run_single(L=48, n=8, steps=60, seed=2, period_window=20)
    # different seeded initial field -> the activity series differs somewhere.
    assert a["change_fraction"] != b["change_fraction"]
