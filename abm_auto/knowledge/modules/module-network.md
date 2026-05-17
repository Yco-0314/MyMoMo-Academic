# Network Module Reference

> Internal reference for LLM code generation agents.
> Original: modules/module-network.md from ABM4ALL/melodie-skills (MIT).

## When to Use

Use Network when: "who has a relationship with whom" determines interactions.
Signal words in DESIGN.md: *network, edges, links, degree, social graph, scale-free,
small-world, connections, topology, neighbours (non-spatial)*.

## Core Classes

| Class | Role |
|---|---|
| `Network` | Graph topology manager; maintains agent_categories dict |
| `NetworkAgent` | Agent with graph connections |

## Setup

```python
# In Model.create():
self.network = self.create_network()

# In Model.setup():
self.agents.setup_agents(agents_num=self.scenario.agent_num)
self.network.setup_agent_connections(
    agent_lists=[self.agents],       # list of AgentList objects
    network_type="watts_strogatz",   # see topology options below
    network_params={"k": 4, "p": 0.1},
)
```

## NetworkAgent Requirements

```python
from abm_auto.runtime import NetworkAgent

class MyAgent(NetworkAgent):
    def set_category(self):
        self.category = 0   # REQUIRED: integer type identifier

    def setup(self):
        self.state: int = getattr(self, "state", 0)
        self.opinion: float = 0.5
```

## Neighbor Access Pattern

```python
# get_neighbors returns [(category, agent_id), ...] — NOT agent objects
neighbors = self.network.get_neighbors(agent)
for category, neighbor_id in neighbors:
    # Retrieve actual agent from network's category registry:
    neighbor = self.network.agent_categories[category].get_agent(neighbor_id)
    # Now use neighbor.opinion, neighbor.state, etc.
```

## Supported Topologies

| `network_type` | Params | Description |
|---|---|---|
| `"watts_strogatz"` | `k` (degree), `p` (rewiring prob) | Small-world |
| `"barabasi_albert"` | `m` (edges per new node) | Scale-free |
| `"erdos_renyi"` | `p` (connection prob) | Random |

Pass topology params from Scenario:
```python
network_params={"k": self.scenario.network_k, "p": self.scenario.network_p}
```

Add to SimulatorScenarios.csv: `network_k`, `network_p` (or `network_m`).

## Dynamic Edge Management

```python
network.create_edge(agent1, agent2)
network.add_agent(agent)
network.remove_agent(agent)
```

## Neighbour Interaction Pattern (in Model.run())

```python
def run(self):
    for t in self.iterator(self.scenario.periods):
        for agent in self.agents:
            neighbors = self.network.get_neighbors(agent)
            for category, neighbor_id in neighbors:
                neighbor = self.network.agent_categories[category].get_agent(neighbor_id)
                # influence / interaction logic
        self.environment.step(self.agents)
        self.data_collector.collect(t)
    self.data_collector.save()
```

## SimulatorScenarios.csv Requirements

Add topology parameters as columns:
```csv
id,run_num,periods,agent_num,network_k,network_p
0,1,200,500,4,0.1
```
