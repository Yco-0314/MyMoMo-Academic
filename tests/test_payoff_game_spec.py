"""Tests for PayoffGameSpec in MechanismSpec (ADR-014 Phase 2 codegen-emit).

Pins the schema slot that lets codegen DECLARE a runtime.PayoffGame: named-game
and matrix forms, validation (game name, square matrix, numeric, strategy_var
cross-check, dup names), and JSON roundtrip.
"""
from __future__ import annotations

from abm_auto.codegen.mechanism_spec import (
    AgentStateVar,
    MechanismSpec,
    PayoffGameSpec,
    ScenarioParam,
)


def _base(**overrides) -> MechanismSpec:
    kw = dict(
        scenario_params=[
            ScenarioParam(name="agent_num", type="int", default=50),
            ScenarioParam(name="periods", type="int", default=150),
        ],
        n_agents_param="agent_num",
        periods_param="periods",
        env_step_pseudocode="play + turnover",
        targets=["cooperator_fraction"],
        agent_state_vars=[AgentStateVar(name="strategy", type="int", init="0")],
    )
    kw.update(overrides)
    return MechanismSpec(**kw)


def test_no_payoff_games_is_the_common_case() -> None:
    spec = _base()
    assert spec.payoff_games == []
    assert spec.validate() == []


def test_named_game_with_strategy_var() -> None:
    spec = _base(payoff_games=[PayoffGameSpec(
        name="game", game="prisoners_dilemma",
        params={"T": 5, "R": 3, "P": 1, "S": 0}, strategy_var="strategy")])
    assert spec.validate() == []


def test_matrix_game() -> None:
    assert _base(payoff_games=[PayoffGameSpec(name="g", game="matrix",
                                              matrix=[[3, 0], [5, 1]])]).validate() == []


def test_unknown_game_rejected() -> None:
    assert any("game=" in e for e in
               _base(payoff_games=[PayoffGameSpec(name="g", game="chess")]).validate())


def test_non_square_matrix_rejected() -> None:
    assert any("square" in e for e in _base(payoff_games=[
        PayoffGameSpec(name="g", game="matrix", matrix=[[1, 2, 3], [4, 5, 6]])]).validate())


def test_non_numeric_matrix_rejected() -> None:
    assert any("numbers" in e for e in _base(payoff_games=[
        PayoffGameSpec(name="g", game="matrix", matrix=[[1, "x"], [0, 1]])]).validate())


def test_strategy_var_must_be_declared() -> None:
    assert any("strategy_var" in e for e in _base(payoff_games=[
        PayoffGameSpec(name="g", game="matrix", matrix=[[1, 0], [0, 1]],
                       strategy_var="ghost")]).validate())


def test_duplicate_game_name_rejected() -> None:
    g = PayoffGameSpec(name="g", game="matrix", matrix=[[1, 0], [0, 1]])
    assert any("duplicate" in e for e in _base(payoff_games=[g, g]).validate())


def test_json_roundtrip_preserves_payoff_game() -> None:
    spec = _base(payoff_games=[PayoffGameSpec(
        name="game", game="hawk_dove", params={"V": 2, "C": 4},
        strategy_var="strategy", description="Hawk-Dove")])
    back = MechanismSpec.from_json(spec.to_json())
    g = back.payoff_games[0]
    assert g.name == "game" and g.game == "hawk_dove" and g.params == {"V": 2, "C": 4}
    assert back.validate() == []


def test_none_roundtrips_empty() -> None:
    assert MechanismSpec.from_json(_base().to_json()).payoff_games == []
