# Space Zoo Codegen Template Phase 1 Design

**Date:** 2026-06-20
**Status:** Approved for implementation
**Scope:** GIS-only point-network and polygon-point codegen

## Summary

Promote the existing space-zoo capabilities `point_network_risk` and
`polygon_point_zoning` from registered gaps to codegen-renderable cells. Because
their registry entries already name deterministic gates but no reusable gate
functions exist yet, this phase first adds a small `_space_zoo_gate.py`, then
adds synthetic runnable templates for both capabilities.

This is codegen coverage over existing point/polygon spaces and coupling
operators. It does not add real data loading, spatial validation, calibration,
traffic modeling, or a shared `CoupledModel` abstraction.

## Goals

- Add `point_network_risk_gate(...)`:
  - computes `point_risk_per_edge(...)`;
  - computes `risk_exposure(...)`;
  - passes when a loaded risky edge lights up and loaded dry edges stay zero.
- Add `polygon_point_zoning_gate(...)`:
  - computes `assign_points_to_polygons(...)`;
  - passes when assignments match an expected deterministic mapping.
- Mark `point_network_risk` as `renderable=True`.
- Mark `polygon_point_zoning` as `renderable=True`.
- Render deterministic runnable code for explicit point/polygon specs.
- Keep base engine directories untouched.

## Non-Goals

- No real point, road, or polygon file I/O.
- No observed spatial validation or calibration.
- No new risk model beyond existing count and exposure helpers.
- No new polygon topology model beyond existing point assignment.
- No codegen scaffold generation.
- No `CoupledModel` extraction.
- No edits under `abm_auto/runtime`, `abm_auto/codegen`,
  `abm_auto/calibration`, `abm_auto/agents`, or `abm_auto/pipeline`.

## Architecture

### Point-Network Risk

The generated model builds:

- a two-edge `GeoNetwork`;
- a `PointSpace` with one point near the first edge and one far away;
- deterministic edge loads where the risky edge has positive load;
- calls to `point_risk_per_edge(...)`, `risk_exposure(...)`, and
  `point_network_risk_gate(...)`.

The gate proves the coupled point-network operator can identify loaded risky
edges in a synthetic case. It does not claim real hazard, exposure, or traffic
validity.

### Polygon-Point Zoning

The generated model builds:

- two adjacent polygons with stable ids `west` and `east`;
- a `PointSpace` with one point in each polygon and one outside;
- calls to `assign_points_to_polygons(...)` and
  `polygon_point_zoning_gate(...)`.

The gate proves deterministic point-to-region assignment in a synthetic case. It
does not validate real zoning data.

## Testing

Update GIS tests for:

- new gate pass/fail cases;
- registry: both capabilities are renderable with required tokens;
- renderable list includes both space-zoo capabilities;
- explicit point/polygon specs validate;
- rendered point-network code contains `PointSpace`, `GeoNetwork`,
  `point_risk_per_edge`, `risk_exposure`, and `point_network_risk_gate`;
- rendered polygon-point code contains `PointSpace`, `PolygonSpace`,
  `assign_points_to_polygons`, and `polygon_point_zoning_gate`;
- both generated models run and print `PASS`;
- codegen fidelity gate passes clean space-zoo code and fails when each gate
  token is removed;
- extractor prompt includes both capabilities once renderable;
- self-extension preflight classifies both as renderable while mechanism cells
  remain registered gaps.

Final verification:

```bash
.venv/bin/python -m pytest tests/gis/test_space_zoo_gate.py tests/gis/test_capabilities.py tests/gis/test_codegen.py tests/gis/test_codegen_gate.py tests/gis/test_extractor.py tests/gis/test_self_extension.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

## Expected Status Update

`docs/reproduce/coupled-seam/STATUS.md` should record point-network and
polygon-point codegen as synthetic space-zoo templates. Both remain deterministic
synthetic evidence only.
