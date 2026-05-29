# Mechanism Spec Extraction

You are a **simulation algorithm specifier**. Read the ABM design document
below and produce a **pseudocode mechanism specification** that pins down
EVERY behavioural decision the design left ambiguous.

## Why this matters

The downstream coder will translate this spec **literally** into Python. If
the spec is ambiguous, the coder will fill in the blanks with whatever
"feels reasonable" — and those small choices (sequential vs simultaneous
update, when probability is checked, order of operations) cause large
divergence from the original mechanism. Your job is to **eliminate every
implementation degree of freedom**.

## Inputs

### DESIGN.md
{{ design }}

{{ hypothesis_block }}

## Required output structure

Produce a single markdown file with these exact sections:

```markdown
# Mechanism Specification

## Tick semantics
What does one tick represent in real-world time?
Does the model run for a fixed number of ticks or until a stopping condition?
If stopping condition: state it precisely (e.g., `count_i == 0`).

## Update order (CRITICAL)
For each phase that happens per tick, state explicitly:
- Phase name (e.g., "infections", "recoveries")
- Order: **sequential per agent** (one agent at a time, sees others' updated state)
           OR **simultaneous** (all agents' next-state computed from current-state)
- If sequential: random shuffle of agent order each tick? Or deterministic order?

## State transition algorithm
ONE pseudocode block per phase. Each block must specify:
- Iteration: who runs the rule (e.g., "every agent A with state == 'I'")
- Per-iteration logic: exact algorithm, including:
  * When `random()` is called
  * The threshold expression in its exact form, with units (e.g., `random() < scenario.spread_chance / 100.0`)
  * State change targets (which agent, which attribute, new value)

Example shape:
```
Phase infections (sequential per infected agent):
  for each agent A where A.state == "I":
    for each neighbor N of A in network:
      if N.state == "S":
        if random() < scenario.spread_chance / 100.0:
          N.state := "I"
```

## Parameter unit discipline
For EVERY calibration parameter, state:
- Name (exact match to calibration_param_specs entry)
- Unit (percent, probability, rate, count)
- Conversion at point of use (e.g., "/100.0 in the random() < ... check")

## Initial conditions
- How many agents start in which state?
- Are initial agents chosen deterministically (e.g., first N) or randomly?
- If random: state the rng seed source (e.g., `random.seed(scenario.seed)`).

## Network / spatial init
If the model uses a Grid or Network:
- Topology callable (one of `topologies.watts_strogatz`, `topologies.barabasi_albert`, `topologies.erdos_renyi`, `topologies.netlogo_spatially_clustered`, or `topologies.melodie_named` as escape hatch — see `01-runtime-api.md` §Network)
- Parameters (with mapping from scenario columns)
- Whether topology is rebuilt each tick or fixed at setup (almost always: fixed)

## Tick-level data collection
Which environment-level metrics are recorded per tick? List exact attribute names.
(These become DataCollector columns and must match the calibration_targets in research_spec.json.)

## Edge cases to specify
List any ambiguity in the design that you resolved with a specific choice:
- e.g., "If an agent recovers and is selected for resistance in the same tick,
        which transition wins? CHOICE: resistance wins (R is absorbing)."
- e.g., "If a tick has zero infected agents at start, does recovery phase
        still run? CHOICE: no, skipped — saves cycles."

## Reproducibility
- RNG seed source (`scenario.seed` or fixed?)
- Order of phases within a tick (e.g., "infections then recoveries then
  data_collector.collect")
- Whether the network sampler uses its own RNG state or the global one
```

## Quality bar

Bad spec: "agents get infected based on neighbor state and a probability"
Good spec: precise pseudocode that has ONE possible implementation

If you read the spec back and could implement two non-equivalent Python
versions of it, the spec is too loose — sharpen it.

## What NOT to do

- Do NOT translate parameter names — match calibration_param_specs exactly
- Do NOT introduce new mechanism not in DESIGN.md — only **pin down ambiguity**
- Do NOT propose multiple options — make ONE concrete choice per ambiguity
- Do NOT include Python imports, class definitions, or framework-specific
  code (Agent, Model, etc.) — this is pure algorithm pseudocode, not code

## Final reminder

Your output IS the contract the coder must implement. Ambiguity in your
output = mechanism drift in the simulator = calibration bias downstream.

---

## Machine-readable JSON spec (REQUIRED, append at the very end)

After the markdown sections above, append a single fenced ```json``` block
containing a structured spec. The TemplateGenerator parses this block and
emits 5 boilerplate files (model.py, scenario.py, data_collector.py,
main.py, SimulatorScenarios.csv) deterministically — the LLM never writes
them. Without a valid JSON block, the pipeline falls back to free-form
codegen and topology / scenario / data-collector boilerplate may regress.

### Schema (all fields required unless marked optional)

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

### Topology type — pick ONE

| Type | Required params |
|---|---|
| `"watts_strogatz"` | `k` (int, even), `p` (float) |
| `"barabasi_albert"` | `m` (int, edges per new node) |
| `"erdos_renyi"` | `p` (float, edge probability) |
| `"netlogo_spatially_clustered"` | `avg_degree` (int) |
| `"melodie_named"` | `name` (str, networkx generator name) + kwargs |

**Topology param values**: bare scenario references use `"scenario.X"`
(quoted as a JSON string — the renderer extracts the identifier).
Numeric literals use raw JSON numbers.

### Scenario param types — pick ONE per param

`"int"` | `"float"` | `"bool"` | `"str"`

### Required scenario_params

Every value in `agent_state_vars`, `topology.params`, and the
`env_step_pseudocode` that comes from `scenario.X` MUST appear in
`scenario_params` (the templated Scenario class only has the fields
you declare here). At minimum include `periods` and the value named
by `n_agents_param`.

### Targets

`targets` lists environment-level attribute names. The DataCollector
template registers each as a column; the environment.step() body that
CoderAgent writes is REQUIRED to set `self.<target>` each tick.

### Failure modes

If you cannot determine a value, use a sensible default (e.g., 250 for
periods, 150 for agent_num). DO NOT emit `null` for required fields —
that causes parse failure. The JSON block MUST be valid JSON; no
trailing commas, no comments, no Python literals.
