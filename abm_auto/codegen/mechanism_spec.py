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
class LearnedOperator:
    """One per-agent learned sub-model (ADR-013 W2 wall fix).

    Configures a `runtime.FeedforwardLearner` that a generated agent
    CARRIES and TRAINS — the schema concept that was missing when the
    Yaman reproduction (Path 1) flattened a trainable semantic net into a
    scalar. This describes only the operator's SHAPE; the runtime library
    owns the math (forward / cross-entropy / backprop), so generated agent
    code never reimplements training — it calls `.train()` / `.predict()`
    / `.nearest()`, exactly as models call `topologies.<x>(...)` or
    calibration calls `fit(...)`.

    Minimal scope: a single-hidden-layer feedforward item→item predictor
    with trainable embeddings (the only learned-operator the runtime
    provides today). `n_items` is the vocabulary size; it may be an
    integer literal or the name of a scenario_param holding it.
    """
    name: str                       # the agent attribute, e.g. "semantic_model"
    n_items: Any                    # int literal, or a scenario_param name (str)
    embed_dim: int = 16
    hidden_dim: int = 16
    learning_rate: float = 0.001
    description: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name or not self.name.isidentifier():
            errors.append(f"learned_operator.name={self.name!r} not a valid identifier")
        # n_items: int literal >= 2, OR a scenario_param reference. The
        # reference may be a bare name ("n_total_items") OR the codebase's
        # "scenario.X" form (same convention topology.params uses) — accept
        # both; the spec-level check strips the prefix when verifying the
        # param exists.
        if isinstance(self.n_items, bool):  # bool is an int subclass — reject explicitly
            errors.append(f"learned_operator.{self.name}.n_items must be int or param name, got bool")
        elif isinstance(self.n_items, int):
            if self.n_items < 2:
                errors.append(f"learned_operator.{self.name}.n_items={self.n_items} must be >= 2")
        elif isinstance(self.n_items, str):
            bare = self.n_items[len("scenario."):] if self.n_items.startswith("scenario.") else self.n_items
            if not bare.isidentifier():
                errors.append(
                    f"learned_operator.{self.name}.n_items={self.n_items!r} is neither an int "
                    f"nor a valid scenario_param name (or 'scenario.<param>' reference)"
                )
        else:
            errors.append(
                f"learned_operator.{self.name}.n_items must be an int or a scenario_param "
                f"name (str), got {type(self.n_items).__name__}"
            )
        for label, val in (("embed_dim", self.embed_dim), ("hidden_dim", self.hidden_dim)):
            if not isinstance(val, int) or isinstance(val, bool) or val < 1:
                errors.append(f"learned_operator.{self.name}.{label}={val!r} must be a positive int")
        if not isinstance(self.learning_rate, (int, float)) or self.learning_rate <= 0:
            errors.append(
                f"learned_operator.{self.name}.learning_rate={self.learning_rate!r} must be > 0"
            )
        return errors


VALID_DEATH_MODELS = {"constant", "gompertz"}

# Sane floor for a CONSTANT-death Moran turnover (Hawk-Dove e2e re-run #3, bug C).
# Below ~1% replacement per generation the dynamics freeze: almost nothing turns
# over, so neither selection nor mutation takes hold and the population stays
# monomorphic. Extraction hits this when the source gives no rate — it anchors on
# the rejected 0.0 and creeps just over the (0,1) floor (0.001). Reject it so the
# spec stage re-extracts a real turnover instead of silently freezing.
MORAN_DEATH_RATE_FLOOR = 0.01


@dataclass
class PopulationDynamicsSpec:
    """Declares a `runtime.MoranProcess` overlapping-generations turnover
    (ADR-013 W4 harvest).

    Set this when the model has BIRTH-DEATH population replacement with
    fitness-proportional selection (Moran / cultural-evolution / evolutionary-
    game ABMs). It replaces the several `AI-ASSUMPTION` tags the design phase
    used to spend inventing a "Moran-style selection process", a death rule,
    and an inheritance rule — those are now a provided operator, not gaps.

    The runtime owns the error-prone parts (who dies, who reproduces ∝
    fitness, holding N constant). The generated `inherit(child, parent)` hook
    is the only model-specific line: ``inherit_attrs`` are deep-copied from
    parent to offspring (e.g. a learned operator), ``reset_attrs`` are reset
    to their agent_state_var init (e.g. inventory, score). Age is handled by
    the operator.

    ``mutation_rate`` (optional) adds undirected mutation to the inheritance
    rule: with this per-offspring probability, ``mutation_attr`` is re-drawn
    uniformly from ``mutation_values`` instead of inherited. This is what lets
    a monomorphic start (e.g. all-Hawk) be invaded and reach a polymorphic
    ESS — pure Moran inheritance from a single type is otherwise absorbing.
    Default 0.0 = no mutation (backward-compatible).
    """
    fitness_attr: str = "score"           # agent attr selection is proportional to
    death_model: str = "constant"         # "constant" | "gompertz"
    death_rate: float = 0.05              # used when death_model == "constant"
    gompertz_a: float = 0.0001365         # used when death_model == "gompertz"
    gompertz_b: float = 0.2097
    age_attr: str = "age"
    inherit_attrs: list = field(default_factory=list)   # offspring deep-copies these from parent
    reset_attrs: list = field(default_factory=list)     # offspring resets these to init
    mutation_rate: float = 0.0            # per-offspring P(re-draw mutation_attr); 0 = off
    mutation_attr: str = ""               # which inherited attr mutates (e.g. "strategy")
    mutation_values: list = field(default_factory=list)  # discrete values mutation draws from
    description: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.death_model not in VALID_DEATH_MODELS:
            errors.append(
                f"population_dynamics.death_model={self.death_model!r} not in "
                f"{sorted(VALID_DEATH_MODELS)}"
            )
        if self.death_model == "constant" and not (0.0 < self.death_rate < 1.0):
            errors.append(
                f"population_dynamics.death_rate={self.death_rate} must be in (0, 1) "
                f"for the constant death model"
            )
        elif self.death_model == "constant" and self.death_rate < MORAN_DEATH_RATE_FLOOR:
            errors.append(
                f"population_dynamics.death_rate={self.death_rate} is below the sane "
                f"floor {MORAN_DEATH_RATE_FLOOR} for a constant-death Moran: under "
                f"{MORAN_DEATH_RATE_FLOOR:.0%} of the population turns over per "
                f"generation, so the dynamics freeze (neither selection nor mutation "
                f"takes hold and the population stays monomorphic). Use the turnover "
                f"the source specifies — commonly 0.05–0.5 per generation."
            )
        if self.death_model == "gompertz" and (self.gompertz_a <= 0 or self.gompertz_b <= 0):
            errors.append("population_dynamics gompertz_a and gompertz_b must be > 0")
        for label, name in (("fitness_attr", self.fitness_attr), ("age_attr", self.age_attr)):
            if not name or not name.isidentifier():
                errors.append(f"population_dynamics.{label}={name!r} not a valid identifier")
        for label, names in (("inherit_attrs", self.inherit_attrs),
                             ("reset_attrs", self.reset_attrs)):
            for nm in names:
                if not isinstance(nm, str) or not nm.isidentifier():
                    errors.append(f"population_dynamics.{label} entry {nm!r} not a valid identifier")
        if not (0.0 <= self.mutation_rate <= 1.0):
            errors.append(
                f"population_dynamics.mutation_rate={self.mutation_rate} must be in [0, 1]"
            )
        if self.mutation_rate > 0.0:
            if not self.mutation_attr or not self.mutation_attr.isidentifier():
                errors.append(
                    f"population_dynamics.mutation_attr={self.mutation_attr!r} must be a valid "
                    f"identifier when mutation_rate > 0"
                )
            if not self.mutation_values:
                errors.append(
                    "population_dynamics.mutation_values must be non-empty when mutation_rate > 0"
                )
        return errors


@dataclass
class ReferenceAsset:
    """An external data file the model loads via `runtime.RuleTable`
    (ADR-013 W3 harvest).

    Set this when the source model is driven by an external rule / recipe /
    transition / payoff TABLE whose contents are DATA, not a formula (the
    Yaman recipe tree; a tech tree; a reaction network). The pipeline copies
    ``filename`` from the workspace assets dir into the generated model's
    data/input/, and the model loads it with `RuleTable` — it never
    enumerates or assumes the rows. This is what lets a design DECLARE such a
    table instead of spending several `AI-ASSUMPTION` tags inventing its
    encoding.

    ``input_cols`` are the columns whose item ids form a combination key;
    ``output_col`` is the produced item; ``given_col`` flags rows available at
    the start; ``weight_col`` / ``label_col`` are optional score and name.
    """
    name: str                                       # model attribute, e.g. "rules"
    filename: str                                   # data file basename (in the assets dir)
    output_col: str                                 # the produced-item column
    kind: str = "rule_table"                        # only kind today
    input_cols: list = field(default_factory=list)  # combination key columns
    given_col: str = ""                             # optional initial-item flag column
    weight_col: str = ""                            # optional score / payoff column
    label_col: str = ""                             # optional human label column
    description: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name or not self.name.isidentifier():
            errors.append(f"reference_asset.name={self.name!r} not a valid identifier")
        if not self.filename:
            errors.append(f"reference_asset.{self.name}.filename is required")
        if self.kind != "rule_table":
            errors.append(
                f"reference_asset.{self.name}.kind={self.kind!r} unsupported "
                f"(only 'rule_table' today)"
            )
        if not self.input_cols:
            errors.append(f"reference_asset.{self.name}.input_cols is empty")
        if not self.output_col:
            errors.append(f"reference_asset.{self.name}.output_col is required")
        return errors


VALID_GAMES = {"matrix", "prisoners_dilemma", "hawk_dove",
               "rock_paper_scissors", "stag_hunt"}


@dataclass
class PayoffGameSpec:
    """Declares a `runtime.PayoffGame` — a symmetric 2-player game (ADR-014
    Phase 2).

    Set this when agents play a game-theoretic interaction with a payoff
    MATRIX. A payoff matrix is ordered + dual-output, which `RuleTable` cannot
    represent, so this is its own operator. Composes with `population_dynamics`
    (Moran) to give evolutionary game theory.

    Either a `game` name with `params` (prisoners_dilemma {T,R,P,S},
    hawk_dove {V,C}, …) OR an explicit `matrix` (game="matrix"). The agent code
    calls `self.<name>.play(a, b)` / `.payoff(a, b)` / `.best_response(b)`.
    """
    name: str                                       # model attribute, e.g. "game"
    game: str = "matrix"                            # one of VALID_GAMES
    matrix: list = field(default_factory=list)      # n x n payoffs (game == "matrix")
    params: dict = field(default_factory=dict)      # named-game params
    strategy_var: str = ""                          # optional agent_state_var holding the strategy
    description: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name or not self.name.isidentifier():
            errors.append(f"payoff_game.name={self.name!r} not a valid identifier")
        if self.game not in VALID_GAMES:
            errors.append(
                f"payoff_game.{self.name}.game={self.game!r} not in {sorted(VALID_GAMES)}"
            )
        if self.game == "matrix":
            n = len(self.matrix)
            if n < 2:
                errors.append(f"payoff_game.{self.name}.matrix needs >= 2 strategies")
            elif any(len(row) != n for row in self.matrix):
                errors.append(f"payoff_game.{self.name}.matrix must be square")
            else:
                for row in self.matrix:
                    if any(not isinstance(x, (int, float)) or isinstance(x, bool) for x in row):
                        errors.append(f"payoff_game.{self.name}.matrix entries must be numbers")
                        break
        if self.strategy_var and not self.strategy_var.isidentifier():
            errors.append(f"payoff_game.{self.name}.strategy_var={self.strategy_var!r} not an identifier")
        return errors


@dataclass
class VitalDynamicsSpec:
    """Declares a `runtime.VitalDynamics` — variable-N birth/death (ADR-014
    Phase 2).

    Set this for an energy/resource ECOLOGY whose population grows and shrinks
    (wolf-sheep, rabbits-grass, daisyworld). Distinct from `population_dynamics`
    (Moran, fixed-N). The agent code applies energy changes each step, then the
    operator removes the dead (energy <= death_at) and spawns offspring from
    agents that reproduce (energy >= reproduce_at, OR with reproduce_prob).
    """
    name: str                                       # model attribute, e.g. "vital"
    energy_attr: str = "energy"                     # agent_state_var holding energy
    death_at: float = 0.0
    reproduce_at: Optional[float] = None            # energy-threshold reproduction
    reproduce_prob: Optional[float] = None          # per-step probabilistic reproduction
    split_energy: bool = True
    max_population: Optional[int] = None            # carrying-capacity cap
    description: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name or not self.name.isidentifier():
            errors.append(f"vital_dynamics.name={self.name!r} not a valid identifier")
        if not self.energy_attr or not self.energy_attr.isidentifier():
            errors.append(f"vital_dynamics.{self.name}.energy_attr={self.energy_attr!r} not an identifier")
        if self.reproduce_at is None and self.reproduce_prob is None:
            errors.append(f"vital_dynamics.{self.name} needs reproduce_at OR reproduce_prob")
        if self.reproduce_prob is not None and not (0.0 <= self.reproduce_prob <= 1.0):
            errors.append(f"vital_dynamics.{self.name}.reproduce_prob={self.reproduce_prob} must be in [0, 1]")
        if self.max_population is not None and (not isinstance(self.max_population, int)
                                                or isinstance(self.max_population, bool)
                                                or self.max_population < 1):
            errors.append(f"vital_dynamics.{self.name}.max_population must be a positive int")
        return errors


def _normalize_heritable_strategy(population_dynamics, payoff_games, agent_state_vars) -> None:
    """Enforce the heritability invariant in-place (Hawk-Dove e2e re-run #2, bug A).

    In an evolutionary game the strategy under selection MUST be heritable, or the
    Moran turnover is a no-op on it: the offspring keeps the dead agent's own
    strategy and fitness-proportional selection never propagates the fit parent's.
    Extraction routinely drops the strategy from `inherit_attrs` — it describes
    "offspring inherit strategy" in prose but leaves the field empty — and the LLM
    then compensates with a (dead) hand-rolled turnover. So when both
    `population_dynamics` and `payoff_games` are present, every
    `payoff_games[].strategy_var` that names a real agent_state_var is added to
    `inherit_attrs` (unless it is already inherited, or — defensively — listed
    under reset_attrs, which would be a separate contradiction). This is a
    structural necessity, not a judgement call: selection on a non-heritable trait
    is meaningless.
    """
    if population_dynamics is None or not payoff_games:
        return
    state_var_names = {v.name for v in agent_state_vars}
    for g in payoff_games:
        sv = getattr(g, "strategy_var", "")
        if (sv and sv in state_var_names
                and sv not in population_dynamics.inherit_attrs
                and sv not in population_dynamics.reset_attrs):
            population_dynamics.inherit_attrs.append(sv)


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
    # `topology` is OPTIONAL. None means the model is NOT network-based
    # (e.g., Grid-based Schelling, or no spatial structure at all). When
    # None, TemplateGenerator emits a model.py skeleton that skips the
    # network setup block — CoderAgent is then responsible for any Grid
    # / spatial setup in environment.py / agent.py.
    # When set, TemplateGenerator emits `Network.setup_agent_connections(
    # topology=topologies.<type>(...))` (Layer 3 happy path).
    topology: Optional[TopologySpec] = field(
        default_factory=lambda: TopologySpec(type="watts_strogatz", params={"k": 6, "p": 0.1})
    )
    n_agents_param: str = "agent_num"         # scenario field holding agent count
    periods_param: str = "periods"             # scenario field holding tick count

    # ── Data ──
    scenario_params: list[ScenarioParam] = field(default_factory=list)
    agent_state_vars: list[AgentStateVar] = field(default_factory=list)
    # Per-agent learned sub-models (ADR-013 W2 fix). Usually empty — only
    # set for learning-representation agents (e.g. Yaman's semantic model).
    learned_operators: list[LearnedOperator] = field(default_factory=list)
    # Population turnover (ADR-013 W4). None = no birth-death dynamics (the
    # common case). Set for Moran / evolutionary / cultural-evolution models.
    population_dynamics: Optional[PopulationDynamicsSpec] = None
    # External data tables the model loads via RuleTable (ADR-013 W3). Usually
    # empty — set when the model is driven by an external rule/recipe table.
    reference_assets: list[ReferenceAsset] = field(default_factory=list)
    # Game-theoretic payoff matrices (ADR-014 Phase 2). Usually empty — set for
    # game-theory / evolutionary-game models. Composes with population_dynamics.
    payoff_games: list[PayoffGameSpec] = field(default_factory=list)
    # Variable-N ecologies (ADR-014 Phase 2). Usually empty — set for energy/
    # resource birth-death models (wolf-sheep, rabbits-grass). VitalDynamics.
    vital_dynamics: list[VitalDynamicsSpec] = field(default_factory=list)
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
        top_raw = data.get("topology")
        if top_raw is None or top_raw == {}:
            # Explicit None or empty dict → model has no network topology
            # (Grid-based or spatial-free). Pass None through so
            # TemplateGenerator emits a network-less model.py.
            topology = None
        else:
            topology = TopologySpec(
                type=top_raw.get("type", "watts_strogatz"),
                params=dict(top_raw.get("params", {})),
            )
        scenario_params = [ScenarioParam(**p) for p in data.get("scenario_params", [])]
        agent_state_vars = [AgentStateVar(**v) for v in data.get("agent_state_vars", [])]
        learned_operators = [LearnedOperator(**lo) for lo in data.get("learned_operators", [])]
        pd_raw = data.get("population_dynamics")
        population_dynamics = (
            PopulationDynamicsSpec(**pd_raw) if pd_raw not in (None, {}) else None
        )
        reference_assets = [ReferenceAsset(**a) for a in data.get("reference_assets", [])]
        payoff_games = [PayoffGameSpec(**g) for g in data.get("payoff_games", [])]
        vital_dynamics = [VitalDynamicsSpec(**v) for v in data.get("vital_dynamics", [])]
        _normalize_heritable_strategy(population_dynamics, payoff_games, agent_state_vars)
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
            learned_operators=learned_operators,
            population_dynamics=population_dynamics,
            reference_assets=reference_assets,
            payoff_games=payoff_games,
            vital_dynamics=vital_dynamics,
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
        # Topology — only validate when non-None (None is the explicit
        # "no network" signal for Grid models / spatial-free models)
        if self.topology is not None:
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
        # Learned operators (per-agent sub-models). Validate each, ensure no
        # name collision with an agent_state_var (both become agent attrs),
        # and that a string n_items refers to a real scenario_param.
        for lo in self.learned_operators:
            errors.extend(f"learned_operators[{lo.name}]: {e}" for e in lo.validate())
            if lo.name in var_names_seen:
                errors.append(
                    f"learned_operators: name {lo.name!r} collides with an agent_state_var"
                )
            var_names_seen.add(lo.name)
            if isinstance(lo.n_items, str):
                # accept bare name or "scenario.<param>" (topology's convention)
                ref = lo.n_items[len("scenario."):] if lo.n_items.startswith("scenario.") else lo.n_items
                if ref not in param_names_seen:
                    errors.append(
                        f"learned_operators[{lo.name}]: n_items={lo.n_items!r} is not a "
                        f"declared scenario_param"
                    )
        # Population dynamics (ADR-013 W4). Validate the operator spec when
        # present; cross-check that inherited/reset attrs name known agent
        # attributes (agent_state_vars or learned_operators) — catches typos
        # in the one model-specific part of the operator.
        if self.population_dynamics is not None:
            errors.extend(
                f"population_dynamics: {e}" for e in self.population_dynamics.validate()
            )
            for label in ("inherit_attrs", "reset_attrs"):
                for nm in getattr(self.population_dynamics, label):
                    if nm not in var_names_seen:
                        errors.append(
                            f"population_dynamics.{label}: {nm!r} is not a declared "
                            f"agent_state_var or learned_operator"
                        )
        # Reference assets (ADR-013 W3). Validate each + no duplicate names.
        asset_names_seen: set[str] = set()
        for a in self.reference_assets:
            errors.extend(f"reference_assets[{a.name}]: {e}" for e in a.validate())
            if a.name in asset_names_seen:
                errors.append(f"reference_assets: duplicate name {a.name!r}")
            asset_names_seen.add(a.name)
        # Payoff games (ADR-014 Phase 2). Validate each + no duplicate names;
        # strategy_var, when set, must reference a declared agent_state_var.
        game_names_seen: set[str] = set()
        for g in self.payoff_games:
            errors.extend(f"payoff_games[{g.name}]: {e}" for e in g.validate())
            if g.name in game_names_seen:
                errors.append(f"payoff_games: duplicate name {g.name!r}")
            game_names_seen.add(g.name)
            if g.strategy_var and g.strategy_var not in var_names_seen:
                errors.append(
                    f"payoff_games[{g.name}]: strategy_var={g.strategy_var!r} is not a "
                    f"declared agent_state_var"
                )
        # Variable-N ecologies (ADR-014 Phase 2). Validate each + no duplicate
        # names; energy_attr must reference a declared agent_state_var.
        vital_names_seen: set[str] = set()
        for v in self.vital_dynamics:
            errors.extend(f"vital_dynamics[{v.name}]: {e}" for e in v.validate())
            if v.name in vital_names_seen:
                errors.append(f"vital_dynamics: duplicate name {v.name!r}")
            vital_names_seen.add(v.name)
            if v.energy_attr and v.energy_attr not in var_names_seen:
                errors.append(
                    f"vital_dynamics[{v.name}]: energy_attr={v.energy_attr!r} is not a "
                    f"declared agent_state_var"
                )
        # Targets non-empty (otherwise DataCollector produces no data → calibration impossible)
        if not self.targets:
            errors.append("targets is empty — no metrics will be collected (calibration impossible)")
        # Pseudocode meta
        if not self.env_step_pseudocode.strip():
            errors.append("env_step_pseudocode is empty — environment will be a no-op")
        return errors
