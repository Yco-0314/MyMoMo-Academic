# Change Impact Guide

> Internal reference: which files to modify for common model changes.
> Original: change-impact.md from ABM4ALL/melodie-skills (MIT).

## Adding an Agent Attribute

| File | Change |
|---|---|
| `core/agent.py` | Add attribute in `setup()` with type annotation |
| `core/data_collector.py` | `add_agent_property("agents", "new_attr")` if tracking output |
| `data/input/AgentParams.csv` | Add column if CSV-initialised; update Scenario.load_data |
| `data/input/SimulatorScenarios.csv` | Add column if it varies per scenario |

## Implementing a Policy Lever

| File | Change |
|---|---|
| `core/scenario.py` | Add `policy_param: float = 0.0` |
| `data/input/SimulatorScenarios.csv` | Add column for policy values |
| `core/environment.py` | Read `self.scenario.policy_param` in `step()` |
| `core/agent.py` | Modify behavior based on policy if needed |

## Adding a New Agent Type

| File | Change |
|---|---|
| `core/agent.py` | Create new agent class (or new file `core/agent_b.py`) |
| `core/model.py` | `self.agents_b = self.create_agent_list(AgentBClass)` |
| `core/model.py` | `self.agents_b.setup_agents(...)` in `setup()` |
| `core/data_collector.py` | Register new agent list properties |
| `data/input/SimulatorScenarios.csv` | Add `agent_b_num` if needed |

## Switching to Grid Module

| File | Change |
|---|---|
| `core/agent.py` | Inherit `GridAgent`; add `set_category()`; remove direct `state = 0` |
| `core/model.py` | Add `self.grid = self.create_grid()` in `create()`; `grid.setup_params()` + `setup_agent_locations()` in `setup()`; neighbor loop in `run()` |
| `data/input/SimulatorScenarios.csv` | Add `grid_width`, `grid_height` columns |
| `main.py` | No change needed |

## Switching to Network Module

| File | Change |
|---|---|
| `core/agent.py` | Inherit `NetworkAgent`; add `set_category()` |
| `core/model.py` | Add `self.network = self.create_network()` in `create()`; `network.setup_agent_connections(...)` in `setup()`; neighbor traversal in `run()` |
| `data/input/SimulatorScenarios.csv` | Add network topology params (`k`, `p`, etc.) |

## Adding Output Metrics

| File | Change |
|---|---|
| `core/environment.py` | Declare new metric in `setup()`; compute in `step()` |
| `core/data_collector.py` | `add_environment_property("new_metric")` |

## Upgrading Agent Pattern

### Reactive → Deliberative
- Agent keeps a history buffer (`self.history = []`)
- In `step()`: update history, compute forecast, choose action to maximise expected utility

### Reactive → Introspective
- Use Trainer module (see `modules/module-trainer.md`)
- Pre-train behavioral params; load trained params into Simulator init data

## Bug Fix Checklist

| Symptom | Likely cause | Fix |
|---|---|---|
| Agent metric is 0 throughout | `setup()` overwrites CSV value | Use `getattr(self, attr, default)` |
| Sensitivity indices all 0 | Wrong output column detected | Skip `id_scenario, id_run, id_agent`; require `nunique > 1` |
| `TypeError` on `grid.width` | Grid attr is method, not property | Store `self._w = self.scenario.grid_width` in `setup()` |
| Neighbor is None or wrong type | `get_neighbors` returns tuples | `self.agents[neighbor_id]` not `neighbor.state` |
| `after_setup()` not found | Method doesn't exist | Use `setup_data()` in Scenario |
