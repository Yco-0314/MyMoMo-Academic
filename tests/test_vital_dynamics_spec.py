"""Tests for VitalDynamicsSpec in MechanismSpec (ADR-014 Phase 2 codegen-emit).

Pins the schema slot that lets codegen DECLARE a runtime.VitalDynamics:
threshold/probabilistic reproduction, validation (reproduction rule required,
prob range, max_population, energy_attr cross-check, dup names), JSON roundtrip.
"""
from __future__ import annotations

from abm_auto.codegen.mechanism_spec import (
    AgentStateVar,
    MechanismSpec,
    ScenarioParam,
    VitalDynamicsSpec,
)


def _base(**overrides) -> MechanismSpec:
    kw = dict(
        scenario_params=[
            ScenarioParam(name="agent_num", type="int", default=50),
            ScenarioParam(name="periods", type="int", default=150),
        ],
        n_agents_param="agent_num",
        periods_param="periods",
        env_step_pseudocode="energy + birth/death",
        targets=["population"],
        agent_state_vars=[AgentStateVar(name="energy", type="float", init="10.0")],
    )
    kw.update(overrides)
    return MechanismSpec(**kw)


def test_no_vital_dynamics_is_the_common_case() -> None:
    spec = _base()
    assert spec.vital_dynamics == []
    assert spec.validate() == []


def test_threshold_reproduction_valid() -> None:
    assert _base(vital_dynamics=[VitalDynamicsSpec(
        name="vital", energy_attr="energy", reproduce_at=20, max_population=200)]).validate() == []


def test_probabilistic_reproduction_valid() -> None:
    assert _base(vital_dynamics=[VitalDynamicsSpec(
        name="vital", energy_attr="energy", reproduce_prob=0.3)]).validate() == []


def test_reproduction_rule_required() -> None:
    assert any("reproduce_at OR" in e for e in _base(vital_dynamics=[
        VitalDynamicsSpec(name="v", energy_attr="energy")]).validate())


def test_reproduce_prob_range_checked() -> None:
    assert any("reproduce_prob" in e for e in _base(vital_dynamics=[
        VitalDynamicsSpec(name="v", energy_attr="energy", reproduce_prob=1.5)]).validate())


def test_max_population_positive_int() -> None:
    assert any("max_population" in e for e in _base(vital_dynamics=[
        VitalDynamicsSpec(name="v", energy_attr="energy", reproduce_at=5, max_population=0)]).validate())


def test_energy_attr_must_be_declared() -> None:
    assert any("energy_attr" in e and "ghost" in e for e in _base(vital_dynamics=[
        VitalDynamicsSpec(name="v", energy_attr="ghost", reproduce_at=5)]).validate())


def test_duplicate_name_rejected() -> None:
    v = VitalDynamicsSpec(name="v", energy_attr="energy", reproduce_at=5)
    assert any("duplicate" in e for e in _base(vital_dynamics=[v, v]).validate())


def test_json_roundtrip_preserves_vital_dynamics() -> None:
    spec = _base(vital_dynamics=[VitalDynamicsSpec(
        name="vital", energy_attr="energy", death_at=0, reproduce_prob=0.25,
        max_population=300, description="rabbits")])
    back = MechanismSpec.from_json(spec.to_json())
    v = back.vital_dynamics[0]
    assert v.name == "vital" and v.reproduce_prob == 0.25 and v.max_population == 300
    assert back.validate() == []


def test_none_roundtrips_empty() -> None:
    assert MechanismSpec.from_json(_base().to_json()).vital_dynamics == []
