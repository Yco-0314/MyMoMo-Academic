# Writing a MyMoMo ABM — End-to-End Walkthrough

This is the integration document. The other four knowledge files describe
WHAT exists ([`01-runtime-api.md`](01-runtime-api.md)), HOW to choose
topology ([`03-modules.md`](03-modules.md)), the file CONTRACTS
([`04-data-contracts.md`](04-data-contracts.md)), and KNOWN MISTAKES
([`05-anti-patterns.md`](05-anti-patterns.md)). This file shows them
working together on one realistic model from start to finish.

**Running example**: virus diffusion on a small-world network — 150
agents, calibrated against an observed (susceptible, infected, resistant)
time series.

The same model in CALIBRATION mode is what the BEHAVE 2025 benchmark
exercises end-to-end (`benchmark_calibration_handcrafted.py`).

---

## Stage 0 — Write `story.md`

The user's only required input. Frame it so ModeDetector can extract
structured fields ([`04-data-contracts.md`](04-data-contracts.md) §1):

```markdown
# Virus on a Network

I want to model SIR-like virus diffusion on a small-world social network
of 150 individuals and calibrate the model parameters against an observed
time series of (susceptible, infected, resistant) counts.

## Mechanism (per tick)

1. Every infected individual independently exposes each susceptible
   neighbour with probability `virus_spread_chance / 100`.
2. Every `virus_check_frequency` ticks, each infected agent rolls
   `recovery_chance / 100`. On recovery they roll
   `gain_resistance_chance / 100` to become resistant; otherwise back to S.

## Observed data

`data/observed.csv` — 251 rows × {tick, susceptible, infected, resistant}.

## Parameters to estimate

| Parameter | Range | Unit |
|---|---|---|
| `virus_spread_chance`     | 0 – 20   | percent  |
| `recovery_chance`         | 0 – 5    | percent  |
| `gain_resistance_chance`  | 0 – 100  | percent  |

## Fixed structural parameters

- `agent_num` = 150
- `average_degree` = 6
- `initial_outbreak_size` = 3
- `virus_check_frequency` = 1 tick
- `periods` = 250 ticks
```

**What ModeDetector extracts** (sketch):

```json
{
  "mode": "originate",
  "phenomenon": "Virus diffusion on a small-world social network",
  "has_calibration_data": true,
  "calibration_data_path": "data/observed.csv",
  "calibration_targets": ["susceptible", "infected", "resistant"],
  "calibration_param_specs": [
    {"name": "virus_spread_chance",    "min": 0, "max": 20,  "unit": "percent"},
    {"name": "recovery_chance",        "min": 0, "max": 5,   "unit": "percent"},
    {"name": "gain_resistance_chance", "min": 0, "max": 100, "unit": "percent"}
  ]
}
```

---

## Stage 1 — Choose the topology

Apply the decision tree in [`03-modules.md`](03-modules.md):

> Does the phenomenon depend on agents observing/contacting each other?
> → Yes (infection requires neighbour contact).
> Is spatial position meaningful? → No (no map mentioned).
> → **Network**.

Specifically a small-world (Watts-Strogatz) graph — the story names it
explicitly. From [`01-runtime-api.md`](01-runtime-api.md) Network table:

- `topology = topologies.watts_strogatz(k=int_even, p=float)`

`k` must be even — see [`05-anti-patterns.md`](05-anti-patterns.md) §3.
`average_degree=6` from the story is already even, so we map directly:
`network_k=6`. For `network_p` (rewiring), pick a reasonable default
like `0.1` (small-world regime).

---

## Stage 2 — Design the data model

Three things to design before writing code:

**A. Agent state**

| Attribute | Type | Init source | Why |
|---|---|---|---|
| `state` | str | model.setup() | `"S"`, `"I"`, or `"R"` |
| `virus_check_timer` | int | model.setup() | counter for periodic recovery roll |

`state` doesn't come from `AgentParams.csv` in this model (initial
infected are chosen at model.setup() time), so `setup()` can simply
assign defaults.

**B. Environment state**

| Attribute | Why |
|---|---|
| `count_s`, `count_i`, `count_r` | aggregated each tick for the DataCollector to track |

These satisfy [`04-data-contracts.md`](04-data-contracts.md) §5 — they
match `spec.calibration_targets` after alias resolution.

**C. Scenario columns**

Mandatory ([`04-data-contracts.md`](04-data-contracts.md) §3): `id`,
`run_num`, `periods`, `agent_num`. Plus calibration params (must match
`spec.calibration_params` names verbatim) plus structural params:

```csv
id,run_num,periods,agent_num,average_degree,initial_outbreak_size,virus_check_frequency,seed,virus_spread_chance,recovery_chance,gain_resistance_chance
0,1,250,150,6,3,1,0,4.4,0.3,25.0
```

`4.4`, `0.3`, `25.0` are the truth values from BEHAVE 2025. In a real
research run you would write **plausible defaults in the declared
units** — `4.4` is fine (in range 0-20 percent). The
BayesianCalibrator uses spec ranges, not CSV defaults, to build priors
(see [`04-data-contracts.md`](04-data-contracts.md) §3 "Unit discipline").

---

## Stage 3 — Write the Python code

File layout (codegen produces these from DESIGN.md):

```
core/
  agent.py           — Person(NetworkAgent)
  environment.py     — VirusEnvironment(Environment)
  data_collector.py  — VirusDataCollector(DataCollector)
  scenario.py        — VirusScenario(Scenario)
  model.py           — VirusModel(Model) — the orchestrator
main.py              — Config + Simulator entry point
data/input/SimulatorScenarios.csv
```

### `core/agent.py`

```python
from abm_auto.runtime import NetworkAgent


class Person(NetworkAgent):
    def setup(self):
        # All attrs initialised in model.setup() — keep this minimal.
        # If you DID load state from AgentParams.csv, use _safe_attr
        # ([05-anti-patterns.md] §8).
        self.state: str = "S"
        self.virus_check_timer: int = 0
```

### `core/environment.py`

```python
from abm_auto.runtime import Environment


class VirusEnvironment(Environment):
    def setup(self):
        self.count_s: int = 0
        self.count_i: int = 0
        self.count_r: int = 0

    def step(self, agents=None):
        # Aggregate after the model's per-agent rules have run this tick.
        self.count_s = sum(1 for a in agents if a.state == "S")
        self.count_i = sum(1 for a in agents if a.state == "I")
        self.count_r = sum(1 for a in agents if a.state == "R")
```

### `core/data_collector.py`

```python
from abm_auto.runtime import DataCollector


class VirusDataCollector(DataCollector):
    def setup(self):
        # Output column names == attribute names (no implicit prefix).
        # These three match spec.calibration_targets via alias table.
        self.add_environment_property("count_s")
        self.add_environment_property("count_i")
        self.add_environment_property("count_r")
```

### `core/scenario.py`

```python
from abm_auto.runtime import Scenario


class VirusScenario(Scenario):
    def setup(self):
        # Mandatory columns
        self.periods: int = 0
        self.agent_num: int = 0
        # Network topology
        self.average_degree: int = 6
        self.initial_outbreak_size: int = 3
        # Recovery cadence
        self.virus_check_frequency: int = 1
        self.seed: int = 0
        # Calibration params — EXACT names matching spec.calibration_params
        self.virus_spread_chance: float = 4.4
        self.recovery_chance: float = 0.3
        self.gain_resistance_chance: float = 25.0
```

### `core/model.py`

```python
import random
from abm_auto.runtime import Model
from .agent import Person
from .environment import VirusEnvironment
from .data_collector import VirusDataCollector


class VirusModel(Model):
    def create(self):
        self.agents = self.create_agent_list(Person)
        self.environment = self.create_environment(VirusEnvironment)
        self.data_collector = self.create_data_collector(VirusDataCollector)
        self.network = self.create_network()

    def setup(self):
        # Reproducibility
        random.seed(self.scenario.seed)

        # Create agents
        self.agents.setup_agents(agents_num=self.scenario.agent_num)

        # Build small-world network
        self.network.setup_agent_connections(
            agent_lists=[self.agents],
            topology=topologies.watts_strogatz(
                k=self.scenario.average_degree,
                p=0.1,   # rewiring; could be exposed via scenario
            ),
        )

        # Seed initial infections (state set in model.setup, not agent.setup,
        # per 05-anti-patterns.md §8 "set initial state in model.setup")
        ids = random.sample(range(self.scenario.agent_num),
                            self.scenario.initial_outbreak_size)
        for i in ids:
            self.agents[i].state = "I"

    def run(self):
        # iterator() — NOT range() (05 §7)
        for t in self.iterator(self.scenario.periods):
            self._step_infections()
            self._step_recoveries()
            # environment aggregates per-tick counts after rules ran
            self.environment.step(self.agents)
            # collect(t) — period arg required (05 §7)
            self.data_collector.collect(t)
        # save() — required at end of run (05 §7)
        self.data_collector.save()

    def _step_infections(self):
        # Convert percent → probability at point of use (05 §4)
        p = self.scenario.virus_spread_chance / 100.0
        for agent in self.agents:
            if agent.state != "I":
                continue
            for neighbor in self.network.get_neighbors(agent):
                if neighbor.state == "S" and random.random() < p:
                    neighbor.state = "I"

    def _step_recoveries(self):
        rec_p = self.scenario.recovery_chance / 100.0
        res_p = self.scenario.gain_resistance_chance / 100.0
        check_n = self.scenario.virus_check_frequency
        for agent in self.agents:
            if agent.state != "I":
                continue
            agent.virus_check_timer += 1
            if agent.virus_check_timer < check_n:
                continue
            agent.virus_check_timer = 0
            if random.random() < rec_p:
                agent.state = "R" if random.random() < res_p else "S"
```

### `main.py`

```python
import os
from abm_auto.runtime import Config, Simulator
from core.model import VirusModel
from core.scenario import VirusScenario


if __name__ == "__main__":
    config = Config(
        project_name="VirusOnNetwork",
        project_root=os.path.dirname(__file__),
        input_folder="data/input",   # ← hard-coded by pipeline (01 §Config)
        output_folder="data/output",
    )
    simulator = Simulator(config=config, model_cls=VirusModel, scenario_cls=VirusScenario)
    simulator.run()
```

---

## Stage 4 — Run

```bash
cd <model_dir>
python main.py
```

Two output files appear in `data/output/`:

| File | Shape |
|---|---|
| `Result_Simulator_Agents.csv` | 150 × 250 = 37 500 rows |
| `Result_Simulator_Environment.csv` | 250 rows (one per tick) |

The Environment CSV has columns `id_scenario, id_run, period, count_s,
count_i, count_r`. The MSE scorer reads this via the `count_s ↔
susceptible` alias table ([`04-data-contracts.md`](04-data-contracts.md) §4).

---

## Stage 5 — Calibrate

When `spec.has_calibration_data` is true and `data/observed.csv` exists,
the pipeline routes Phase 6 to `BayesianCalibrator` instead of the
heuristic optimiser:

```python
# (Pipeline does this automatically — sketch:)
from abm_auto.calibration import BayesianCalibrator
result = BayesianCalibrator(client, workspace).run(executor, spec=spec, max_sims=30)
```

The calibrator:

1. Reads `spec.calibration_param_specs` for prior bounds (range + unit).
2. Builds uniform priors from those bounds — NOT from CSV defaults (this
   is the unit-drift fix, [`05-anti-patterns.md`](05-anti-patterns.md) §4).
3. Samples 30 parameter vectors, runs the simulator for each, collects
   summary stats (mean/std/last per target column).
4. Fits a Random Forest regressor: features = stats, target = params.
5. Predicts params from observed stats → posterior sample (per-tree).
6. Writes:
   - `posterior_summary.csv` — mean / std / 95% CI per param
   - `best_params.json` — posterior means
   - `calibration_report.md` — LLM-written human summary
   - `calibration_final_sim.csv` — one validation sim at best_params
7. Updates `SimulatorScenarios.csv` row 0 with the calibrated values
   (downstream phases see the calibrated configuration).

`benchmark_calibration_handcrafted.py` runs exactly this pipeline against
the BEHAVE 2025 ground truth.

---

## Reading the audit ledger

After a full pipeline run, open `<workspace>/audit_ledger.md` for a
chronological record of every agent's decisions. Format (one bullet per
event, real excerpt from a BEHAVE 2025 benchmark run):

```
- `ev-0001` ℹ **info** [INFO] Phase -1 (by ModeDetector): Research mode FORCED by --mode flag: originate (user override; LLM detection skipped)
- `ev-0002` ℹ **info** [INFO] Phase 0.5 (by HypothesisAgent): Generated 3 competing hypotheses; recommended H2
- `ev-0003` ℹ **info** [INFO] Phase 1 (by DesignAgent): DESIGN.md generated (prompt=phase1_design_originate, mode=originate, length=15768 chars, recommended_h=H2, used_h=H2)
- `ev-0004` ℹ **info** [INFO] Phase 1c (by ViabilityChecker): Viability Gate passed (assumptions=9, missing=0)
- `ev-0005` 🚩 **raise** [MEDIUM] Phase 1c (by ViabilityChecker): Design relies on 9 AI-ASSUMPTION tags ...
- `ev-0007` ℹ **info** [INFO] Phase 2 (by CoderAgent): Generated 8 files (172 lines total)
- `ev-0009` ℹ **info** [INFO] Phase 6 (calibration) (by BayesianCalibrator): Bayesian calibration complete via abc-rejection; 100 simulator calls, 3 params fit
```

Every agent writes here — see CalibrationBenchmark output for a real
example. Re-running the same workspace appends events rather than
overwriting (audit is append-only).

---

## Common pitfalls (quick index into 05)

| Symptom | See `05-anti-patterns.md` § |
|---|---|
| `AttributeError: module 'networkx' has no attribute 'watts_strogatz'` | §3 |
| `ModuleNotFoundError: No module named 'core.model'` from inside `core/` | §6 |
| Simulation runs but `count_i` stays at 0 throughout | §8 (setup overwrites CSV state) |
| `BayesianCalibrator` reports a param as `missing` | §5 (CSV column rename) |
| Calibration estimates 100× off truth | §4 (unit drift, percent vs probability) |
| `TypeError: collect() missing 1 required positional argument: 't'` | §7 |
| `cannot import name 'NetworkGrid' from 'abm_auto.runtime'` | §1 (hallucinated class) |

---

## Where this fits in the wider pipeline

This walkthrough covers **what code the LLM should produce**. The MyMoMo
pipeline (driven by `abm_auto/pipeline.py`) automates the surrounding
work:

| Phase | What runs | Reads | Writes |
|---|---|---|---|
| −1 | ModeDetector | `story.md` | `research_spec.json` |
| 0 | LitReviewer (optional) | `story.md` | `lit_notes.md` |
| 0.5 | HypothesisAgent (originate only) | `story.md`, `lit_notes.md` | `hypothesis.md` |
| 1 + 1c | DesignAgent + ViabilityChecker (GVR adapter, up to 3 iters) | `story.md`, `hypothesis.md` | `DESIGN.md` |
| 1b | OddWriter | `DESIGN.md` | `ODD.md` |
| 2 + 3 | CoderAgent + VerifierAgent (GVR adapter, up to 5 fix iters) | `DESIGN.md`, this knowledge base | `core/*.py`, `main.py`, CSVs |
| **4 + 5 + 6 loop** | Simulator → AnalyzerAgent → (Calibrator OR Optimizer); typically 2-3 iters | `SimulatorScenarios.csv`, `observed.csv` | `Result_Simulator_*.csv`, per-iter insights |
| 6 (in loop) | BayesianCalibrator OR OptimizerAgent | `observed.csv` (if any) | `best_params.json`, `posterior_summary.csv` |
| 6.5 | WhatIfOracle (originate only) | results | `what_if_analysis.md` |
| 7 | ReporterAgent | everything | `report.md` |
| 7b | VisualizerAgent | results | `figures/*.png` |
| 8 | ReviewerAgent (optional, `--review`) | everything | `peer_review.md` |

Each phase produces a contract-bound artifact ([`04-data-contracts.md`](04-data-contracts.md))
consumed by the next.

---

## Cross-references

- API surface: [`01-runtime-api.md`](01-runtime-api.md)
- Topology choice: [`03-modules.md`](03-modules.md)
- File contracts: [`04-data-contracts.md`](04-data-contracts.md)
- Errors to avoid: [`05-anti-patterns.md`](05-anti-patterns.md)
- Real benchmark: `benchmark_calibration_handcrafted.py` +
  `examples/calibration_challenge_virus/`
