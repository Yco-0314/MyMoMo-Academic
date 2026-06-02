# Data Contracts

Five concrete file formats that the MyMoMo pipeline reads or writes:

1. **`story.md`** — the user's research description; ModeDetector extracts
   structured fields from it.
2. **`research_spec.json`** — internal handoff between ModeDetector and the
   rest of the pipeline.
3. **`data/input/SimulatorScenarios.csv`** — driver input that the
   Simulator iterates over.
4. **`data/observed.csv`** — empirical data the calibrator fits against
   (originate mode only).
5. **`data/output/Result_Simulator_*.csv`** — simulation outputs.

Each section below states the contract, who reads it, who writes it, and
the failure modes when the contract is violated.

---

## 1. `story.md`

**Producer**: the user. Hand-written research description.  
**Consumer**: ModeDetector → DesignAgent → HypothesisAgent (originate mode).

No schema is enforced — it's free-form Markdown. But ModeDetector's
extraction prompt looks for a set of cues, so cooperative authoring helps:

| Section cue | Extracted into | Example |
|---|---|---|
| Paper citation, classic-model name | `mode="reproduce"`, `paper_ref` | "Reproduce Schelling 1971 segregation" |
| Phenomenon description, "I want to model …" | `mode="originate"`, `phenomenon` | "Cascading trust collapse in online markets" |
| Mention of empirical data | `has_calibration_data=true` | "Observed data at data/observed.csv" |
| Explicit path | `calibration_data_path` | "Data: data/observed.csv" |
| Calibration target columns | `calibration_targets` | "Match infected, susceptible, resistant time series" |
| Parameter table (name + range + unit) | `calibration_param_specs` | See template below |

**Recommended template for the parameter table** (so ModeDetector reliably
extracts `calibration_param_specs`):

```markdown
## Parameters to estimate

| Parameter | Range | Unit |
|---|---|---|
| `virus_spread_chance`   | 0 – 20  | percent  |
| `recovery_chance`       | 0 – 5   | percent  |
| `gain_resistance_chance`| 0 – 100 | percent  |
```

Use backticks around parameter names, exact integer/float ranges, and the
unit (`percent`, `probability`, `rate`, `count`, ...) as the last column.
The CoderAgent passes these specs verbatim into the codegen prompt as a
hard contract — see §3 below.

---

## 2. `research_spec.json` (written by ModeDetector)

**Producer**: `abm_auto/agents/mode_detector.py`.  
**Consumer**: every downstream agent (DesignAgent, ViabilityChecker,
CoderAgent, BayesianCalibrator, ReviewerAgent, …).

Single JSON object with these keys:

```json
{
  "mode": "reproduce" | "originate",
  "confidence": 0.95,

  "paper_ref": "Schelling 1971",
  "paper_doi": "",

  "phenomenon": "",
  "research_question": "",

  "has_calibration_data": true,
  "calibration_data_path": "data/observed.csv",
  "calibration_targets":   ["susceptible", "infected", "resistant"],
  "calibration_params":    ["virus_spread_chance", "recovery_chance",
                            "gain_resistance_chance"],
  "calibration_param_specs": [
    {"name": "virus_spread_chance",    "min": 0, "max": 20,  "unit": "percent"},
    {"name": "recovery_chance",        "min": 0, "max": 5,   "unit": "percent"},
    {"name": "gain_resistance_chance", "min": 0, "max": 100, "unit": "percent"}
  ],

  "viability_max_assumptions":    5,
  "viability_max_missing_elements": 3,
  "viability_llm_question": "Is this design a SEMANTICALLY consistent ..."
}
```

**Invariants**:

- `calibration_params` is the flat list of names; `calibration_param_specs`
  is the rich list with `{name, min, max, unit}`. They MUST stay
  synchronised — every entry in `_specs` has its `name` in `_params`.
  ModeDetector enforces this on detection. Manually edited specs must
  preserve the invariant.
- `mode` is set ONCE per workspace. If `research_spec.json` already exists,
  ModeDetector reuses it instead of re-detecting (idempotent re-runs).
- The `viability_*` fields are mode-derived defaults; the orchestrator
  pulls them into ViabilityChecker.

**Force a mode**: pass `--mode reproduce|originate` to the CLI; the
override wins over LLM detection.

---

## 3. `data/input/SimulatorScenarios.csv`

**Producer**: CoderAgent (initial) → BayesianCalibrator (mutates row 0 per
sample) → OptimizerAgent (rewrites between iterations).  
**Consumer**: the Simulator driver.

One row per scenario. Each column becomes an attribute on the Scenario
object during the run (see [`01-runtime-api.md`](01-runtime-api.md)
"Scenario").

**Mandatory columns** (the Simulator looks for these by name):

| Column | Type | Purpose |
|---|---|---|
| `id` | int | Scenario id, MUST start at 0 |
| `run_num` | int | Replications per scenario (1 = single run) |
| `periods` | int | Time steps |
| `agent_num` | int | Number of agents to create |

**Calibration contract** (originate mode with calibration data): every
name in `spec.calibration_params` MUST also appear as a column here, with
a default value in the declared range and unit.

❌ Wrong (contract violation):
```csv
id,run_num,periods,agent_num,natural_recovery_chance,...
```
The LLM renamed `recovery_chance` to `natural_recovery_chance`. The
BayesianCalibrator's allowlist (which trusts `spec.calibration_params`)
filters this column out → returns `recovery_chance: missing`. CoderVerifier
detects the missing column and routes through GVR feedback to regenerate.

**Unit discipline**: if `spec.calibration_param_specs` declares unit
`percent` with range 0-20, the CSV default MUST be in that scale (e.g.
`4.4`), not its probability equivalent (`0.044`). The CoderAgent enforces
this via a hard-constraint block in the codegen prompt. See
[`05-anti-patterns.md`](05-anti-patterns.md) §4.

**Structural vs tunable params**: columns NOT in `spec.calibration_params`
(typically `agent_num`, `periods`, `seed`, network topology constants) are
NEVER perturbed by the calibrator — they stay at the row-0 default for
every calibration sample. This protects the simulator from crashing on
mis-typed structural changes.

**Multiple scenarios**: each row is a separate run. The Simulator iterates
them in order, calling `model.create() → setup() → run()` per row.

**Example** (virus-on-a-network calibration challenge):
```csv
id,run_num,periods,agent_num,average_degree,initial_outbreak_size,virus_check_frequency,seed,virus_spread_chance,recovery_chance,gain_resistance_chance
0,1,250,150,6,3,1,0,4.4,0.3,25.0
```

---

## 4. `data/observed.csv`

**Producer**: the user (or, in benchmarks, copied from a published
challenge).  
**Consumer**: BayesianCalibrator (compares simulator output against this).

Required structure: one column for the time axis, one column per
calibration target. The time-axis column name is recognised by alias
(`tick`, `period`, `step`, `time`, `t`). Calibration-target columns
should match the names declared in `spec.calibration_targets`.

**Example**:
```csv
tick,susceptible,infected,resistant
0,147,3,0
1,145,5,0
2,144,6,0
...
249,10,27,113
```

The calibrator aligns on the time-axis column via inner-join and computes
MSE over the matched ticks. Length mismatches are tolerated (the inner
join finds whatever overlaps).

**Column-name flexibility**: the MSE scorer (`benchmark_calibration_*.score_calibration_mse`)
tolerates per-target aliases:

| Observed col | Acceptable simulator cols |
|---|---|
| `susceptible` | `susceptible`, `count_s`, `s`, `count_susceptible`, `n_susceptible` |
| `infected`    | `infected`, `count_i`, `i`, `count_infected`, `n_infected` |
| `resistant`   | `resistant`, `count_r`, `r`, `count_resistant`, `n_resistant`, `recovered` |

This is a benchmarking concession only — for production calibration runs
the safest path is to make the simulator output column names match
`observed.csv` exactly.

**Location**: by default `<workspace>/data/observed.csv`. The
`calibration_data_path` field in `research_spec.json` can override this.

---

## 5. `data/output/Result_Simulator_*.csv`

**Producer**: DataCollector at `.save()` time, called from `Model.run()`.  
**Consumer**: AnalyzerAgent, BayesianCalibrator (per-sample sim output),
the MSE scorer, the user.

Two files are written per Simulator run, named by convention:

| File | Granularity | Rows |
|---|---|---|
| `Result_Simulator_Agents.csv` | one per (agent × period) | `agent_num × periods` |
| `Result_Simulator_Environment.csv` | one per period | `periods` |

**Column schema (Agents CSV)**:

| Column | Source |
|---|---|
| `id_scenario` | scenario id from `SimulatorScenarios.csv` |
| `id_run` | replication index within scenario |
| `period` | time step (0-indexed) |
| `id` | agent's internal id |
| ...one column per `add_agent_property()` call... | the agent's attribute at that period |

Sample first row (virus-on-a-network calibration benchmark):
```csv
id_scenario,id_run,period,id,state,virus_check_timer
0,0,0,0,S,1
```

**Column schema (Environment CSV)**:

| Column | Source |
|---|---|
| `id_scenario` | scenario id |
| `id_run` | replication index |
| `period` | time step |
| ...one column per `add_environment_property()` call... | the env's attribute at that period |

**Output column = attribute name**: when DataCollector.setup() declares
`self.add_environment_property("total_demand")`, the output CSV gets a
column literally named `total_demand`. No implicit prefixing.

For calibration purposes the BayesianCalibrator looks for the column
names in `spec.calibration_targets`. If the simulator outputs `count_s`
but `spec.calibration_targets = ["susceptible"]`, the MSE scorer's alias
table (see §4) bridges the gap. Direct name match is preferable.

---

## How to add a new data contract

When you introduce a new file the pipeline must read or write:

1. Choose a fixed path under `<workspace>/` and document it here.
2. State producer + consumer agents and the schema.
3. Identify the failure modes when the contract is violated.
4. If a violation is detectable mechanically, add the check to the
   relevant validator (typically inside an existing GVR adapter).
5. Add an example with real values from a benchmark run.
