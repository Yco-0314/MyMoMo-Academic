# Time-Varying Flood Design Spec

**Status:** Draft. **Date:** 2026-06-18. **Repo:** MyMoMo-GIS-Academic.
**Parent:** [ADR-019](../../decisions/ADR-019-gis-abm-platform-vision.md)
(coupling matrix layer B: time-varying layers after space zoo).

Note: this document records the historical Phase 1 scope. Moving-agent dynamic
evacuation is now covered by
[Dynamic Flood Evacuation Design Spec](2026-06-18-dynamic-flood-evacuation-design.md).
Statements below that moving agents, per-tick route following, and rerouting are
out of scope apply to Phase 1 only.

## Goal

Add the first temporal GIS layer for the coupled flood seam: a sequence of
flood-depth rasters evaluated over the same road `GeoNetwork`. The immediate model
answers: as flood depth evolves over time, how do stranded agents, flooded edges,
and evacuation detours change?

This is deliberately **not** the moving-agent evacuation model yet. Phase 1 makes
time-varying raster state a small, verified adapter. Phase 2 can then add agents
moving over edges and rerouting as flood state changes, using a temporal layer that
already has its own contract and gate.

## Build order

### Phase 1 - Temporal Flood Evaluation

Build a temporal raster adapter, then reuse the existing static flood evacuation
model at each time step.

1. `RasterTimeline`: an ordered, validated sequence of `RasterSpace` frames.
2. `run_temporal_flood_evacuation`: per-step calls to `run_flood_evacuation`.
3. `temporal_flood_gate`: deterministic synthetic signature for worsening and
   recovering flood sequences.
4. `STATUS.md` update and zero-change verification.

### Phase 2 - Dynamic Flood Evacuation

After Phase 1 is green, add moving agents and rerouting:

1. agent state on graph nodes or edge progress,
2. per-tick travel over the `GeoNetwork`,
3. flood-aware edge availability or edge cost at each tick,
4. rerouting when the current route becomes blocked or costlier,
5. metrics such as arrival time, stranded time, reroute count, and exposure.

Phase 2 should be a separate spec and plan. It introduces behaviour dynamics, not
just temporal layer state, so mixing it into Phase 1 would make failures harder to
diagnose.

## Architecture

### `RasterTimeline` - `abm_auto/gis/_temporal.py`

`RasterTimeline` is a small adapter over multiple `RasterSpace` frames. It is a
temporal layer, not a general scheduler.

Minimal API:

- `RasterTimeline.from_frames(frames) -> RasterTimeline`
- `RasterTimeline.n_steps`
- `RasterTimeline.at(t) -> RasterSpace`
- `RasterTimeline.crs`
- `RasterTimeline.width`
- `RasterTimeline.height`

Validation:

- reject an empty frame sequence,
- reject non-`RasterSpace` frames,
- reject inconsistent CRS,
- reject inconsistent width/height,
- reject inconsistent affine transforms,
- reject non-integer, bool, negative, or out-of-range time indexes.

The interface stays intentionally narrow. It gives callers a time-indexed raster
layer and nothing else. It does not own the road network, agents, or simulation
clock.

### Temporal flood model - `abm_auto/gis/_flood_model.py`

Add:

`run_temporal_flood_evacuation(geonet, flood_timeline, threshold, safe_nodes, agent_nodes, n_samples=8) -> dict`

The function iterates over `range(flood_timeline.n_steps)`, calls
`run_flood_evacuation` for each frame, and returns:

- `steps`: a list of per-step static flood evacuation metrics,
- `n_steps`,
- `max_stranded`,
- `max_flooded_edges`,
- `max_mean_detour_m`,
- `recovered`: whether the final step improves relative to the worst step.

This is a repeated evaluation model: the same agent start nodes are evaluated under
each flood state. It does not mutate agent positions between steps. That limitation
is explicit because Phase 1 is testing temporal layer behaviour, not movement
policy.

### Temporal flood gate - `abm_auto/gis/_flood_gate.py`

Add:

`temporal_flood_gate(geonet, flood_timeline, safe_nodes, agent_nodes, threshold) -> tuple[bool, str]`

The gate uses a synthetic sequence with three semantic phases:

1. dry or weak flood,
2. stronger flood that worsens evacuation,
3. dry or weaker flood that recovers.

Acceptance:

- the timeline has at least three steps,
- the worst step is worse than the first step by `stranded`, `mean_detour_m`, or
  `n_flooded_edges`,
- the final step improves relative to the worst step by at least one of those
  metrics,
- all checks are deterministic and synthetic.

This gate makes the temporal claim structural: flood state over time affects the
coupled network outcome and can recover when the flood recedes.

## Seam decision

Do **not** extract `CoupledModel` or `CoupledSpace` in Phase 1. Time-varying flood
adds a temporal layer adapter and a repeated evaluation function, but it still does
not require a shared lifecycle object. The repeated structure remains:

1. a model owns layers,
2. `_coupling.py` reads across layers,
3. a model or gate decides how to iterate time.

Extraction becomes justified only if Phase 2 or codegen registry work reveals
shared lifecycle needs that multiple models must share: layer registration, CRS
negotiation, per-tick update order, route invalidation, or common temporal metrics.

## Validation

Unit tests use synthetic rasters and synthetic road networks only. No external GIS
data is required for the gate.

Run sequence after implementation:

```bash
python -m pytest tests/gis/test_temporal.py tests/gis/test_flood_model.py tests/gis/test_flood_gate.py -q
python -m pytest tests/gis -q
python engine_oracle.py --science
python engine_oracle.py --check
python -m pytest tests/ -q --ignore=tests/gis
```

Acceptance:

- `RasterTimeline` rejects malformed timelines and returns stable frames by time
  index.
- `run_temporal_flood_evacuation` reports one static flood result per frame and
  stable aggregate metrics.
- `temporal_flood_gate` passes for a dry -> flooded -> receded synthetic sequence
  and fails for a no-effect sequence.
- Existing static flood tests, coupled seam tests, and space zoo tests still pass.
- Base engine oracle remains green, proving the temporal layer is additive.

## Out of scope

- Moving agents along road edges.
- Per-tick route following and rerouting.
- Flood-dependent edge speed or exposure accumulation.
- Codegen templates or registry coverage for temporal models.
- Calibration to observed flood extent or traffic counts.
- A general `CoupledModel` / `CoupledSpace` abstraction.
