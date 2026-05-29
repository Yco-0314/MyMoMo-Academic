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

Pick the ONE that the mechanism markdown declares. Each requires specific params:

| `type` | Required params |
|---|---|
| `"watts_strogatz"` | `k` (int, even), `p` (float 0-1) |
| `"barabasi_albert"` | `m` (int, edges per new node) |
| `"erdos_renyi"` | `p` (float 0-1, edge probability) |
| `"netlogo_spatially_clustered"` | `avg_degree` (int) |
| `"melodie_named"` | `name` (str — networkx generator) plus arbitrary kwargs |

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
