"""Tests for the Coverage Gate deterministic core (ADR-014).

Pins the verdict logic with NO LLM: every mechanism named in the ADR-014
analysis lands in the right tier, the anti-flatten backstop holds, and tier-3
mechanisms route to build+verify.
"""
from __future__ import annotations

from abm_auto.codegen.coverage_gate import (
    CoverageGate,
    Mechanism,
    classify,
    self_test,
)


def test_self_test_passes() -> None:
    assert self_test() is True


# ── the six-fixture cross-failure-mode table ───────────────────────────────


def test_operator_covered_mechanisms_pass() -> None:
    gate = CoverageGate()
    mechs = [
        Mechanism("m", "learned_predictor", "single_item", "item_distribution", "supervised_pairs"),
        Mechanism("t", "population_process"),
        Mechanism("r", "lookup_table"),
    ]
    assert gate.check(mechs).passed


def test_gan_halts_uncovered() -> None:
    gan = Mechanism("gan", "generative_model",
                    markers=frozenset({"adversarial", "multi_network"}))
    v = CoverageGate().check([gan])
    assert not v.passed and v.uncovered == ["gan"]


def test_deep_rl_halts_tabular_q_passes() -> None:
    deep = Mechanism("deep", "reinforcement_learning", markers=frozenset({"reward", "multi_network"}))
    tab = Mechanism("tab", "reinforcement_learning", markers=frozenset({"reward"}),
                    std_algorithm="tabular_q_learning")
    assert not CoverageGate().check([deep]).passed
    assert CoverageGate().check([tab]).passed


def test_kalman_passes_particle_filter_halts() -> None:
    kal = Mechanism("k", "bayesian_filter", std_algorithm="kalman_filter")
    par = Mechanism("p", "bayesian_filter")
    assert CoverageGate().check([kal]).passed
    assert not CoverageGate().check([par]).passed


# ── anti-flatten guard (the load-bearing one) ──────────────────────────────


def test_reward_marker_overrides_supervised_label() -> None:
    """An RL learner the LLM mislabels 'supervised_pairs' must NOT pass as
    FeedforwardLearner — the reward marker forces reward_td, breaking the
    contract match. The deterministic backstop, not the LLM's word."""
    sneaky = Mechanism("sneaky", "learned_predictor",
                       "single_item", "item_distribution", "supervised_pairs",
                       markers=frozenset({"reward"}))
    assert classify(sneaky)[0] != "operator"
    assert not CoverageGate().check([sneaky]).passed


def test_partial_faithfulness_is_not_operator_covered() -> None:
    partial = Mechanism("p", "learned_predictor", "single_item", "item_distribution",
                        "supervised_pairs", faithfulness="partial")
    assert classify(partial)[0] != "operator"


def test_deep_markers_disqualify_learned_operator() -> None:
    deep = Mechanism("d", "learned_predictor", "single_item", "item_distribution",
                     "supervised_pairs", markers=frozenset({"multi_network"}))
    assert classify(deep)[0] != "operator"


# ── tier-3 build+verify routing ────────────────────────────────────────────


def test_stdlib_mechanisms_flagged_for_build_and_verify() -> None:
    gate = CoverageGate()
    v = gate.check([
        Mechanism("k", "bayesian_filter", std_algorithm="kalman_filter"),
        Mechanism("q", "reinforcement_learning", markers=frozenset({"reward"}),
                  std_algorithm="tabular_q_learning"),
    ])
    assert v.passed
    assert sorted(v.build_and_verify) == ["k", "q"]


def test_unverifiable_optimization_halts() -> None:
    custom = Mechanism("milp", "optimization")               # no named std algorithm
    simple = Mechanism("lp", "optimization", std_algorithm="linear_program")
    assert not CoverageGate().check([custom]).passed
    assert CoverageGate().check([simple]).passed


def test_market_mechanism_is_a_demand_signal() -> None:
    """No market operator yet → halt naming it (so a future operator is
    demand-driven, not speculative)."""
    v = CoverageGate().check([Mechanism("clear", "market_mechanism")])
    assert not v.passed and v.uncovered == ["clear"]
