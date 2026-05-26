# Choosing the Right Topology Module

Three topology choices ship with the MyMoMo Runtime:

- **No topology** — agents interact through the Environment, not each other directly
- **Grid** — agents live at integer `(x, y)` positions; neighbours are spatial
- **Network** — agents are nodes in a graph; neighbours follow edges

This file is the **decision guide**: read DESIGN.md, decide which module
fits, then jump to [`01-runtime-api.md`](01-runtime-api.md) for the
concrete API.

---

## Decision Tree

Ask these in order. The first "yes" decides:

```
1. Does the phenomenon depend on agents observing or contacting EACH OTHER?
   No  → No topology (agents read Environment; e.g. Schelling-the-game,
                       El Farol attendance, market-clearing models)
   Yes → continue ↓

2. Is geographic / spatial position meaningful to the dynamics?
   Yes → Grid     (e.g. Schelling segregation, forest fire, infection
                   in a physical space, predator-prey with movement)
   No  → continue ↓

3. Do connections follow a fixed structural pattern (network)?
   Yes → Network  (e.g. opinion dynamics on social network, contagion
                   on contact graph, information spread)
```

Quick reference table:

| Phenomenon cue in DESIGN.md | Module |
|---|---|
| "patches", "grid cell", "lattice", "von Neumann", "Moore" | **Grid** |
| "spatial", "neighbourhood", "physical location", "x,y" | **Grid** |
| "network", "graph", "edges", "degree", "scale-free", "small-world" | **Network** |
| "social ties", "contact graph", "Facebook friends", "links" | **Network** |
| "well-mixed", "random matching", "anyone can pair", "global signal" | **No topology** |
| "market price", "aggregate attendance", "global state" | **No topology** |

When DESIGN.md mentions **both** (e.g. "agents on a grid AND a social
network"), use both:

```python
def create(self):
    self.agents = self.create_agent_list(Person)
    self.grid    = self.create_grid()
    self.network = self.create_network()
```

`get_neighbors()` then has its own semantics on each — call the right one
in `Model.run()` depending on which kind of neighbour the rule needs.

---

## No Topology — agents react to environment only

When agents do NOT need direct knowledge of other agents:

```python
class Trader(Agent):
    def step(self):
        if self.environment.market_signal > self.threshold:
            self.position = 1

class MarketModel(Model):
    def create(self):
        self.agents = self.create_agent_list(Trader)
        self.environment = self.create_environment(MarketEnvironment)
        self.data_collector = self.create_data_collector(MarketDataCollector)

    def setup(self):
        self.agents.setup_agents(agents_num=self.scenario.agent_num)

    def run(self):
        for t in self.iterator(self.scenario.periods):
            self.environment.step(self.agents)   # update market_signal
            for agent in self.agents:
                agent.step()                     # each agent reads env
            self.data_collector.collect(t)
        self.data_collector.save()
```

**Use when**: micro-to-macro dynamics where every agent reads the same
global state. Cleaner and faster than Grid/Network because no neighbour
queries are needed.

**Classic examples**: El Farol Bar (attendance signal), beer game (price
signal), generic auction models.

---

## Grid — spatial topology

When dynamics depend on **physical position** and **local spatial
neighbourhoods**:

```python
class HouseHolder(GridAgent):
    def setup(self):
        self.race: int = self._safe_attr("race", 0)
        self.satisfied: bool = False

class SchellingModel(Model):
    def create(self):
        self.agents = self.create_agent_list(HouseHolder)
        self.environment = self.create_environment(SchellingEnvironment)
        self.data_collector = self.create_data_collector(SchellingDataCollector)
        self.grid = self.create_grid()

    def setup(self):
        self.grid.setup_params(
            width=self.scenario.grid_width,
            height=self.scenario.grid_height,
            wrap=True,
            multi=False,
        )
        self.agents.setup_agents(agents_num=self.scenario.agent_num)
        self.grid.setup_agent_locations(
            self.agents, initial_placement="random_single",
        )

    def run(self):
        for t in self.iterator(self.scenario.periods):
            for agent in self.agents:
                neighbors = self.grid.get_neighbors(agent, radius=1, moore=True)
                similar = sum(1 for n in neighbors if n.race == agent.race)
                agent.satisfied = similar / max(1, len(neighbors)) >= 0.3
                if not agent.satisfied:
                    self._relocate(agent)        # writes new x, y
            self.data_collector.collect(t)
        self.data_collector.save()
```

**Use when**:
- DESIGN.md says "spatial", "neighbourhood", "Moore", "von Neumann"
- Agents move (positions change during simulation)
- Adjacency = physical proximity

**Grid-specific scenario columns** in `SimulatorScenarios.csv`:

| Column | Required | Default |
|---|---|---|
| `grid_width`  | ✓ (no implicit default) | — |
| `grid_height` | ✓ | — |
| `grid_wrap`   | optional | `True` (toroidal) |

**`setup_agent_locations()` placement modes**:

| Mode | Behaviour |
|---|---|
| `"random_single"` | Random cell; one agent per cell |
| `"direct_position"` | Use the `x`, `y` columns from AgentParams.csv |

After placement, each GridAgent has `self.x`, `self.y`, `self.grid` set.

---

## Network — graph topology

When dynamics depend on **explicit connections** that don't follow spatial
proximity:

```python
class Voter(NetworkAgent):
    def setup(self):
        self.opinion: float = self._safe_attr("opinion", 0.5)

class OpinionModel(Model):
    def create(self):
        self.agents = self.create_agent_list(Voter)
        self.environment = self.create_environment(OpinionEnvironment)
        self.data_collector = self.create_data_collector(OpinionDataCollector)
        self.network = self.create_network()

    def setup(self):
        self.agents.setup_agents(agents_num=self.scenario.agent_num)
        self.network.setup_agent_connections(
            agent_lists=[self.agents],
            network_type="watts_strogatz_graph",
            network_params={
                "k": self.scenario.network_k,    # must be EVEN
                "p": self.scenario.network_p,
            },
        )

    def run(self):
        for t in self.iterator(self.scenario.periods):
            for agent in self.agents:
                neighbors = self.network.get_neighbors(agent)
                if neighbors:
                    avg = sum(n.opinion for n in neighbors) / len(neighbors)
                    agent.opinion = 0.5 * agent.opinion + 0.5 * avg
            self.data_collector.collect(t)
        self.data_collector.save()
```

**Use when**:
- DESIGN.md says "network", "graph", "degree", "edges", "social ties"
- Connections persist over the simulation (built once in `setup()`)
- Influence flows along specific paths, not via spatial proximity

**Network-specific scenario columns**:

| Column | When | Type |
|---|---|---|
| `network_k` | Watts-Strogatz | int (must be even) |
| `network_p` | Watts-Strogatz, Erdős-Rényi | float |
| `network_m` | Barabási-Albert | int |

**Supported topologies** (full table in [`01-runtime-api.md`](01-runtime-api.md)):

- `"watts_strogatz_graph"` — small-world
- `"barabasi_albert_graph"` — scale-free
- `"erdos_renyi_graph"` — random

The `_graph` suffix is mandatory; see
[`05-anti-patterns.md`](05-anti-patterns.md) §3.

---

## When the Choice Looks Ambiguous

These are the classic borderline cases from real research:

| Phenomenon | Looks like… | Actually use |
|---|---|---|
| Infection spread through a population at a workplace | Network | **Network** — the "who-meets-whom" graph is more structural than a grid |
| Infection spread in a city neighbourhood with travel | Grid + Network | **Both** — grid for physical location, network for long-range travel |
| Belief diffusion in a homogeneous population | Network | **No topology** if literally well-mixed; **Network** if any structure matters |
| Forest fire spreading | Grid | **Grid** — adjacency = physical |
| Innovation adoption from peers | Network | **Network** — adoption follows social ties, not geography |
| Schelling segregation on a square map | Grid | **Grid** — spatial preference is the mechanism |
| Predator-prey with random movement | Grid | **Grid** — movement is the dynamic |

**Rule of thumb**: if positions / movement matter → Grid. If "who-is-
connected-to-whom" matters and is fixed → Network. If neither, use no
topology and let the Environment carry the global signal.

---

## Performance Note

Grid neighbour queries are O(1) (cached). Network neighbour queries depend
on the underlying graph structure but are also fast for the supported
topologies. The bottleneck in calibration is almost always the
**total number of simulator runs** (priors × sample count), not single-run
inner loops. Optimise topology choice for **correctness**, not speed.

---

## Cross-references

- API surface and method signatures → [`01-runtime-api.md`](01-runtime-api.md)
- Required CSV columns per topology → [`04-data-contracts.md`](04-data-contracts.md)
- Common topology coding mistakes → [`05-anti-patterns.md`](05-anti-patterns.md)
- Full walkthrough of writing a model from scratch → [`02-writing-models.md`](02-writing-models.md)
