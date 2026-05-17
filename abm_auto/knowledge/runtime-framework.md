# ABM Auto Runtime — Framework Reference

> Internal reference for LLM code generation agents.
> Original: melodie-framework.md from ABM4ALL/melodie-skills (MIT).
> In generated code, use `from abm_auto.runtime import ...` — not `from Melodie import ...`.

## Architecture Philosophy

**"Smart Environment, Simple Agents"**

- Agents hold their own state and expose transition methods
- Environment manages macro-level coordination and decides when/how agents interact
- Model orchestrates calling order within each time step
- The value of ABM lies in connecting micro behaviors to macro phenomena

## Execution Chain

```
Config
  └─→ Simulator
        └─→ for each scenario row:
              Scenario.setup()          ← 1. declare attrs + types
              → CSV loaded              ← 2. runtime overwrites attrs from SimulatorScenarios.csv
              → Scenario.load_data()    ← 3. optional: load extra data files
              → Scenario.setup_data()   ← 4. optional: preprocess loaded data
              → Model.create()          ← 5. instantiate components
              → Model.setup()           ← 6. bulk-initialise agents HERE (safe, after CSV)
              → for each agent:
                    agent.setup()       ← 7. ⚠️ runs AFTER CSV — do NOT set attrs unconditionally
              → Model.run()
                   └─→ for t in model.iterator(periods):
                             environment.step()
                             data_collector.collect(t)
              → data_collector.save()
              → output CSVs
```

### ⚠️ Critical: agent.setup() runs AFTER CSV loading

Steps 2 and 7 interact dangerously:

```
Step 2: agent.state loaded from AgentParams.csv → agent.state = 1
Step 7: agent.setup() runs → self.state = 0   ← OVERWRITES the CSV value!
```

**Always use `getattr` to preserve CSV-loaded values:**
```python
def setup(self):
    self.state: int = getattr(self, "state", 0)   # ✅ preserves CSV value
    # self.state: int = 0                          # ❌ overwrites CSV value
```

**Alternative: bulk-initialise in Model.setup() instead:**
```python
def setup(self):
    self.agents.setup_agents(agents_num=self.scenario.agent_num)
    # Set initial states directly — runs BEFORE agent.setup()
    for i, agent in enumerate(self.agents):
        agent.state = i % 2   # or load from a list
```

## Core Components

### Config
Establishes project paths, input/output folders, and execution settings.
```python
from abm_auto.runtime import Config
config = Config(
    project_name="MyProject",
    project_root=os.path.dirname(__file__),
    input_folder="data/input",
    output_folder="data/output",
)
```

### Scenario
Single source of truth for all input parameters. Three-step lifecycle:
1. `setup()` — declare attributes with correct types and default values
2. (auto) — runtime reads SimulatorScenarios.csv, overwriting declared attrs
3. `load_data()` / `setup_data()` — load and preprocess additional data files

```python
from abm_auto.runtime import Scenario
class MyScenario(Scenario):
    def setup(self):
        self.periods: int = 0
        self.agent_num: int = 0
        self.param_x: float = 0.0  # all CSV columns declared here

    def load_data(self):
        pass  # optional: load additional data files

    def setup_data(self):
        pass  # optional: preprocess loaded data
```

### Model
Orchestrator that assembles Environment, Agents, and DataCollector.
```python
from abm_auto.runtime import Model
class MyModel(Model):
    def create(self):
        # Called once — instantiate components
        self.agents = self.create_agent_list(MyAgent)
        self.environment = self.create_environment(MyEnvironment)
        self.data_collector = self.create_data_collector(MyDataCollector)

    def setup(self):
        # Called once per scenario — initialize state
        self.agents.setup_agents(agents_num=self.scenario.agent_num)

    def run(self):
        # Simulation loop — MUST use iterator(), never range()
        for t in self.iterator(self.scenario.periods):
            self.environment.step(self.agents)
            self.data_collector.collect(t)
        self.data_collector.save()
```

### Environment
Manages macro-state and coordinates agent interactions.
- Auto-receives `self.model` and `self.scenario` references
- `step()` is the main update method — called once per time step
```python
from abm_auto.runtime import Environment
class MyEnvironment(Environment):
    def setup(self):
        self.metric: float = 0.0

    def step(self, agents=None):
        # macro logic + agent coordination
        pass
```

### Agent
Lightweight state holder with auto-assigned `id`.
- `setup()` runs AFTER CSV loading — use `getattr(self, attr, default)` to preserve CSV values
- Implement behavioral methods called by Environment or Model
```python
from abm_auto.runtime import Agent
class MyAgent(Agent):
    def setup(self):
        self.state: int = getattr(self, "state", 0)  # preserve CSV value
        self.energy: float = 1.0

    def step(self):
        pass
```

### DataCollector
Records specified properties at each timestep; saves to CSV.
```python
from abm_auto.runtime import DataCollector
class MyDataCollector(DataCollector):
    def setup(self):
        self.add_agent_property("agents", "state")        # agent list name + attr
        self.add_environment_property("metric")           # env attr
```

### Simulator
Main execution manager.
```python
from abm_auto.runtime import Config, Simulator
simulator = Simulator(config=config, model_cls=MyModel, scenario_cls=MyScenario)
simulator.run()                    # sequential
simulator.run_parallel(cores=4)   # parallel across scenarios
simulator.run_visual()             # browser-based visualisation
```

## AgentList Helpers
```python
self.agents.setup_agents(agents_num=N)       # create N agents
self.agents.filter(lambda a: a.state == 1)   # filter subset
self.agents.to_dataframe()                   # pandas DataFrame
len(self.agents)                             # count
self.agents[i]                              # get by index
```

## Module Selection Guide
| Scenario | Use |
|---|---|
| Spatial proximity drives interaction | Grid + GridAgent |
| Social/network topology drives interaction | Network + NetworkAgent |
| No spatial/network structure | Plain Agent |
| Parameter fitting to empirical data | Calibrator |
| Agent behavioral parameter evolution | Trainer |
