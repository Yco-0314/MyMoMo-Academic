# ABM Auto Runtime — Quick Reference

> Internal reference for LLM code generation agents.
> Original: melodie-quickref.md from ABM4ALL/melodie-skills (MIT).
> Always use `from abm_auto.runtime import ...` in generated code.

## Core Classes (always available)

| Class | Role |
|---|---|
| `Config` | Project path and output configuration |
| `Scenario` | Input parameter container (CSV → attributes) |
| `Model` | Simulation orchestrator |
| `Environment` | Macro-level state and agent coordination |
| `Agent` | Base class for plain agents |
| `AgentList` | Managed collection of agents |
| `DataCollector` | Output recorder |
| `Simulator` | Execution engine |

## Spatial Classes (Grid module)

| Class | Role |
|---|---|
| `Grid` | 2D discrete space manager |
| `GridAgent` | Agent with `x`, `y` coordinates on Grid |
| `Spot` | Individual grid cell (customisable attributes) |

## Network Classes

| Class | Role |
|---|---|
| `Network` | Graph topology manager |
| `NetworkAgent` | Agent with network connections |

## Optimisation Classes

| Class | Role |
|---|---|
| `Calibrator` | Genetic-algorithm parameter fitting |
| `Trainer` | Agent behaviour pre-training via GA |

## Key API Signatures

### Model
```python
self.create_agent_list(AgentClass)           # → AgentList
self.create_environment(EnvClass)            # → Environment instance
self.create_data_collector(DCClass)          # → DataCollector instance
self.create_grid()                           # → Grid (no args!)
self.create_network()                        # → Network
self.iterator(n)                             # → range-like, MUST use in run()
```

### AgentList
```python
agents.setup_agents(agents_num=N)
agents.filter(predicate)                     # → list of agents
agents.to_dataframe()                        # → pd.DataFrame
agents[i]                                    # get by index
len(agents)
```

### Grid
```python
grid.setup_params(width, height, wrap=True, caching=True, multi=True)
grid.setup_agent_locations(agents, initial_placement="random_single")
grid.get_neighbors(agent, radius=1, moore=True, except_self=True)
    # → [(category_str, agent_id_int), ...]   ← NOT agent objects
grid.move_agent(agent, x, y)
grid.get_empty_spots()                       # → [(x,y), ...]
grid.find_empty_spot()                       # → (x, y)
grid.set_spot_property(attr_name, 2d_array)
```

### Network
```python
network.setup_agent_connections(agent_lists, network_type, network_params)
network.get_neighbors(agent)                 # → [(category, agent_id), ...]
network.create_edge(agent1, agent2)
network.add_agent(agent) / remove_agent(agent)
# Access neighbor object:
network.agent_categories[category].get_agent(agent_id)
```

### DataCollector
```python
dc.add_agent_property("agent_list_name", "attr_name")
dc.add_environment_property("attr_name")
dc.collect(t)
dc.save()
```

### Calibrator
```python
calibrator.add_scenario_calibrating_property("param_name")
calibrator.add_environment_property("output_metric")
# Must implement:
def distance(self, model) -> float: ...     # GA minimises this
```

### Trainer
```python
trainer.add_agent_training_property("attr_name")
trainer.collect_data()
# Must implement:
def utility(self, agent) -> float: ...      # GA maximises per agent
```

## File Naming Conventions (data/input/)

| Filename | Content |
|---|---|
| `SimulatorScenarios.csv` | Scenario rows: `id, run_num, periods, agent_num, ...` |
| `AgentParams.csv` | Per-agent initial attributes |
| `ID_*.csv` | Categorical dimension enumerations |
| `Relation_*.csv` | Valid parent→child ID pairs |
| `Data_*.csv` | Parameter tables (fixed or time-varying) |
| `CalibratorScenarios.csv` | Calibrator scenario parameters |
| `CalibratorParamsScenarios.csv` | GA hyperparameters + search ranges |
| `TrainerScenarios.csv` | Trainer scenario parameters |
| `TrainerParamsScenarios.csv` | Trainer GA hyperparameters |

## CSV Column Conventions

### SimulatorScenarios.csv
- `id` column **must start at 0** (not 1) — Melodie silently skips scenarios if id starts at 1
- Required columns: `id, run_num, periods, agent_num`
- All Scenario attributes declared in `setup()` must appear as columns here

### Metadata columns — exclude from collected metrics
The following columns are automatically written by the runtime and carry **no simulation
signal**. Do NOT register them with `add_agent_property()` or `add_environment_property()`,
and exclude them from sensitivity analysis:

```
id, id_scenario, id_run, agent_id, period, step, t, time, tick, x, y, run_num
```

**Why this matters**: The sensitivity analyser auto-detects output metrics by scanning
DataCollector output CSVs. If metadata columns are collected, they appear constant across
parameters → all Morris/Sobol indices become 0.

### Network topology columns (add to SimulatorScenarios.csv)
| Topology | Required columns |
|---|---|
| `watts_strogatz` | `network_k` (degree), `network_p` (rewiring prob) |
| `barabasi_albert` | `network_m` (edges per new node) |
| `erdos_renyi` | `network_p` (connection prob) |

## Common Mistakes → Corrections

| Wrong | Correct |
|---|---|
| `from Melodie import Agent` | `from abm_auto.runtime import Agent` |
| `for t in range(self.scenario.periods):` | `for t in self.iterator(self.scenario.periods):` |
| `agent.setup()` sets `self.state = 0` unconditionally | `self.state = getattr(self, "state", 0)` |
| `grid.get_neighbors(...)[0].state` | `self.agents[grid.get_neighbors(...)[0][1]].state` |
| `network.get_neighbors(...)[0].state` | `network.agent_categories[cat].get_agent(aid).state` |
| `self.grid.width` (may error) | store `self._w = self.scenario.grid_width` in `setup()` |
| `after_setup()` | Does not exist — use `setup_data()` in Scenario |
| Hard-coded parameter values | All params from Scenario / CSV |
| `id` column starts at 1 in SimulatorScenarios.csv | Must start at 0 |
| Collecting `period`, `id_scenario` with `add_agent_property` | These are metadata — never collect them |
