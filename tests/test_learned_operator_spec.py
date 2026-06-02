"""Tests for LearnedOperator in MechanismSpec (ADR-013 W2 fix, block 2).

The schema concept that was MISSING when the Yaman reproduction flattened
a trainable semantic net into scalars. Pins: validation of the operator's
shape, the n_items→scenario_param reference check, name-collision with
agent_state_vars, and JSON roundtrip.
"""
from __future__ import annotations

from abm_auto.codegen.mechanism_spec import (
    AgentStateVar,
    LearnedOperator,
    MechanismSpec,
    ScenarioParam,
)


def _base_spec(**overrides) -> MechanismSpec:
    kw = dict(
        scenario_params=[
            ScenarioParam(name="agent_num", type="int", default=100),
            ScenarioParam(name="periods", type="int", default=50),
        ],
        n_agents_param="agent_num",
        periods_param="periods",
        env_step_pseudocode="pass",
        targets=["mean_innovation_count"],
    )
    kw.update(overrides)
    return MechanismSpec(**kw)


# ── operator-level validation ───────────────────────────────────────────


def test_valid_operator_with_int_n_items() -> None:
    spec = _base_spec(
        learned_operators=[LearnedOperator(name="semantic_model", n_items=96)]
    )
    assert spec.validate() == []


def test_valid_operator_with_param_ref_n_items() -> None:
    spec = _base_spec(
        scenario_params=[
            ScenarioParam(name="n_items", type="int", default=96),
            ScenarioParam(name="agent_num", type="int", default=100),
            ScenarioParam(name="periods", type="int", default=50),
        ],
        learned_operators=[LearnedOperator(name="semantic_model", n_items="n_items")],
    )
    assert spec.validate() == []


def test_n_items_too_small_rejected() -> None:
    spec = _base_spec(learned_operators=[LearnedOperator(name="m", n_items=1)])
    assert any("n_items=1 must be >= 2" in e for e in spec.validate())


def test_n_items_bool_rejected() -> None:
    spec = _base_spec(learned_operators=[LearnedOperator(name="m", n_items=True)])
    assert any("bool" in e for e in spec.validate())


def test_bad_dims_rejected() -> None:
    spec = _base_spec(
        learned_operators=[LearnedOperator(name="m", n_items=8, embed_dim=0, hidden_dim=-2)]
    )
    errs = spec.validate()
    assert any("embed_dim=0" in e for e in errs)
    assert any("hidden_dim=-2" in e for e in errs)


def test_bad_learning_rate_rejected() -> None:
    spec = _base_spec(
        learned_operators=[LearnedOperator(name="m", n_items=8, learning_rate=0)]
    )
    assert any("learning_rate" in e for e in spec.validate())


# ── spec-level cross-checks ─────────────────────────────────────────────


def test_n_items_param_ref_must_exist() -> None:
    spec = _base_spec(learned_operators=[LearnedOperator(name="m", n_items="ghost")])
    assert any("ghost' is not a declared scenario_param" in e for e in spec.validate())


def test_name_collision_with_state_var_rejected() -> None:
    spec = _base_spec(
        agent_state_vars=[AgentStateVar(name="semantic_model", type="int", init="0")],
        learned_operators=[LearnedOperator(name="semantic_model", n_items=8)],
    )
    assert any("collides with an agent_state_var" in e for e in spec.validate())


def test_invalid_operator_name_rejected() -> None:
    spec = _base_spec(learned_operators=[LearnedOperator(name="2bad", n_items=8)])
    assert any("not a valid identifier" in e for e in spec.validate())


# ── roundtrip ───────────────────────────────────────────────────────────


def test_json_roundtrip_preserves_operators() -> None:
    spec = _base_spec(
        learned_operators=[
            LearnedOperator(name="semantic_model", n_items=96, embed_dim=16,
                            hidden_dim=16, learning_rate=0.001,
                            description="Yaman distributional semantic model"),
        ]
    )
    back = MechanismSpec.from_json(spec.to_json())
    assert len(back.learned_operators) == 1
    lo = back.learned_operators[0]
    assert lo.name == "semantic_model"
    assert lo.n_items == 96
    assert lo.embed_dim == 16
    assert lo.learning_rate == 0.001
    assert back.validate() == []


def test_empty_operators_is_the_common_case() -> None:
    """Most specs have no learned operators — must validate fine + roundtrip."""
    spec = _base_spec()
    assert spec.learned_operators == []
    assert MechanismSpec.from_json(spec.to_json()).learned_operators == []
