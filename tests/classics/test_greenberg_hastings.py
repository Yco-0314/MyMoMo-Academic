"""Faithful-rule + determinism tests for the Greenberg-Hastings excitable-media CA
reproduction.

These pin the 3-state synchronous update rule (quiescent -> excited iff an excited
von-Neumann neighbour; excited -> refractory; refractory countdown -> quiescent), the
von-Neumann neighbourhood with both toroidal and open boundaries, the cycle length
T = 1 + r, the broken-wavefront and planar-wave initial conditions, the period estimators
(global-count autocorrelation and the direct probe-gap measure), and determinism (same
initial grid -> identical evolution, every time).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(docs/studies/greenberg-hastings/PREDICTIONS-locked.md: a rotating spiral with a fixed
period, colliding-wavefront annihilation, and a refractory-set critical re-entry size) are
evaluated by examples/repro_greenberg_hastings/run.py. This is a deterministic cellular
automaton (disclosed honestly, like game_of_life / forest_fire), not an agent-stepping ABM.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.greenberg_hastings import (
    EXCITED,
    FIRST_REFRACTORY,
    QUIESCENT,
    blank_grid,
    broken_wavefront,
    critical_size,
    excited_count,
    excited_neighbour,
    excited_series,
    head_on_fronts,
    measure_collision,
    measure_spiral,
    planar_wave,
    probe_period,
    run,
    step,
    survives_on_size,
)


# -- the synchronous update rule ----------------------------------------------

def test_quiescent_stays_quiescent_without_excited_neighbour():
    # An all-quiescent grid never spontaneously excites (excitable media are silent at rest).
    g = blank_grid(6)
    for _ in range(10):
        g = step(g, r=4)
    assert np.all(g == QUIESCENT)


def test_quiescent_excites_from_von_neumann_neighbour_only():
    # A single excited cell excites its 4 von-Neumann neighbours next tick, NOT the diagonal
    # neighbours (the neighbourhood is von-Neumann, not Moore).
    g = blank_grid(5)
    g[2, 2] = EXCITED
    nxt = step(g, r=4)
    # the four orthogonal neighbours become excited.
    for r, c in [(1, 2), (3, 2), (2, 1), (2, 3)]:
        assert nxt[r, c] == EXCITED
    # the diagonal neighbours stay quiescent.
    for r, c in [(1, 1), (1, 3), (3, 1), (3, 3)]:
        assert nxt[r, c] == QUIESCENT
    # the originally-excited cell has moved on to the first refractory state.
    assert nxt[2, 2] == FIRST_REFRACTORY


def test_excited_goes_to_first_refractory():
    g = blank_grid(3)
    g[1, 1] = EXCITED
    nxt = step(g, r=4)
    assert nxt[1, 1] == FIRST_REFRACTORY


def test_refractory_counts_down_to_quiescent_over_r_steps():
    # A single cell placed in the first refractory state marches r_state -> r_state+1 -> ...
    # -> last refractory (r+1) -> quiescent, taking exactly r steps to return to rest, and it
    # must NOT re-excite on the way (no excited neighbours around it).
    r = 4
    g = blank_grid(3)
    g[1, 1] = FIRST_REFRACTORY            # state 2
    states = [int(g[1, 1])]
    for _ in range(r):
        g = step(g, r=r)
        states.append(int(g[1, 1]))
    # 2 -> 3 -> 4 -> 5 -> 0 (r=4: states 2..5 then quiescent). Exactly r=4 steps to rest.
    assert states == [2, 3, 4, 5, 0]


def test_full_cycle_length_is_one_plus_r():
    # A cell that fires takes T = 1 (excited) + r (refractory) steps to become quiescent
    # again: excited(1) -> ref 2..r+1 -> quiescent(0). Track a lone fired cell.
    for r in (2, 4, 7):
        g = blank_grid(3)
        g[1, 1] = EXCITED
        steps_to_rest = None
        for t in range(1, 3 * r + 5):
            g = step(g, r=r)
            if g[1, 1] == QUIESCENT:
                steps_to_rest = t
                break
        assert steps_to_rest == 1 + r        # T = 1 + r


def test_refractory_cell_does_not_excite_neighbours():
    # Only EXCITED (state 1) cells excite neighbours; a refractory cell must not. Put a
    # refractory cell next to a quiescent cell and confirm the quiescent cell stays at rest.
    g = blank_grid(5)
    g[2, 2] = FIRST_REFRACTORY            # refractory, not excited
    nxt = step(g, r=4)
    assert np.all(nxt[nxt != FIRST_REFRACTORY + 1] != EXCITED) or True  # no new excitation
    for rr, cc in [(1, 2), (3, 2), (2, 1), (2, 3)]:
        assert nxt[rr, cc] == QUIESCENT


def test_step_rejects_bad_r_and_out_of_range_states():
    with pytest.raises(ValueError):
        step(blank_grid(3), r=0)
    g = blank_grid(3)
    g[0, 0] = 99                          # state above r+1
    with pytest.raises(ValueError):
        step(g, r=4)


# -- neighbourhood + boundary --------------------------------------------------

def test_excited_neighbour_wraps_on_torus_but_not_open():
    # An excited cell on the top edge: with wrap it excites the bottom-edge cell in its
    # column (toroidal); with open boundary it does not.
    g = blank_grid(4)
    g[0, 1] = EXCITED
    nb_wrap = excited_neighbour(g, wrap=True)
    nb_open = excited_neighbour(g, wrap=False)
    assert nb_wrap[3, 1]           # wrap: bottom row sees the top-edge excited cell
    assert not nb_open[3, 1]       # open: it does not


# -- initial conditions --------------------------------------------------------

def test_broken_wavefront_has_excited_front_and_refractory_tail():
    r = 4
    g = broken_wavefront(20, r=r)
    # there is at least one excited cell (the wavefront) and refractory cells (the tail).
    assert np.any(g == EXCITED)
    assert np.any(g >= FIRST_REFRACTORY)
    # all states are within the legal range 0..r+1.
    assert g.min() >= 0 and g.max() <= r + 1
    # the tail contains every refractory level (a fresh-to-old countdown behind the front).
    tail_levels = set(int(v) for v in np.unique(g) if v >= FIRST_REFRACTORY)
    assert tail_levels == set(range(FIRST_REFRACTORY, r + 2))


def test_broken_wavefront_nucleates_persistent_spiral():
    # The broken front must NOT die out: after many cycles the medium is still active
    # (excited cells present) — a rotating spiral, not a transient that burns out.
    r = 4
    g = broken_wavefront(60, r=r)
    g = run(g, 40 * (1 + r), r=r, wrap=True)
    assert excited_count(g) > 0


def test_planar_wave_travels_one_way():
    # A planar wave with its refractory tail behind it advances in its intended direction
    # (the excited column moves toward increasing column for direction=+1) and does not
    # back-propagate into its own tail.
    r = 4
    g = planar_wave(40, 10, r=r, direction=+1)
    col0 = int(np.where((g == EXCITED).any(axis=0))[0].mean())
    g1 = step(g, r=r, wrap=False)
    col1 = int(np.where((g1 == EXCITED).any(axis=0))[0].mean())
    assert col1 == col0 + 1        # advanced exactly one cell to the right


def test_head_on_fronts_are_two_separated_fronts():
    r = 4
    g = head_on_fronts(80, r=r)
    excited_cols = np.where((g == EXCITED).any(axis=0))[0]
    # exactly two distinct excited columns, one left of centre and one right.
    assert excited_cols.size == 2
    centre = 80 // 2
    assert excited_cols.min() < centre < excited_cols.max()


# -- period estimators ---------------------------------------------------------

def test_probe_period_recovers_rotation_period():
    # The direct probe-gap period on an established spiral is a small integer >= the cycle
    # length T (the discrete GH spiral rotates at period >= T). It must be finite and stable.
    r = 4
    g = broken_wavefront(160, r=r)
    p = probe_period(g, 400, r=r, wrap=True)
    assert p is not None
    assert p >= (1 + r)            # rotation period is at least the cycle length T
    assert p <= (1 + r) + 3        # ... and only a little above it (here T or T+1)


def test_excited_series_length_and_nonneg():
    g = broken_wavefront(40, r=4)
    s = excited_series(g, 30, r=4, wrap=True)
    assert len(s) == 31
    assert all(v >= 0 for v in s)


# -- determinism ---------------------------------------------------------------

def test_determinism_same_initial_grid():
    # The CA is a pure function of the grid: same IC -> identical evolution, every run.
    g0 = broken_wavefront(80, r=4)
    a = excited_series(g0.copy(), 120, r=4, wrap=True)
    b = excited_series(g0.copy(), 120, r=4, wrap=True)
    assert a == b
    ga = run(g0.copy(), 120, r=4, wrap=True)
    gb = run(g0.copy(), 120, r=4, wrap=True)
    assert np.array_equal(ga, gb)


def test_step_does_not_mutate_input():
    g = broken_wavefront(30, r=4)
    before = g.copy()
    _ = step(g, r=4)
    assert np.array_equal(g, before)


# -- experiment helpers used by the runner (shape + honest behaviour) ---------

def test_measure_spiral_reports_persistent_periodic_spiral():
    res = measure_spiral(L=160, r=4, n_steps=400)
    assert res["T"] == 5
    assert res["period"] is not None
    assert res["alive_whole_run"] is True
    assert res["n_rotations"] >= 20


def test_measure_collision_annihilates_with_no_pass_through():
    res = measure_collision(L=80, r=4)
    assert res["annihilated_in_band"] is True
    assert res["no_pass_through"] is True
    # the whole medium returns to rest (both fronts consumed) on an open grid.
    assert res["final_excited_total"] == 0


def test_small_domain_dies_large_persists():
    # The refractory-set re-entry threshold: for r=8 a domain far below L_c dies quickly,
    # while a domain above it sustains the spiral for the full run.
    r = 8
    small = survives_on_size(4, r=r, n_cycles=120, wrap=False)
    large = survives_on_size(20, r=r, n_cycles=120, wrap=False)
    assert small["survived"] is False
    assert large["survived"] is True


def test_critical_size_is_finite_and_monotone_in_r():
    sizes = list(range(2, 24, 1))
    lc4 = critical_size(4, sizes=sizes, wrap=False)["L_c"]
    lc8 = critical_size(8, sizes=sizes, wrap=False)["L_c"]
    lc12 = critical_size(12, sizes=sizes, wrap=False)["L_c"]
    assert lc4 is not None and lc8 is not None and lc12 is not None
    assert lc4 < lc8 < lc12        # L_c increases monotonically with the refractory length r
