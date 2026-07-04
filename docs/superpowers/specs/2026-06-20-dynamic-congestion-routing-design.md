# Dynamic Congestion Routing Design Spec

**Status:** Approved for implementation planning
**Date:** 2026-06-20
**Repo:** MyMoMo-GIS-Academic
**Parent:** [ADR-019](../../decisions/ADR-019-gis-abm-platform-vision.md)
and [ADR-019 synthesis](../../reproduce/coupled-seam/ADR-019-SYNTHESIS.md)

## Goal

Add a second dynamic moving-agent lifecycle mechanism that does not depend on
flood rasters. The model answers one narrow question: when edge costs change by
tick because agents create congestion, can node-based moving agents reroute and
produce a deterministic outcome difference compared with static initial routes?

This is lifecycle evidence for ADR-019. It is not a traffic-flow model, a
capacity model, or a real-world congestion simulator.

## Scope

Build **Dynamic Congestion Routing Phase 1** as a synthetic GIS-only runtime
mechanism:

- `GeoNetwork` road graph;
- moving agents that start on graph nodes;
- safe destination nodes;
- per-tick edge load summaries;
- congestion-dependent routing cost;
- node-only route planning and rerouting;
- deterministic gate comparing rerouting enabled and disabled.

No `RasterSpace`, no `RasterTimeline`, and no flood coupling are involved. This
is intentionally the second dynamic lifecycle mechanism after dynamic flood, so
that lifecycle commonality can be judged from two independent mechanisms.

## Architecture

Create a new runtime module:

```text
abm_auto/gis/_dynamic_congestion.py
```

The module should mirror the dynamic flood model's small local structure where
useful, but keep its own model because congestion summaries and costs differ
from flood exposure.

Core helper concepts:

- `_CongestionAgent`: internal dataclass for one moving agent.
- `_edge_key(u, v)`: stable undirected edge key.
- `_shortest_route_by_cost(graph, start, safe_nodes, edge_costs)`: deterministic
  shortest path with tie-breaking by `repr(node)`.
- `_move_agent(...)`: one-edge-per-tick movement helper.
- `_edge_loads(agents)`: count agents currently occupying each edge.
- `_congested_edge_costs(graph, previous_loads, congestion_alpha)`: map edge to
  `length * (1 + congestion_alpha * max(previous_load - 1, 0))`.

Each tick uses this fixed order:

1. compute edge costs from the previous tick's edge loads;
2. at nodes, plan or reroute using those current costs;
3. let agents enter or continue edges;
4. compute current tick edge loads after edge entry;
5. move agents along their current edge using a simple speed penalty from the
   current edge load;
6. append a step summary and carry current edge loads into the next tick.

The first tick starts with empty previous loads, so all costs equal edge length.
This creates a baseline initial route. Later ticks can make loaded edges more
expensive.

Agents may reroute only at nodes. Agents already on an edge do not turn around
mid-edge. One tick can complete at most one edge, and unused speed does not carry
across to the next edge.

Congestion is deliberately minimal: a single agent on an edge is not penalized;
additional agents on the same edge increase both routing cost and movement time
by the same multiplier:

```python
1 + congestion_alpha * max(edge_load - 1, 0)
```

## API

```python
def run_dynamic_congestion_routing(
    geonet,
    safe_nodes,
    agent_nodes,
    n_steps=6,
    speed_m_per_tick=100.0,
    congestion_alpha=2.0,
    reroute=True,
) -> dict:
    ...
```

Input requirements:

- `geonet` must provide a `GeoNetwork.graph` with edge `length` attributes.
- `safe_nodes` is an iterable of graph nodes that count as destinations.
- `agent_nodes` is an iterable of starting graph nodes.
- `n_steps` must be a positive integer and must reject bool.
- `speed_m_per_tick` must be positive.
- `congestion_alpha` must be non-negative.
- `reroute=True` permits node-based replanning when current costs change enough
  to produce a different route.
- `reroute=False` permits only the initial route plan.

Top-level return structure:

```python
{
    "steps": [
        {
            "t": int,
            "arrived": int,
            "moving": int,
            "waiting": int,
            "stranded": int,
            "edge_loads": dict,
            "max_edge_load": int,
            "reroutes_this_step": int,
            "total_reroutes": int,
            "mean_congested_cost": float,
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
    "max_edge_load": int,
}
```

Agents that have not arrived by the end of `n_steps` are marked stranded with
`stranded_reason == "not_arrived"`. Missing or unreachable safe nodes should not
crash; affected agents should end as not arrived.

## Synthetic Gate

Add the gate to:

```text
abm_auto/gis/_congestion_gate.py
```

Gate API:

```python
def dynamic_congestion_reroute_gate(
    geonet,
    safe_nodes,
    agent_nodes,
    n_steps=6,
    speed_m_per_tick=100.0,
    congestion_alpha=2.0,
) -> tuple[bool, str]:
    ...
```

The gate runs the same synthetic scenario twice:

- `run_dynamic_congestion_routing(..., reroute=True)`
- `run_dynamic_congestion_routing(..., reroute=False)`

It passes only when:

- the rerouting run records `total_reroutes > 0`; and
- rerouting improves at least one deterministic outcome:
  - more arrivals;
  - fewer stranded agents;
  - earlier `mean_arrival_t` when arrivals and stranded counts tie.

The gate description must be cautious:

```text
moving-agent congestion rerouting changes deterministic outcomes; this is not a
traffic-flow or congestion-validity claim
```

## Synthetic Network Pattern

Use a small deterministic network where a follower's initial shortest route
overlaps with leading agents and later congestion makes a detour preferable:

```text
A ---- B ---- C ---- safe
      \          /
       D ------ E
```

Recommended coordinates:

- A `(0, 0)`
- B `(100, 0)`
- C `(200, 0)`
- safe `(300, 0)`
- D `(100, -100)`
- E `(200, -100)`

At least two leading agents start at B and initially occupy the direct B-C edge.
A follower starts at A, initially heads toward B-C, and can reroute through D/E
after the previous tick's B-C load makes the direct edge expensive. Tests should
use deterministic line insertion order and tie-breaking to avoid flaky route
choices.

## Tests

Create:

```text
tests/gis/test_dynamic_congestion.py
tests/gis/test_congestion_gate.py
```

`test_dynamic_congestion.py` should cover:

- one 200m edge with speed 100m/tick arrives in two ticks;
- speed does not carry across edge boundaries;
- higher previous edge load increases that edge's cost;
- reroute-enabled agents switch to a lower congested-cost detour;
- reroute-disabled agents keep the initial route;
- unreachable or missing safe nodes end with `stranded_reason == "not_arrived"`;
- non-positive speed fails;
- non-positive `n_steps`, bool `n_steps`, and negative `congestion_alpha` fail;
- equal-cost routes are stable across line insertion order.

`test_congestion_gate.py` should cover:

- synthetic rerouting scenario passes;
- no-effect scenario fails;
- scenario with no reroutes fails even if routes are valid.

## Documentation Updates

Update:

```text
docs/reproduce/coupled-seam/STATUS.md
docs/reproduce/coupled-seam/ADR-019-SYNTHESIS.md
```

The docs should record that dynamic congestion routing is the second dynamic
lifecycle mechanism. If the implementation shows a repeated lifecycle shape with
dynamic flood, the docs should say so explicitly. The docs should still defer
`CoupledModel` extraction unless implementation exposes a concrete shared API
need.

## Validation

Targeted commands:

```bash
.venv/bin/python -m pytest tests/gis/test_dynamic_congestion.py tests/gis/test_congestion_gate.py -q
```

Full verification:

```bash
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

Run `engine_oracle.py --science` and `engine_oracle.py --check` sequentially, not
in parallel.

## Non-Goals

- No `CoupledModel` or `CoupledSpace` extraction in this phase.
- No raster, flood, or temporal raster layer.
- No codegen registry entry or template.
- No real road data demo.
- No BPR function, lane capacity, queue spillback, car-following, or traffic
  assignment.
- No calibration to observed traffic counts.
- No base-engine changes.
