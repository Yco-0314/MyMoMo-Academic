"""Faithful-rule + determinism tests for the Sugarscape (Epstein-Axtell 1996)
reproduction.

These pin the metrics (Gini / top-decile / median on hand-computed inputs), the
toroidal von-Neumann movement-and-harvest rule M, the metabolism/death rule, the
two regrow rules (G1 +1/tick and G_infinity instant), the two-peak landscape, and
determinism (same seed -> identical run; different seeds differ). They are
faithfulness tests, NOT prediction tests (the locked P1-P3 are evaluated by
examples/repro_sugarscape/run.py).
"""
from __future__ import annotations

from abm_auto.classics.sugarscape import (
    SugarAgent,
    SugarscapeModel,
    classic_two_peak_capacity,
    gini,
    median,
    run_many_seeds,
    run_single,
    top_decile_share,
)


# -- pure metrics: hand-computable -------------------------------------------

def test_gini_equal_is_zero_and_extreme_is_high():
    assert gini([5, 5, 5, 5]) == 0.0            # perfect equality
    assert gini([]) == 0.0
    assert gini([0, 0, 0]) == 0.0               # all-zero -> undefined -> 0
    # One agent holds everything (n=10): Gini -> (n-1)/n = 0.9.
    one_hot = [0] * 9 + [100]
    assert abs(gini(one_hot) - 0.9) < 1e-9


def test_gini_two_agents_one_one_zero_is_half():
    # Classic two-person case: {0, x} has Gini = 0.5.
    assert abs(gini([0, 10]) - 0.5) < 1e-9


def test_top_decile_share_and_median():
    # 10 agents, richest holds 100, rest 0 -> top decile (1 agent) = 100% share.
    vals = [0] * 9 + [100]
    assert abs(top_decile_share(vals) - 1.0) < 1e-9
    # 20 agents: top decile = 2 richest.
    vals2 = list(range(1, 21))            # 1..20, total 210; top 2 = 20+19 = 39
    assert abs(top_decile_share(vals2) - 39 / 210) < 1e-9
    assert median([1, 2, 3]) == 2
    assert median([1, 2, 3, 4]) == 2.5
    assert median([]) == 0.0


# -- the two-peak landscape ---------------------------------------------------

def test_two_peak_capacity_shape_and_bounds():
    cap = classic_two_peak_capacity(50, 50, peak=4)
    assert len(cap) == 50 and all(len(row) == 50 for row in cap)
    flat = [v for row in cap for v in row]
    assert min(flat) >= 0 and max(flat) == 4          # terraces 0..peak
    # The two peak centres sit at capacity == peak.
    assert cap[round(0.25 * 50)][round(0.25 * 50)] == 4
    assert cap[round(0.75 * 50)][round(0.75 * 50)] == 4
    # There really are two distinct high regions (not one blob): plenty of cells
    # at capacity, and plenty at 0 (between/around the mountains).
    assert sum(1 for v in flat if v == 4) >= 2
    assert sum(1 for v in flat if v == 0) > 0


# -- construction: distinct cells, attribute ranges ---------------------------

def test_construction_places_distinct_agents_in_ranges():
    m = SugarscapeModel(nrows=50, ncols=50, n_agents=250, seed=0)
    assert m.population() == 250
    cells = [a.cell for a in m.living]
    assert len(set(cells)) == 250                      # all on distinct cells
    for a in m.living:
        assert 1 <= a.vision <= 6
        assert 1 <= a.metabolism <= 4
        assert 5 <= a.sugar <= 25
        assert m.grid[a.cell[0]][a.cell[1]] is a       # grid agrees with agent


# -- rule M: von-Neumann, nearest-max-sugar, harvest --------------------------

def _bare_model(nrows, ncols, regrow=1, peak=4):
    """A model with NO auto-placed agents (n_agents=0) and a hand-set sugarscape."""
    m = SugarscapeModel(nrows=nrows, ncols=ncols, n_agents=0, regrow=regrow,
                        peak=peak, seed=0)
    assert m.population() == 0
    # zero out the landscape so we can set specific cells by hand.
    m.capacity = [[0] * ncols for _ in range(nrows)]
    m.sugar = [[0] * ncols for _ in range(nrows)]
    return m


def _place(m, agent_id, cell, *, vision=1, metabolism=1, sugar=10):
    a = SugarAgent(agent_id, m, cell=cell, vision=vision, metabolism=metabolism,
                   sugar=sugar)
    m.grid[cell[0]][cell[1]] = a
    m.agent_by_id[agent_id] = a
    m.living.append(a)
    return a


def test_move_to_max_sugar_along_axis_and_harvest():
    m = _bare_model(1, 7)
    a = _place(m, 0, (0, 3), vision=3, metabolism=1, sugar=10)
    # Put sugar to the east at distance 2; everything else 0.
    m.sugar[0][5] = 7
    target = a.best_site()
    assert target == (0, 5)
    a.step()
    assert a.cell == (0, 5)
    assert a.sugar == 10 + 7 - 1                       # harvested 7, paid metab 1
    assert m.sugar[0][5] == 0                          # cell emptied
    assert m.grid[0][3] is None and m.grid[0][5] is a  # grid moved


def test_diagonal_sugar_is_ignored_von_neumann_only():
    m = _bare_model(3, 3)
    a = _place(m, 0, (1, 1), vision=2, metabolism=0, sugar=10)
    m.sugar[0][0] = 9          # diagonal, must be invisible to rule M
    target = a.best_site()
    assert target == (1, 1)    # no axial sugar -> stay put (own cell is max at 0)
    a.step()
    assert a.cell == (1, 1)


def test_ties_broken_by_nearest_then_direction_order():
    m = _bare_model(1, 7)
    a = _place(m, 0, (0, 3), vision=3, metabolism=0, sugar=10)
    # Equal sugar east at dist 1 and west at dist 2 -> nearest (east, dist1) wins.
    m.sugar[0][4] = 5
    m.sugar[0][1] = 5
    assert a.best_site() == (0, 4)


def test_cannot_move_onto_occupied_cell():
    m = _bare_model(1, 5)
    a = _place(m, 0, (0, 2), vision=2, metabolism=0, sugar=10)
    _place(m, 1, (0, 4), vision=1, metabolism=0, sugar=10)
    m.sugar[0][4] = 50         # most sugar is on an occupied cell -> unreachable
    m.sugar[0][0] = 3
    assert a.best_site() == (0, 0)   # picks the best UNOCCUPIED axial site


def test_toroidal_wrap_in_vision():
    m = _bare_model(1, 5)
    a = _place(m, 0, (0, 0), vision=2, metabolism=0, sugar=10)
    # Sugar one west of col 0 wraps to col 4.
    m.sugar[0][4] = 8
    assert a.best_site() == (0, 4)


# -- metabolism + death -------------------------------------------------------

def test_agent_dies_when_sugar_negative():
    m = _bare_model(1, 3)
    a = _place(m, 0, (0, 1), vision=1, metabolism=5, sugar=2)
    # No sugar anywhere; metabolism 5 > sugar 2 -> sugar goes to -3 -> dies.
    a.step()
    assert a.alive is False
    assert a.sugar == 2 - 5
    assert m.grid[0][1] is None                        # removed from grid


def test_agent_survives_when_sugar_exactly_zero():
    m = _bare_model(1, 3)
    a = _place(m, 0, (0, 1), vision=1, metabolism=2, sugar=2)
    a.step()
    assert a.alive is True                              # 0 is not < 0
    assert a.sugar == 0


# -- regrow rules -------------------------------------------------------------

def test_regrow_g1_adds_one_up_to_capacity():
    m = _bare_model(2, 2, regrow=1)
    m.capacity = [[4, 4], [4, 4]]
    m.sugar = [[0, 3], [4, 1]]
    m.regrow_sugar()
    assert m.sugar == [[1, 4], [4, 2]]                 # +1, clamped at cap


def test_regrow_ginfinity_snaps_to_capacity():
    m = _bare_model(2, 2, regrow=None)
    m.capacity = [[4, 2], [1, 0]]
    m.sugar = [[0, 0], [0, 0]]
    m.regrow_sugar()
    assert m.sugar == [[4, 2], [1, 0]]                 # instant to capacity


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_run():
    a = run_single(nrows=50, ncols=50, n_agents=200, n_steps=40, seed=7)
    b = run_single(nrows=50, ncols=50, n_agents=200, n_steps=40, seed=7)
    assert a["gini_series"] == b["gini_series"]
    assert a["population_series"] == b["population_series"]
    assert a["final_gini"] == b["final_gini"]


def test_different_seeds_differ():
    a = run_single(nrows=50, ncols=50, n_agents=200, n_steps=40, seed=1)
    b = run_single(nrows=50, ncols=50, n_agents=200, n_steps=40, seed=2)
    assert a["gini_series"] != b["gini_series"]


# -- end-to-end run shape -----------------------------------------------------

def test_run_shape_and_series_lengths():
    r = run_single(nrows=50, ncols=50, n_agents=200, n_steps=50, seed=0)
    # series include the t=0 baseline; length = steps + 1.
    assert len(r["gini_series"]) == r["steps"] + 1
    assert len(r["population_series"]) == r["steps"] + 1
    assert r["gini_series"][0] == r["initial_gini"]
    assert r["gini_series"][-1] == r["final_gini"]
    assert 0.0 <= r["initial_gini"] <= 1.0
    assert 0.0 <= r["final_gini"] <= 1.0
    assert r["initial_population"] == 200


def test_run_many_seeds_aggregates():
    out = run_many_seeds([0, 1, 2], nrows=50, ncols=50, n_agents=150, n_steps=30)
    assert len(out["rows"]) == 3
    assert out["rows"][0]["seed"] == 0
    mean_final = sum(r["final_gini"] for r in out["rows"]) / 3
    assert abs(out["mean_final_gini"] - mean_final) < 1e-12
    assert out["min_final_gini"] <= out["mean_final_gini"] <= out["max_final_gini"]
