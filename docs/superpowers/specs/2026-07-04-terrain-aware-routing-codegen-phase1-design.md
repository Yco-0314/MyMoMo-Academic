# Terrain-Aware Routing Codegen Phase 1 - Design Spec

## Summary

Turn `terrain_aware_routing` from a registered non-renderable gap into a runnable
synthetic GIS codegen capability. Leave `terrain_network_cost` non-renderable.

Generated code builds a small two-route `GeoNetwork`, writes a temporary
synthetic ASCII heightfield plus manifest, calls `terrain_aware_shortest_path`
and `terrain_aware_routing_gate`, and prints `PASS` when terrain-derived cost
changes shortest-path route choice.

## Scope

Modify:

- `abm_auto/gis/_capabilities.py`
- `abm_auto/gis/_templates.py`
- `tests/gis/test_capabilities.py`
- `tests/gis/test_codegen.py`
- `tests/gis/test_codegen_gate.py`
- `tests/gis/test_extractor.py`
- `docs/reproduce/coupled-seam/STATUS.md`

Do not make `terrain_network_cost` renderable. Do not add real-data terrain I/O
or a generic terrain template.

## Template Contract

The generated model must be self-contained:

- create a temporary `terrain.asc` file;
- compute its SHA-256 in generated code;
- build a manifest dictionary satisfying the existing terrain bridge validator;
- build a synthetic `GeoNetwork` with a shorter uphill route and longer flat
  detour;
- call `terrain_aware_shortest_path(...)`;
- verify with `terrain_aware_routing_gate(...)`.

Required tokens for fidelity:

- `GeoNetwork`
- `LineString`
- `terrain_aware_shortest_path`
- `terrain_aware_routing_gate`

Parameters:

- `grade_weight`: float, default `0.25`, min `0.0`;
- `n_samples`: int, default `5`, min `2`.

## Tests

- Registry:
  - `terrain_aware_routing` is renderable;
  - `terrain_network_cost` remains non-renderable;
  - `renderable_capabilities()` includes `terrain_aware_routing` only.

- Codegen:
  - explicit `terrain_aware_routing` spec validates and renders;
  - rendered code contains every required token;
  - generated model executes and prints `PASS`;
  - `render(...)` still refuses `terrain_network_cost`.

- Gate:
  - fidelity gate passes on the clean render;
  - removing `terrain_aware_routing_gate` fails through registry-required tokens.

- Extractor:
  - prompt now lists `terrain_aware_routing`;
  - prompt still omits `terrain_network_cost`;
  - explicit LLM output for `terrain_aware_routing` is accepted;
  - explicit LLM output for `terrain_network_cost` is still refused.

Final verification:

- `.venv/bin/python -m pytest tests/gis/test_capabilities.py tests/gis/test_codegen.py tests/gis/test_codegen_gate.py tests/gis/test_extractor.py -q`
- `.venv/bin/python -m pytest tests/gis -q`
- `.venv/bin/python engine_oracle.py --science`
- `.venv/bin/python engine_oracle.py --check`
- forbidden base-engine diff check must be empty.

## Boundaries

Do not:

- add a generic terrain renderer;
- add 3D, meshes, hydrology, vehicle dynamics, congestion, or traffic-flow claims;
- make `terrain_network_cost` renderable;
- read external terrain data;
- add `CoupledModel`;
- touch base-engine forbidden paths.
