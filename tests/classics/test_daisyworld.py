"""Faithful-rule + determinism + mechanism tests for the agent-based Daisyworld
(Watson & Lovelock 1983) reproduction.

These pin the temperature rule (Stefan-Boltzmann planetary mean + local albedo heating +
diffusion), the parabolic growth response, the agent death/colonisation rules, the
bare-control arm, and determinism (same seed -> identical trajectory). They are
faithfulness tests, NOT prediction tests (the locked P1-P3 are evaluated by
examples/repro_daisyworld/run.py).
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.daisyworld import (
    ALBEDO_BARE,
    ALBEDO_BLACK,
    ALBEDO_WHITE,
    BARE,
    BLACK,
    WHITE,
    Daisyworld,
    equilibrate,
    solar_constant_for_optimum,
    sweep_luminosity,
    temp_range,
)


# -- construction / validation -------------------------------------------------

def test_rejects_bad_L():
    with pytest.raises(ValueError):
        Daisyworld(L=0)


def test_rejects_non_monotone_albedos():
    # require black < bare < white (black absorbs, white reflects)
    with pytest.raises(ValueError):
        Daisyworld(albedo_black=0.6, albedo_bare=0.5, albedo_white=0.75)


def test_albedo_ordering_is_physical():
    # black absorbs (low albedo, warm), white reflects (high albedo, cool).
    assert ALBEDO_BLACK < ALBEDO_BARE < ALBEDO_WHITE


# -- temperature rule ----------------------------------------------------------

def test_solar_constant_puts_bare_planet_at_optimum_at_unit_luminosity():
    # By construction an all-bare planet at L_sol=1.0 sits at the daisy optimum 22.5 C.
    m = Daisyworld(L_sol=1.0, with_daisies=False, seed=0, collect=False)
    m._compute_temperatures()
    assert m.mean_temp() == pytest.approx(22.5, abs=1e-6)


def test_bare_planet_warms_monotonically_with_luminosity():
    temps = []
    for ls in [0.7, 0.9, 1.1, 1.3]:
        m = Daisyworld(L_sol=ls, with_daisies=False, seed=0, collect=False)
        m._compute_temperatures()
        temps.append(m.mean_temp())
    assert all(b > a for a, b in zip(temps, temps[1:]))  # strictly increasing


def test_black_planet_warmer_than_white_planet():
    # A uniformly-black world (low albedo) is hotter than a uniformly-white world.
    mb = Daisyworld(L_sol=1.0, with_daisies=False, seed=0, collect=False, diffuse=0.0)
    mb.grid[:] = BLACK
    mb._compute_temperatures()
    mw = Daisyworld(L_sol=1.0, with_daisies=False, seed=0, collect=False, diffuse=0.0)
    mw.grid[:] = WHITE
    mw._compute_temperatures()
    assert mb.mean_temp() > mw.mean_temp()


def test_local_heating_black_warmer_white_cooler_than_planet():
    # In a mixed world, a black cell is locally warmer than the planetary mean, a white
    # cell locally cooler (the local albedo-correction term).
    m = Daisyworld(L_sol=1.0, with_daisies=True, seed=3, collect=False, diffuse=0.0,
                   init_black_frac=0.3, init_white_frac=0.3)
    m._compute_temperatures()
    black_temps = m.temp_grid[m.grid == BLACK]
    white_temps = m.temp_grid[m.grid == WHITE]
    assert black_temps.mean() > white_temps.mean()


# -- growth response (parabola) ------------------------------------------------

def test_growth_prob_peaks_at_optimum_and_is_zero_far_away():
    m = Daisyworld(seed=0, collect=False)
    assert m.growth_prob(m.t_opt) == pytest.approx(1.0)
    # symmetric parabola: equal offsets give equal growth prob
    assert m.growth_prob(m.t_opt - 5) == pytest.approx(m.growth_prob(m.t_opt + 5))
    # far from the optimum the clamped parabola is exactly 0 (never negative)
    assert m.growth_prob(m.t_opt + 1000) == 0.0
    assert m.growth_prob(m.t_opt - 1000) == 0.0


# -- agent rules: death + colonisation -----------------------------------------

def test_daisy_dies_at_rate_one():
    # gamma=1 -> every occupied patch dies in a single tick.
    m = Daisyworld(L=8, gamma=1.0, seed=0, init_black_frac=0.5, init_white_frac=0.5,
                   collect=False)
    m.step()
    assert m.counts()["black"] == 0
    assert m.counts()["white"] == 0


def test_no_death_when_gamma_zero_and_no_room():
    # gamma=0 and a fully-occupied grid -> states are conserved (no death, no empty to fill).
    m = Daisyworld(L=6, gamma=0.0, seed=0, init_black_frac=0.5, init_white_frac=0.5,
                   collect=False)
    before = m.counts()
    m.step()
    after = m.counts()
    assert before["bare"] == 0 and after["bare"] == 0
    assert before["black"] + before["white"] == after["black"] + after["white"]


def test_colonisation_spreads_a_daisy_into_an_empty_neighbour():
    # A single black daisy at the optimum temperature, gamma=0, deterministic spread
    # (beta=1 at optimum) -> it colonises a neighbour within a few ticks.
    m = Daisyworld(L=10, gamma=0.0, seed=1, with_daisies=False, collect=False)
    m.grid[5, 5] = BLACK
    # rebuild patch states from the hand-set grid
    for r in range(m.L):
        for c in range(m.L):
            m._patches[r][c].state = int(m.grid[r, c])
    start = m.counts()["black"]
    for _ in range(5):
        m.step()
    assert m.counts()["black"] > start


def test_bare_control_stays_bare_forever():
    # with_daisies=False -> no biota ever appears; temperature is the energy balance only.
    m = Daisyworld(L=12, with_daisies=False, seed=0, collect=False)
    for _ in range(10):
        m.step()
    assert m.counts()["black"] == 0 and m.counts()["white"] == 0
    assert m.counts()["bare"] == m.L * m.L


# -- determinism ---------------------------------------------------------------

def test_same_seed_identical_trajectory():
    a = equilibrate(L_sol=1.0, with_daisies=True, seed=7, steps=60, avg_last=20)
    b = equilibrate(L_sol=1.0, with_daisies=True, seed=7, steps=60, avg_last=20)
    assert a == b


def test_different_seeds_can_differ():
    a = equilibrate(L_sol=1.0, with_daisies=True, seed=1, steps=60, avg_last=20)
    b = equilibrate(L_sol=1.0, with_daisies=True, seed=2, steps=60, avg_last=20)
    assert (a["mean_temp"], a["black_frac"]) != (b["mean_temp"], b["black_frac"])


# -- sweep / metric helpers ----------------------------------------------------

def test_sweep_returns_one_row_per_luminosity():
    rows = sweep_luminosity(L_sol_grid=[0.9, 1.0, 1.1], seeds=[0, 1],
                            with_daisies=True, steps=50, avg_last=20)
    assert [r["L_sol"] for r in rows] == [0.9, 1.0, 1.1]
    assert all("mean_temp" in r and "black_frac" in r for r in rows)


def test_temp_range_is_max_minus_min():
    rows = [{"mean_temp": 10.0}, {"mean_temp": 25.0}, {"mean_temp": 18.0}]
    assert temp_range(rows) == pytest.approx(15.0)


# -- mechanism sanity: in the populated window, daisies regulate ---------------

def test_with_daisies_band_narrower_than_bare_control_in_window():
    # Over a luminosity window where daisies persist, the WITH-daisies temperature band is
    # much narrower than the bare control over the SAME window (the homeostasis mechanism).
    grid = [0.85, 0.95, 1.05, 1.15]
    seeds = [0, 1, 2]
    with_d = sweep_luminosity(L_sol_grid=grid, seeds=seeds, with_daisies=True,
                              steps=200, avg_last=50)
    bare = sweep_luminosity(L_sol_grid=grid, seeds=seeds, with_daisies=False,
                            steps=200, avg_last=50)
    assert temp_range(with_d) < temp_range(bare)
    # and the daisy mix shifts black -> white as luminosity rises (P3 mechanism)
    assert with_d[0]["black_frac"] > with_d[0]["white_frac"]   # cold end: black-dominated
    assert with_d[-1]["white_frac"] > with_d[-1]["black_frac"]  # hot end: white-dominated
