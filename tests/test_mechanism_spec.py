"""Unit tests for MechanismSpec — schema validation + JSON roundtrip."""
from __future__ import annotations

import pytest

from abm_auto.codegen.mechanism_spec import (
    AgentStateVar,
    MechanismSpec,
    ScenarioParam,
    TopologySpec,
    VALID_TOPOLOGY_TYPES,
)


def _valid_sir_spec() -> MechanismSpec:
    """Build a well-formed SIR spec for use as a baseline in tests."""
    return MechanismSpec(
        project_name="VirusOnNetwork",
        model_class_name="VirusModel",
        agent_class_name="Person",
        environment_class_name="VirusEnvironment",
        scenario_class_name="VirusScenario",
        data_collector_class_name="VirusDataCollector",
        topology=TopologySpec(
            type="netlogo_spatially_clustered",
            params={"avg_degree": "scenario.average_degree"},
        ),
        scenario_params=[
            ScenarioParam(name="periods", type="int", default=250, unit="ticks"),
            ScenarioParam(name="agent_num", type="int", default=150, unit="count"),
            ScenarioParam(name="average_degree", type="int", default=6, unit="count"),
        ],
        agent_state_vars=[
            AgentStateVar(name="state", type="int", init="0"),
        ],
        targets=["count_s", "count_i", "count_r"],
        env_step_pseudocode="spread + recovery loop",
    )


# ── Validation ──────────────────────────────────────────────────────────


def test_valid_spec_passes() -> None:
    assert _valid_sir_spec().validate() == []


def test_bad_topology_type_caught() -> None:
    spec = _valid_sir_spec()
    spec.topology = TopologySpec(type="invented_topology", params={"foo": 1})
    errors = spec.validate()
    assert any("invented_topology" in e for e in errors)


def test_missing_topology_params_caught() -> None:
    spec = _valid_sir_spec()
    spec.topology = TopologySpec(type="watts_strogatz", params={"k": 6})  # missing p
    errors = spec.validate()
    assert any("p" in e and "missing" in e for e in errors), errors


def test_missing_n_agents_param_caught() -> None:
    """If n_agents_param doesn't exist in scenario_params, validation fails."""
    spec = _valid_sir_spec()
    spec.n_agents_param = "not_a_real_param"
    errors = spec.validate()
    assert any("not_a_real_param" in e for e in errors)


def test_empty_targets_caught() -> None:
    spec = _valid_sir_spec()
    spec.targets = []
    errors = spec.validate()
    assert any("targets" in e for e in errors)


def test_empty_env_step_pseudocode_caught() -> None:
    spec = _valid_sir_spec()
    spec.env_step_pseudocode = ""
    errors = spec.validate()
    assert any("env_step_pseudocode" in e for e in errors)


def test_duplicate_scenario_param_caught() -> None:
    spec = _valid_sir_spec()
    spec.scenario_params.append(
        ScenarioParam(name="periods", type="int", default=999, unit="ticks")
    )
    errors = spec.validate()
    assert any("duplicate" in e.lower() for e in errors)


def test_bad_python_type_caught() -> None:
    spec = _valid_sir_spec()
    spec.scenario_params.append(
        ScenarioParam(name="ratio", type="number", default=1.0)  # "number" not valid
    )
    errors = spec.validate()
    assert any("number" in e for e in errors)


def test_bad_class_name_caught() -> None:
    spec = _valid_sir_spec()
    spec.model_class_name = "1BadName"   # starts with digit, not valid identifier
    errors = spec.validate()
    assert any("model_class_name" in e for e in errors)


# ── Roundtrip ───────────────────────────────────────────────────────────


def test_json_roundtrip_preserves_all_fields() -> None:
    original = _valid_sir_spec()
    js = original.to_json()
    restored = MechanismSpec.from_json(js)
    assert restored.validate() == []
    assert restored.project_name == original.project_name
    assert restored.topology.type == original.topology.type
    assert restored.topology.params == original.topology.params
    assert len(restored.scenario_params) == len(original.scenario_params)
    assert restored.scenario_params[0].name == original.scenario_params[0].name
    assert restored.scenario_params[0].unit == original.scenario_params[0].unit
    assert len(restored.agent_state_vars) == len(original.agent_state_vars)
    assert restored.targets == original.targets


def test_from_dict_with_defaults_only() -> None:
    """from_dict tolerates a minimal dict — uses dataclass defaults for missing fields.

    Note: defaults still need overriding for `topology.params` and
    a few other fields to pass validation; this test asserts the dict
    is LOADABLE, not that the defaults form a valid spec.
    """
    minimal = {
        "scenario_params": [
            {"name": "periods", "type": "int", "default": 100, "unit": "ticks"},
            {"name": "agent_num", "type": "int", "default": 10, "unit": "count"},
        ],
        "targets": ["m"],
        "env_step_pseudocode": "noop",
        "topology": {"type": "watts_strogatz", "params": {"k": 6, "p": 0.1}},
    }
    spec = MechanismSpec.from_dict(minimal)
    assert spec.validate() == []
    assert spec.topology.type == "watts_strogatz"
    assert spec.n_agents_param == "agent_num"


# ── Topology catalog ────────────────────────────────────────────────────


@pytest.mark.parametrize("topology_type", sorted(VALID_TOPOLOGY_TYPES))
def test_every_topology_type_has_required_params_table(topology_type: str) -> None:
    """Every entry in VALID_TOPOLOGY_TYPES must have an entry in TOPOLOGY_REQUIRED_PARAMS."""
    from abm_auto.codegen.mechanism_spec import TOPOLOGY_REQUIRED_PARAMS
    assert topology_type in TOPOLOGY_REQUIRED_PARAMS
