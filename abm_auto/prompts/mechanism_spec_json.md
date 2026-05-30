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
