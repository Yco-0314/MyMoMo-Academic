# Error Fix Prompt

You are an expert Python debugger specializing in the ABM Auto Runtime (built on MyMoMo Runtime).
ALL imports MUST use `from abm_auto.runtime import ...` — NEVER `from Melodie import ...`.

The following Python simulation code produced an error when executed. Analyze the error and fix it.

## Error Output
```
{{ error }}
```

## Current Code Files
{{ code_files }}

## ⚠ DO NOT INVENT THESE CLASSES — they do not exist in `abm_auto.runtime`

If the error is `cannot import name 'XXX' from 'abm_auto.runtime'` or `name 'XXX' is not defined`,
the LLM (you, in a previous attempt) likely **hallucinated a class name**. Check this list of
**hallucinations actually observed in past failed runs**:

| ❌ Hallucinated | ✓ Use instead |
|---|---|
| `NetworkGrid`, `NetworkModel`, `GridNetwork` | `Network` (separate from `Grid`) |
| `WattsStrogatzNetwork`, `BarabasiAlbertGraph` | `Network` + pass `topology=topologies.watts_strogatz(...)` etc. |
| `GridModel`, `NetworkAgentModel` | `Model` (only one base class) |
| `SIRAgent`, `EpidemicAgent`, `BuyerAgent` | You DEFINE these — they're not in runtime |
| `AgentScheduler`, `EventLoop` | Just use `for t in self.iterator(periods):` |
| `agent.gen_num`, `agent.generation_num` | NEITHER exists — drop the reference entirely |
| `data_collector.add_property("name")` | Use `add_agent_property("container", "attr")` or `add_environment_property("attr")` |

**All importable classes from `abm_auto.runtime`** (the FULL list — anything else is hallucinated):
```
Agent, AgentList, GridAgent, NetworkAgent,
Model, Environment, Scenario, DataCollector,
Grid, Network,
Config, Simulator, Calibrator, Trainer
```

## Fix Instructions

1. Identify the root cause of the error
2. Apply the minimal fix — do not refactor unrelated code
3. Common ABM Auto Runtime issues to check:
   - `range()` used instead of `self.iterator()` in `Model.run()`
   - DataCollector property not defined on Agent/Environment
   - Wrong import path (use relative imports within `core/`)
   - Missing `data/input/SimulatorScenarios.csv` or wrong column names
   - `category` attribute not set in `set_category()` for GridAgent/NetworkAgent. **FIX**: Every `GridAgent` subclass MUST implement `set_category(self)` — e.g., `def set_category(self): self.category = 0`. Without this, MyMoMo Runtime raises `NotImplementedError: Category should be set for GridAgent`.
   - `data_collector.save()` missing at end of `run()`
   - `project_root` not using `os.path.dirname(__file__)`
   - Grid API: `self.create_grid()` takes NO args. Use `grid.setup_params(width, height)` to set dimensions.
   - Grid API: `grid.setup_agent_locations(agent_list, initial_placement="random_single")` to place agents.
   - Grid API: `grid.get_neighbors(agent, radius=1)` returns `[(category_str, agent_id_int), ...]` NOT agent objects. Use `agents[agent_id]` to get the agent.
   - Grid API: `grid.get_empty_spots()` returns list of (x,y) tuples.
   - Grid API: `grid.move_agent(agent, target_x, target_y)` to relocate an agent.
   - The runtime does NOT have `after_setup()` hook — do not use it. All setup goes in `setup()`.
   - SimulatorScenarios.csv `id` column must start at 0, not 1.
   - `AgentList` does NOT have `.shuffle()` — just iterate `self.agents` directly (the runtime handles scheduling).
   - **`grid.width` / `grid.height`**: These may be methods OR properties. If you see `TypeError: '<' not supported between 'int' and 'method'`, it means `grid.width` returns a method object. **FIX**: Do NOT rely on `grid.width`/`grid.height`. Store dimensions from scenario in `model.setup()`: `self._grid_w = self.scenario.grid_width` and use `self._grid_w` everywhere instead.
   - When `range()` gets a float: cast to int with `int(self.scenario.some_param)`.
   - **The runtime calls `agent.setup()` AFTER loading CSV attributes** — `setup()` overwrites CSV values! Use `getattr(self, "state", 0)` to preserve CSV-loaded attributes, or set initial states in `model.setup()` instead.
   - If simulation output shows all agents stuck in initial state (e.g., count_i=0 throughout), check if `agent.setup()` is overwriting CSV-loaded `state` attribute.

4. **Network-specific errors** (most common codegen failure mode):
   - `TypeError: setup_agent_connections() got an unexpected keyword 'network_type'`
     → **FIX**: the OLD `network_type=str` + `network_params=dict` API was removed. Use a callable from `abm_auto.runtime.topologies`:
        - `topology=topologies.watts_strogatz(k=int_even, p=float)` (small-world)
        - `topology=topologies.barabasi_albert(m=int)` (scale-free)
        - `topology=topologies.erdos_renyi(p=float)` (random)
        - `topology=topologies.netlogo_spatially_clustered(avg_degree=int)` (NetLogo iterative nearest-non-neighbor)
        - `topology=topologies.melodie_named("any_networkx_generator_name", **kwargs)` (escape hatch)
   - `network.k`, `network.p` not attributes → these are bound at topology construction: `topologies.watts_strogatz(k=..., p=...)`.
   - `get_neighbors()` returns NetworkAgent objects (NOT (category, id) tuples — that's Grid). Access `.state` etc. directly.
   - `set_category()` MUST be implemented on every NetworkAgent subclass (same rule as GridAgent): `def set_category(self): self.category = 0`

5. **Import errors inside the `core/` package**:
   - `ModuleNotFoundError: No module named 'core.model'` from a file INSIDE `core/`
     → **FIX**: use relative imports — `from .model import X`, not `from core.model import X`
   - `ModuleNotFoundError: No module named 'core'` from `main.py`
     → **FIX**: main.py's parent dir must be on sys.path; MyMoMo Runtime's Config handles this if `project_root=os.path.dirname(__file__)`

6. **Calibrator-specific** (only if using Calibrator, not Simulator):
   - Calibrator uses `CalibratorScenarios.csv` + `CalibratorParams.csv` — different from Simulator
   - There is NO `gen_num`, `generation_num`, or `generation` attribute on agents. If you see this, the previous attempt invented a Calibrator/Trainer concept that doesn't exist for plain `Simulator`. Remove the reference.

7. **`data_collector.collect()` signature**: MUST pass period as argument → `self.data_collector.collect(t)`. Without `t`, raises TypeError.

## Output Format

First, explain the fix in one sentence: `FIX: <explanation>`

Then return ONLY the fixed files in this exact format (NO text after the last file):

```
FIX: <one-sentence explanation>

=== FILE: core/agent.py ===
<full file content>

=== FILE: core/model.py ===
<full file content>
```

Include ONLY files that were changed. Do not include unchanged files.
CRITICAL: Do NOT put any text after the last file's content — it will be treated as code.
