# Dynamic Flood Evacuation Design Spec

**Status:** Implemented. **Date:** 2026-06-18. **Repo:** MyMoMo-GIS-Academic.
**Parent:** [ADR-019](../../decisions/ADR-019-gis-abm-platform-vision.md)
(coupling matrix layer B plus dynamic evacuation mechanism evidence).

## Goal

Add the first moving-agent dynamic flood evacuation layer on top of the existing
`RasterTimeline` x `GeoNetwork` flood seam. The model answers a narrow behavioural
question: when flood state changes by tick, can node-based moving agents reroute at
road nodes and produce a deterministic outcome difference compared with a static
initial route?

This is a coupled GIS lifecycle model, not a traffic-flow or optimal emergency
evacuation model.

## Architecture

The dynamic model lives in `abm_auto/gis/_dynamic_flood.py` and composes existing
GIS pieces:

- `RasterTimeline.at(t)` supplies the flood raster for the current tick.
- `flood_depth_per_edge(geonet, flood, n_samples)` maps that raster to per-edge
  flood depth.
- A routable copy of `geonet.graph` removes edges whose depth is above
  `threshold`.
- Agents start at graph nodes, plan shortest routes to any safe node, and move
  along one edge at a time.

Each tick uses this order:

1. read `RasterTimeline.at(t)`;
2. compute `flood_depth_per_edge`;
3. at nodes, plan or reroute against the current flooded-edge set;
4. move agents along their current edge;
5. append a step summary.

Agents already on an edge are checked against the current tick's flooded-edge set
before any node planning. If their current edge is flooded, they are marked
stranded and recorded with `stranded_reason == "flooded_on_edge"`; they do not
turn around mid-edge.

Movement is intentionally discrete at edge boundaries: one tick can complete at
most one edge, and unused speed does not carry across to the next edge. Rerouting
also happens only at nodes. An agent already on an edge keeps moving unless that
edge is flooded in the current tick.

## Dynamic Model API and Return Shape

Implemented API:

```python
run_dynamic_flood_evacuation(
    geonet,
    flood_timeline,
    threshold,
    safe_nodes,
    agent_nodes,
    speed_m_per_tick=100.0,
    n_samples=8,
    reroute=True,
) -> dict
```

Important inputs:

- `geonet`: a `GeoNetwork` whose `graph` provides nodes, edges, and edge lengths.
- `flood_timeline`: a validated `RasterTimeline`.
- `threshold`: edge depths greater than this value are treated as flooded.
- `safe_nodes`: graph nodes that count as evacuation destinations.
- `agent_nodes`: starting graph nodes for moving agents.
- `speed_m_per_tick`: positive distance budget per tick.
- `reroute`: when true, node-based agents replan if they have no route or their
  next edge becomes unavailable; when false, agents plan once.

Top-level result keys:

- `steps`: one summary per tick, with `t`, `arrived`, `moving`, `waiting`,
  `stranded`, `n_flooded_edges`, `reroutes_this_step`, and `total_reroutes`.
- `agents`: final per-agent states, including `id`, `node`, `edge`,
  `edge_progress_m`, `route`, `arrived`, `stranded`, `stranded_reason`,
  `reroutes`, `exposure_depth`, and `arrival_t`.
- `n_steps`, `n_agents`, `arrived`, `stranded`, `moving`, `total_reroutes`,
  `mean_arrival_t`, and `max_exposure_depth`.

Agents that are neither arrived nor already stranded when the timeline ends are
marked stranded with `stranded_reason == "not_arrived"`.

## Gate

`dynamic_flood_reroute_gate` lives in `abm_auto/gis/_flood_gate.py`. It runs the
same scenario twice:

- `run_dynamic_flood_evacuation(..., reroute=True)`
- `run_dynamic_flood_evacuation(..., reroute=False)`

The gate passes only when the rerouting run records at least one successful
reroute and improves a deterministic outcome: more arrivals, fewer stranded
agents, or earlier mean arrival time when arrivals and stranded counts tie.

The claim is deliberately narrow: the gate proves that moving-agent rerouting has
a deterministic behavioural impact on time-varying flood outcomes. It does not
prove real traffic flow, congestion realism, emergency evacuation optimality, or
policy validity.

## Seam Decision / YAGNI

Do **not** extract `CoupledModel` or `CoupledSpace` yet.

Phase 2 now provides real per-tick lifecycle evidence: current raster frame,
cross-layer edge flooding, node planning/rerouting, edge movement, and step
summary. That is stronger evidence than Phase 1's repeated static evaluation.
However, there is still only one dynamic lifecycle mechanism. The shared shape is
visible but not yet proven reusable.

Extraction becomes justified when a second dynamic lifecycle mechanism or the
codegen registry reveals the same lifecycle needs across models, such as layer
registration, CRS negotiation, tick ordering, route invalidation, agent lifecycle
hooks, or common temporal metrics.

## Validation

Targeted tests:

```bash
python -m pytest tests/gis/test_dynamic_flood.py tests/gis/test_flood_gate.py -q
```

Validation covers:

- two-tick movement and arrival history;
- speed not carrying across edge boundaries;
- stable route tie-breaking;
- node-only rerouting to a dry detour;
- failed reroute attempts not incrementing reroute counts;
- on-edge agents becoming stranded when their current edge floods;
- missing or unreachable safe nodes ending as `not_arrived`;
- rejection of non-positive speed and malformed timelines;
- the reroute gate's pass and failure modes.

## Out of Scope

- A general `CoupledModel` / `CoupledSpace` abstraction.
- Congestion, capacity, BPR functions, car-following, or traffic assignment.
- Mid-edge turning, residual speed carry-over, or multi-edge traversal in one tick.
- Optimal emergency evacuation claims.
- Codegen templates, registry wiring, or coupled-model generation.
- Real-data demonstration or calibration to observed evacuation/flood outcomes.
