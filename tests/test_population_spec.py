"""Tests for PopulationDynamicsSpec + MoranProcess (ADR-013 W4 harvest).

The schema slot + runtime operator harvested from the Yaman reproduction's
Moran turnover. Pins: spec validation (death models, rates, identifiers),
the inherit/reset cross-check against declared agent attrs, JSON roundtrip,
and the runtime operator's invariants (fixed N, fitness-proportional
selection, age-based Gompertz death).
"""
from __future__ import annotations

import random

from abm_auto.codegen.mechanism_spec import (
    AgentStateVar,
    LearnedOperator,
    MechanismSpec,
    PopulationDynamicsSpec,
    ScenarioParam,
)
from abm_auto.runtime import MoranProcess
from abm_auto.runtime._population import self_test as population_self_test


def _base(**overrides) -> MechanismSpec:
    kw = dict(
        scenario_params=[
            ScenarioParam(name="agent_num", type="int", default=50),
            ScenarioParam(name="periods", type="int", default=150),
        ],
        n_agents_param="agent_num",
        periods_param="periods",
        env_step_pseudocode="one generation",
        targets=["repertoire_size"],
        agent_state_vars=[
            AgentStateVar(name="inventory", type="str", init="set()"),
            AgentStateVar(name="score", type="float", init="0.0"),
            AgentStateVar(name="age", type="int", init="0"),
        ],
        learned_operators=[LearnedOperator(name="semantic_model", n_items=96)],
    )
    kw.update(overrides)
    return MechanismSpec(**kw)


# ── spec validation ──────────────────────────────────────────────────────


def test_no_population_dynamics_is_the_common_case() -> None:
    spec = _base()
    assert spec.population_dynamics is None
    assert spec.validate() == []


def test_valid_moran_inheriting_learned_operator() -> None:
    spec = _base(population_dynamics=PopulationDynamicsSpec(
        fitness_attr="score", death_model="gompertz",
        inherit_attrs=["semantic_model"], reset_attrs=["inventory", "score"],
    ))
    assert spec.validate() == []


def test_constant_death_rate_must_be_a_probability() -> None:
    spec = _base(population_dynamics=PopulationDynamicsSpec(
        death_model="constant", death_rate=1.5))
    assert any("death_rate" in e for e in spec.validate())


def test_unknown_death_model_rejected() -> None:
    spec = _base(population_dynamics=PopulationDynamicsSpec(death_model="exponential"))
    assert any("death_model" in e for e in spec.validate())


def test_gompertz_constants_must_be_positive() -> None:
    spec = _base(population_dynamics=PopulationDynamicsSpec(
        death_model="gompertz", gompertz_a=0, gompertz_b=-1))
    assert any("gompertz" in e for e in spec.validate())


def test_inherit_attr_must_name_a_declared_attribute() -> None:
    spec = _base(population_dynamics=PopulationDynamicsSpec(inherit_attrs=["ghost"]))
    assert any("ghost" in e and "inherit_attrs" in e for e in spec.validate())


def test_reset_attr_must_name_a_declared_attribute() -> None:
    spec = _base(population_dynamics=PopulationDynamicsSpec(reset_attrs=["nope"]))
    assert any("nope" in e and "reset_attrs" in e for e in spec.validate())


def test_json_roundtrip_preserves_population_dynamics() -> None:
    spec = _base(population_dynamics=PopulationDynamicsSpec(
        fitness_attr="score", death_model="gompertz",
        gompertz_a=0.0001365, gompertz_b=0.2097,
        inherit_attrs=["semantic_model"], reset_attrs=["inventory", "score"],
        description="Yaman Moran turnover"))
    back = MechanismSpec.from_json(spec.to_json())
    pd = back.population_dynamics
    assert pd is not None
    assert pd.death_model == "gompertz"
    assert pd.inherit_attrs == ["semantic_model"]
    assert pd.reset_attrs == ["inventory", "score"]
    assert back.validate() == []


def test_none_roundtrips_as_none() -> None:
    assert MechanismSpec.from_json(_base().to_json()).population_dynamics is None


# ── runtime operator ─────────────────────────────────────────────────────


def test_runtime_self_test_passes() -> None:
    assert population_self_test() is True


def test_turnover_holds_population_constant() -> None:
    class _A:
        pass

    agents = []
    for i in range(30):
        a = _A(); a.score = float(i); a.age = 0
        agents.append(a)
    mp = MoranProcess(fitness_attr="score", death_model="constant",
                      death_rate=0.25, seed=1)
    rng = random.Random(1)

    def inherit(child, parent):
        child.score = 0.0

    for _ in range(40):
        mp.turnover(agents, inherit=inherit, rng=rng)
        assert len(agents) == 30


def test_gompertz_death_rises_with_age() -> None:
    class _A:
        pass

    mp = MoranProcess(death_model="gompertz")
    young = _A(); young.age = 0
    old = _A(); old.age = 40
    assert mp.death_probability(young) < mp.death_probability(old)
    assert mp.death_probability(young) < 0.01


def test_invalid_death_model_raises() -> None:
    import pytest
    with pytest.raises(ValueError):
        MoranProcess(death_model="quadratic")
