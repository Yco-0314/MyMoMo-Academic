# ABM Auto Runtime — Code Templates

> Internal reference for LLM code generation agents.
> Original: melodie-code-templates.md from ABM4ALL/melodie-skills (MIT).
> Always use `from abm_auto.runtime import ...` in generated code.

## Minimal Simulator (plain agents)

### main.py
```python
import os
from abm_auto.runtime import Config, Simulator
from core.model import MyModel
from core.scenario import MyScenario

if __name__ == "__main__":
    config = Config(
        project_name="MyProject",
        project_root=os.path.dirname(__file__),
        input_folder="data/input",
        output_folder="data/output",
    )
    simulator = Simulator(config=config, model_cls=MyModel, scenario_cls=MyScenario)
    simulator.run()
```

### core/scenario.py
```python
from abm_auto.runtime import Scenario

class MyScenario(Scenario):
    def setup(self):
        self.periods: int = 0
        self.agent_num: int = 0
        # Declare every column from SimulatorScenarios.csv with correct type
        self.param_x: float = 0.0

    def load_data(self):
        pass  # optional: pd.read_csv(self.input_folder / "Data_X.csv")

    def setup_data(self):
        pass  # optional: preprocess loaded data
```

### core/model.py
```python
from abm_auto.runtime import Model
from .agent import MyAgent
from .environment import MyEnvironment
from .data_collector import MyDataCollector

class MyModel(Model):
    def create(self):
        self.agents = self.create_agent_list(MyAgent)
        self.environment = self.create_environment(MyEnvironment)
        self.data_collector = self.create_data_collector(MyDataCollector)

    def setup(self):
        self.agents.setup_agents(agents_num=self.scenario.agent_num)
        # Set initial agent state here (preferred over AgentParams.csv):
        for agent in self.agents:
            agent.state = 1 if agent.id < self.scenario.initial_infected else 0

    def run(self):
        for t in self.iterator(self.scenario.periods):  # MUST use iterator()
            self.environment.step(self.agents)
            self.data_collector.collect(t)
        self.data_collector.save()
```

### core/environment.py
```python
from abm_auto.runtime import Environment

class MyEnvironment(Environment):
    def setup(self):
        self.count_infected: int = 0

    def step(self, agents=None):
        # Macro logic: coordinate agents, update aggregate metrics
        if agents:
            self.count_infected = sum(1 for a in agents if a.state == 1)
```

### core/agent.py
```python
from abm_auto.runtime import Agent
import random

class MyAgent(Agent):
    def setup(self):
        # CRITICAL: use getattr to preserve CSV-loaded values
        self.state: int = getattr(self, "state", 0)
        self.param: float = 0.0

    def step(self):
        # Reactive pattern — respond to current state
        pass
```

### core/data_collector.py
```python
from abm_auto.runtime import DataCollector

class MyDataCollector(DataCollector):
    def setup(self):
        self.add_agent_property("agents", "state")
        self.add_environment_property("count_infected")
```

---

## Grid Simulator

### core/agent.py (GridAgent)
```python
from abm_auto.runtime import GridAgent
import random

class MyGridAgent(GridAgent):
    def set_category(self):
        self.category = 0  # REQUIRED for GridAgent

    def setup(self):
        self.state: int = getattr(self, "state", 0)

    def step(self):
        pass  # neighbor logic runs in Model.run() which has grid reference
```

### core/model.py (Grid)
```python
from abm_auto.runtime import Model
from .agent import MyGridAgent
from .environment import MyEnvironment
from .data_collector import MyDataCollector

class MyGridModel(Model):
    def create(self):
        self.agents = self.create_agent_list(MyGridAgent)
        self.environment = self.create_environment(MyEnvironment)
        self.data_collector = self.create_data_collector(MyDataCollector)
        self.grid = self.create_grid()  # NO args

    def setup(self):
        self._grid_w = self.scenario.grid_width
        self._grid_h = self.scenario.grid_height
        self.grid.setup_params(
            width=self._grid_w,
            height=self._grid_h,
            wrap=True,
            multi=False,
        )
        self.agents.setup_agents(agents_num=self.scenario.agent_num)
        self.grid.setup_agent_locations(self.agents, initial_placement="random_single")
        # Set initial states
        for agent in self.agents:
            agent.state = 1 if agent.id < self.scenario.initial_infected else 0

    def run(self):
        for t in self.iterator(self.scenario.periods):
            for agent in self.agents:
                neighbors = self.grid.get_neighbors(agent, radius=1)
                for category, neighbor_id in neighbors:
                    neighbor = self.agents[neighbor_id]
                    # interaction logic: neighbor.state, etc.
            self.environment.step(self.agents)
            self.data_collector.collect(t)
        self.data_collector.save()
```

---

## Network Simulator

### core/agent.py (NetworkAgent)
```python
from abm_auto.runtime import NetworkAgent

class MyNetworkAgent(NetworkAgent):
    def set_category(self):
        self.category = 0

    def setup(self):
        self.state: int = getattr(self, "state", 0)
        self.opinion: float = 0.5
```

### core/model.py (Network)
```python
from abm_auto.runtime import Model

class MyNetworkModel(Model):
    def create(self):
        self.agents = self.create_agent_list(MyNetworkAgent)
        self.environment = self.create_environment(MyEnvironment)
        self.data_collector = self.create_data_collector(MyDataCollector)
        self.network = self.create_network()

    def setup(self):
        self.agents.setup_agents(agents_num=self.scenario.agent_num)
        self.network.setup_agent_connections(
            agent_lists=[self.agents],
            network_type="watts_strogatz",   # or "barabasi_albert", "erdos_renyi"
            network_params={"k": 4, "p": 0.1},
        )

    def run(self):
        for t in self.iterator(self.scenario.periods):
            for agent in self.agents:
                neighbors = self.network.get_neighbors(agent)
                for category, neighbor_id in neighbors:
                    neighbor = self.network.agent_categories[category].get_agent(neighbor_id)
                    # interaction: neighbor.opinion, etc.
            self.environment.step(self.agents)
            self.data_collector.collect(t)
        self.data_collector.save()
```

---

## AI-ASSUMPTION Tagging Template

Any decision beyond DESIGN.md must be tagged inline AND summarised at file top:
```python
# ============================================================
# AI-ASSUMPTION SUMMARY
# [1] infection spreads only to susceptible neighbours — SIR convention
# [2] grid wrap=True — DESIGN.md silent on boundary condition
# ============================================================

def step(self):
    # ⚠️ AI-ASSUMPTION [1]: only infect if neighbour is susceptible
    if neighbour.state == SUSCEPTIBLE:
        ...
```
