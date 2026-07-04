"""Faithful-rule + determinism tests for the 2D Ising / Glauber reproduction.

These pin the Glauber heat-bath probability (ΔE = 2·s·h, accept with 1/(1+exp(ΔE/T))),
the periodic 4-neighbour field, the per-site agent decision, the equilibration /
back-half averaging, and determinism (same seed -> identical result). They are
faithfulness tests, NOT prediction tests (the predictions P1-P3 are evaluated by
examples/repro_ising_2d/run.py).
"""
from __future__ import annotations

import math

import numpy as np

from abm_auto.classics.ising import (
    IsingModel,
    SpinAgent,
    T_C_ONSAGER,
    flip_probability,
    half_magnetization_crossing,
    heat_bath_up_probability,
    is_monotone_non_increasing,
    neighbour_field,
    run_many_seeds,
    run_single,
    sweep_temperatures,
)


# -- the Glauber heat-bath probability (pure functions) -----------------------

def test_onsager_critical_temperature():
    # T_c = 2 / ln(1 + sqrt(2)) ≈ 2.269185 (Onsager 1944).
    assert abs(T_C_ONSAGER - 2.0 / math.log(1.0 + math.sqrt(2.0))) < 1e-12
    assert abs(T_C_ONSAGER - 2.269185) < 1e-5


def test_flip_probability_energy_lowering_favoured():
    # s=-1 in an all-up field h=+4: flipping to +1 lowers energy (ΔE=2*-1*4=-8 < 0),
    # so the flip is accepted with high probability (> 1/2).
    assert flip_probability(-1, 4, 2.0) > 0.9
    # s=+1 in an all-up field h=+4: flipping to -1 RAISES energy (ΔE=+8 > 0), accepted
    # with low probability (< 1/2).
    assert flip_probability(1, 4, 2.0) < 0.1
    # ΔE = 0 (h=0) -> exactly 1/2 regardless of spin or T.
    assert flip_probability(1, 0, 2.0) == 0.5
    assert flip_probability(-1, 0, 5.0) == 0.5


def test_flip_and_heat_bath_forms_agree():
    # The flip form applied to the current spin must agree with the heat-bath p_up:
    # if currently s=+1, P(stay +1) = 1 - P(flip) must equal p_up.
    for h in (-4, -2, 0, 2, 4):
        for T in (1.5, 2.27, 3.5):
            p_up = heat_bath_up_probability(h, T)
            # currently +1: prob of ending +1 = 1 - flip_probability(+1, h, T)
            assert abs((1.0 - flip_probability(1, h, T)) - p_up) < 1e-12
            # currently -1: prob of ending +1 = flip_probability(-1, h, T)
            assert abs(flip_probability(-1, h, T) - p_up) < 1e-12


def test_heat_bath_monotone_in_field():
    # Stronger up-field -> higher prob the spin ends up. Symmetric around h=0.
    T = 2.27
    assert heat_bath_up_probability(-4, T) < heat_bath_up_probability(0, T) \
        < heat_bath_up_probability(4, T)
    assert heat_bath_up_probability(0, T) == 0.5
    assert abs(heat_bath_up_probability(2, T) + heat_bath_up_probability(-2, T) - 1.0) < 1e-12


def test_low_T_is_near_deterministic_descent():
    # As T -> 0 the heat bath becomes a deterministic alignment with the field.
    assert heat_bath_up_probability(2, 0.01) > 0.999999
    assert heat_bath_up_probability(-2, 0.01) < 1e-6


# -- the periodic 4-neighbour field -------------------------------------------

def test_neighbour_field_periodic_wraps():
    L = 4
    lat = -np.ones((L, L), dtype=np.int8)
    # corner site (0,0): its 4 NN are (L-1,0),(1,0),(0,L-1),(0,1) — all wrap correctly.
    lat[L - 1, 0] = 1
    lat[1, 0] = 1
    lat[0, L - 1] = 1
    lat[0, 1] = 1
    assert neighbour_field(lat, 0, 0) == 4   # all four neighbours are +1
    # a fully +1 lattice: every field is +4; fully -1: every field is -4.
    assert neighbour_field(np.ones((L, L), dtype=np.int8), 2, 3) == 4
    assert neighbour_field(-np.ones((L, L), dtype=np.int8), 2, 3) == -4


def test_neighbour_field_counts_only_four():
    L = 5
    lat = np.zeros((L, L), dtype=np.int8)
    lat[1, 2] = 1   # up
    lat[3, 2] = 1   # down
    lat[2, 1] = 1   # left
    lat[2, 3] = 1   # right
    lat[1, 1] = 1   # diagonal — must NOT be counted
    assert neighbour_field(lat, 2, 2) == 4


# -- model construction + agent wiring ----------------------------------------

def test_model_has_one_spinagent_per_site():
    m = IsingModel(L=8, T=2.27, seed=0, n_sweeps=1)
    assert len(m.agents) == 64
    assert m.N == 64
    assert all(isinstance(a, SpinAgent) for a in m.agents)
    # lattice is ±1 only.
    assert set(np.unique(m.lattice)).issubset({-1, 1})


def test_agent_step_updates_its_own_site_only():
    # A SpinAgent.step must only touch its own (row,col). Put the lattice in a frozen
    # all-up state, step one agent in a strong up-field at very low T: it stays +1 and
    # no other cell changes.
    m = IsingModel(L=6, T=0.1, seed=0, n_sweeps=1)
    m.lattice[:] = 1
    before = m.lattice.copy()
    agent = next(a for a in m.agents if a.row == 2 and a.col == 3)
    agent.step()
    # In an all-up field h=+4 at T=0.1, p_up ≈ 1, so the site stays +1; lattice unchanged.
    assert np.array_equal(m.lattice, before)


def test_invalid_params_raise():
    for bad in dict(L=0), dict(T=0.0), dict(T=-1.0):
        try:
            IsingModel(**bad, seed=0, n_sweeps=1)  # type: ignore[arg-type]
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad}")


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_series():
    a = run_single(L=16, T=2.27, seed=7, n_sweeps=200)
    b = run_single(L=16, T=2.27, seed=7, n_sweeps=200)
    assert a["abs_m"] == b["abs_m"]
    assert a["abs_m_series"] == b["abs_m_series"]
    assert a["final_abs_m"] == b["final_abs_m"]


def test_different_seeds_can_differ():
    a = run_single(L=16, T=2.27, seed=1, n_sweeps=200)
    b = run_single(L=16, T=2.27, seed=2, n_sweeps=200)
    # Near T_c the trajectory is seed-dependent; the full series should differ.
    assert a["abs_m_series"] != b["abs_m_series"]


def test_run_many_seeds_shaped_and_deterministic():
    a = run_many_seeds(L=16, T=2.0, n_seeds=4, seed_base=0, n_sweeps=300)
    b = run_many_seeds(L=16, T=2.0, n_seeds=4, seed_base=0, n_sweeps=300)
    assert a["per_seed_abs_m"] == b["per_seed_abs_m"]
    assert a["mean_abs_m"] == b["mean_abs_m"]
    assert len(a["per_seed"]) == 4
    assert 0.0 <= a["mean_abs_m"] <= 1.0
    assert a["min_abs_m"] <= a["mean_abs_m"] <= a["max_abs_m"]


# -- physics sanity (coarse; the real claims live in the runner) --------------

def test_low_T_orders_high_T_disorders():
    # Far below T_c the system orders (|m| near 1); far above it disorders (|m| small).
    low = run_single(L=24, T=1.5, seed=0, n_sweeps=600)
    high = run_single(L=24, T=3.5, seed=0, n_sweeps=600)
    assert low["abs_m"] > 0.7
    assert high["abs_m"] < 0.2


def test_equilibration_uses_back_half():
    m = IsingModel(L=8, T=2.27, seed=0, n_sweeps=10)
    res = m.run()
    # series has n_sweeps + 1 entries (sweep-0 baseline + 10 sweeps); burn = half.
    assert len(res["abs_m_series"]) == 11
    assert res["burn_in"] == 5


# -- analysis helpers ---------------------------------------------------------

def test_is_monotone_non_increasing():
    assert is_monotone_non_increasing([0.99, 0.95, 0.6, 0.2, 0.05]) is True
    assert is_monotone_non_increasing([0.99, 0.99, 0.99]) is True
    assert is_monotone_non_increasing([0.9, 0.92, 0.3]) is False   # a rise breaks it
    # within tolerance: a tiny wobble up is allowed.
    assert is_monotone_non_increasing([0.50, 0.5000000001, 0.4], tol=1e-6) is True


def test_half_magnetization_crossing_interpolates():
    Ts = [1.5, 2.0, 2.27, 2.5, 3.0, 3.5]
    # |m| crosses 0.5 between T=2.27 (0.62) and T=2.5 (0.30).
    ms = [0.98, 0.90, 0.62, 0.30, 0.10, 0.05]
    tc = half_magnetization_crossing(Ts, ms, level=0.5)
    assert tc is not None
    assert 2.27 < tc < 2.5
    # exact bracket: m0=0.62, m1=0.30 -> frac=(0.62-0.5)/(0.62-0.30)=0.375
    assert abs(tc - (2.27 + 0.375 * (2.5 - 2.27))) < 1e-9


def test_half_magnetization_crossing_edge_cases():
    Ts = [1.5, 2.0, 3.5]
    # never drops below 0.5 -> None.
    assert half_magnetization_crossing(Ts, [0.9, 0.8, 0.7], level=0.5) is None
    # already below 0.5 at the lowest T -> returns the lowest T.
    assert half_magnetization_crossing(Ts, [0.4, 0.3, 0.1], level=0.5) == 1.5


def test_sweep_temperatures_shape():
    rows = sweep_temperatures([2.0, 3.0], L=12, n_seeds=2, seed_base=0, n_sweeps=100)
    assert len(rows) == 2
    assert rows[0]["T"] == 2.0 and rows[1]["T"] == 3.0
    assert all("mean_abs_m" in r for r in rows)
