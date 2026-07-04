# DEM Raster Terrain Metrics Phase 1 - Design Spec

## Summary

Extend the terrain bridge metrics path so `terrain_source.kind == "dem_raster"`
can consume a local GeoTIFF DEM through the same manifest contract used by ASCII
heightfields.

This is the first real-data terrain ingestion bridge: a reviewer can point a
terrain bridge manifest at a local official DEM clip, and the same
`summarize_terrain_bridge_manifest(...)` / `terrain_metrics_gate(...)` path will
compute deterministic terrain metrics. It does not download DEMs, reproject,
resample, render 3D, build meshes, run hydrology, or certify real-world terrain
accuracy.

## Scope

Modify:

- `abm_auto/terrain_bridge.py`
- `tests/test_terrain_bridge.py`
- `docs/reproduce/terrain-bridge/STATUS.md`

Do not modify base-engine forbidden paths. Do not add committed binary DEM
fixtures in this phase; tests can generate a tiny temporary GeoTIFF.

## Runtime Contract

For `terrain_source.kind == "dem_raster"`:

- lazily import `rasterio` inside the DEM metrics path;
- read band 1 as a masked array;
- reject unreadable raster files;
- reject rasters with no valid cells;
- reject shape mismatch against `coordinate_frame.grid_shape`;
- compute:
  - rows;
  - cols;
  - min elevation;
  - max elevation;
  - mean elevation;
  - relief;
  - maximum horizontal/vertical neighbor delta over valid neighboring cells.

The existing manifest checksum, source path, boundary rule, consumer, and
verification checks remain unchanged.

If `rasterio` is unavailable, return a clear issue:

`terrain metrics for dem_raster require rasterio`

## Tests

Update `tests/test_terrain_bridge.py`:

- generate a tiny temporary GeoTIFF DEM with `rasterio` and a valid manifest;
- `summarize_terrain_bridge_manifest(...)` reports deterministic metrics;
- `terrain_metrics_gate(...)` passes with boundary text;
- declared `grid_shape` mismatch fails clearly;
- if `rasterio` is unavailable, skip DEM-raster tests.

Final verification:

- `.venv/bin/python -m pytest tests/test_terrain_bridge.py -q`
- `.venv/bin/python -m pytest tests/gis/test_terrain_network_coupling.py tests/gis/test_terrain_aware_routing.py tests/test_terrain_bridge.py -q`
- `.venv/bin/python -m pytest tests/gis -q`
- `.venv/bin/python engine_oracle.py --science`
- `.venv/bin/python engine_oracle.py --check`
- forbidden base-engine diff check must be empty.

## Boundaries

Do not:

- fetch remote DEMs;
- reproject or resample rasters;
- interpret CRS beyond manifest/file contract checks;
- render 3D terrain;
- build meshes;
- run hydrology, erosion, collision, or vehicle dynamics;
- claim real-world terrain accuracy;
- add `CoupledModel`;
- touch base-engine forbidden paths.
