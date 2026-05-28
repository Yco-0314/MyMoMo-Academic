# MyMoMo Runtime API Reference

This is the canonical reference for `abm_auto.runtime` — the engine layer
that all generated ABM code imports from. Source of truth: the six files
under `abm_auto/runtime/` (read these directly when in doubt).

This file lists **what exists**. For end-to-end usage see
[`02-writing-models.md`](02-writing-models.md). For known mistakes see
[`05-anti-patterns.md`](05-anti-patterns.md).

---

## Importable Surface

Every name accessible via `from abm_auto.runtime import ...`:

```
Agent         AgentList       GridAgent     NetworkAgent
Model         Environment     Scenario      DataCollector
Grid          Network
Config        Simulator       Calibrator    Trainer
```

Anything outside this list is hallucinated — see `05-anti-patterns.md` §1.

The runtime is split into two layers:

- **Custom wrappers** (in `abm_auto/runtime/_*.py`): fix gotchas, add safety
  rails, sometimes fully replace the upstream class. **Use these.**
- **Delegated** (re-exported as-is): pass-through to the underlying engine
  for complex CSV/DB machinery. Their behaviour matches their upstream docs.

| Class | Layer | Why |
|---|---|---|
| `Agent`, `GridAgent`, `NetworkAgent` | Custom | Adds `_safe_attr`; provides default `set_category` |
| `Model` | Custom | Auto-injects `self.agents` into Grid/Network |
| `Environment` | **Standalone** | Zero engine dependency — fully owned by MyMoMo |
| `Grid` | Custom | `get_neighbors()` returns agents not tuples; public `width`/`height` |
| `Network` | Custom | Same `get_neighbors()` improvement |
| `AgentList`, `DataCollector`, `Scenario`, `Config`, `Simulator`, `Calibrator`, `Trainer` | Delegated | Complex CSV/DB machinery — match upstream API |

---

## Agent

Base class for entities in the simulation. Subclass it and override
`setup()` to declare per-agent state.

```python
from abm_auto.runtime import Agent

class Buyer(Agent):
    def setup(self):
        self.trust: float = self._safe_attr("trust", 0.5)
        self.purchased: bool = False

    def step(self):
        # called from Model.run() each tick (when iterated explicitly)
        if self.trust > 0.6:
            self.purchased = True
```

**Methods you should know about**:

| Method | Purpose |
|---|---|
| `setup()` | Override — declare attributes, set initial values |
| `step()` | Optional — your behaviour per tick (called from your Model.run loop) |
| `_safe_attr(name, default)` | Use inside `setup()` for any attribute that may come from `AgentParams.csv` |

The runtime calls `agent.setup()` **AFTER** loading attributes from CSV. A
plain assignment in `setup()` overwrites the CSV value. `_safe_attr` is the
fix — see [`05-anti-patterns.md`](05-anti-patterns.md) §8.

---

## GridAgent / NetworkAgent

`Agent` subclasses that participate in a spatial or network topology.

```python
from abm_auto.runtime import GridAgent, NetworkAgent

class Schelling(GridAgent):
    def setup(self):
        self.race: int = self._safe_attr("race", 0)
        # GridAgent gets x, y, grid attributes automatically after placement

class Voter(NetworkAgent):
    def setup(self):
        self.opinion: float = self._safe_attr("opinion", 0.5)
```

**Extras over `Agent`**:

| Attribute / method | Set by | Notes |
|---|---|---|
| `self.x`, `self.y` | Grid placement | GridAgent only — position in the grid |
| `self.grid` | Grid placement | GridAgent only — reference to the grid |
| `set_category()` | Default in wrapper | Returns category=0. Override only for multi-type grids/networks. |

**Multi-type example**:

```python
class Buyer(NetworkAgent):
    def set_category(self):
        self.category = 0    # one int per agent type, never changes

class Seller(NetworkAgent):
    def set_category(self):
        self.category = 1
```

The Grid/Network keeps separate lists per category. Single-type models
should NOT override `set_category` — just inherit the default.

---

## Model

The orchestrator. Subclass and implement `create()`, `setup()`, `run()`.

```python
from abm_auto.runtime import Model
from .agent import Buyer
from .environment import MarketEnvironment
from .data_collector import MarketDataCollector

class MarketModel(Model):
    def create(self):
        self.agents = self.create_agent_list(Buyer)
        self.environment = self.create_environment(MarketEnvironment)
        self.data_collector = self.create_data_collector(MarketDataCollector)
        # Optional: spatial / topology
        self.network = self.create_network()

    def setup(self):
        self.agents.setup_agents(agents_num=self.scenario.agent_num)
        self.network.setup_agent_connections(
            agent_lists=[self.agents],
            topology=topologies.watts_strogatz(k=self.scenario.network_k, p=self.scenario.network_p),
        )

    def run(self):
        for t in self.iterator(self.scenario.periods):
            self.environment.step(self.agents)
            for agent in self.agents:
                neighbors = self.network.get_neighbors(agent)
                agent.step()
            self.data_collector.collect(t)
        self.data_collector.save()
```

**Lifecycle (called by the framework in this order)**:

1. `__init__` — framework constructs the Model; `self.scenario` becomes available
2. `create()` — instantiate all components via `self.create_*` factories
3. `setup()` — initialise agents, build topology, set initial states
4. `run()` — your time loop. MUST use `self.iterator(periods)`.

**Factory methods (all return the created object AND assign it to `self.<role>`)**:

| Method | Returns | Assigned to |
|---|---|---|
| `create_agent_list(agent_cls)` | AgentList | by convention: `self.agents` |
| `create_environment(env_cls)` | Environment subclass | `self.environment` |
| `create_data_collector(dc_cls)` | DataCollector subclass | `self.data_collector` |
| `create_grid(grid_cls=None, spot_cls=None)` | Grid (defaults to MyMoMo Grid) | `self.grid` |
| `create_network(network_cls=None, edge_cls=None)` | Network | `self.network` |

`create_grid()` and `create_network()` automatically inject `self.agents`
into the returned object, so `get_neighbors(agent)` works without an
`agent_list=` parameter.

**`self.iterator(periods)`** is mandatory in `run()`. It yields `0, 1, …,
periods-1` AND drives the framework's data-collection plumbing. `range()`
is not a substitute — see `05-anti-patterns.md` §7.

---

## Environment

Standalone (no engine dependency). Holds shared / global state that any
agent reads and that you update each tick.

```python
from abm_auto.runtime import Environment

class MarketEnvironment(Environment):
    def setup(self):
        self.total_demand: int = 0
        self.shock_active: bool = False

    def step(self, agents=None):
        self.total_demand = sum(1 for a in agents if a.purchased)
```

**Lifecycle**:

| Attribute / method | Set by / when |
|---|---|
| `self.model` | Set by Model after construction |
| `self.scenario` | Same — shortcut to `self.model.scenario` |
| `setup()` | Called once per run, after `self.scenario` is available |
| `step(agents=None)` | Called by you from `Model.run()` once per tick |
| `to_dict(properties=None)` | Serialise to a plain dict — used by DataCollector |

**Pattern: smart environment, simple agents**. Put aggregate computations,
policy logic, "who can talk to whom" decisions in the environment. Keep
agents lightweight (state + small per-tick decisions only). This makes
agent-level CSV output stable and environment-level aggregates explicit.

---

## Scenario

CSV-driven configuration container. Declare default values in `setup()`;
the framework auto-loads matching columns from
`data/input/SimulatorScenarios.csv` and overwrites the defaults.

```python
from abm_auto.runtime import Scenario

class MarketScenario(Scenario):
    def setup(self):
        # Required for every Simulator run
        self.periods: int = 0
        self.agent_num: int = 0
        # Domain-specific
        self.network_k: int = 6
        self.network_p: float = 0.1
        self.trust_threshold: float = 0.5
```

**Column-to-attribute contract**: a column named `network_k` in the CSV
gets bound to `self.network_k` on the Scenario instance. The value type
follows what pandas infers from the CSV column (integers stay int, floats
stay float). Declaring `self.network_k: int = 6` in `setup()` mainly
serves two purposes: (a) gives the attribute a default when the CSV omits
the column, and (b) documents the expected type to readers. Columns the
Scenario does not declare are still accessible via `self.<col_name>` but
should be considered undocumented. See
[`04-data-contracts.md`](04-data-contracts.md) for the full CSV schema.

The framework does NOT have an `after_setup()` hook — all initialisation
goes in `setup()`. See `05-anti-patterns.md` §2.

---

## DataCollector

Declarative output-collection container. List which properties to track;
the framework writes them to CSV automatically at `save()` time.

```python
from abm_auto.runtime import DataCollector

class MarketDataCollector(DataCollector):
    def setup(self):
        # agent-level: collected once per agent per tick
        self.add_agent_property("agents", "trust")
        self.add_agent_property("agents", "purchased")
        # environment-level: collected once per tick
        self.add_environment_property("total_demand")
```

**Methods**:

| Method | Effect |
|---|---|
| `add_agent_property(container_name, attr_name)` | Track an Agent attribute |
| `add_environment_property(attr_name)` | Track an Environment attribute |
| `collect(t)` | Snapshot all tracked properties at period t. **Must pass t.** |
| `save()` | Write the accumulated rows to CSV. **Required at end of `run()`.** |

Output files (in `data/output/`):

- `Result_Simulator_Agent_<agent_list_name>.csv` — one row per agent per tick
- `Result_Simulator_Environment.csv` — one row per tick

Columns are named exactly as the attribute names you passed to
`add_*_property()`. There is no implicit prefixing.

---

## Grid

2D spatial container. Holds agents at integer (x, y) positions and resolves
neighbour queries.

```python
# Model.create():
self.grid = self.create_grid()    # no args needed

# Model.setup():
self.grid.setup_params(width=20, height=20, wrap=True, multi=False)
self.agents.setup_agents(agents_num=400)
self.grid.setup_agent_locations(self.agents, initial_placement="random_single")

# Model.run():
for agent in self.agents:
    neighbors = self.grid.get_neighbors(agent)   # zero-arg form OK
    for n in neighbors:
        agent.expose(n)
```

**Methods**:

| Method | Purpose |
|---|---|
| `setup_params(width, height, wrap=True, caching=True, multi=True)` | Set dimensions and topology behaviour |
| `setup_agent_locations(agent_list, initial_placement="random_single")` | Place agents; alternatives include `"direct_position"` (uses agent.x/y) |
| `get_neighbors(agent, radius=1, moore=True, except_self=True)` | List of GridAgent objects |
| `move_agent(agent, target_x, target_y)` | Relocate an agent |
| `width`, `height` | int properties |

**`get_neighbors()` returns agent OBJECTS by default**, not (category, id)
tuples. You can read `.state`, `.opinion` etc. directly:

```python
for neighbor in self.grid.get_neighbors(agent):
    agent.opinion = 0.9 * agent.opinion + 0.1 * neighbor.opinion
```

For the original tuple form pass `return_agents=False`.

---

## Network

Graph-based topology. Same neighbour API as Grid; topology is supplied as a
**callable** (see `Topology` in `abm_auto.runtime.topologies`).

```python
from abm_auto.runtime import Model, topologies

# Model.create():
self.network = self.create_network()

# Model.setup():
self.agents.setup_agents(agents_num=self.scenario.agent_num)
self.network.setup_agent_connections(
    agent_lists=[self.agents],
    topology=topologies.watts_strogatz(
        k=self.scenario.network_k,        # degree (must be even for WS)
        p=self.scenario.network_p,        # rewiring prob
    ),
)
```

**Built-in topology adapters** (`abm_auto.runtime.topologies`):

| Adapter | Signature | Notes |
|---|---|---|
| `watts_strogatz(k, p)` | k = int (even), p = float | Small-world |
| `barabasi_albert(m)` | m = int (edges per new node) | Scale-free |
| `erdos_renyi(p)` | p = float (edge probability) | Random |
| `netlogo_spatially_clustered(avg_degree)` | avg_degree = int | Faithful port of NetLogo `setup-spatially-clustered-network`: iterative random-node → nearest-non-neighbor linking, no per-node degree cap, terminates at n*d/2 edges. High-variance degree distribution. |
| `melodie_named(name, **params)` | name = networkx generator function name | Escape hatch for anything networkx ships. Bridges `random.Random` to networkx's int seed. |

A `Topology` is `Callable[[int, random.Random], nx.Graph]`. RNG is supplied
by `Network._rng` (auto-seeded from `scenario.seed` in `Model.create_network()`).

**Methods**:

| Method | Purpose |
|---|---|
| `setup_agent_connections(agent_lists, topology)` | Build the graph via the supplied Topology callable |
| `get_neighbors(agent)` | List of NetworkAgent objects (agent_list auto-injected) |
| `add_edge(a, b)` | Manually add an edge after setup |

---

## Config + Simulator

Top-level driver. You usually only touch these in `main.py`.

```python
import os
from abm_auto.runtime import Config, Simulator
from core.model import MarketModel
from core.scenario import MarketScenario

if __name__ == "__main__":
    config = Config(
        project_name="MarketReproduction",
        project_root=os.path.dirname(__file__),
        input_folder="data/input",
        output_folder="data/output",
    )
    simulator = Simulator(config=config, model_cls=MarketModel, scenario_cls=MarketScenario)
    simulator.run()
```

**Rules**:

- `input_folder="data/input"` and `output_folder="data/output"` are
  **hard-coded** by the pipeline. Do not deviate — the verifier and
  workspace assume these exact paths.
- `project_root=os.path.dirname(__file__)` ensures `core/` is importable
  via absolute import from `main.py`.
- `Simulator.run()` iterates every row of `SimulatorScenarios.csv`, runs
  `model.create() → setup() → run()` once per row, and writes outputs.

For parameter calibration use `Calibrator(config, model_cls, scenario_cls)`
in place of `Simulator`; for evolutionary optimisation use `Trainer`. Both
share `Simulator`'s API surface but read different input CSVs (see
[`04-data-contracts.md`](04-data-contracts.md)).

---

## Implementation Reading Order

To verify any claim in this document, read these files in order:

1. `abm_auto/runtime/__init__.py` — what gets exported, why
2. `abm_auto/runtime/_agent.py` — Agent / GridAgent / NetworkAgent (87 LoC)
3. `abm_auto/runtime/_model.py` — Model (64 LoC)
4. `abm_auto/runtime/_environment.py` — standalone Environment (78 LoC)
5. `abm_auto/runtime/_grid.py` — Grid (116 LoC)
6. `abm_auto/runtime/_network.py` — Network (87 LoC)

Total: ~520 LoC. If something here disagrees with the source, the source
wins — file an update to this document.
