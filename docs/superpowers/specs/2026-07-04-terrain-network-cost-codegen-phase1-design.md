# Terrain Network Cost Codegen Phase 1 - Design Spec

## Summary

Turn `terrain_network_cost` from a registered non-renderable gap into a runnable
synthetic GIS codegen capability.

Generated code builds a small `GeoNetwork`, writes a temporary synthetic ASCII
heightfield plus manifest, calls `terrain_cost_per_edge(...)`, verifies with
`terrain_network_coupling_gate(...)`, and prints `PASS` when terrain-derived
cost differs across network edges.

This is the codegen closure for the static terrain-network cost cell. It does
not perform route choice, traffic flow, vehicle dynamics, real DEM ingestion,
3D rendering, hydrology, or physical terrain validation.

## Scope

Modify:

- `abm_auto/gis/_capabilities.py`
- `abm_auto/gis/_templates.py`
- `tests/gis/test_capabilities.py`
- `tests/gis/test_codegen.py`
- `tests/gis/test_codegen_gate.py`
- `tests/gis/test_extractor.py`
- `docs/reproduce/coupled-seam/STATUS.md`

Do not add generic real-data terrain ingestion and do not alter base-engine
forbidden paths.

## Template Contract

The generated model must be self-contained:

- create a temporary `terrain.asc` file;
- compute its SHA-256 in generated code;
- build a terrain bridge manifest dictionary satisfying the existing validator;
- build a synthetic `GeoNetwork` with one flat edge and one uphill edge;
- call `terrain_cost_per_edge(...)`;
- verify with `terrain_network_coupling_gate(...)`;
- print `PASS` with `terrain changes network edge cost`.

Required tokens:

- `GeoNetwork`
- `LineString`
- `terrain_cost_per_edge`
- `terrain_network_coupling_gate`

Parameters:

- `grade_weight`: float, default `1.0`, min `0.0`;
- `n_samples`: int, default `5`, min `2`;
- `threshold`: float, default `0.01`, min `0.0`.

## Tests

- Registry:
  - `terrain_network_cost` is renderable;
  - `terrain_aware_routing` remains renderable;
  - `renderable_capabilities()` includes both terrain renderable capabilities.

- Codegen:
  - explicit `terrain_network_cost` spec validates and renders;
  - rendered code contains every required token;
  - generated model executes and prints `PASS`;
  - generated model output includes `terrain changes network edge cost`.

- Gate:
  - fidelity gate passes on clean render;
  - removing `terrain_network_coupling_gate` fails through registry-required
    token checks.

- Extractor:
  - prompt now lists `terrain_network_cost`;
  - explicit LLM output for `terrain_network_cost` is accepted.

Final verification:

- `.venv/bin/python -m pytest tests/gis/test_capabilities.py tests/gis/test_codegen.py tests/gis/test_codegen_gate.py tests/gis/test_extractor.py -q`
- `.venv/bin/python -m pytest tests/gis -q`
- `.venv/bin/python engine_oracle.py --science`
- `.venv/bin/python engine_oracle.py --check`
- forbidden base-engine diff check must be empty.

## Boundaries

Do not:

- add real terrain download or DEM ingestion;
- add 3D, mesh, hydrology, vehicle dynamics, congestion, or traffic-flow claims;
- add `CoupledModel`;
- change base-engine forbidden paths.
