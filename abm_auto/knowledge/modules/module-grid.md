# Grid Module Reference

> Internal reference for LLM code generation agents.
> Original: modules/module-grid.md from ABM4ALL/melodie-skills (MIT).

## When to Use

Use Grid when: "spatial proximity determines who interacts with whom."
Signal words in DESIGN.md: *spatial, grid, neighbourhood, cell, Moore, Von Neumann,
diffusion, movement, territory, land-use, patch*.

Do NOT use Grid when: interactions depend on social networks, or continuous space is needed.

## Core Classes

| Class | Role |
|---|---|
| `Grid` | Manages 2D discrete space; tracks agent positions; spatial queries |
| `GridAgent` | Agent with auto-maintained `x`, `y` coordinates |
| `Spot` | Individual grid cell (customisable attributes, e.g. resource level) |

## Setup

```python
# In Model.create():
self.grid = self.create_grid()   # NO arguments

# In Model.setup():
self.grid.setup_params(
    width=self.scenario.grid_width,
    height=self.scenario.grid_height,
    wrap=True,    # toroidal edges
    caching=True, # accelerates repeated neighbor lookups
    multi=False,  # one agent per cell (multi=True allows stacking)
)
self.agents.setup_agents(agents_num=self.scenario.agent_num)
self.grid.setup_agent_locations(self.agents, initial_placement="random_single")
```

**Note**: Always store grid dimensions in a model attribute:
```python
self._grid_w = self.scenario.grid_width
self._grid_h = self.scenario.grid_height
# Do NOT access grid.width / grid.height directly — may error
```

## GridAgent Requirements

```python
from abm_auto.runtime import GridAgent

class MyAgent(GridAgent):
    def set_category(self):
        self.category = 0  # REQUIRED: integer, static type identifier

    def setup(self):
        self.state: int = getattr(self, "state", 0)
```

GridAgent auto-attributes: `self.x`, `self.y` (set by grid), `self.grid` (Grid ref).

## Neighbor Queries

```python
# Returns list of (category_str, agent_id_int) tuples — NOT agent objects
neighbors = self.grid.get_neighbors(agent, radius=1, moore=True, except_self=True)

# To get the actual agent:
for category, neighbor_id in neighbors:
    neighbor = self.agents[neighbor_id]
    # Now use neighbor.state, etc.
```

**Alternative (spot-centric):**
```python
spots = self.grid.get_agent_neighborhood(agent, radius=1, moore=True, except_self=True)
# → list of Spot objects
```

## Movement

```python
grid.move_agent(agent, target_x, target_y)    # direct placement
agent.rand_move_agent(x_range, y_range)        # random displacement
grid.get_empty_spots()                         # → [(x,y), ...]
grid.find_empty_spot()                         # → (x, y) single empty cell
```

## Spot Attributes

```python
# Batch-assign property to all spots from 2D numpy array:
grid.set_spot_property("resource", resource_matrix)   # matrix[y][x] = value

# Access per-spot:
spot = grid.get_spot(x, y)
value = spot.resource
```

## SimulatorScenarios.csv Requirements

Must include `grid_width` and `grid_height` columns:
```csv
id,run_num,periods,agent_num,grid_width,grid_height,infection_prob
0,1,100,200,20,20,0.3
```

## Common Mistakes

| Wrong | Correct |
|---|---|
| `neighbors[0].state` | `self.agents[neighbors[0][1]].state` |
| `self.grid.width` | `self._grid_w` (stored in setup) |
| `self.create_grid(width, height)` | `self.create_grid()` (no args) |
| `agent.step()` calls `grid.get_neighbors(self)` | Move neighbor logic to `Model.run()` |
