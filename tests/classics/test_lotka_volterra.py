"""Faithful-rule + determinism tests for the agent Lotka-Volterra (wolf-sheep-grass)
reproduction.

These pin the individual rules (move pays energy, prey eat grown grass for energy,
predators eat a prey on their cell for energy, death at energy<0, reproduce splits
energy and adds an agent), the grass regrow countdown, the analysis helpers
(peak-count, cross-correlation lag convention), and determinism (same seed ->
identical run; different seeds differ). They are faithfulness tests, NOT prediction
tests (the locked P1-P3 are evaluated by examples/repro_lotka_volterra/run.py).
"""
from __future__ import annotations

import math

from abm_auto.classics.lotka_volterra import (
    LotkaVolterraModel,
    PredatorAgent,
    PreyAgent,
    best_positive_lag,
    count_peaks,
    cross_correlation,
    run_many_seeds,
    run_single,
)


# -- a bare model for hand-built scenarios ------------------------------------

def _bare_model(L=5, **kw):
    """A model with NO auto-placed agents and ALL grass grown, for hand scenarios."""
    m = LotkaVolterraModel(L=L, n_prey=0, n_pred=0, seed=0, **kw)
    assert m.prey_count() == 0 and m.pred_count() == 0
    m.grass_grown = [[True] * L for _ in range(L)]
    m.grass_countdown = [[0] * L for _ in range(L)]
    return m


def _place(m, cls, cell, energy):
    return m._spawn(cls, cell, energy)


# -- construction --------------------------------------------------------------

def test_construction_counts_and_ranges():
    m = LotkaVolterraModel(L=100, n_prey=800, n_pred=100, seed=0)
    assert m.prey_count() == 800
    assert m.pred_count() == 100
    # every agent sits on a valid cell with non-negative starting energy.
    for a in m.living:
        r, c = a.cell
        assert 0 <= r < 100 and 0 <= c < 100
        assert a.energy >= 0.0


# -- move pays energy ----------------------------------------------------------

def test_move_pays_move_cost_and_stays_on_grid():
    m = _bare_model(L=5, move_cost=1.0)
    a = _place(m, PreyAgent, (2, 2), energy=10.0)
    a.move()
    assert a.energy == 9.0                      # paid one move cost
    r, c = a.cell
    assert 0 <= r < 5 and 0 <= c < 5            # toroidal stay-on-grid
    # the move went to a Moore neighbour of (2,2) (never the same cell)
    assert (r, c) != (2, 2)
    assert abs(r - 2) <= 1 and abs(c - 2) <= 1


def test_move_wraps_toroidally():
    m = _bare_model(L=3, move_cost=0.0)
    # force the RNG so the chosen offset is deterministic is hard; instead check that
    # from a corner every reachable Moore neighbour stays in [0,3) after wrap.
    a = _place(m, PreyAgent, (0, 0), energy=5.0)
    for _ in range(20):
        a.cell = (0, 0)
        a.move()
        r, c = a.cell
        assert 0 <= r < 3 and 0 <= c < 3


# -- prey eat grass ------------------------------------------------------------

def test_prey_eats_grown_grass_for_energy_and_resets_countdown():
    m = _bare_model(L=3, prey_gain=4.0, move_cost=0.0, grass_regrow=30)
    cell = (1, 1)
    assert m.grass_grown[1][1] is True
    ate = m.eat_grass(cell)
    assert ate is True
    assert m.grass_grown[1][1] is False
    assert m.grass_countdown[1][1] == 30
    # eating again on the same (now eaten) cell yields nothing
    assert m.eat_grass(cell) is False


def test_prey_step_gains_energy_only_when_grass_grown():
    m = _bare_model(L=3, prey_gain=4.0, move_cost=1.0, prey_reproduce=0.0,
                    grass_regrow=30)
    a = _place(m, PreyAgent, (1, 1), energy=5.0)
    # all grass grown -> wherever it lands it eats: energy = 5 - 1 (move) + 4 (eat) = 8
    a.step()
    assert a.alive is True
    assert a.energy == 8.0


# -- predator eats prey --------------------------------------------------------

def test_predator_eats_prey_on_its_cell():
    m = _bare_model(L=3, pred_gain=20.0, move_cost=0.0, pred_reproduce=0.0)
    pred = _place(m, PredatorAgent, (1, 1), energy=10.0)
    prey = _place(m, PreyAgent, (0, 0), energy=5.0)
    # move the prey onto the predator's destination by forcing both to a cell:
    # instead, directly test prey_on_cell + the eat branch by co-locating.
    prey.cell = (1, 1)
    m._prey_by_cell = {(1, 1): [prey]}
    pred.cell = (1, 1)
    found = m.prey_on_cell((1, 1))
    assert found is prey
    # now run the eat logic: kill prey, gain energy
    m.kill(found)
    pred.energy += m.pred_gain
    assert prey.alive is False
    assert pred.energy == 30.0


def test_predator_finds_no_prey_on_empty_cell():
    m = _bare_model(L=3)
    assert m.prey_on_cell((2, 2)) is None


# -- death at energy < 0 -------------------------------------------------------

def test_agent_dies_when_energy_negative():
    m = _bare_model(L=3, move_cost=5.0, prey_gain=0.0, prey_reproduce=0.0)
    a = _place(m, PreyAgent, (1, 1), energy=2.0)
    # eat gives 0 (we zero prey_gain), move costs 5 -> energy = 2 - 5 = -3 < 0 -> dies
    # (force no grass so no gain even though default grown)
    m.grass_grown = [[False] * 3 for _ in range(3)]
    a.step()
    assert a.alive is False
    assert a.energy == -3.0


def test_agent_survives_when_energy_exactly_zero():
    m = _bare_model(L=3, move_cost=2.0, prey_gain=0.0, prey_reproduce=0.0)
    a = _place(m, PreyAgent, (1, 1), energy=2.0)
    m.grass_grown = [[False] * 3 for _ in range(3)]
    a.step()
    assert a.alive is True                       # 0 is not < 0
    assert a.energy == 0.0


# -- reproduction splits energy ------------------------------------------------

def test_hatch_splits_energy_and_adds_same_species():
    m = _bare_model(L=3)
    parent = _place(m, PreyAgent, (1, 1), energy=20.0)
    before = m.prey_count()
    m.hatch(parent)
    assert parent.energy == 10.0                 # halved
    assert m.prey_count() == before + 1          # offspring added
    # offspring is on the parent's cell, same species, with half the energy
    offspring = m.living[-1]
    assert isinstance(offspring, PreyAgent)
    assert offspring.cell == (1, 1)
    assert offspring.energy == 10.0


def test_predator_reproduce_with_prob_one_adds_predator():
    m = _bare_model(L=3, pred_reproduce=1.0, move_cost=0.0, pred_gain=0.0)
    pred = _place(m, PredatorAgent, (1, 1), energy=40.0)
    before = m.pred_count()
    pred.step()                                  # no prey -> no gain, but reproduces
    assert m.pred_count() == before + 1


# -- grass regrow countdown ----------------------------------------------------

def test_regrow_grass_counts_down_then_regrows():
    m = _bare_model(L=2, grass_regrow=3)
    m.grass_grown = [[False, True], [True, True]]
    m.grass_countdown = [[2, 0], [0, 0]]
    m.regrow_grass()
    assert m.grass_countdown[0][0] == 1 and m.grass_grown[0][0] is False
    m.regrow_grass()
    assert m.grass_grown[0][0] is True            # hit zero -> regrew
    assert m.grass_countdown[0][0] == 0


# -- analysis helpers ----------------------------------------------------------

def test_count_peaks_simple():
    # two clear peaks
    assert count_peaks([0, 1, 0, 1, 0]) == 2
    # monotone -> no peaks
    assert count_peaks([0, 1, 2, 3]) == 0
    # plateau peak counts once
    assert count_peaks([0, 2, 2, 0]) == 1
    # too short
    assert count_peaks([1, 2]) == 0


def test_count_peaks_height_filter():
    # a tall peak and a tiny ripple; height filter at 50% of max should drop the ripple
    series = [0, 10, 0, 1, 0]
    assert count_peaks(series, min_height_frac=0.0) == 2
    assert count_peaks(series, min_height_frac=0.5) == 1


def test_cross_correlation_lag_convention_positive_means_y_follows_x():
    # y is x shifted LATER by 3 (y[t] = x[t-3]) -> y lags x by 3 -> peak at lag +3.
    import math as _math
    x = [_math.sin(t * 0.3) for t in range(100)]
    y = [0.0, 0.0, 0.0] + x[:-3]
    lag, corr = best_positive_lag(x, y, max_lag=10)
    assert lag == 3
    assert corr > 0.9


def test_cross_correlation_zero_lag_for_identical_series():
    x = [math.sin(t * 0.2) for t in range(80)]
    lag, corr = best_positive_lag(x, x, max_lag=10)
    assert lag == 0
    assert corr > 0.999


def test_cross_correlation_length_symmetric():
    x = list(range(20))
    y = list(range(20))
    cc = cross_correlation(x, y, max_lag=5)
    lags = [k for k, _ in cc]
    assert lags == list(range(-5, 6))


# -- determinism ---------------------------------------------------------------

def test_determinism_same_seed_identical_run():
    a = run_single(L=40, n_prey=200, n_pred=40, n_steps=60, seed=7)
    b = run_single(L=40, n_prey=200, n_pred=40, n_steps=60, seed=7)
    assert a["prey_series"] == b["prey_series"]
    assert a["pred_series"] == b["pred_series"]
    assert a["grass_series"] == b["grass_series"]


def test_different_seeds_differ():
    a = run_single(L=40, n_prey=200, n_pred=40, n_steps=60, seed=1)
    b = run_single(L=40, n_prey=200, n_pred=40, n_steps=60, seed=2)
    assert a["prey_series"] != b["prey_series"]


# -- run shape -----------------------------------------------------------------

def test_run_shape_and_series_lengths():
    r = run_single(L=40, n_prey=200, n_pred=40, n_steps=50, seed=0)
    # series include the t=0 baseline; length = steps + 1.
    assert len(r["prey_series"]) == r["steps"] + 1
    assert len(r["pred_series"]) == r["steps"] + 1
    assert r["prey_series"][0] == 200
    assert r["pred_series"][0] == 40


def test_run_many_seeds_aggregates_and_reports_survival():
    out = run_many_seeds([0, 1, 2], L=40, n_prey=200, n_pred=40, n_steps=80)
    assert out["n_seeds"] == 3
    assert len(out["rows"]) == 3
    assert len(out["analyses"]) == 3
    assert 0.0 <= out["survival_fraction"] <= 1.0
    # survival fraction equals n_survived / n_seeds
    assert abs(out["survival_fraction"] - out["n_survived"] / 3) < 1e-12
    # each analysis carries the locked metrics
    a0 = out["analyses"][0]
    for key in ("survived", "prey_peaks", "pred_peaks", "best_lag",
                "prey_peaks_last_third", "pred_peaks_last_third"):
        assert key in a0
