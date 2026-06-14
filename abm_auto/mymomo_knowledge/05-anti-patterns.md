# Anti-Patterns — Errors Actually Observed in MyMoMo Benchmark Runs

This catalogue records **specific mistakes that the LLM made** while
generating or fixing MyMoMo Runtime code during real benchmark runs. Each
entry pairs the wrong code with the correct fix, plus a short note on **why
the LLM kept making this mistake** (so the prompt-engineering and verifier
layers can address it at the source).

LLM agents consult this file at codegen and verification time. If you ship a
new benchmark and a new failure mode appears, append a section here — the
verifier prompt automatically picks up new anti-patterns on the next run.

---

## 1. Hallucinated class names

The LLM invents class names that "sound right" but do not exist in
`abm_auto.runtime`. Real failures, all observed in this repository:

| ❌ Hallucinated | ✓ Use instead |
|---|---|
| `NetworkGrid`, `GridNetwork`, `NetworkModel` | `Network` (a separate top-level class from `Grid`) |
| `WattsStrogatzNetwork`, `BarabasiAlbertGraph` | `Network` + `topology=topologies.watts_strogatz(...)` etc. (see `01-runtime-api.md` §Network) |
| `GridModel`, `NetworkAgentModel`, `SIRModel` | `Model` — there is only one base class |
| `SIRAgent`, `EpidemicAgent`, `BuyerAgent` | These are **your** classes; subclass `Agent` / `GridAgent` / `NetworkAgent` |
| `AgentScheduler`, `EventLoop` | No such thing. Use `for t in self.iterator(periods):` |

**Why it happens**: combining a topology adjective (network / grid / SIR)
with a base class name produces a plausible-looking identifier. The LLM has
no compile-time signal that the resulting name is invented.

**Cure**: the canonical list of importable names lives in
[`01-runtime-api.md`](01-runtime-api.md). Anything outside that list is
hallucinated.

---

## 2. Hallucinated attribute / method names

| ❌ Hallucinated | ✓ Reality |
|---|---|
| `agent.gen_num`, `agent.generation_num` | Neither exists. The LLM invented "generation" from the word "Calibrator". Drop the reference entirely. |
| `agent_list.shuffle()` | `AgentList` does not have `.shuffle()`. Iterate `self.agents` directly. |
| `model.after_setup()` | There is no `after_setup()` hook. All initialisation goes in `setup()`. |
| `data_collector.add_property("name")` | Use either `add_agent_property("container", "attr")` or `add_environment_property("attr")`. |
| `network.k`, `network.p` | These are not attributes. Bind them at topology construction: `topology=topologies.watts_strogatz(k=..., p=...)`. |

**Why `gen_num` was particularly stubborn**: in early benchmarks the LLM
oscillated between `gen_num` and `generation_num` across 5 retries — both
were hallucinations. Fix was architectural: cumulative feedback in the GVR
loop (see `abm_auto/refinement.py`) now shows the LLM the FULL failure
history so it stops cycling through equivalent wrong answers.

---

## 3. Old string-based network API (removed)

The OLD API took a `network_type=str` + `network_params=dict`:

```python
# ❌ REMOVED — will raise TypeError("unexpected keyword 'network_type'")
self.network.setup_agent_connections(
    agent_lists=[self.agents],
    network_type="watts_strogatz_graph",
    network_params={"k": 6, "p": 0.1},
)
```

Use the callable form from `abm_auto.runtime.topologies` instead:

```python
# ✓ Current
self.network.setup_agent_connections(
    agent_lists=[self.agents],
    topology=topologies.watts_strogatz(k=6, p=0.1),
)
```

`k` for Watts-Strogatz must be an **even** integer (networkx enforces it).

Other built-in adapters: `barabasi_albert(m)`, `erdos_renyi(p)`,
`netlogo_spatially_clustered(avg_degree)`, and the escape hatch
`nx_named("any_networkx_graph_fn", **kwargs)`.

---

## 4. Unit drift (silent — discovered only via benchmark)

The story.md says `virus_spread_chance: 0–20 percent`. LLM-generated code
converts to probability scale (0.044 instead of 4.4), then the calibrator's
priors end up 100× off truth.

❌ Wrong:
```python
# Story says 4.4 percent, code stores as probability
self.virus_spread_chance: float = 0.044
# ... then later:
if random.random() < self.scenario.virus_spread_chance:  # too small
```

✓ Right:
```python
# Match the unit declared in story.md / calibration_param_specs
self.virus_spread_chance: float = 4.4    # percent, range 0–20
# Convert only at the point of use:
if random.random() < self.scenario.virus_spread_chance / 100.0:
```

**Cure**: `ResearchSpec.calibration_param_specs` carries `unit` per param;
`CoderAgent` injects this into the codegen prompt as a hard constraint. See
[`04-data-contracts.md`](04-data-contracts.md).

---

## 5. Calibration parameter renaming

`ResearchSpec.calibration_params` says the user wants `recovery_chance`
estimated. LLM-generated `SimulatorScenarios.csv` calls the column
`natural_recovery_chance`. BayesianCalibrator then reports `recovery_chance`
as `missing` — silent contract violation.

❌ Wrong (codegen output):
```csv
id,run_num,periods,...,natural_recovery_chance,...
```

✓ Right:
```csv
id,run_num,periods,...,recovery_chance,...
```

**Cure**: CoderAgent injects a "Calibration Contract" block listing the
EXACT names. After codegen, the verifier checks that every requested name
is a column in the CSV — violation → GVR feedback loop.

---

## 6. Import style inside the `core/` package

❌ Wrong (from inside `core/model.py`):
```python
from core.agent import MyAgent       # ModuleNotFoundError: No module named 'core.agent'
```

✓ Right:
```python
from .agent import MyAgent           # relative import — package-aware
```

`main.py` is OUTSIDE the package and CAN use `from core.model import ...`
(absolute), provided `Config(project_root=os.path.dirname(__file__))` adds
its directory to sys.path.

---

## 7. `Model.run()` lifecycle mistakes

❌ Wrong:
```python
def run(self):
    for t in range(self.scenario.periods):     # ← Simulator can't collect
        self.environment.step()
    # ← missing data_collector.save()
```

✓ Right:
```python
def run(self):
    for t in self.iterator(self.scenario.periods):   # MUST use iterator()
        self.environment.step()
        self.data_collector.collect(t)               # pass period
    self.data_collector.save()                       # required at end
```

Three rules:
1. `self.iterator(periods)` — not `range(periods)`. Without this the
   simulator's data-collection plumbing never advances.
2. `self.data_collector.collect(t)` — the period argument is required.
   Calling `collect()` raises `TypeError`.
3. `self.data_collector.save()` at end of `run()` — without it no output CSV
   is written.

---

## 8. `setup()` overwrites CSV-loaded attributes

The runtime loads agent attributes from `AgentParams.csv` BEFORE calling
`agent.setup()`. A naive `setup()` overwrites them:

❌ Wrong:
```python
class Person(Agent):
    def setup(self):
        self.state = 0    # ← always overwrites CSV value
```

Result: every agent starts in state 0 regardless of CSV. In an SIR model,
infected initial agents never appear → simulation never produces dynamics.

✓ Right:
```python
class Person(Agent):
    def setup(self):
        self.state = self._safe_attr("state", 0)   # preserves CSV value
```

`_safe_attr(name, default)` returns the existing attribute if already set
(CSV-loaded), else the default. Use it for **any attribute that may come
from CSV**.

Alternative: set initial states in `model.setup()` after `setup_agents()`,
not in `agent.setup()`.

---

## 9. `GridAgent` / `NetworkAgent.set_category()` — gotcha when overriding

MyMoMo Runtime provides a **default** `set_category()` that assigns
`self.category = 0`, so for single-agent-type models you can just inherit:

```python
class Person(NetworkAgent):
    pass    # set_category() inherited — category becomes 0 automatically
```

But if you **override** `set_category()` and forget to set `self.category`,
the simulator raises `AttributeError` the first time anything reads it:

❌ Wrong:
```python
class Person(NetworkAgent):
    def set_category(self):
        print("setting up")    # ← never assigns self.category → AttributeError
```

✓ Right:
```python
class Person(NetworkAgent):
    def set_category(self):
        self.category = 0       # integer category id — required when overriding
```

When you have multiple agent classes sharing the same grid/network, give
each a distinct integer (`0`, `1`, `2`, ...). `category` is a STATIC type
id — it never changes during the simulation.

---

## How to add a new anti-pattern

When a benchmark surfaces a new LLM error mode:

1. Identify the **minimal wrong code** that caused the failure
2. Write the **correct code** beside it
3. Note **why the LLM kept making this mistake** (token bias / API ambiguity
   / silent symptom)
4. Append a section here, numbered.
5. If the error is severe enough to warrant prompt-side prevention, also add
   it to `abm_auto/prompts/verify_fix.md` under "DO NOT INVENT THESE".

This file is consulted by the codegen + verifier LLM calls — every new
entry directly reduces future bug rate.
