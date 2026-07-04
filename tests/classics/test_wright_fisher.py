"""Faithful-rule + determinism tests for the Wright-Fisher neutral genetic drift
(Wright 1931 / Fisher 1930) reproduction.

These pin the generational resample micro-rule (sample N parents uniformly WITH
replacement; each offspring inherits its sampled parent's allele), the p0 initial
condition, the constant population size, the run-to-fixation stop, the neutral analytic
anchors (fixation prob = p0; haploid heterozygosity decay factor 1 - 1/N), and
determinism (same seed -> identical result). They are faithfulness tests, NOT prediction
tests (the locked predictions P1-P3 are evaluated by examples/repro_wright_fisher/run.py).
"""
from __future__ import annotations

import pytest

from abm_auto.classics.wright_fisher import (
    ALLELE_A,
    ALLELE_a,
    AlleleAgent,
    WrightFisherModel,
    analytic_fixation,
    fixation_fraction,
    heterozygosity,
    heterozygosity_decay_factor,
    run_single,
)


# -- analytic anchors ---------------------------------------------------------

def test_analytic_fixation_is_initial_frequency():
    for p0 in (0.0, 0.2, 0.5, 0.8, 1.0):
        assert analytic_fixation(p0) == pytest.approx(p0)


def test_analytic_fixation_rejects_out_of_range():
    with pytest.raises(ValueError):
        analytic_fixation(-0.1)
    with pytest.raises(ValueError):
        analytic_fixation(1.1)


def test_heterozygosity_decay_factor_is_one_minus_one_over_N():
    assert heterozygosity_decay_factor(100) == pytest.approx(0.99)
    assert heterozygosity_decay_factor(50) == pytest.approx(0.98)
    with pytest.raises(ValueError):
        heterozygosity_decay_factor(0)


def test_heterozygosity_formula():
    assert heterozygosity(0.5) == pytest.approx(0.5)
    assert heterozygosity(0.0) == pytest.approx(0.0)
    assert heterozygosity(1.0) == pytest.approx(0.0)
    assert heterozygosity(0.2) == pytest.approx(2 * 0.2 * 0.8)


# -- model construction + invariants ------------------------------------------

def test_initial_A_fraction_is_round_p0_times_N():
    m = WrightFisherModel(100, p0=0.2, seed=0)
    assert len(m.agent_list) == 100
    assert m.n_A() == 20
    assert all(isinstance(a, AlleleAgent) for a in m.agent_list)
    assert all(a.allele in (ALLELE_A, ALLELE_a) for a in m.agent_list)


def test_initial_fraction_for_each_grid_p0():
    assert WrightFisherModel(100, p0=0.2, seed=0).n_A() == 20
    assert WrightFisherModel(100, p0=0.5, seed=0).n_A() == 50
    assert WrightFisherModel(100, p0=0.8, seed=0).n_A() == 80


def test_population_size_constant_under_resample():
    m = WrightFisherModel(50, p0=0.5, seed=3)
    for _ in range(100):
        m.generation_step()
        assert len(m.agent_list) == 50  # N never changes


def test_requires_valid_N_and_p0():
    with pytest.raises(ValueError):
        WrightFisherModel(1, p0=0.5, seed=0)     # N must be > 1
    with pytest.raises(ValueError):
        WrightFisherModel(100, p0=-0.1, seed=0)  # p0 in [0,1]
    with pytest.raises(ValueError):
        WrightFisherModel(100, p0=1.5, seed=0)   # p0 in [0,1]


# -- the elementary mechanics: uniform parent sampling with replacement -------

def test_offspring_inherits_sampled_parent_allele():
    # 4 agents: A, A, a, a. Force every parent draw to land on index 0 (an A) -> the whole
    # next generation is A. (randrange(n) is the uniform parent index.)
    m = WrightFisherModel(4, p0=0.5, seed=0)
    assert [a.allele for a in m.agent_list] == [ALLELE_A, ALLELE_A, ALLELE_a, ALLELE_a]
    m.rng.randrange = lambda *_a, **_k: 0  # every parent draw -> agent 0 (an A)
    m.generation_step()
    assert m.n_A() == 4
    assert all(a.allele == ALLELE_A for a in m.agent_list)


def test_sampling_an_a_parent_for_all_slots_loses_A():
    # Force every parent draw to land on index 3 (an 'a') -> A is lost in one generation.
    m = WrightFisherModel(4, p0=0.5, seed=0)
    m.rng.randrange = lambda *_a, **_k: 3  # every parent draw -> agent 3 (an a)
    m.generation_step()
    assert m.n_A() == 0
    assert all(a.allele == ALLELE_a for a in m.agent_list)


def test_resample_reads_current_generation_not_partially_updated():
    # The next generation must be sampled from a SNAPSHOT of the current generation, not
    # from a roster being mutated in place. With agents [A, a] and parent draws [1, 0]
    # (slot0<-agent1='a', slot1<-agent0='A') the result must be [a, A]. If the code
    # updated agent0 to 'a' BEFORE drawing slot1 from agent0, slot1 would wrongly become
    # 'a' and #A would be 0. Pin that it stays 1.
    m = WrightFisherModel(2, p0=0.5, seed=0)
    assert [a.allele for a in m.agent_list] == [ALLELE_A, ALLELE_a]
    draws = iter([1, 0])
    m.rng.randrange = lambda *_a, **_k: next(draws)
    m.generation_step()
    assert [a.allele for a in m.agent_list] == [ALLELE_a, ALLELE_A]
    assert m.n_A() == 1


# -- fixation / absorbing states ----------------------------------------------

def test_is_fixed_only_at_absorbing_states():
    m = WrightFisherModel(4, p0=0.5, seed=0)
    assert not m.is_fixed()                    # 2 A, 2 a
    for a in m.agent_list:
        a.allele = ALLELE_a
    assert m.is_fixed()                        # all a (#A=0)
    for a in m.agent_list:
        a.allele = ALLELE_A
    assert m.is_fixed()                        # all A (#A=N)


def test_run_reaches_an_absorbing_state():
    res = run_single(50, p0=0.5, seed=7)
    assert res["absorbed"] is True
    assert res["final_A"] in (0, 50)
    assert res["fixed"] == (res["final_A"] == 50)


def test_run_records_trajectories_and_anchor():
    res = run_single(100, p0=0.2, seed=0)
    assert res["analytic_fixation"] == pytest.approx(0.2)
    # trajectory starts at the t=0 baseline (#A = round(0.2*100) = 20) and ends absorbed.
    assert res["n_A_trajectory"][0] == 20
    assert res["n_A_trajectory"][-1] in (0, 100)
    assert len(res["h_trajectory"]) == len(res["n_A_trajectory"])
    # H(0) = 2*0.2*0.8 = 0.32; H at absorption = 0.
    assert res["h_trajectory"][0] == pytest.approx(0.32)
    assert res["h_trajectory"][-1] == pytest.approx(0.0)


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_run():
    a = run_single(100, p0=0.5, seed=42)
    b = run_single(100, p0=0.5, seed=42)
    assert a["generations"] == b["generations"]
    assert a["final_A"] == b["final_A"]
    assert a["n_A_trajectory"] == b["n_A_trajectory"]


def test_determinism_fixation_fraction_repeatable():
    a = fixation_fraction(100, p0=0.5, n_runs=100, seed_base=0)
    b = fixation_fraction(100, p0=0.5, n_runs=100, seed_base=0)
    assert a["fixations"] == b["fixations"]
    assert a["measured_fixation"] == b["measured_fixation"]
    assert a["measured_decay_factor"] == b["measured_decay_factor"]


def test_different_seed_can_differ():
    a = run_single(100, p0=0.5, seed=1)
    b = run_single(100, p0=0.5, seed=2)
    for res in (a, b):
        assert res["absorbed"] is True
        assert res["final_A"] in (0, 100)


# -- Monte-Carlo sanity (loose; the locked grade lives in run.py) -------------

def test_neutral_fixation_near_p0_small_run():
    # Neutral fixation prob = p0. With a modest run the measured fraction is near p0
    # (loose tolerance here — the locked +-0.05 grade is in run.py at >=2000 runs).
    res = fixation_fraction(100, p0=0.5, n_runs=2000, seed_base=0)
    assert res["analytic_fixation"] == pytest.approx(0.5)
    assert abs(res["measured_fixation"] - 0.5) < 0.05


def test_heterozygosity_decays_roughly_at_one_over_N():
    # Measured per-gen MEAN-H decay factor (across-run ensemble) should sit near
    # 1 - 1/N = 0.99 (haploid law), and inside the locked P2 band [1-2/N, 1-1/(4N)].
    res = fixation_fraction(100, p0=0.5, n_runs=500, seed_base=0)
    assert res["analytic_decay_factor"] == pytest.approx(0.99)
    assert 0.985 <= res["measured_decay_factor"] <= 0.995  # ~0.989, near the 1-1/N law


def test_mean_delta_p_is_approximately_zero():
    # The direct neutrality (martingale) statement: mean one-generation increment over
    # polymorphic steps is ~0 to Monte-Carlo precision, for every p0.
    for p0 in (0.2, 0.5, 0.8):
        res = fixation_fraction(100, p0=p0, n_runs=1000, seed_base=0)
        assert abs(res["mean_delta_p"]) < 0.005


def test_ensemble_mean_p_near_p0_early():
    # The mean A-fraction ACROSS runs at a fixed early generation stays ~p0.
    for p0 in (0.2, 0.5, 0.8):
        res = fixation_fraction(100, p0=p0, n_runs=1000, seed_base=0)
        assert abs(res["ensemble_mean_p_early"] - p0) < 0.05


def test_higher_p0_fixes_more_often():
    lo = fixation_fraction(100, p0=0.2, n_runs=1000, seed_base=0)
    hi = fixation_fraction(100, p0=0.8, n_runs=1000, seed_base=0)
    assert hi["measured_fixation"] > lo["measured_fixation"]


def test_binomial_se_reported_and_finite():
    res = fixation_fraction(100, p0=0.5, n_runs=500, seed_base=0)
    assert res["binomial_se"] >= 0.0
    assert res["binomial_se"] < 0.05
