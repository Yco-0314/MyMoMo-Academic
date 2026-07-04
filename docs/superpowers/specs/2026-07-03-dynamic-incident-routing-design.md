# Dynamic Incident Routing Design Spec

**Status:** Approved for implementation planning
**Date:** 2026-07-03
**Repo:** MyMoMo-GIS-Academic
**Parent:** [ADR-019](../../decisions/ADR-019-gis-abm-platform-vision.md)
and [coupled seam status](../../reproduce/coupled-seam/STATUS.md)

## Goal

Add a small synthetic dynamic incident-routing mechanism over `GeoNetwork`.
Agents move tick by tick; incident events close or reopen road edges; agents may
reroute only at graph nodes. This creates a third moving-agent dynamic lifecycle
cell after dynamic flood and dynamic congestion.

This is lifecycle and rerouting evidence only. It is not traffic-flow validity,
incident-response optimization, capacity inference, or real event ingestion.

## Scope

Build **Dynamic Incident Routing Phase 1** as an additive GIS-only runtime:

- `GeoNetwork` road graph;
- moving agents that start on graph nodes;
- safe destination nodes;
- per-tick edge closure events;
- node-only planning/rerouting around closed edges;
- deterministic gate comparing `reroute=True` and `reroute=False`.

No `RasterSpace`, no `RasterTimeline`, no codegen registry wiring, no real data,
no capacity/congestion, and no `CoupledModel` extraction are in scope.

## Architecture

Create:

```text
abm_auto/gis/_dynamic_incident.py
abm_auto/gis/_incident_gate.py
```

The runtime should follow the existing production dynamic adapters:

- `IncidentAgent(GISAgent)`
- `IncidentRoutingModel(StagedGISModel)`
- `DataCollector` for per-tick summaries
- `RunReporter` for peak/run-level summaries

Each tick uses this fixed order:

1. apply incident events at the current tick to produce the active closed-edge
   set;
2. strand agents already on an edge that becomes closed;
3. for agents at nodes, plan or reroute around closed edges;
4. enter the next edge only if that edge is open;
5. move along the current edge by `speed_m_per_tick`;
6. collect a step summary.

Agents reroute only at nodes. If an agent is already on an edge and that edge is
closed at the current tick, it becomes stranded with
`stranded_reason == "incident_on_edge"`. Unused speed does not carry across
edge boundaries.

The model should avoid closed edges by routing over a copy of the graph with
closed edges removed, then using the existing deterministic `dijkstra_route`.

## API

```python
def run_dynamic_incident_routing(
    geonet,
    safe_nodes,
    agent_nodes,
    incidents,
    n_steps=6,
    speed_m_per_tick=100.0,
    reroute=True,
) -> dict:
    ...
```

Incident events are dictionaries:

```python
{"t": 1, "edge": (u, v), "closed": True}
{"t": 3, "edge": (u, v), "closed": False}
```

Input requirements:

- `n_steps` must be a positive integer and must reject bool;
- `speed_m_per_tick` must be finite and positive;
- each event must be a mapping with integer non-bool `t >= 0`;
- each event must have a two-node `edge` that exists in `geonet.graph`;
- each event must have boolean `closed`;
- events at `t >= n_steps` are valid but have no effect during the run.

Return structure:

```python
{
    "steps": [
        {
            "t": int,
            "arrived": int,
            "moving": int,
            "waiting": int,
            "stranded": int,
            "n_closed_edges": int,
            "closed_edges": list,
            "reroutes_this_step": int,
            "total_reroutes": int,
        },
        ...
    ],
    "agents": [
        {
            "id": int,
            "node": object,
            "edge": tuple | None,
            "edge_progress_m": float,
            "route": list,
            "arrived": bool,
            "stranded": bool,
            "stranded_reason": str | None,
            "reroutes": int,
            "arrival_t": int | None,
        },
        ...
    ],
    "n_steps": int,
    "n_agents": int,
    "arrived": int,
    "stranded": int,
    "moving": int,
    "total_reroutes": int,
    "mean_arrival_t": float | None,
    "max_closed_edges": int,
}
```

Agents that have not arrived by the end of `n_steps` are marked stranded with
`stranded_reason == "not_arrived"`.

## Gate

Add:

```python
def dynamic_incident_reroute_gate(
    geonet,
    safe_nodes,
    agent_nodes,
    incidents,
    n_steps=6,
    speed_m_per_tick=100.0,
) -> tuple[bool, str]:
    ...
```

The gate compares the same scenario with rerouting enabled and disabled. It
passes only when:

- the rerouting run records `total_reroutes > 0`; and
- rerouting improves at least one deterministic outcome:
  - more arrivals;
  - fewer stranded agents;
  - earlier `mean_arrival_t` when arrival and stranded counts tie.

The success text must state that this proves deterministic moving-agent
incident rerouting behavior only, not real traffic-flow validity or optimal
incident management.

## Synthetic Network Pattern

Use a small deterministic detour network:

```text
A ---- B ---- D
|            /
C ----------
```

Coordinates:

- A `(0, 0)`
- B `(100, 0)`
- D `(200, 0)`
- C `(0, 100)`

The agent starts at A, initially chooses A-B-D, and B-D closes at tick 1. With
rerouting enabled, the agent reroutes from B through A-C-D and arrives. With
rerouting disabled, the agent waits at B and ends not arrived.

## Tests

Create:

```text
tests/gis/test_dynamic_incident.py
tests/gis/test_incident_gate.py
```

Runtime tests should cover:

- a 200m edge with speed 100m/tick arrives in two ticks;
- the model uses `StagedGISModel`, `AgentSet.do`, and `DataCollector`;
- reroute-enabled agents take the open detour when the direct edge closes;
- reroute-disabled agents wait on the stale route and end not arrived;
- an agent already on an edge becomes stranded when that edge closes;
- missing or unreachable safe nodes do not crash and end not arrived;
- invalid `n_steps`, bool `n_steps`, non-finite/non-positive speed, malformed
  events, non-bool `closed`, bool/non-integer/negative `t`, and nonexistent
  event edges fail;
- equal-cost route selection remains deterministic across line insertion order.

Gate tests should cover:

- the synthetic incident reroute case passes;
- no-effect incidents fail;
- reroutes without outcome improvement fail.

## Documentation

Update:

```text
docs/reproduce/coupled-seam/STATUS.md
```

Record dynamic incident routing as the third dynamic lifecycle cell. Keep the
YAGNI boundary: this phase still does not extract `CoupledModel`; it gives the
next lifecycle-helper audit concrete evidence.

## Final Verification

Run:

```bash
.venv/bin/python -m pytest tests/gis/test_dynamic_incident.py tests/gis/test_incident_gate.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

The forbidden base-engine diff must be empty.
