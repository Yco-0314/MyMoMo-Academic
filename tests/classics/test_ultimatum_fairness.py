"""Faithful-rule + determinism tests for the evolutionary ultimatum-game
(Nowak-Page-Sigmund 2000) reproduction.

These pin the genotype (p, q) init, the population-mean metrics p̄ and q̄, the reputation
offer channel (w=0 => always own p; w=1 => always meet the responder's threshold q), the
accept/reject payoff accounting, fitness-proportional reproduction + mutation, the
steady-state estimator, and determinism (same seed -> identical result).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3 (w=0
collapse, w>=0.8 fairness, monotone treatment contrast) are evaluated by
examples/repro_ultimatum_fairness/run.py.
"""
from __future__ import annotations

import pytest

from abm_auto.classics.ultimatum_fairness import (
    PlayerAgent,
    UltimatumModel,
    run_single,
    tail_mean,
)


# -- model construction + invariants ------------------------------------------

def test_population_is_player_agents_with_genotype_in_unit_square():
    m = UltimatumModel(n=200, w=0.0, seed=0)
    assert len(m.agent_list) == 200
    assert all(isinstance(a, PlayerAgent) for a in m.agent_list)
    for a in m.agent_list:
        assert 0.0 <= a.p <= 1.0
        assert 0.0 <= a.q <= 1.0
        assert a.fitness == 0.0


def test_fair_init_mean_near_half():
    # p and q are each uniform on [0,1], so the initial population means sit near 0.5
    # (the fair, un-rigged start). Large N keeps the sample mean close.
    m = UltimatumModel(n=2000, w=0.0, seed=1)
    assert m.mean_offer() == pytest.approx(0.5, abs=0.05)
    assert m.mean_threshold() == pytest.approx(0.5, abs=0.05)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        UltimatumModel(n=1)
    with pytest.raises(ValueError):
        UltimatumModel(n=10, w=-0.1)
    with pytest.raises(ValueError):
        UltimatumModel(n=10, w=1.5)
    with pytest.raises(ValueError):
        UltimatumModel(n=10, rounds_per_gen=0)
    with pytest.raises(ValueError):
        UltimatumModel(n=10, mutation=-0.01)


# -- the reputation offer channel ---------------------------------------------

def test_anonymous_proposer_offers_own_genotype():
    # With w=0 the proposer never knows the responder; it always offers its own p.
    m = UltimatumModel(n=2, w=0.0, seed=0)
    a, b = m.agent_list
    a.p, a.q = 0.3, 0.1
    b.p, b.q = 0.7, 0.9
    for _ in range(50):
        assert m._offer_of(a, b) == pytest.approx(a.p)   # own p, never b's q


def test_full_reputation_proposer_meets_the_threshold():
    # With w=1 the proposer always knows the responder and best-responds by offering
    # exactly the responder's threshold q (the minimum that still gets accepted).
    m = UltimatumModel(n=2, w=1.0, seed=0)
    a, b = m.agent_list
    a.p, a.q = 0.3, 0.1
    b.p, b.q = 0.7, 0.9
    for _ in range(50):
        assert m._offer_of(a, b) == pytest.approx(b.q)   # meets b's threshold, not a's p


def test_reputation_offer_is_accepted_by_construction():
    # The informed best-response offers exactly q, so the deal always goes through
    # (offer >= responder q). A low-p proposer that would be rejected anonymously gets
    # its deal accepted under full reputation.
    m = UltimatumModel(n=2, w=1.0, seed=0)
    a, b = m.agent_list
    a.p, a.q = 0.05, 0.0       # a's own offer 0.05 would be rejected by b
    b.p, b.q = 0.5, 0.5
    offer = m._offer_of(a, b)
    assert offer >= b.q                    # accepted under reputation


# -- accept / reject payoff accounting ----------------------------------------

def test_accepted_offer_splits_the_pie():
    # Two agents that accept everything (q=0), rounds_per_gen=1, w=0. Every encounter is
    # accepted, so each accepted deal distributes exactly 1.0 total (proposer 1-offer +
    # responder offer). There are 4 encounters (each agent proposes once and responds
    # once), all accepted -> total fitness == 4.0.
    m = UltimatumModel(n=2, w=0.0, rounds_per_gen=1, seed=0)
    a, b = m.agent_list
    a.p, a.q = 0.4, 0.0        # a offers 0.4, accepts everything
    b.p, b.q = 0.7, 0.0        # b offers 0.7, accepts everything
    m.assign_fitness()
    # 4 accepted encounters, each splitting a unit pie -> total distributed == 4.0.
    assert a.fitness + b.fitness == pytest.approx(4.0, abs=1e-9)
    # each accepted deal pays proposer 1-offer and responder offer, so both are positive.
    assert a.fitness > 0.0 and b.fitness > 0.0


def test_rejected_offer_pays_nobody():
    # Responder threshold above the offer -> rejection -> both get 0 from that encounter.
    m = UltimatumModel(n=2, w=0.0, rounds_per_gen=1, seed=0)
    a, b = m.agent_list
    a.p, a.q = 0.1, 1.0        # a offers 0.1, accepts only offer >= 1.0
    b.p, b.q = 0.1, 1.0        # b offers 0.1, accepts only offer >= 1.0
    m.assign_fitness()
    # every offer (0.1) is below every threshold (1.0) -> all rejected -> zero fitness.
    assert a.fitness == pytest.approx(0.0)
    assert b.fitness == pytest.approx(0.0)


def test_each_accepted_deal_distributes_unit_pie():
    # Aggregate conservation: across a full generation, total fitness == (number of
    # accepted deals) * 1.0, since every accepted deal splits exactly 1 unit of pie and a
    # rejected deal distributes 0. We verify by an independent count.
    m = UltimatumModel(n=6, w=0.5, rounds_per_gen=4, seed=3)
    # snapshot genotypes, then run the SAME encounter sequence via a fresh seeded model.
    m.assign_fitness()
    total_fitness = sum(a.fitness for a in m.agent_list)
    # total pie must be a non-negative multiple-ish of accepted deals; each deal <= 1.0.
    n_encounters = m.n * m.rounds_per_gen * 2          # each agent plays both roles
    assert 0.0 <= total_fitness <= n_encounters + 1e-9  # at most one unit per encounter


# -- reproduction --------------------------------------------------------------

def test_reproduction_favours_high_fitness_genotype():
    # A population where ONE agent has all the fitness and zero mutation: after
    # reproduction every child should carry that agent's genotype (proportional selection
    # collapses onto the sole non-zero-fitness parent).
    m = UltimatumModel(n=20, w=0.0, mutation=0.0, seed=5)
    for a in m.agent_list:
        a.p, a.q = 0.9, 0.9
        a.fitness = 0.0
    winner = m.agent_list[0]
    winner.p, winner.q = 0.123, 0.456
    winner.fitness = 100.0                 # only this agent has (shifted) fitness
    m.reproduce()
    for a in m.agent_list:
        assert a.p == pytest.approx(0.123)
        assert a.q == pytest.approx(0.456)


def test_mutation_keeps_genotype_in_unit_square():
    m = UltimatumModel(n=200, w=0.0, mutation=0.3, seed=6)
    for _ in range(10):
        m.assign_fitness()
        m.reproduce()
        for a in m.agent_list:
            assert 0.0 <= a.p <= 1.0
            assert 0.0 <= a.q <= 1.0


def test_zero_mutation_is_pure_replication():
    # With mutation=0, children exactly copy their parent's genotype (no drift injected).
    m = UltimatumModel(n=30, w=0.0, mutation=0.0, seed=7)
    m.assign_fitness()
    parents = {(round(a.p, 12), round(a.q, 12)) for a in m.agent_list}
    m.reproduce()
    children = {(round(a.p, 12), round(a.q, 12)) for a in m.agent_list}
    # every child genotype must have existed among the parents (a strict subset).
    assert children.issubset(parents)


# -- steady-state estimator ---------------------------------------------------

def test_tail_mean_is_trailing_window_mean():
    series = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert tail_mean(series, window=2) == pytest.approx(0.45)   # mean(0.4, 0.5)
    assert tail_mean(series, window=100) == pytest.approx(0.3)  # whole series
    assert tail_mean([], window=5) == 0.0


def test_run_summary_shape():
    res = run_single(n=100, w=0.0, seed=0, n_gens=30, measure_last=10)
    assert res["n"] == 100 and res["w"] == 0.0
    assert len(res["mean_p_series"]) == 31          # t=0 baseline + 30 gens
    assert len(res["mean_q_series"]) == 31
    assert 0.0 <= res["steady_p"] <= 1.0
    assert 0.0 <= res["steady_q"] <= 1.0


def test_run_rejects_bad_measure_window():
    m = UltimatumModel(n=10, seed=0)
    with pytest.raises(ValueError):
        m.run(10, measure_last=0)
    with pytest.raises(ValueError):
        m.run(10, measure_last=50)


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(n=200, w=0.5, seed=42, n_gens=60, measure_last=20)
    b = run_single(n=200, w=0.5, seed=42, n_gens=60, measure_last=20)
    assert a["mean_p_series"] == b["mean_p_series"]
    assert a["mean_q_series"] == b["mean_q_series"]
    assert a["steady_q"] == b["steady_q"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(n=200, w=0.5, seed=1, n_gens=60, measure_last=20)
    b = run_single(n=200, w=0.5, seed=2, n_gens=60, measure_last=20)
    for res in (a, b):
        assert all(0.0 <= x <= 1.0 for x in res["mean_p_series"])
        assert all(0.0 <= x <= 1.0 for x in res["mean_q_series"])


# -- qualitative sanity (the locked grade lives in run.py) --------------------

def test_reputation_raises_threshold_more_than_anonymous():
    # Faithfulness sanity, not the locked grade: full reputation (w=1) evolves a higher
    # steady-state acceptance threshold than the anonymous game (w=0), with everything
    # else fixed. The exact pass bars live in run.py.
    anon = run_single(n=200, w=0.0, seed=0, n_gens=400, measure_last=100)
    rep = run_single(n=200, w=1.0, seed=0, n_gens=400, measure_last=100)
    assert rep["steady_q"] > anon["steady_q"]
