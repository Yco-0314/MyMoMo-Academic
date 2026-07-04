"""Faithful-rule + determinism tests for the Conway's Game of Life (B3/S23) reproduction.

These pin the synchronous B3/S23 transition (birth on exactly 3 live Moore-8 neighbours,
survival on 2 or 3, death otherwise), the toroidal wrap, the canonical pattern catalogue
(glider / blinker / block / beacon), and the period+translation detector. They are
faithfulness tests, NOT prediction tests (the locked predictions P1-P3 are evaluated by
examples/repro_game_of_life/run.py).

NOTE: this is a DETERMINISTIC CELLULAR AUTOMATON, not an agent-stepping ABM — there is no
scheduler / agent roster to test, only the synchronous transition rule. There is no
randomness, so the tests assert EXACT outcomes (no seeding / tolerance).
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.game_of_life import (
    ALIVE,
    BEACON,
    BLINKER,
    BLOCK,
    DEAD,
    GLIDER,
    blank_grid,
    detect_period,
    history,
    live_count,
    live_count_series,
    live_neighbour_counts,
    place_pattern,
    run,
    step,
)
from examples.repro_game_of_life.run import measure, verdicts_for


# -- transition rule: B3/S23 --------------------------------------------------

def test_empty_grid_stays_empty():
    g = blank_grid(8)
    assert live_count(step(g)) == 0


def test_lonely_cell_dies():
    # A single live cell has 0 neighbours -> dies (under-population).
    g = blank_grid(5)
    g[2, 2] = ALIVE
    assert step(g)[2, 2] == DEAD
    assert live_count(step(g)) == 0


def test_birth_on_exactly_three_neighbours():
    # An empty cell with exactly 3 live neighbours is born (B3). Place 3 live cells in an
    # L around an empty centre.
    g = blank_grid(5)
    g[1, 2] = ALIVE
    g[2, 1] = ALIVE
    g[2, 3] = ALIVE
    # cell (2,2) is dead with exactly 3 live neighbours -> born.
    assert live_neighbour_counts(g)[2, 2] == 3
    assert step(g)[2, 2] == ALIVE


def test_no_birth_on_two_or_four_neighbours():
    # 2 neighbours: no birth.
    g2 = blank_grid(5)
    g2[2, 1] = ALIVE
    g2[2, 3] = ALIVE
    assert live_neighbour_counts(g2)[2, 2] == 2
    assert step(g2)[2, 2] == DEAD
    # 4 neighbours: no birth (overcrowding for a dead cell, B is only 3).
    g4 = blank_grid(5)
    g4[1, 2] = ALIVE
    g4[3, 2] = ALIVE
    g4[2, 1] = ALIVE
    g4[2, 3] = ALIVE
    assert live_neighbour_counts(g4)[2, 2] == 4
    assert step(g4)[2, 2] == DEAD


def test_survival_on_two_or_three_neighbours():
    # A live cell with 2 neighbours survives (S2).
    g = blank_grid(5)
    g[2, 2] = ALIVE
    g[2, 1] = ALIVE
    g[2, 3] = ALIVE
    assert live_neighbour_counts(g)[2, 2] == 2
    assert step(g)[2, 2] == ALIVE


def test_death_on_overcrowding():
    # A live cell with 4 live neighbours dies (S is only 2 or 3).
    g = blank_grid(5)
    g[2, 2] = ALIVE
    g[1, 2] = ALIVE
    g[3, 2] = ALIVE
    g[2, 1] = ALIVE
    g[2, 3] = ALIVE
    assert live_neighbour_counts(g)[2, 2] == 4
    assert step(g)[2, 2] == DEAD


def test_neighbour_count_is_moore8():
    # A fully-surrounded centre cell has 8 live neighbours (the cell itself excluded).
    g = np.ones((3, 3), dtype=np.int64)
    assert live_neighbour_counts(g)[1, 1] == 8


def test_neighbour_count_wraps_toroidally():
    # A single live cell at the corner contributes to the diagonally-opposite corner's
    # neighbour count via wrap-around.
    g = blank_grid(4)
    g[0, 0] = ALIVE
    nc = live_neighbour_counts(g)
    # (0,0)'s Moore-8 neighbours on a torus include the opposite corner (3,3).
    assert nc[3, 3] == 1
    assert nc[0, 1] == 1
    assert nc[1, 0] == 1


# -- determinism / purity -----------------------------------------------------

def test_step_does_not_mutate_input():
    g = place_pattern(GLIDER, 10)
    before = g.copy()
    step(g)
    assert np.array_equal(g, before)


def test_run_is_deterministic_and_matches_repeated_step():
    g = place_pattern(GLIDER, 20)
    a = run(g, 7)
    # repeated single steps must give the identical grid (no randomness anywhere).
    b = g.copy()
    for _ in range(7):
        b = step(b)
    assert np.array_equal(a, b)
    # and a second run is bit-identical.
    assert np.array_equal(run(g, 7), a)


def test_run_zero_is_identity():
    g = place_pattern(BEACON, 12)
    assert np.array_equal(run(g, 0), g)


def test_run_rejects_negative():
    with pytest.raises(ValueError):
        run(blank_grid(5), -1)


# -- canonical pattern catalogue ----------------------------------------------

def test_block_is_still_life():
    # The block (2x2) is unchanged every generation: period 1, zero translation,
    # live-cell count conserved at 4.
    g = place_pattern(BLOCK, 10)
    assert live_count(g) == 4
    one = step(g)
    assert np.array_equal(one, g)  # truly unchanged
    res = detect_period(g)
    assert res["period"] == 1
    assert res["translation"] == (0, 0)
    assert live_count_series(g, 5) == [4, 4, 4, 4, 4, 4]


def test_blinker_period_two():
    # The blinker oscillates with period 2 and does not translate; live-cell count is
    # conserved at 3 (a 3-in-a-row flips horizontal<->vertical).
    g = place_pattern(BLINKER, 11)
    assert live_count(g) == 3
    res = detect_period(g)
    assert res["period"] == 2
    assert res["translation"] == (0, 0)
    assert not np.array_equal(step(g), g)        # actually changes after 1 gen
    assert np.array_equal(run(g, 2), g)          # returns after 2 gens
    assert live_count_series(g, 4) == [3, 3, 3, 3, 3]


def test_locked_p3_misses_because_blinker_live_count_is_constant():
    measured = measure()
    verdicts = verdicts_for(measured)
    assert measured["blinker"]["live_count_series_one_period"] == [3, 3, 3]
    assert verdicts[2].passed is False
    assert "blinker count series=[3, 3, 3]" in verdicts[2].reasons[0]


def test_beacon_period_two():
    # The beacon oscillates with period 2; its live-cell count oscillates 6 <-> 8.
    g = place_pattern(BEACON, 12)
    res = detect_period(g)
    assert res["period"] == 2
    assert res["translation"] == (0, 0)
    assert np.array_equal(run(g, 2), g)
    series = live_count_series(g, 4)
    # period-2 oscillation in the count: same every other generation.
    assert series[0] == series[2] == series[4]
    assert series[1] == series[3]
    assert series[0] != series[1]  # genuinely oscillates


def test_glider_period_four_translates_diagonally():
    # The glider is a period-4 diagonal spaceship: after 4 generations it returns to the
    # GLIDER shape translated by exactly (+1, +1). Live-cell count is conserved at 5.
    L = 40
    g = place_pattern(GLIDER, L, offset=(2, 2))
    assert live_count(g) == 5
    res = detect_period(g, max_period=8)
    assert res["period"] == 4
    assert res["translation"] == (1, 1)
    assert res["live_count"] == 5
    # After 4 gens the grid equals the glider re-stamped one cell down+right.
    moved = place_pattern(GLIDER, L, offset=(3, 3))
    assert np.array_equal(run(g, 4), moved)
    # count conserved throughout one full period.
    assert live_count_series(g, 4) == [5, 5, 5, 5, 5]


def test_glider_returns_to_origin_after_full_diagonal_loop():
    # On an L x L torus the glider returns to its EXACT original cells after 4*L gens
    # (it has crossed the whole torus diagonally). A strong end-to-end determinism +
    # wrap check.
    L = 16
    g = place_pattern(GLIDER, L, offset=(0, 0))
    assert np.array_equal(run(g, 4 * L), g)


# -- detector edge cases ------------------------------------------------------

def test_detect_period_returns_none_for_empty():
    assert detect_period(blank_grid(6)) is None


def test_history_length_and_first_frame():
    g = place_pattern(BLINKER, 9)
    frames = history(g, 3)
    assert len(frames) == 4
    assert np.array_equal(frames[0], g)
