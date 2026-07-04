"""Faithful-rule + determinism tests for the Schelling (1971) segregation model.

These pin the Moore-8 occupied-neighbour rule, the strict ``< f`` unhappiness
threshold (and its ``>=`` boundary), the documented isolated-agent = happy
convention, the random-empty-cell relocation (grid/empty-set consistency), the
equal-type / vacancy construction, and determinism (same seed -> identical run;
different seeds -> different placements). They are faithfulness tests, NOT
prediction tests (the locked predictions P1-P3 are evaluated by
examples/repro_schelling_segregation/run.py).
"""
from __future__ import annotations

from abm_auto.classics.schelling import (
    ResidentAgent,
    SchellingModel,
    run_many_seeds,
    run_single,
)


# -- construction: equal types, vacancy, grid integrity -----------------------

def test_construction_equal_types_and_vacancy():
    m = SchellingModel(nrows=50, ncols=50, vacancy=0.28, seed=0)
    n_cells = 50 * 50
    assert m.n_empty == round(0.28 * n_cells)             # 700
    assert m.n_occupied == n_cells - m.n_empty            # 1800
    # Two equal-size types (equal here since n_occupied is even).
    assert m.n_type0 == m.n_type1 == m.n_occupied // 2
    # Every agent sits on its claimed cell; every empty cell is truly empty.
    for a in m.agent_by_id.values():
        r, c = a.cell
        assert m.grid[r][c] is a
    assert len(m.empty_cells) == m.n_empty
    for (r, c) in m.empty_cells:
        assert m.grid[r][c] is None
    # Occupied + empty exactly tile the grid, no overlap.
    occupied_cells = {a.cell for a in m.agent_by_id.values()}
    assert len(occupied_cells) == m.n_occupied
    assert occupied_cells.isdisjoint(m.empty_cells)
    assert len(occupied_cells) + len(m.empty_cells) == n_cells


def test_odd_occupancy_gives_type0_the_extra_agent():
    # 3x3 grid, vacancy small enough to leave an odd occupied count.
    m = SchellingModel(nrows=3, ncols=3, vacancy=2.0 / 9.0, seed=1)  # 7 occupied
    assert m.n_occupied == 7
    assert m.n_type0 == 4 and m.n_type1 == 3                # extra goes to type 0


# -- the Moore-8 occupied-neighbour rule, hand-built ---------------------------

def _empty_model(nrows, ncols):
    """A model with NO auto-placement (vacancy=1.0) we can populate by hand."""
    m = SchellingModel(nrows=nrows, ncols=ncols, vacancy=1.0, seed=0)
    # vacancy=1.0 -> 0 occupied; start from a fully-empty, consistent grid.
    assert m.n_occupied == 0
    return m


def _place(m, agent_id, cell, type_):
    a = ResidentAgent(agent_id, m, cell=cell, type_=type_)
    r, c = cell
    m.grid[r][c] = a
    m.empty_cells.discard(cell)
    m.agent_by_id[agent_id] = a
    return a


def test_moore8_counts_only_occupied_neighbours():
    m = _empty_model(3, 3)
    centre = _place(m, 0, (1, 1), 0)
    # Two like (type 0) + one unlike (type 1) neighbours; rest empty.
    _place(m, 1, (0, 0), 0)
    _place(m, 2, (0, 1), 0)
    _place(m, 3, (2, 2), 1)
    nbrs = centre.occupied_neighbors()
    assert len(nbrs) == 3                                   # empties excluded
    assert abs(centre.same_type_fraction() - 2.0 / 3.0) < 1e-9


def test_isolated_agent_is_happy_and_contributes_zero():
    m = _empty_model(3, 3)
    lone = _place(m, 0, (1, 1), 0)
    assert lone.occupied_neighbors() == []
    assert lone.same_type_fraction() == 0.0                 # no like-neighbours
    assert lone.is_happy() is True                          # but happy (convention)
    assert m.unhappy_count() == 0


def test_unhappiness_is_strict_less_than_f_boundary():
    # f = 1/3. An agent with exactly 1/3 same-type is HAPPY (>=); below is unhappy.
    m = _empty_model(1, 7)
    # Row layout (col): [me=0][unlike][unlike] -> 0/2 same => unhappy.
    me = _place(m, 0, (0, 1), 0)
    _place(m, 1, (0, 0), 1)
    _place(m, 2, (0, 2), 1)
    assert me.same_type_fraction() == 0.0
    assert me.is_happy() is False                           # 0.0 < 1/3

    # Now exactly 1/3: 1 like + 2 unlike among 3 occupied neighbours.
    m2 = _empty_model(3, 3)
    c = _place(m2, 0, (1, 1), 0)
    _place(m2, 1, (0, 0), 0)                                # 1 like
    _place(m2, 2, (0, 1), 1)
    _place(m2, 3, (0, 2), 1)                                # 2 unlike
    assert abs(c.same_type_fraction() - 1.0 / 3.0) < 1e-9
    assert c.is_happy() is True                             # 1/3 >= 1/3 (boundary)


def test_f_threshold_is_configurable():
    m = SchellingModel(nrows=3, ncols=3, vacancy=1.0, seed=0, f=0.5)
    c = _place(m, 0, (1, 1), 0)
    _place(m, 1, (0, 0), 0)                                 # 1 like
    _place(m, 2, (0, 1), 1)                                 # 1 unlike => 1/2 same
    assert c.same_type_fraction() == 0.5
    assert c.is_happy() is True                             # 0.5 >= f=0.5
    m.f = 0.6
    assert c.is_happy() is False                            # 0.5 < 0.6


# -- relocation keeps grid + empty-set consistent ------------------------------

def test_relocate_moves_agent_and_keeps_grid_consistent():
    m = SchellingModel(nrows=5, ncols=5, vacancy=0.5, seed=3)
    a = next(iter(m.agent_by_id.values()))
    old = a.cell
    n_empty_before = len(m.empty_cells)
    m.relocate(a)
    new = a.cell
    assert new != old
    assert m.grid[old[0]][old[1]] is None                  # old cell vacated
    assert m.grid[new[0]][new[1]] is a                      # new cell occupied
    assert old in m.empty_cells                             # old now empty
    assert new not in m.empty_cells                         # target consumed
    assert len(m.empty_cells) == n_empty_before             # count preserved


def test_relocate_noop_when_grid_full():
    m = SchellingModel(nrows=2, ncols=2, vacancy=0.0, seed=0)
    assert len(m.empty_cells) == 0
    a = next(iter(m.agent_by_id.values()))
    cell = a.cell
    m.relocate(a)
    assert a.cell == cell                                   # nothing to move to


# -- end-to-end run shape + convergence ---------------------------------------

def test_run_converges_and_raises_segregation():
    r = run_single(nrows=30, ncols=30, vacancy=0.28, seed=0, max_steps=200)
    assert r["final_unhappy"] == 0 or r["steps"] == 200    # stable or capped
    assert r["final_segregation"] > r["initial_segregation"]
    assert 0.45 <= r["initial_segregation"] <= 0.55        # random baseline ~0.5
    # series include the t=0 baseline; length = steps + 1.
    assert len(r["same_fraction_series"]) == r["steps"] + 1
    assert len(r["unhappy_series"]) == r["steps"] + 1
    assert r["same_fraction_series"][0] == r["initial_segregation"]


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_run():
    a = run_single(nrows=30, ncols=30, seed=7)
    b = run_single(nrows=30, ncols=30, seed=7)
    assert a["initial_segregation"] == b["initial_segregation"]
    assert a["final_segregation"] == b["final_segregation"]
    assert a["same_fraction_series"] == b["same_fraction_series"]
    assert a["unhappy_series"] == b["unhappy_series"]
    assert a["steps"] == b["steps"]


def test_different_seeds_differ():
    a = run_single(nrows=30, ncols=30, seed=1)
    b = run_single(nrows=30, ncols=30, seed=2)
    # Different random placements -> different initial layouts (vanishingly
    # unlikely to coincide).
    assert a["same_fraction_series"] != b["same_fraction_series"]


def test_run_many_seeds_aggregates():
    out = run_many_seeds([0, 1, 2], nrows=30, ncols=30)
    assert len(out["rows"]) == 3
    assert out["rows"][0]["seed"] == 0
    # Cross-seed means are the average of the per-seed numbers.
    mean_init = sum(r["initial_segregation"] for r in out["rows"]) / 3
    mean_fin = sum(r["final_segregation"] for r in out["rows"]) / 3
    assert abs(out["mean_initial_segregation"] - mean_init) < 1e-12
    assert abs(out["mean_final_segregation"] - mean_fin) < 1e-12
