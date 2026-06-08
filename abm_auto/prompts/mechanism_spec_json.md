# MechanismSpec — JSON-only extractor

You will receive a markdown mechanism specification (produced by an earlier
LLM call) plus the original DESIGN.md. Your single job is to emit a JSON
object matching the schema below. **NO commentary, NO markdown, NO prose,
NO code fences except the single ```json``` block. Just the JSON.**

The downstream TemplateGenerator parses your output to write 5 deterministic
boilerplate files (model.py, scenario.py, data_collector.py, main.py,
SimulatorScenarios.csv). If your JSON is malformed or missing fields, the
pipeline degrades to legacy LLM codegen — which has a known failure rate.

## Inputs

### Mechanism markdown (from prior extraction)

{{ mechanism_md }}

### Original DESIGN.md (context)

{{ design }}

## Schema (all fields required unless marked optional)

```json
{
  "project_name": "VirusOnNetwork",
  "model_class_name": "VirusModel",
  "agent_class_name": "Person",
  "environment_class_name": "VirusEnvironment",
  "scenario_class_name": "VirusScenario",
  "data_collector_class_name": "VirusDataCollector",
  "topology": {
    "type": "netlogo_spatially_clustered",
    "params": {"avg_degree": "scenario.average_degree"}
  },
  "n_agents_param": "agent_num",
  "periods_param": "periods",
  "scenario_params": [
    {"name": "periods", "type": "int", "default": 250, "unit": "ticks"},
    {"name": "agent_num", "type": "int", "default": 150, "unit": "count"},
    {"name": "virus_spread_chance", "type": "float", "default": 4.4,
     "unit": "percent", "min": 0, "max": 20}
  ],
  "agent_state_vars": [
    {"name": "state", "type": "int", "init": "0"}
  ],
  "learned_operators": [],
  "population_dynamics": null,
  "reference_assets": [],
  "payoff_games": [],
  "vital_dynamics": [],
  "targets": ["count_s", "count_i", "count_r"],
  "env_step_pseudocode": "snapshot infecteds; spread to S-neighbors with prob...",
  "agent_step_pseudocode": null,
  "initial_setup_pseudocode": "sample K=initial_outbreak_size agents and set state=1"
}
```

## Topology types

Decide first: **does this mechanism use an explicit AGENT NETWORK** (links
between agents that drive interaction)?

- **Yes — network-based** (e.g., epidemic spread via contact links, opinion
  diffusion through friendship graphs, information cascades over follower
  networks): pick a topology type from the table below.
- **No — Grid-based or spatial-free** (e.g., Schelling segregation on a
  spatial grid where neighbours = adjacent cells, NOT agent-to-agent
  links; cellular automata; well-mixed populations): emit
  **`"topology": null`** (literal JSON null). The downstream
  TemplateGenerator will emit a model.py that does NOT create a Network
  — Grid/spatial setup happens inside agent.py / environment.py code
  that CoderAgent fills in.

| `type` | Required params | Typical use |
|---|---|---|
| `null` | — | **Schelling, cellular automata, spatial-grid models, well-mixed populations** — anything where neighbours are geographic adjacency or the model has no topology at all |
| `"watts_strogatz"` | `k` (int, even), `p` (float 0-1) | small-world |
| `"barabasi_albert"` | `m` (int, edges per new node) | scale-free preferential attachment |
| `"erdos_renyi"` | `p` (float 0-1, edge probability) | random graph |
| `"netlogo_spatially_clustered"` | `avg_degree` (int) | NetLogo's spatially-clustered network |
| `"melodie_named"` | `name` (str — networkx generator) plus arbitrary kwargs | escape hatch |

### When in doubt

If the mechanism markdown says agents move around a grid / have spatial
positions / interact with "neighbours" defined by adjacency, choose
**`null`**. Do NOT pick `watts_strogatz` as a "safe default" — picking
the wrong topology causes a runtime crash (NetworkAgent/GridAgent
inheritance contradiction surfaces only at sim time).

### Example: Schelling-shaped Grid model

```json
{
  "project_name": "SegregationDynamics",
  "model_class_name": "SegregationModel",
  "agent_class_name": "Household",
  "environment_class_name": "SegregationEnvironment",
  "scenario_class_name": "SegregationScenario",
  "data_collector_class_name": "SegregationDataCollector",
  "topology": null,
  "n_agents_param": "agent_num",
  "periods_param": "periods",
  "scenario_params": [
    {"name": "periods", "type": "int", "default": 100, "unit": "ticks"},
    {"name": "agent_num", "type": "int", "default": 1500, "unit": "count"},
    {"name": "tolerance", "type": "float", "default": 0.3, "unit": "probability"}
  ],
  "agent_state_vars": [
    {"name": "group", "type": "int", "init": "0"}
  ],
  "targets": ["fraction_unhappy", "segregation_index"],
  "env_step_pseudocode": "for each unhappy agent: relocate to a random empty cell whose neighbourhood satisfies tolerance...",
  "agent_step_pseudocode": null,
  "initial_setup_pseudocode": "place agents on grid, assign group by ratio"
}
```

## Learned operators (agents that TRAIN a sub-model)

`learned_operators` is **almost always `[]`** (empty). Set it ONLY when an
agent in the source model **learns a representation it trains over time** —
e.g. a neural network / embedding model the agent updates from experience.
Fixed-rule agents (state machines, thresholds, probabilities) do NOT use
this — leave it empty.

If the model DOES have a per-agent trainable sub-model, do NOT try to
describe the network's weights or training loop in `agent_state_vars` or
pseudocode. The runtime provides the operator (`FeedforwardLearner`); you
only declare its SHAPE here, and the agent code will call it:

```json
"learned_operators": [
  {
    "name": "semantic_model",
    "n_items": "n_total_items",
    "embed_dim": 16,
    "hidden_dim": 16,
    "learning_rate": 0.001,
    "description": "per-agent distributional model: predicts which item completes a recipe"
  }
]
```

- `name` — the agent attribute (becomes `self.semantic_model`).
  **DO NOT also list this name in `agent_state_vars`** — a learned
  operator IS the agent attribute; listing it in both is a duplicate that
  will be rejected. The operator is the ONLY place it belongs.
- `n_items` — vocabulary/output size. EITHER an **integer literal**
  (e.g. `96`), OR a **scenario_param reference** (e.g.
  `"scenario.n_total_items"` or the bare name `"n_total_items"`). If you
  use a param reference, that param **MUST also appear in
  `scenario_params`** — add it there (type `"int"`) if it is not already
  present, or just use the integer literal to avoid the dependency.
- `embed_dim`, `hidden_dim`, `learning_rate` — small ints / float; use the
  paper's values if stated, else 16 / 16 / 0.001.

The agent will `self.<name> = FeedforwardLearner(n_items=..., ...)` and use
`.train(pairs)` / `.predict(item)` / `.nearest(item)` — it never
implements the network. (See the Phase-2 implementation prompt.)

The agent's OTHER state (inventory, memory, etc.) goes in
`agent_state_vars` as usual — but those must be scalar types
(`int`/`float`/`bool`/`str`). A list/set inventory should be declared as
`"str"` with an init expression like `"list(range(6))"` or `"set()"`
(the type field constrains the column, the init expression is real
Python). Do NOT put `"list"` or `"set"` in the `type` field.

## Population dynamics (birth-death turnover)

`population_dynamics` is **almost always `null`**. Set it ONLY when the
source model has **population replacement**: individuals die and are
replaced by offspring of selected survivors (a Moran process, a Wright-
Fisher generation, evolutionary/cultural-evolution selection). Models with
a FIXED set of agents that just update state (epidemics, opinion dynamics,
Schelling) leave it `null`.

When the model DOES have selection-driven turnover, do NOT describe the
death loop or the selection mechanics in pseudocode. The runtime provides
the operator (`MoranProcess`); you only declare its SHAPE:

```json
"population_dynamics": {
  "fitness_attr": "score",
  "death_model": "gompertz",
  "gompertz_a": 0.0001365,
  "gompertz_b": 0.2097,
  "inherit_attrs": ["semantic_model"],
  "reset_attrs": ["inventory", "score"],
  "mutation_rate": 0.0,
  "description": "Moran turnover: offspring inherit the trained model, reset inventory"
}
```

- `fitness_attr` — the agent attribute selection is proportional to (e.g.
  `"score"`). Must be a real agent attribute.
- `death_model` — `"constant"` (give `death_rate`, a probability in (0,1))
  or `"gompertz"` (age-based `P = a·e^(b·age)`; give `gompertz_a`,
  `gompertz_b`, or use the defaults). `death_rate` is the FRACTION of the
  population replaced per generation — use the turnover the source specifies,
  typically **0.05–0.5**. Do NOT pick a near-zero value (e.g. 0.001): under ~1%
  turnover the dynamics freeze (nothing evolves) and the spec is rejected.
- `inherit_attrs` — agent attributes the OFFSPRING deep-copies from its
  parent (e.g. a `learned_operators` model the lineage keeps training).
  Each name MUST be a declared `agent_state_var` or `learned_operator`.
- `reset_attrs` — agent attributes the offspring RESETS to their
  `agent_state_var` init (e.g. `"inventory"`, `"score"`). Also must name
  declared attributes. (Age is reset by the operator automatically.)
- `mutation_rate` / `mutation_attr` / `mutation_values` — set these ONLY when
  the source text says offspring sometimes MUTATE (adopt a random trait
  instead of inheriting). `mutation_rate` is the per-offspring probability
  (e.g. `0.01`); `mutation_attr` is the inherited attribute that mutates (a
  declared `agent_state_var`, e.g. `"strategy"`); `mutation_values` is the
  discrete set it is re-drawn from (e.g. `[0, 1]` for a binary strategy).
  Mutation is REQUIRED for a monomorphic start (all one strategy) to reach a
  polymorphic equilibrium — pure inheritance from a single type is otherwise
  frozen. Omit (rate stays `0.0`) when the text describes no mutation.

The generated `environment.step` will call
`self.moran.turnover(agents, inherit=...)` once per generation — it never
writes the death/selection loop. (See the Phase-2 implementation prompt.)

## Reference assets (external data tables)

`reference_assets` is **almost always `[]`**. Set it ONLY when the model is
driven by an **external rule / recipe / transition / payoff TABLE** whose
contents are DATA in a file (a recipe or tech tree, a reaction network, a
state-transition table), not a formula. The design will have declared the
file and its column roles; copy that here. The runtime provides the operator
(`RuleTable`) — you declare the table's SHAPE, the model loads it, and you
NEVER enumerate the rows.

```json
"reference_assets": [
  {
    "name": "rules",
    "filename": "rules_tidied.csv",
    "output_col": "item",
    "input_cols": ["c1", "c2", "c3"],
    "given_col": "given",
    "weight_col": "point",
    "label_col": "name_simplified",
    "description": "Totem innovation tree: ingredient columns -> produced item"
  }
]
```

- `name` — the model attribute (becomes `self.rules`).
- `filename` — the data file basename; the pipeline copies it into the
  generated model's `data/input/`.
- `output_col` — the column naming the item each row produces (REQUIRED).
- `input_cols` — the columns whose item ids form the combination key
  (REQUIRED; empty cells are ignored).
- `given_col` / `weight_col` / `label_col` — optional: an initial-item flag,
  a score/payoff, a human label.

The model will `self.rules = RuleTable.from_csv(path, input_cols=..., ...)`
and call `.combine(items)` / `.recipe_for(x)` / `.given_indices()` — it never
hard-codes the table. (See the Phase-2 implementation prompt.)

## Payoff games (game-theoretic interactions)

`payoff_games` is **almost always `[]`**. Set it when agents play a 2-player
game with a **payoff matrix** (prisoner's dilemma, hawk-dove, public goods,
coordination). A payoff is ORDERED (a player's payoff vs an opponent) and
dual-output — do NOT model it as a `reference_assets` rule table (order-free,
single-output cannot represent it). The runtime provides `PayoffGame`; you
declare the game, the agent code calls it.

```json
"payoff_games": [
  {
    "name": "game",
    "game": "prisoners_dilemma",
    "params": {"T": 5, "R": 3, "P": 1, "S": 0},
    "strategy_var": "strategy",
    "description": "agents play PD each round; payoff feeds Moran fitness"
  }
]
```

- `name` — the model attribute (becomes `self.game`).
- `game` — one of `prisoners_dilemma` | `hawk_dove` | `rock_paper_scissors` |
  `stag_hunt` | `matrix`. For `matrix`, give an n×n `matrix` of numbers instead
  of `params`.
- `params` — named-game parameters (PD: T,R,P,S; hawk_dove: V,C).
- `strategy_var` — optional: the `agent_state_vars` entry holding the agent's
  strategy index (must be declared there).

The agent will `self.game = PayoffGame.prisoners_dilemma(**params)` (or
`PayoffGame.from_matrix(matrix)`) and call `.play(a, b)` / `.payoff(a, b)` /
`.best_response(b)`. Pairs naturally with `population_dynamics` (Moran) —
play → accumulate payoff as fitness → turnover = evolutionary game theory.

## Vital dynamics (variable-population birth/death)

`vital_dynamics` is **almost always `[]`**. Set it for an **energy/resource
ecology** whose population SIZE grows and shrinks — wolf-sheep, rabbits-grass,
daisyworld, predator-prey. This is DIFFERENT from `population_dynamics` (Moran),
which is FIXED-N (one death per birth). Here births and deaths are independent:
agents below a death threshold are removed; agents that meet a reproduction
condition spawn offspring. The runtime provides `VitalDynamics`.

```json
"vital_dynamics": [
  {
    "name": "vital",
    "energy_attr": "energy",
    "death_at": 0,
    "reproduce_prob": 0.04,
    "max_population": 3000,
    "description": "sheep die at 0 energy, reproduce w.p. 0.04 splitting energy"
  }
]
```

- `name` — the model attribute (becomes `self.vital`).
- `energy_attr` — the `agent_state_vars` field holding energy (must be declared).
- `death_at` — agents with energy ≤ this are removed (default 0).
- Give EITHER `reproduce_at` (energy threshold) OR `reproduce_prob` (per-step
  probability; the NetLogo wolf-sheep style). On reproduction the parent's
  energy is split with the offspring unless `split_energy: false`.
- `max_population` — optional carrying-capacity cap.

The model calls `self.vital.step(agents, spawn=..., on_birth=...)` once per
tick — `spawn` creates a blank offspring, `on_birth(parent, child)` finishes it
(position, etc.). NEVER hand-write the death-filter / energy-split / list
rebuild. For a FIXED-size selection turnover use `population_dynamics` instead.

## Param value forms

Param values in `topology.params` are EITHER:

1. **Numeric literals**: `6`, `0.1`, `0.05`  — emitted as raw JSON numbers
2. **Scenario references**: `"scenario.average_degree"` — JSON string; the
   renderer strips the quotes and emits `self.scenario.average_degree`

Use scenario references when the value is calibration-tunable or
configurable; numeric literals when it's structurally fixed.

## Scenario param types

Pick ONE per param: `"int"` | `"float"` | `"bool"` | `"str"`.

## Required scenario_params

Every value referenced via `"scenario.X"` in topology / pseudocode MUST
appear in `scenario_params`. At minimum include `periods` and the value
named by `n_agents_param`.

## Pseudocode fields

- `env_step_pseudocode` — non-empty, one paragraph describing the per-tick
  environment update logic from the mechanism markdown
- `agent_step_pseudocode` — `null` when all logic is in env.step (typical),
  otherwise paragraph describing agent.step body
- `initial_setup_pseudocode` — describes any extra setup beyond agent
  creation + network construction (e.g., "sample K agents to be infected")

## Failure modes to avoid

- Trailing commas (invalid JSON)
- Python literals: `True`/`False`/`None` instead of `true`/`false`/`null`
- Comments (// or #) anywhere
- Multi-line strings without escaping
- Fields outside the schema — extra keys are silently ignored but waste
  your output budget

## Output format — read this twice

Your ENTIRE response is one fenced ```json``` block containing one
top-level JSON object. Nothing before. Nothing after. No "Here is the
JSON:" preamble. No closing "I have produced..." remark. Just:

```json
{...}
```

Anything outside the fenced block is wasted output and may confuse the
downstream parser.
