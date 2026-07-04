# Coupled Flood Codegen Template Phase 1 Design

**Date:** 2026-06-20
**Status:** Approved for implementation
**Scope:** GIS-only, additive, static raster-network flood evacuation codegen

## Summary

Add the first runnable coupled GIS codegen template by promoting the existing
`flood_evacuation` capability from runtime-only to codegen-renderable. The
template renders a deterministic synthetic road network plus flood raster, runs
`run_flood_evacuation(...)`, and verifies behavior with `flood_gate(...)`.

This phase proves codegen can emit a multi-layer model that composes
`GeoNetwork` and `RasterSpace` through the existing flood coupling seam. It does
not add temporal flood, dynamic moving-agent evacuation, social-spatial
contagion, real-data flood ingestion, or a shared `CoupledModel` abstraction.

## Goals

- Mark `flood_evacuation` as `renderable=True` in the GIS capability registry.
- Add required fidelity tokens for the coupled template:
  - `GeoNetwork`
  - `RasterSpace`
  - `run_flood_evacuation`
  - `flood_gate`
- Render deterministic runnable code for explicit
  `GISModelSpec(spatial_type="network", mechanism="flood_evacuation",
  capability="flood_evacuation")`.
- Keep legacy implicit network specs mapped only to `network_routing_load`; flood
  codegen requires the explicit capability key.
- Keep extractor output limited to currently renderable capabilities after this
  phase, so `flood_evacuation` may be emitted only once it is truly renderable.

## Non-Goals

- No codegen templates for `temporal_flood_evacuation` or
  `dynamic_flood_evacuation`.
- No codegen templates for social-spatial, point-network, polygon-point,
  mechanism-library, spatial validation, or spatial calibration cells.
- No real flood raster file loading or road shapefile requirement for this first
  coupled template.
- No edits under `abm_auto/runtime`, `abm_auto/codegen`,
  `abm_auto/calibration`, `abm_auto/agents`, or `abm_auto/pipeline`.
- No `CoupledModel` extraction.

## Architecture

The registry remains the truth-table. `flood_evacuation` becomes a renderable
capability while keeping its explicit capability requirement. The template layer
branches on `cap.key == "flood_evacuation"` and emits a single `main.py`.

The generated `main.py` uses only GIS runtime imports plus `numpy`, `affine`,
and `shapely`:

- build a small detour `GeoNetwork` from `LineString` objects;
- build a `RasterSpace` with a flood blob on the direct route;
- select `agent` and `safe` nodes by `nearest_node`;
- call `run_flood_evacuation(...)` once for a representative threshold;
- call `flood_gate(...)` across dry and wet thresholds;
- print `PASS: ...` or `FAIL: ...`.

The codegen fidelity gate continues to read required tokens from the registry.
It must fail if the coupled generated code omits either the coupled model call
or the flood gate call.

## Spec Validation

`GISModelSpec.validate()` remains capability-driven. Existing behavior stays:

- `network_routing_load` still requires `data_path`.
- `flood_evacuation` does not require `data_path` in this phase because it
  renders a deterministic synthetic coupled fixture.
- implicit `(spatial_type="network", mechanism="routing_load")` continues to
  resolve to `network_routing_load`.
- implicit `(spatial_type="network", mechanism="flood_evacuation")` remains
  invalid unless `capability="flood_evacuation"` is provided.

## Testing

Add and update tests for:

- registry: `flood_evacuation` is renderable and has coupled required tokens;
- spec validation: explicit flood capability validates without `data_path`;
- render: flood code contains `GeoNetwork`, `RasterSpace`,
  `run_flood_evacuation`, and `flood_gate`;
- runtime: rendered flood model executes and prints `PASS`;
- codegen gate: clean flood code passes;
- codegen gate: removing `run_flood_evacuation` or `flood_gate` fails via
  registry-required tokens;
- extractor: renderable capability list now includes `flood_evacuation`, while
  still rejecting nonrenderable temporal/dynamic capabilities.

Final verification:

```bash
.venv/bin/python -m pytest tests/gis/test_capabilities.py tests/gis/test_codegen.py tests/gis/test_codegen_gate.py tests/gis/test_extractor.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

## Expected Status Update

`docs/reproduce/coupled-seam/STATUS.md` should record that codegen now has one
runnable coupled template for static flood evacuation. Runtime-only dynamic,
temporal, and social-spatial cells remain registered gaps until their own
template phases.
