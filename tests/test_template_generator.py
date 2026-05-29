"""Unit tests for TemplateGenerator — emit valid Python that compiles."""
from __future__ import annotations

import ast

import pytest

from abm_auto.codegen.mechanism_spec import (
    AgentStateVar,
    MechanismSpec,
    ScenarioParam,
    TopologySpec,
)
from abm_auto.codegen.template_generator import (
    TEMPLATE_FILES,
    generate_all,
    generate_data_collector_py,
    generate_main_py,
    generate_model_py,
    generate_scenario_py,
    generate_scenarios_csv,
    is_template_file,
)


def _valid_sir_spec() -> MechanismSpec:
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
            ScenarioParam(
                name="virus_spread_chance", type="float", default=4.4,
                unit="percent", min=0, max=20,
            ),
        ],
        agent_state_vars=[
            AgentStateVar(name="state", type="int", init="0"),
        ],
        targets=["count_s", "count_i", "count_r"],
        env_step_pseudocode="loop",
        initial_setup_pseudocode="seed initial outbreak",
    )


# ── Each generator emits parseable Python ───────────────────────────────


@pytest.mark.parametrize(
    "generator",
    [
        generate_model_py,
        generate_scenario_py,
        generate_data_collector_py,
        generate_main_py,
    ],
)
def test_generators_emit_valid_python(generator) -> None:
    """ast.parse must accept every generator's output."""
    spec = _valid_sir_spec()
    source = generator(spec)
    # Will raise SyntaxError if generator emitted bad code
    ast.parse(source)


# ── Topology rendering — the actual root cause of the dogfood breakage ──


def test_topology_call_does_not_include_n_kwarg() -> None:
    """The dogfood bug: LLM kept writing `watts_strogatz(n=150, ...)`. The
    template renderer must NEVER include `n=` because n is auto-derived
    from agent_lists by Network.setup_agent_connections.
    """
    spec = _valid_sir_spec()
    model_src = generate_model_py(spec)
    assert "n=" not in model_src, (
        "TemplateGenerator emitted `n=...` in topology call — this is the "
        "exact bug Layer 3 was meant to prevent. Check _render_topology_call."
    )


def test_topology_scenario_reference_renders_unquoted() -> None:
    """A param value like 'scenario.average_degree' must render as the
    Python identifier `self.scenario.average_degree`, not a quoted string.
    """
    spec = _valid_sir_spec()
    model_src = generate_model_py(spec)
    assert "self.scenario.average_degree" in model_src
    assert '"scenario.average_degree"' not in model_src
    assert "'scenario.average_degree'" not in model_src


@pytest.mark.parametrize(
    "topology_type,params,expected_substring",
    [
        ("watts_strogatz", {"k": 6, "p": 0.1}, "topologies.watts_strogatz(k=6, p=0.1)"),
        ("barabasi_albert", {"m": 3}, "topologies.barabasi_albert(m=3)"),
        ("erdos_renyi", {"p": 0.05}, "topologies.erdos_renyi(p=0.05)"),
        (
            "netlogo_spatially_clustered", {"avg_degree": 6},
            "topologies.netlogo_spatially_clustered(avg_degree=6)",
        ),
    ],
)
def test_topology_renders_each_adapter_correctly(
    topology_type: str, params: dict, expected_substring: str,
) -> None:
    spec = _valid_sir_spec()
    spec.topology = TopologySpec(type=topology_type, params=params)
    src = generate_model_py(spec)
    assert expected_substring in src


# ── Scenario class has every param ──────────────────────────────────────


def test_scenario_py_declares_every_param() -> None:
    spec = _valid_sir_spec()
    src = generate_scenario_py(spec)
    for p in spec.scenario_params:
        assert f"self.{p.name}" in src
        # Type annotation
        assert f": {p.type}" in src
        # Default value
        assert repr(p.default) in src or str(p.default) in src


def test_scenario_unit_comment_present_when_declared() -> None:
    spec = _valid_sir_spec()
    src = generate_scenario_py(spec)
    # virus_spread_chance has unit="percent" + range, both should appear in the
    # trailing comment
    assert "percent" in src
    assert "range [0, 20]" in src


# ── DataCollector registers every target ───────────────────────────────


def test_data_collector_registers_every_target() -> None:
    spec = _valid_sir_spec()
    src = generate_data_collector_py(spec)
    for target in spec.targets:
        assert f'add_environment_property("{target}")' in src


# ── CSV header matches scenario_params ─────────────────────────────────


def test_scenarios_csv_header_matches_params() -> None:
    spec = _valid_sir_spec()
    csv = generate_scenarios_csv(spec)
    header_row = csv.splitlines()[0]
    cols = header_row.split(",")
    # id + run_num are Melodie-required infrastructure cols
    assert cols[0] == "id"
    assert cols[1] == "run_num"
    # Every scenario_param must appear
    for p in spec.scenario_params:
        assert p.name in cols


def test_scenarios_csv_has_one_default_row() -> None:
    spec = _valid_sir_spec()
    csv = generate_scenarios_csv(spec)
    lines = [l for l in csv.splitlines() if l.strip()]
    assert len(lines) == 2  # header + one data row


# ── Bundle ──────────────────────────────────────────────────────────────


def test_generate_all_returns_every_template_file() -> None:
    spec = _valid_sir_spec()
    files = generate_all(spec)
    assert set(files.keys()) == set(TEMPLATE_FILES)


# ── topology=None branch (Grid / spatial-free models) ──────────────────


def test_topology_free_model_py_skips_network_setup() -> None:
    """When spec.topology is None, model.py must NOT mention Network or topologies."""
    spec = _valid_sir_spec()
    spec.topology = None
    src = generate_model_py(spec)
    # No Network references
    assert "self.network" not in src
    assert "create_network" not in src
    assert "setup_agent_connections" not in src
    assert "topologies." not in src
    # Imports adjusted — no `topologies` import
    assert "import topologies" not in src
    # environment.step() signature drops the network arg
    assert "self.environment.step(self.agents, self.scenario)" in src


def test_topology_free_model_py_compiles() -> None:
    import ast
    spec = _valid_sir_spec()
    spec.topology = None
    ast.parse(generate_model_py(spec))


def test_topology_free_model_py_still_creates_agents_and_env() -> None:
    spec = _valid_sir_spec()
    spec.topology = None
    src = generate_model_py(spec)
    assert "create_agent_list" in src
    assert "create_environment" in src
    assert "create_data_collector" in src
    # initialize hook takes (agents, scenario), not (agents, network, scenario)
    assert "self.environment.initialize(self.agents, self.scenario)" in src


def test_network_model_py_still_includes_network() -> None:
    """Regression — topology=set still produces the existing happy-path output."""
    spec = _valid_sir_spec()
    # topology is already set in _valid_sir_spec
    assert spec.topology is not None
    src = generate_model_py(spec)
    assert "self.network = self.create_network()" in src
    assert "setup_agent_connections" in src


def test_is_template_file_recognises_template_files() -> None:
    assert is_template_file("core/model.py")
    assert is_template_file("core/scenario.py")
    assert is_template_file("data/input/SimulatorScenarios.csv")
    assert not is_template_file("core/agent.py")           # LLM-owned
    assert not is_template_file("core/environment.py")    # LLM-owned
    assert not is_template_file("README.md")
