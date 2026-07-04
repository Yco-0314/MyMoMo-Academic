# Dynamic Flood Codegen Template Phase 1 Design

**Date:** 2026-06-20
**Status:** Approved for implementation
**Scope:** GIS-only dynamic flood evacuation codegen

## Summary

Promote the existing `dynamic_flood_evacuation` capability from registered gap
to codegen-renderable. The generated model builds a synthetic road network, a
time-varying `RasterTimeline`, runs `run_dynamic_flood_evacuation(...)`, and
verifies rerouting behavior with `dynamic_flood_reroute_gate(...)`.

This is a codegen coverage step over an existing gated runtime mechanism. It
does not add traffic flow, congestion, real-data loading, or a shared
`CoupledModel` abstraction.

## Goals

- Mark `dynamic_flood_evacuation` as `renderable=True`.
- Add required codegen tokens:
  - `RasterTimeline`
  - `RasterSpace`
  - `GeoNetwork`
  - `run_dynamic_flood_evacuation`
  - `dynamic_flood_reroute_gate`
- Render deterministic runnable code for explicit
  `GISModelSpec(spatial_type="network", mechanism="dynamic_flood_evacuation",
  capability="dynamic_flood_evacuation")`.
- Keep runtime behavior unchanged.
- Update extractor prompt and self-extension preflight behavior through the
  registry automatically.

## Non-Goals

- No new dynamic flood model behavior.
- No moving-agent traffic flow, congestion, BPR, capacity, or real evacuation
  optimality claims.
- No real road or flood file I/O.
- No `CoupledModel` extraction.
- No edits under `abm_auto/runtime`, `abm_auto/codegen`,
  `abm_auto/calibration`, `abm_auto/agents`, or `abm_auto/pipeline`.

## Architecture

The template uses the same synthetic network shape as the dynamic reroute gate:

- direct path from start toward safe node;
- dry detour alternative;
- first frame dry so the initial direct route is planned;
- later frames flood the direct next edge so reroute-enabled agents switch to
  the dry detour;
- `dynamic_flood_reroute_gate(...)` compares reroute-enabled and static routing
  runs and must print `PASS`.

The generated code calls `run_dynamic_flood_evacuation(...)` before the gate so
the fidelity gate can verify the runnable model uses the dynamic runtime, not
only the gate wrapper.

## Testing

Update GIS tests for:

- registry: dynamic flood is renderable, temporal, dynamic, and has required
  tokens;
- renderable list includes `dynamic_flood_evacuation`;
- explicit dynamic flood spec validates without data path;
- rendered code contains `RasterTimeline`, `run_dynamic_flood_evacuation`, and
  `dynamic_flood_reroute_gate`;
- rendered code runs and prints `PASS`;
- codegen fidelity gate passes clean dynamic code and fails if dynamic gate or
  runtime call is removed;
- extractor prompt includes dynamic flood once renderable;
- self-extension preflight classifies dynamic flood as renderable.

Final verification:

```bash
.venv/bin/python -m pytest tests/gis/test_capabilities.py tests/gis/test_codegen.py tests/gis/test_codegen_gate.py tests/gis/test_extractor.py tests/gis/test_self_extension.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

## Expected Status Update

`docs/reproduce/coupled-seam/STATUS.md` should record dynamic flood as the first
runnable moving-agent dynamic codegen cell. It remains synthetic and does not
claim real traffic-flow validity.
