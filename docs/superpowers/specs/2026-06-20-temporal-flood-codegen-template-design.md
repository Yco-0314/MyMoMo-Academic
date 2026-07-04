# Temporal Flood Codegen Template Phase 1 Design

**Date:** 2026-06-20
**Status:** Approved for implementation
**Scope:** GIS-only temporal raster-network flood codegen

## Summary

Promote the existing `temporal_flood_evacuation` capability from registered gap
to codegen-renderable. The generated model builds a synthetic `GeoNetwork`, a
three-frame `RasterTimeline` (`dry -> flooded -> receded`), runs
`run_temporal_flood_evacuation(...)`, and verifies the behavior with
`temporal_flood_gate(...)`.

This is the next known-pattern scaffold-and-gate step after static coupled flood
codegen. It proves codegen can emit a temporal layer cell that composes
`RasterTimeline`, `RasterSpace`, and `GeoNetwork`. It does not generate dynamic
moving-agent rerouting code.

## Goals

- Mark `temporal_flood_evacuation` as `renderable=True`.
- Add registry required tokens:
  - `RasterTimeline`
  - `RasterSpace`
  - `GeoNetwork`
  - `run_temporal_flood_evacuation`
  - `temporal_flood_gate`
- Render deterministic runnable code for explicit
  `GISModelSpec(spatial_type="temporal", mechanism="temporal_flood_evacuation",
  capability="temporal_flood_evacuation")`.
- Keep `dynamic_flood_evacuation` nonrenderable.
- Let extractor prompt include temporal flood once it is renderable.

## Non-Goals

- No dynamic moving-agent codegen.
- No traffic flow, congestion, or route replanning codegen.
- No real road/flood file I/O.
- No `CoupledModel` extraction.
- No edits under `abm_auto/runtime`, `abm_auto/codegen`,
  `abm_auto/calibration`, `abm_auto/agents`, or `abm_auto/pipeline`.

## Architecture

The registry remains the source of truth. The template layer gets a
`cap.key == "temporal_flood_evacuation"` branch that emits one `main.py`.

The generated program:

- creates a detour road network from Shapely `LineString` objects;
- creates `RasterSpace` frames sharing CRS, shape, and affine transform;
- builds `RasterTimeline.from_frames([dry, flooded, receded])`;
- selects safe and agent nodes using `GeoNetwork.nearest_node`;
- calls `run_temporal_flood_evacuation(...)`;
- calls `temporal_flood_gate(...)`;
- prints `PASS: ...` only when the deterministic temporal signature is present.

The codegen fidelity gate continues to read required tokens from the registry.
Missing `RasterTimeline`, `run_temporal_flood_evacuation`, or
`temporal_flood_gate` must fail structurally.

## Testing

Update GIS tests for:

- registry: temporal flood is renderable and has temporal required tokens;
- renderable list includes `temporal_flood_evacuation`;
- explicit temporal spec validates without `data_path`;
- rendered temporal code contains `RasterTimeline`,
  `run_temporal_flood_evacuation`, and `temporal_flood_gate`;
- rendered temporal model runs and prints `PASS`;
- fidelity gate passes clean temporal code and fails if a required token is
  removed;
- extractor prompt includes temporal flood and still excludes dynamic flood;
- dynamic flood render still fails as nonrenderable;
- self-extension preflight now classifies temporal flood as renderable and
  dynamic flood as registered gap.

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

`docs/reproduce/coupled-seam/STATUS.md` should record temporal flood as the
second runnable multi-layer codegen template and the first runnable temporal
codegen cell. Dynamic flood remains a registered gap.
