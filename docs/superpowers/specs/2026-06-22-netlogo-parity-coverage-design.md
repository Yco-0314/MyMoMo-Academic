# NetLogo GIS Parity — Areal Coverage (Phase 3) — Design Spec

**Status:** Draft. **Date:** 2026-06-22. **Repo:** MyMoMo-GIS-Academic.
**Parent:** [ADR-019](../../decisions/ADR-019-gis-abm-platform-vision.md);
companion to [Phase 1 topology](2026-06-22-netlogo-parity-topology-design.md)
and [Phase 2 focal](2026-06-22-netlogo-parity-focal-design.md). Independent
branch off `main`.

## Why

NetLogo's `gis:apply-coverage` copies polygon attribute values to raster cells,
**area-weighted** by the polygon-cell intersection. We have point-in-polygon
grouping (`assign_points_to_polygons`) but cannot rasterise polygon attributes —
the missing primitive to push census/land-use/zoning polygons onto a raster
grid for mechanism consumption (population density, suitability rasters, …).

## Hard constraints

1. Zero-change to `abm_auto/runtime/`, `codegen/`, `calibration/`, `agents/`,
   `pipeline/`. Additive only.
2. **No new dependency.** shapely (2.1.2) already in the GIS extra.
3. Lazy `from shapely.geometry import box` etc. inside `_coverage.py`.
4. **No conflict with `feat/netlogo-parity-topology`,
   `feat/netlogo-parity-focal`, or `codex/real-data-validation-pack-v2*`.**
   Lands on `feat/netlogo-parity-coverage` off `main` (14e668a).
5. Predictions locked: every test pins a known polygon × raster result.

## Scope (this branch ships)

A new module `abm_auto/gis/_coverage.py` with one primitive + one gate:

### C1 `apply_coverage(polygons, values, raster_template, default=0.0) -> RasterField`

For each cell `(col, row)` in `raster_template`'s grid (defined by its
`transform` + `data.shape`):

1. Build the cell polygon (a 1-pixel `box` in world coordinates).
2. For each input polygon (with attribute `values[i]`), compute the
   intersection area with the cell.
3. **Area-weighted aggregation**: cell value =
   `Σ(area_i × values[i]) / Σ(area_i)` over the polygons that intersect.
4. If no polygon covers the cell → `default` (callers can choose `nodata` /
   `nan` / `0.0`).

The returned `RasterField` has the same shape / transform / CRS as
`raster_template`; `nodata` is preserved.

`polygons` is an iterable of shapely Polygons; `values` is a parallel iterable
of floats. **STRtree-indexed** so it scales: per cell, only query the polygons
whose bounding boxes touch the cell.

### C2 `apply_coverage_gate(polygons, values, raster_template) -> (bool, str)`

Deterministic signature pinning the contract:

1. **constant-attribute identity**: a single polygon covering the whole raster
   with attribute `v` → every cell `== v` (within numerical tolerance).
2. **disjoint-polygon area-weighted average**: two non-overlapping polygons
   with attributes `vA`, `vB` covering the raster → each cell's value is the
   area-weighted average of the polygons it intersects.
3. **empty-input identity**: zero polygons → every cell `== default`.

The gate must FAIL on a broken implementation (e.g. one that returns the raw
sum without dividing by intersection area).

## Decomposition (TDD)

1. C1.a `_cell_polygon(template, col, row)` helper (pure, testable).
2. C1.b `apply_coverage` — STRtree-indexed, area-weighted, default fill.
3. C2 `apply_coverage_gate` — 3 contract checks.
4. Reverse tests (gate must fail on a broken stub).

## Validation

```
.venv/bin/python -m pytest tests/gis/test_coverage.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline   # must be EMPTY
```

## Non-goals

- No new STATUS adapter row (coverage is an operator over an existing layer
  combination, not a new cross-layer coupling cell — same call as focal).
- No registry / codegen template (deferred).
- No real GIS data; synthetic polygons + rasters only.
- No nodata propagation logic beyond `default` fill for uncovered cells.
- No vector tile / streamed input — single in-memory layer per call.
- No edits to `feat/netlogo-parity-topology`, `feat/netlogo-parity-focal`,
  or `codex/real-data-validation-pack-v2*`.
