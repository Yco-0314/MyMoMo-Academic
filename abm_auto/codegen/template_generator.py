"""TemplateGenerator — emit 100%-correct boilerplate Python from MechanismSpec.

Five files come out of this module, every one of them deterministic and
guaranteed-correct by construction:

    core/model.py          — imports, topology call, lifecycle hooks
    core/scenario.py       — Scenario subclass with all scenario_params
    core/data_collector.py — register targets as environment properties
    main.py                — Config + Simulator wiring
    data/input/SimulatorScenarios.csv  — header + default row from spec

CoderAgent NEVER writes these files; it only fills agent.py and
environment.py. That contract is enforced by post-template overwrite
(the orchestrator regenerates templates after CoderAgent so any LLM
edits to template files are silently reverted).

Why this matters
----------------
Pre-Layer-3 codegen: LLM wrote all 7 files. Topology API confusion
(`topologies.watts_strogatz(n=150, k=6, p=0.1)` — wrong) caused dogfood
to fail. Even when LLM got it right, the boilerplate had silent drift
(unit mistakes, wrong column names, missing imports).

Post-Layer-3 codegen: 5 files are mechanical — LLM cannot get them
wrong because it doesn't touch them. The remaining 2 files (agent.py,
environment.py) contain the genuine mechanism, which is what LLMs are
actually good at.
"""
from __future__ import annotations

from typing import Any

from abm_auto.codegen.mechanism_spec import (
    MechanismSpec,
    ScenarioParam,
    TopologySpec,
)


# ── Topology rendering ───────────────────────────────────────────────────


def _render_topology_call(topology: TopologySpec) -> str:
    """Render `topologies.<type>(<params>)` as Python source.

    Param values may be:
      - bare scenario references (`"scenario.average_degree"`) — emitted unquoted
      - literals — emitted via repr() so strings get quoted, numbers stay raw
    """
    parts = []
    for key, value in topology.params.items():
        parts.append(f"{key}={_render_param_value(value)}")
    args = ", ".join(parts)
    return f"topologies.{topology.type}({args})"


def _render_param_value(value: Any) -> str:
    """Render a topology/scenario param value as Python source."""
    if isinstance(value, str) and (value.startswith("scenario.") or value.startswith("self.scenario.")):
        # Treat as identifier reference, emit raw
        if value.startswith("scenario."):
            return f"self.{value}"
        return value
    return repr(value)


# ── model.py ─────────────────────────────────────────────────────────────


# ── operator emission (ADR-014 codegen fidelity) ─────────────────────────────
# The Hawk-Dove e2e showed the CoderAgent hand-rolls a DECLARED operator (the
# payoff matrix, the Moran loop) instead of calling it. So — exactly as topology
# is wired — the TemplateGenerator now emits operator CONSTRUCTION + the turnover
# CALL deterministically from the spec slots. The CoderAgent can no longer
# construct-drift or hand-roll a declared operator; it only fills the truly-custom
# interaction body.


def _param_value(v) -> str:
    """Render a payoff/operator param value: a 'scenario.X' ref -> self.scenario.X,
    else a Python literal."""
    if isinstance(v, str) and v.startswith("scenario."):
        return f"self.scenario.{v[len('scenario.'):]}"
    return repr(v)


def _operator_runtime_imports(spec: MechanismSpec) -> list[str]:
    names = []
    if spec.payoff_games:
        names.append("PayoffGame")
    if spec.population_dynamics is not None:
        names.append("MoranProcess")
    if spec.vital_dynamics:
        names.append("VitalDynamics")
    if spec.reference_assets:
        names.append("RuleTable")
    return names


def _render_operator_construction(spec: MechanismSpec) -> str:
    """Lines for Model.setup(): construct each declared model-level operator AND
    hand the INTERACTION operators (PayoffGame / VitalDynamics / RuleTable) to the
    environment as `self.environment.<name>`.

    Construction alone was not enough (Hawk-Dove e2e E5b): the CoderAgent
    re-derived the payoff matrix by hand because the constructed operator was not
    in the path of `environment.step()`. Wiring it onto the env as `self.<name>`
    makes `self.<name>.play(...)` the path of least resistance — the env owns it
    like any other attribute, no signature change. MoranProcess is NOT wired (it
    is model-driven turnover in run(), never called from the interaction body)."""
    lines: list[str] = []
    for g in spec.payoff_games:
        if g.game == "matrix":
            lines.append(f"        self.{g.name} = PayoffGame.from_matrix({g.matrix!r})")
        else:
            params = ", ".join(f"{k}={_param_value(v)}" for k, v in (g.params or {}).items())
            lines.append(f"        self.{g.name} = PayoffGame.{g.game}({params})")
        lines.append(f"        self.environment.{g.name} = self.{g.name}  # interaction body calls self.{g.name}.play(a, b)")
    pd = spec.population_dynamics
    if pd is not None:
        extra = (f", gompertz_a={pd.gompertz_a}, gompertz_b={pd.gompertz_b}"
                 if pd.death_model == "gompertz" else f", death_rate={pd.death_rate}")
        lines.append(
            f"        self._moran = MoranProcess(fitness_attr={pd.fitness_attr!r}, "
            f"death_model={pd.death_model!r}{extra}, age_attr={pd.age_attr!r}, "
            f"seed=int(getattr(self.scenario, 'seed', 0)))"
        )
    for v in spec.vital_dynamics:
        repro = (f"reproduce_at={v.reproduce_at}" if v.reproduce_at is not None
                 else f"reproduce_prob={v.reproduce_prob}")
        cap = f", max_population={v.max_population}" if v.max_population is not None else ""
        lines.append(
            f"        self.{v.name} = VitalDynamics(energy_attr={v.energy_attr!r}, "
            f"death_at={v.death_at}, {repro}{cap}, "
            f"seed=int(getattr(self.scenario, 'seed', 0)))"
        )
        lines.append(f"        self.environment.{v.name} = self.{v.name}  # interaction body calls self.{v.name}.step(...)")
    for a in spec.reference_assets:
        cols = f"input_cols={a.input_cols!r}, output_col={a.output_col!r}"
        for opt in ("given_col", "weight_col", "label_col"):
            val = getattr(a, opt)
            if val:
                cols += f", {opt}={val!r}"
        lines.append(
            f"        self.{a.name} = RuleTable.from_csv(__import__('os').path.join("
            f"self.config.project_root, self.config.input_folder, {a.filename!r}), {cols})"
        )
        lines.append(f"        self.environment.{a.name} = self.{a.name}  # interaction body calls self.{a.name}.combine(...)")
    return "\n".join(lines)


def _render_turnover_call(spec: MechanismSpec) -> str:
    """The per-tick Moran turnover call for Model.run() (population_dynamics)."""
    if spec.population_dynamics is None:
        return ""
    return "            self._moran.turnover(self.agents, inherit=self._moran_inherit)\n"


def _render_inherit_method(spec: MechanismSpec) -> str:
    """The Moran inherit hook: offspring deep-copies inherit_attrs, resets
    reset_attrs to their agent_state_var init, then (if mutation_rate > 0)
    re-draws mutation_attr with that probability so a monomorphic start can be
    invaded. random is module-seeded in setup(), so mutation is reproducible."""
    pd = spec.population_dynamics
    if pd is None:
        return ""
    inits = {v.name: v.init for v in spec.agent_state_vars}
    mutates = bool(pd.mutation_rate and pd.mutation_rate > 0.0 and pd.mutation_attr)
    body = ["    def _moran_inherit(self, child, parent):"]
    if pd.inherit_attrs or pd.reset_attrs:
        body.append("        import copy")
    for attr in pd.inherit_attrs:
        body.append(f"        child.{attr} = copy.deepcopy(parent.{attr})")
    for attr in pd.reset_attrs:
        body.append(f"        child.{attr} = {inits.get(attr, '0')}")
    if mutates:
        body.append(f"        if random.random() < {pd.mutation_rate}:")
        body.append(f"            child.{pd.mutation_attr} = random.choice({pd.mutation_values!r})")
    if not (pd.inherit_attrs or pd.reset_attrs or mutates):
        body.append("        pass")
    return "\n" + "\n".join(body) + "\n"


def generate_model_py(spec: MechanismSpec) -> str:
    """Emit core/model.py — branches on whether the model has a network topology.

    When `spec.topology` is set (typical): emit the Network setup with a
    templated `topologies.<type>(...)` callable.
    When `spec.topology` is None (Grid models, spatial-free models): omit
    the network entirely. CoderAgent's environment.py is then responsible
    for any Grid creation / spatial setup; the templated model.py only
    handles agents + environment + data_collector + iteration loop.

    The split is what cross-domain dogfood revealed we needed: Schelling
    is Grid-based and the network-assuming template produced GVR-thrash
    until CoderAgent fixed it. With topology=None, Schelling-shaped
    models get a network-free skeleton from the start.
    """
    if spec.topology is not None:
        return _generate_model_py_network(spec)
    return _generate_model_py_topology_free(spec)


def _generate_model_py_network(spec: MechanismSpec) -> str:
    """Network-based model.py: Network + topology adapter call in setup()."""
    op_imports = "".join(f", {n}" for n in _operator_runtime_imports(spec))
    construction = _render_operator_construction(spec)
    construction_block = (
        "\n        # 3. Construct declared operators DETERMINISTICALLY from the spec,\n"
        "        #    and hand the interaction ones to the environment as self.<name>.\n"
        "        #    The CoderAgent CALLS these (self.<name>.play/step/combine/...),\n"
        "        #    never re-builds the matrix / table / birth-death (codegen fidelity).\n"
        + construction + "\n"
    ) if construction else ""
    turnover = _render_turnover_call(spec)
    inherit = _render_inherit_method(spec)
    return f'''"""Generated by abm_auto.codegen.template_generator. DO NOT EDIT.

The mechanism body lives in environment.py / agent.py; this file is pure
plumbing (imports, lifecycle, network construction, declared operators).
Regenerated from mechanism_spec.json on every codegen run — manual edits are
silently overwritten.
"""
import random

from abm_auto.runtime import Model, topologies{op_imports}

from .agent import {spec.agent_class_name}
from .data_collector import {spec.data_collector_class_name}
from .environment import {spec.environment_class_name}


class {spec.model_class_name}(Model):
    def create(self):
        self.agents = self.create_agent_list({spec.agent_class_name})
        self.environment = self.create_environment({spec.environment_class_name})
        self.data_collector = self.create_data_collector({spec.data_collector_class_name})
        self.network = self.create_network()

    def setup(self):
        # Reproducibility — seed before any random call
        random.seed(int(getattr(self.scenario, "seed", 0)))

        # 1. Create agents
        self.agents.setup_agents(agents_num=self.scenario.{spec.n_agents_param})

        # 2. Build network from the templated topology adapter
        self.network.setup_agent_connections(
            agent_lists=[self.agents],
            topology={_render_topology_call(spec.topology)},
        )
{construction_block}
        # 4. Defer model-specific initial state setup to the environment.
        #    The environment is LLM-owned; CoderAgent fills .initialize()
        #    if the mechanism needs initial state beyond what agent.setup()
        #    handles (e.g., seeding K initial infected agents).
        if hasattr(self.environment, "initialize"):
            self.environment.initialize(self.agents, self.network, self.scenario)

    def run(self):
        # Per tick: the environment does the interaction (LLM-owned), the model
        # drives the declared turnover operator (deterministic), then we record.
        for t in self.iterator(self.scenario.{spec.periods_param}):
            self.environment.step(self.agents, self.network, self.scenario)
            self.data_collector.collect(t)
{turnover}        self.data_collector.save()
{inherit}'''


def _generate_model_py_topology_free(spec: MechanismSpec) -> str:
    """Network-free model.py: Grid models, spatial-free models, etc.

    No Network created. environment.step() takes (agents, scenario) only —
    no `network` argument. CoderAgent's environment.py is responsible
    for any spatial structure (Grid, custom spatial index) and for
    agent-to-agent interaction patterns.
    """
    op_imports = "".join(f", {n}" for n in _operator_runtime_imports(spec))
    construction = _render_operator_construction(spec)
    construction_block = (
        "\n        # 2. Construct declared operators DETERMINISTICALLY from the spec,\n"
        "        #    and hand the interaction ones to the environment as self.<name>.\n"
        "        #    The CoderAgent CALLS these (self.<name>.play/step/combine/...),\n"
        "        #    never re-builds the matrix / table / birth-death (codegen fidelity).\n"
        + construction + "\n"
    ) if construction else ""
    turnover = _render_turnover_call(spec)
    inherit = _render_inherit_method(spec)
    return f'''"""Generated by abm_auto.codegen.template_generator. DO NOT EDIT.

Network-FREE model: spec.topology is None (Grid-based, spatial-free, or
custom-spatial mechanism). Network setup is omitted — environment.py
(LLM-owned) is responsible for any spatial structure beyond the agents
themselves. Declared operators are constructed + driven here. Regenerated on
every codegen run.
"""
import random

from abm_auto.runtime import Model{op_imports}

from .agent import {spec.agent_class_name}
from .data_collector import {spec.data_collector_class_name}
from .environment import {spec.environment_class_name}


class {spec.model_class_name}(Model):
    def create(self):
        self.agents = self.create_agent_list({spec.agent_class_name})
        self.environment = self.create_environment({spec.environment_class_name})
        self.data_collector = self.create_data_collector({spec.data_collector_class_name})

    def setup(self):
        # Reproducibility — seed before any random call
        random.seed(int(getattr(self.scenario, "seed", 0)))

        # 1. Create agents
        self.agents.setup_agents(agents_num=self.scenario.{spec.n_agents_param})
{construction_block}
        # 3. Defer model-specific initial state setup to the environment.
        #    The environment is LLM-owned; CoderAgent fills .initialize()
        #    (when needed) to set up Grid / spatial structures + seed any
        #    initial agent states.
        if hasattr(self.environment, "initialize"):
            self.environment.initialize(self.agents, self.scenario)

    def run(self):
        # Per tick: the environment does the interaction (LLM-owned), the model
        # drives the declared turnover operator (deterministic), then we record.
        for t in self.iterator(self.scenario.{spec.periods_param}):
            self.environment.step(self.agents, self.scenario)
            self.data_collector.collect(t)
{turnover}        self.data_collector.save()
{inherit}'''


# NB: _render_initial_setup was removed in commit deleting the LLM-FILL
# marker convention. Templates no longer emit "fill this region" markers
# because no mechanism in CodegenPhase reads them — CoderAgent owns
# agent.py + environment.py and is responsible for model-specific initial
# state setup there. See ADR-007 §"Open questions".


# ── scenario.py ──────────────────────────────────────────────────────────


def generate_scenario_py(spec: MechanismSpec) -> str:
    """Emit core/scenario.py — Scenario class with each scenario_param as an attribute."""
    attr_lines = []
    for p in spec.scenario_params:
        # Format: `self.virus_spread_chance: float = 4.4   # percent` (or no comment if no unit)
        comment_parts = []
        if p.unit:
            comment_parts.append(p.unit)
        if p.min is not None and p.max is not None:
            comment_parts.append(f"range [{p.min}, {p.max}]")
        comment = f"   # {', '.join(comment_parts)}" if comment_parts else ""
        attr_lines.append(
            f"        self.{p.name}: {p.type} = {_format_default(p.default, p.type)}{comment}"
        )
    attrs_block = "\n".join(attr_lines) if attr_lines else "        pass"

    return f'''"""Generated by abm_auto.codegen.template_generator. DO NOT EDIT.

Every scenario parameter ends up as an attribute here AND a column in
data/input/SimulatorScenarios.csv. The CSV row overrides these defaults
at simulation time; defaults below are used only when the CSV is missing
a column or you instantiate the class directly.
"""
from abm_auto.runtime import Scenario


class {spec.scenario_class_name}(Scenario):
    def setup(self):
{attrs_block}
'''


def _format_default(value: Any, py_type: str) -> str:
    """Format a default value as Python source matching its declared type."""
    if py_type == "str":
        return repr(str(value))
    if py_type == "bool":
        return repr(bool(value))
    return repr(value)


# ── data_collector.py ────────────────────────────────────────────────────


def generate_data_collector_py(spec: MechanismSpec) -> str:
    """Emit core/data_collector.py — register each target as an environment property."""
    lines = []
    for target in spec.targets:
        lines.append(
            f'        self.add_environment_property("{target}")'
        )
    body = "\n".join(lines) if lines else "        pass"
    return f'''"""Generated by abm_auto.codegen.template_generator. DO NOT EDIT.

DataCollector registers every target metric as an environment-level
property. The environment must set these attributes on itself during
its step() method, otherwise the CSV column will be empty.
"""
from abm_auto.runtime import DataCollector


class {spec.data_collector_class_name}(DataCollector):
    def setup(self):
{body}
'''


# ── main.py ──────────────────────────────────────────────────────────────


def generate_main_py(spec: MechanismSpec) -> str:
    """Emit main.py — Config + Simulator wiring at the package root."""
    return f'''"""Generated by abm_auto.codegen.template_generator. DO NOT EDIT.

Entry point. Loads SimulatorScenarios.csv from data/input/, runs the
model for each scenario row, writes results to data/output/.
"""
import os
from abm_auto.runtime import Config, Simulator
from core.model import {spec.model_class_name}
from core.scenario import {spec.scenario_class_name}

if __name__ == "__main__":
    config = Config(
        project_name="{spec.project_name}",
        project_root=os.path.dirname(__file__),
        input_folder="data/input",
        output_folder="data/output",
    )
    simulator = Simulator(
        config=config,
        model_cls={spec.model_class_name},
        scenario_cls={spec.scenario_class_name},
    )
    simulator.run()
'''


# ── SimulatorScenarios.csv ───────────────────────────────────────────────


def generate_scenarios_csv(spec: MechanismSpec) -> str:
    """Emit data/input/SimulatorScenarios.csv — header + one default row.

    The header includes the runtime's required `id` and `run_num` columns
    plus every scenario_param.name. The single data row uses each
    param's declared default — calibration will overwrite these values
    when it fires.
    """
    header_cols = ["id", "run_num"] + [p.name for p in spec.scenario_params]
    default_values = ["0", "1"] + [_csv_format(p.default, p.type) for p in spec.scenario_params]
    return ",".join(header_cols) + "\n" + ",".join(default_values) + "\n"


def _csv_format(value: Any, py_type: str) -> str:
    """Format a value for CSV — bare numbers/strings, no Python quoting."""
    if py_type == "str":
        # Escape commas/quotes if the value contains them
        s = str(value)
        if "," in s or '"' in s:
            return '"' + s.replace('"', '""') + '"'
        return s
    if py_type == "bool":
        return "True" if value else "False"
    return str(value)


# ── Bundle ──────────────────────────────────────────────────────────────


TEMPLATE_FILES = (
    "core/model.py",
    "core/scenario.py",
    "core/data_collector.py",
    "main.py",
    "data/input/SimulatorScenarios.csv",
)


def generate_all(spec: MechanismSpec) -> dict[str, str]:
    """Generate every template file. Returns {relative_path: file_content}."""
    return {
        "core/model.py": generate_model_py(spec),
        "core/scenario.py": generate_scenario_py(spec),
        "core/data_collector.py": generate_data_collector_py(spec),
        "main.py": generate_main_py(spec),
        "data/input/SimulatorScenarios.csv": generate_scenarios_csv(spec),
    }


def is_template_file(rel_path: str) -> bool:
    """True if rel_path is owned by TemplateGenerator (never LLM-written)."""
    return rel_path in TEMPLATE_FILES
