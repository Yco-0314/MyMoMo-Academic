"""Faithful-rule + determinism tests for the Moran process with selection (Moran 1958)
reproduction.

These pin the exact Moran fixation formula rho=(1-1/r)/(1-1/r**N) (and 1/N at r=1), the
single-mutant initial condition, the fitness-weighted BIRTH / uniform DEATH / replace
micro-rule, the run-to-fixation stop, and determinism (same seed -> identical result).
They are faithfulness tests, NOT prediction tests (the locked predictions P1-P3 are
evaluated by examples/repro_moran_process/run.py).
"""
from __future__ import annotations

import pytest

from abm_auto.classics.moran_process import (
    MUTANT,
    RESIDENT,
    IndividualAgent,
    MoranModel,
    analytic_fixation,
    fixation_fraction,
    run_single,
)


# -- analytic anchor: the exact Moran fixation probability --------------------

def test_analytic_neutral_is_one_over_N():
    assert analytic_fixation(1.0, 100) == pytest.approx(0.01)
    assert analytic_fixation(1.0, 50) == pytest.approx(0.02)
    assert analytic_fixation(1.0, 4) == pytest.approx(0.25)


def test_analytic_formula_matches_closed_form():
    # rho = (1 - 1/r) / (1 - 1/r**N) for r != 1.
    for r, N in [(1.05, 100), (1.1, 100), (1.2, 100), (2.0, 100), (1.5, 30)]:
        x = 1.0 / r
        expected = (1.0 - x) / (1.0 - x ** N)
        assert analytic_fixation(r, N) == pytest.approx(expected)


def test_analytic_large_N_limit_is_one_minus_one_over_r_not_2s():
    # The Moran large-N limit is 1 - 1/r (~= s), NOT the Wright-Fisher 2s. For r=1.2,
    # s=0.2; 1-1/r = 0.1667, which is far from 2s=0.4. Pin the Moran value.
    r, N = 1.2, 5000
    assert analytic_fixation(r, N) == pytest.approx(1.0 - 1.0 / r, abs=1e-6)
    assert abs(analytic_fixation(r, N) - 2.0 * (r - 1.0)) > 0.2  # not WF 2s


def test_analytic_monotone_increasing_in_r():
    N = 100
    rhos = [analytic_fixation(r, N) for r in (1.0, 1.05, 1.1, 1.2, 2.0)]
    assert all(b > a for a, b in zip(rhos, rhos[1:]))


def test_analytic_rejects_bad_inputs():
    with pytest.raises(ValueError):
        analytic_fixation(1.1, 0)
    with pytest.raises(ValueError):
        analytic_fixation(0.0, 100)


# -- model construction + invariants ------------------------------------------

def test_starts_with_exactly_one_mutant():
    m = MoranModel(100, r=1.1, seed=0)
    assert len(m.agent_list) == 100
    assert m.n_mutants() == 1
    assert all(isinstance(a, IndividualAgent) for a in m.agent_list)
    assert all(a.type in (MUTANT, RESIDENT) for a in m.agent_list)


def test_population_size_is_constant_under_birth_death():
    m = MoranModel(50, r=1.2, seed=3)
    for _ in range(200):
        m.birth_death_step()
        assert len(m.agent_list) == 50  # N never changes


def test_agent_fitness_is_r_for_mutant_one_for_resident():
    m = MoranModel(10, r=1.7, seed=0)
    mutants = [a for a in m.agent_list if a.is_mutant()]
    residents = [a for a in m.agent_list if not a.is_mutant()]
    assert len(mutants) == 1
    assert mutants[0].fitness() == pytest.approx(1.7)
    assert all(a.fitness() == pytest.approx(1.0) for a in residents)


def test_requires_valid_N_and_r_and_mutant_index():
    with pytest.raises(ValueError):
        MoranModel(1, r=1.1, seed=0)         # N must be > 1
    with pytest.raises(ValueError):
        MoranModel(100, r=0.0, seed=0)       # r must be positive
    with pytest.raises(ValueError):
        MoranModel(100, r=1.1, seed=0, mutant_index=100)  # out of range


# -- the elementary mechanics: fitness-weighted birth, uniform death ----------

def test_birth_picks_mutant_when_rng_lands_in_mutant_fitness_band():
    # One mutant (fitness r) among residents (fitness 1). Total = r + (N-1). A BIRTH
    # draw that lands inside the FIRST agent's fitness band (the mutant, index 0) makes
    # the mutant reproduce; force the dier to be a resident -> mutant count rises to 2.
    m = MoranModel(5, r=2.0, seed=0)  # agent 0 is the mutant, total fitness = 2 + 4 = 6
    assert m.agent_list[0].is_mutant()
    # threshold = random()*total; pick random() small so threshold < mutant fitness (2).
    draws = iter([0.0])               # birth: lands in mutant band
    m.rng.random = lambda: next(draws)
    m.rng.randrange = lambda *_a, **_k: 1  # death: a resident dies
    m.birth_death_step()
    assert m.n_mutants() == 2
    assert m.agent_list[1].type == MUTANT


def test_birth_picks_resident_when_rng_lands_past_mutant_band():
    # A BIRTH draw past the mutant's fitness band selects a resident reproducer; if the
    # mutant then dies, the mutant count drops to 0 (extinction).
    m = MoranModel(5, r=2.0, seed=0)  # total fitness 6, mutant band = [0, 2)
    m.rng.random = lambda: 0.9        # threshold = 0.9*6 = 5.4 -> a resident reproduces
    m.rng.randrange = lambda *_a, **_k: 0  # the mutant (index 0) dies
    m.birth_death_step()
    assert m.n_mutants() == 0


def test_death_is_uniform_replacement_overwrites_type():
    # Two mutants, three residents; force a resident to reproduce and a specific mutant
    # to die -> that mutant becomes a resident.
    m = MoranModel(5, r=1.0, seed=0)
    m.agent_list[0].type = MUTANT
    m.agent_list[1].type = MUTANT
    m.agent_list[2].type = RESIDENT
    m.agent_list[3].type = RESIDENT
    m.agent_list[4].type = RESIDENT
    # r=1 so all fitness 1; threshold lands in agent 2 (a resident) reproducer band.
    m.rng.random = lambda: (2.0 + 0.5) / 5.0  # cumulative passes agents 0,1,2 -> agent 2
    m.rng.randrange = lambda *_a, **_k: 1      # mutant index 1 dies
    m.birth_death_step()
    assert m.agent_list[1].type == RESIDENT
    assert m.n_mutants() == 1


# -- fixation / absorbing states ----------------------------------------------

def test_is_fixed_only_at_absorbing_states():
    m = MoranModel(4, r=1.1, seed=0)
    assert not m.is_fixed()                    # 1 mutant, 3 residents
    for a in m.agent_list:
        a.type = RESIDENT
    assert m.is_fixed()                        # all residents (m=0)
    for a in m.agent_list:
        a.type = MUTANT
    assert m.is_fixed()                        # all mutants (m=N)


def test_run_reaches_an_absorbing_state():
    res = run_single(50, r=1.2, seed=7)
    assert res["absorbed"] is True
    assert res["final_mutants"] in (0, 50)
    assert res["fixed"] == (res["final_mutants"] == 50)


def test_run_records_analytic_anchor():
    res = run_single(100, r=1.1, seed=0)
    assert res["analytic_fixation"] == pytest.approx(analytic_fixation(1.1, 100))


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_run():
    a = run_single(100, r=1.1, seed=42)
    b = run_single(100, r=1.1, seed=42)
    assert a["events"] == b["events"]
    assert a["final_mutants"] == b["final_mutants"]
    assert a["fixed"] == b["fixed"]


def test_determinism_fixation_fraction_repeatable():
    a = fixation_fraction(100, r=1.1, n_runs=200, seed_base=0)
    b = fixation_fraction(100, r=1.1, n_runs=200, seed_base=0)
    assert a["fixations"] == b["fixations"]
    assert a["measured_fixation"] == b["measured_fixation"]


def test_different_seed_can_differ():
    # Different seeds give independent outcomes (not guaranteed to differ on one draw,
    # but the event counts almost surely do). Check shape invariants either way.
    a = run_single(100, r=1.1, seed=1)
    b = run_single(100, r=1.1, seed=2)
    for res in (a, b):
        assert res["absorbed"] is True
        assert res["final_mutants"] in (0, 100)


# -- Monte-Carlo sanity (loose; the locked grade lives in run.py) -------------

def test_neutral_fixation_near_one_over_N_small_run():
    # r=1 -> rho=1/N=0.01; with a modest run the measured fraction is near 0.01 (loose
    # tolerance here — the locked +-0.01 grade is in run.py at >=2000 runs).
    res = fixation_fraction(100, r=1.0, n_runs=2000, seed_base=0)
    assert res["analytic_fixation"] == pytest.approx(0.01)
    assert abs(res["measured_fixation"] - 0.01) < 0.02


def test_advantageous_mutant_fixes_more_often_than_neutral():
    neutral = fixation_fraction(100, r=1.0, n_runs=1000, seed_base=0)
    strong = fixation_fraction(100, r=2.0, n_runs=1000, seed_base=0)
    assert strong["measured_fixation"] > neutral["measured_fixation"]


def test_binomial_se_reported_and_finite():
    res = fixation_fraction(100, r=1.2, n_runs=500, seed_base=0)
    assert res["binomial_se"] >= 0.0
    assert res["binomial_se"] < 0.05
