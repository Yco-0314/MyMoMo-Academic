"""Faithful-rule + determinism tests for the Granovetter (1978) threshold model.

These pin the GLOBAL-count rule (act iff active_count >= threshold), the monotone
once-acting-stays-acting convention, hand-verifiable cascades on tiny threshold sets,
the two locked distributions' equilibria, and determinism (no RNG -> identical result
every run). They are faithfulness tests, NOT prediction tests (the locked predictions
P1-P3 are evaluated by examples/repro_granovetter_threshold/run.py).
"""
from __future__ import annotations

from abm_auto.classics.granovetter_threshold import (
    ThresholdAgent,
    ThresholdModel,
    perturbed_thresholds,
    run_distribution,
    uniform_thresholds,
)


# -- hand-verifiable tiny cascades --------------------------------------------

def test_tiny_full_cascade_is_hand_verifiable():
    # Thresholds {0, 1, 1}. Round 1: count 0 -> only thr-0 acts (count 1).
    # Round 2: count 1 -> both thr-1 agents act too (count 3). Round 3: no change.
    res = ThresholdModel([0, 1, 1]).run()
    assert res["equilibrium"] == 3
    assert res["active_series"] == [0, 1, 3, 3]
    assert res["n"] == 3


def test_gap_stalls_cascade_at_instigator():
    # Thresholds {0, 2}. Round 1: count 0 -> thr-0 acts (count 1). Round 2: count 1
    # < 2, so the thr-2 agent never joins -> stalls at 1 (the trailing 1 is the
    # terminal no-change round that confirms the fixed point).
    res = ThresholdModel([0, 2]).run()
    assert res["equilibrium"] == 1
    assert res["active_series"] == [0, 1, 1]


def test_no_instigator_means_no_one_acts():
    # Every threshold >= 1: with count 0 nobody can start. Equilibrium = 0.
    res = ThresholdModel([1, 1, 2, 3]).run()
    assert res["equilibrium"] == 0
    assert res["active_series"] == [0, 0]


def test_global_count_rule_exact_boundary():
    # An agent acts iff active_count >= its threshold (>=, not >). Drive directly:
    # with two acting, a threshold-2 agent flips; a threshold-3 agent does not.
    model = ThresholdModel([0, 0, 2, 3])
    model.agent_list[0].acting = True
    model.agent_list[1].acting = True  # active_count() == 2
    assert model.active_count() == 2
    thr2 = next(a for a in model.agent_list if a.threshold == 2)
    thr3 = next(a for a in model.agent_list if a.threshold == 3)
    thr2.step(); thr3.step()
    assert thr2._next_acting is True   # 2 >= 2
    assert thr3._next_acting is False  # 2 < 3


def test_monotone_once_acting_stays_acting():
    model = ThresholdModel([0, 1, 1])
    model.run()  # all three acting
    for a in model.agent_list:
        assert a.acting is True
    # A further manual round must not deactivate anyone.
    for a in model.agent_list:
        a.step()
    for a in model.agent_list:
        assert a._next_acting is True


# -- the two locked distributions ---------------------------------------------

def test_uniform_distribution_cascades_to_all():
    # P1's distribution: {0,1,...,99}. Each round adds exactly one actor (the next
    # threshold), marching to all 100.
    res = run_distribution(uniform_thresholds(100))
    assert res["n"] == 100
    assert res["equilibrium"] == 100
    # One new actor per round, 0..100, then a terminal no-change round at 100.
    assert res["active_series"] == list(range(101)) + [100]
    assert res["mean_threshold"] == 49.5


def test_perturbed_distribution_stalls_at_one():
    # P2's distribution: {0,2,2,3,...,99} (gap at 1). thr-0 acts -> count 1; the two
    # thr-2 agents need count >= 2 and never get it -> stalls at the instigator.
    res = run_distribution(perturbed_thresholds(100))
    assert res["n"] == 100
    assert res["equilibrium"] == 1
    # [0] baseline, [1] after the instigator acts, [1] terminal no-change round.
    assert res["active_series"] == [0, 1, 1]
    assert res["mean_threshold"] == 49.51


def test_perturbed_multiset_is_the_locked_one():
    # Exact multiset check: remove one 1, add one 2; no agent at threshold 1.
    thr = perturbed_thresholds(100)
    assert len(thr) == 100
    assert thr.count(1) == 0
    assert thr.count(2) == 2
    assert thr.count(0) == 1
    # Sum is exactly the uniform sum + 1 (mean-invariant to ~0.02%).
    assert sum(thr) == sum(uniform_thresholds(100)) + 1


def test_mean_invariance_of_the_perturbation():
    mean_u = sum(uniform_thresholds(100)) / 100
    mean_p = sum(perturbed_thresholds(100)) / 100
    assert abs(mean_u - mean_p) < 0.1   # 49.5 vs 49.51, Delta = 0.01


# -- determinism (no RNG) -----------------------------------------------------

def test_determinism_no_rng_identical_results():
    a = run_distribution(uniform_thresholds(100))
    b = run_distribution(uniform_thresholds(100))
    assert a == b
    c = run_distribution(perturbed_thresholds(100))
    d = run_distribution(perturbed_thresholds(100))
    assert c == d


def test_order_independence_synchronous_commit():
    # The synchronous commit makes the equilibrium independent of input order.
    forward = ThresholdModel([0, 1, 2, 3, 4]).run()
    shuffled = ThresholdModel([3, 0, 4, 1, 2]).run()
    assert forward["equilibrium"] == shuffled["equilibrium"] == 5
    assert forward["active_series"] == shuffled["active_series"]
