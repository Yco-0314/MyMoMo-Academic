"""MechanismSpec — structured contract between MechanismExtractor and TemplateGenerator.

This dataclass is the single source of truth that lets `template_generator`
emit 100%-correct boilerplate Python files (model.py, scenario.py,
data_collector.py, main.py, SimulatorScenarios.csv) without LLM
involvement. The CoderAgent's narrowed job is to fill ONLY the
mechanism bodies in agent.py and environment.py.

Pipeline placement
------------------

    DesignAgent → DESIGN.md
        ↓
    MechanismExtractor → mechanism_spec.json (THIS SCHEMA)
                       → mechanism_spec.md (human-readable, audit trail)
        ↓
    TemplateGenerator → 5 boilerplate files (deterministic, no LLM)
        ↓
    CoderAgent → fills agent.py + environment.py mechanism bodies only
        ↓
    Verifier → dry_run + anti_pattern + fidelity validators (unchanged)

Why this exists
---------------
Dogfood on 2026-05-29 revealed the Topology callable API (commit 276c1a9)
broke codegen: LLM kept writing `topologies.watts_strogatz(n=150, k=6, p=0.1)`
when the correct shape is `topologies.watts_strogatz(k=6, p=0.1)` (n comes
from agent_list automatically). 5 GVR retries didn't recover. Root cause:
the boilerplate that wires Topology/Network/Scenario is mechanical, but
the LLM has to re-derive it every time and gets it wrong.

Layer 3 of the fix architecture: stop asking the LLM to write boilerplate.
Generate it from a schema. LLM only fills the genuinely mechanism-specific
parts (the inner step() bodies that encode the actual research model).

Why stdlib dataclasses (not Pydantic)
-------------------------------------
- Zero new deps (Pydantic is heavy)
- to_dict / from_dict written by hand keeps the JSON shape under our
  control rather than buried in a serializer's conventions
- Validation lives in `validate()` method, called after from_dict; explicit
  rather than auto-magical
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


# Topology types correspond 1-to-1 with the adapters in
# abm_auto/runtime/_topologies.py. The string is what TemplateGenerator
# uses to emit `topologies.<type>(...)`.
VALID_TOPOLOGY_TYPES = {
    "watts_strogatz",
    "barabasi_albert",
    "erdos_renyi",
    "netlogo_spatially_clustered",
    "melodie_named",
}

# Map topology type → required param names. Used by validate() so missing
# params surface at JSON-parse time, not at simulator runtime.
TOPOLOGY_REQUIRED_PARAMS: dict[str, set[str]] = {
    "watts_strogatz": {"k", "p"},
    "barabasi_albert": {"m"},
    "erdos_renyi": {"p"},
    "netlogo_spatially_clustered": {"avg_degree"},
    "melodie_named": {"name"},  # plus arbitrary kwargs
}

VALID_PYTHON_TYPES = {"int", "float", "bool", "str"}


@dataclass
class TopologySpec:
    """Which topology adapter to call + what params to bind.

    `params` values are emitted into the template as Python source. Two
    forms are supported:
      - literals: 6, 0.1, "foo"  (TemplateGenerator emits them via repr())
      - scenario references: "scenario.average_degree" (passed through)
    """
    type: str
    params: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.type not in VALID_TOPOLOGY_TYPES:
            errors.append(
                f"topology.type={self.type!r} not in {sorted(VALID_TOPOLOGY_TYPES)}"
            )
        required = TOPOLOGY_REQUIRED_PARAMS.get(self.type, set())
        missing = required - set(self.params.keys())
        if missing:
            errors.append(
                f"topology.params missing required keys for {self.type!r}: {sorted(missing)}"
            )
        return errors


@dataclass
class ScenarioParam:
    """One row in the scenario CSV + one attribute on the Scenario class."""
    name: str
    type: str   # "int" | "float" | "bool" | "str"
    default: Any
    unit: str = ""   # "percent", "probability", "count", "ticks", ...
    min: Optional[float] = None
    max: Optional[float] = None
    description: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name or not self.name.isidentifier():
            errors.append(f"scenario_param.name={self.name!r} not a valid identifier")
        if self.type not in VALID_PYTHON_TYPES:
            errors.append(
                f"scenario_param.{self.name}.type={self.type!r} not in {sorted(VALID_PYTHON_TYPES)}"
            )
        return errors


@dataclass
class AgentStateVar:
    """One agent-level state variable initialised in agent.setup()."""
    name: str
    type: str
    init: str = "0"   # Python expression as source string

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name or not self.name.isidentifier():
            errors.append(f"agent_state_var.name={self.name!r} not a valid identifier")
        if self.type not in VALID_PYTHON_TYPES:
            errors.append(
                f"agent_state_var.{self.name}.type={self.type!r} not in {sorted(VALID_PYTHON_TYPES)}"
            )
        return errors


@dataclass
class MechanismSpec:
    """Full structured spec — the contract between MechanismExtractor and the
    template-driven codegen pipeline.

    Naming fields determine class names + filenames; structure fields
    determine what TemplateGenerator emits; pseudocode fields are what
    CoderAgent fills into agent.py / environment.py.
    """
    # ── Naming (the LLM picks these from the design) ──
    project_name: str = "ABMProject"          # used in Config(project_name=...)
    model_class_name: str = "MyModel"          # class in core/model.py
    agent_class_name: str = "MyAgent"          # class in core/agent.py
    environment_class_name: str = "MyEnvironment"
    scenario_class_name: str = "MyScenario"
    data_collector_class_name: str = "MyDataCollector"

    # ── Structure ──
    topology: TopologySpec = field(default_factory=lambda: TopologySpec(type="watts_strogatz", params={"k": 6, "p": 0.1}))
    n_agents_param: str = "agent_num"         # scenario field holding agent count
    periods_param: str = "periods"             # scenario field holding tick count

    # ── Data ──
    scenario_params: list[ScenarioParam] = field(default_factory=list)
    agent_state_vars: list[AgentStateVar] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)   # env attributes data_collector tracks

    # ── LLM-filled regions (kept as pseudocode) ──
    env_step_pseudocode: str = ""
    agent_step_pseudocode: Optional[str] = None        # None when all logic in env.step
    initial_setup_pseudocode: str = ""                 # extra setup in model.setup()

    # ── Free-form notes for the LLM (not used by templates) ──
    notes: str = ""

    # ── Roundtripping ──

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MechanismSpec":
        # Hand-coded so nested dataclasses get reconstructed (asdict /
        # auto-from-dict don't handle nested @dataclass without help).
        top_raw = data.get("topology", {})
        topology = TopologySpec(
            type=top_raw.get("type", "watts_strogatz"),
            params=dict(top_raw.get("params", {})),
        )
        scenario_params = [ScenarioParam(**p) for p in data.get("scenario_params", [])]
        agent_state_vars = [AgentStateVar(**v) for v in data.get("agent_state_vars", [])]
        return cls(
            project_name=data.get("project_name", "ABMProject"),
            model_class_name=data.get("model_class_name", "MyModel"),
            agent_class_name=data.get("agent_class_name", "MyAgent"),
            environment_class_name=data.get("environment_class_name", "MyEnvironment"),
            scenario_class_name=data.get("scenario_class_name", "MyScenario"),
            data_collector_class_name=data.get("data_collector_class_name", "MyDataCollector"),
            topology=topology,
            n_agents_param=data.get("n_agents_param", "agent_num"),
            periods_param=data.get("periods_param", "periods"),
            scenario_params=scenario_params,
            agent_state_vars=agent_state_vars,
            targets=list(data.get("targets", [])),
            env_step_pseudocode=data.get("env_step_pseudocode", ""),
            agent_step_pseudocode=data.get("agent_step_pseudocode"),
            initial_setup_pseudocode=data.get("initial_setup_pseudocode", ""),
            notes=data.get("notes", ""),
        )

    def to_json(self, **dumps_kwargs) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **dumps_kwargs)

    @classmethod
    def from_json(cls, s: str) -> "MechanismSpec":
        return cls.from_dict(json.loads(s))

    # ── Validation ──

    def validate(self) -> list[str]:
        """Return list of human-readable errors. Empty list = valid."""
        errors: list[str] = []
        # Naming sanity
        for label, value in [
            ("project_name", self.project_name),
            ("model_class_name", self.model_class_name),
            ("agent_class_name", self.agent_class_name),
            ("environment_class_name", self.environment_class_name),
            ("scenario_class_name", self.scenario_class_name),
        ]:
            if not value or not value.isidentifier():
                errors.append(f"{label}={value!r} not a valid Python identifier")
        # Topology
        errors.extend(f"topology: {e}" for e in self.topology.validate())
        # Scenario params
        param_names_seen: set[str] = set()
        for p in self.scenario_params:
            errors.extend(f"scenario_params[{p.name}]: {e}" for e in p.validate())
            if p.name in param_names_seen:
                errors.append(f"scenario_params: duplicate name {p.name!r}")
            param_names_seen.add(p.name)
        # n_agents / periods params must exist in scenario_params (otherwise
        # the template's `self.scenario.agent_num` reference would fail)
        for required in (self.n_agents_param, self.periods_param):
            if required and required not in param_names_seen:
                errors.append(
                    f"required scenario param {required!r} missing from scenario_params "
                    f"(declared as n_agents_param or periods_param)"
                )
        # Agent state vars
        var_names_seen: set[str] = set()
        for v in self.agent_state_vars:
            errors.extend(f"agent_state_vars[{v.name}]: {e}" for e in v.validate())
            if v.name in var_names_seen:
                errors.append(f"agent_state_vars: duplicate name {v.name!r}")
            var_names_seen.add(v.name)
        # Targets non-empty (otherwise DataCollector produces no data → calibration impossible)
        if not self.targets:
            errors.append("targets is empty — no metrics will be collected (calibration impossible)")
        # Pseudocode meta
        if not self.env_step_pseudocode.strip():
            errors.append("env_step_pseudocode is empty — environment will be a no-op")
        return errors
