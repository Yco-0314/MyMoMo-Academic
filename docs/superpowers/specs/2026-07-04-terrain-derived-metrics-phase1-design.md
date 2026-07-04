# Terrain Derived Metrics Phase 1 - Design Spec

## Summary

Extend the terrain bridge with a tiny deterministic metrics reader for committed
ASCII heightfields. Given a valid terrain bridge manifest, the new API returns
basic terrain summary metrics that later GIS, 3D, or physical-space consumers
can inspect before any renderer, mesh builder, or solver exists.

This phase proves the bridge is computationally consumable. It does not render
3D, construct meshes, run hydrology/physics, parse arbitrary DEM rasters, or
validate real-world terrain accuracy.

## Scope

Modify:

- `abm_auto/terrain_bridge.py`
- `tests/test_terrain_bridge.py`
- `docs/reproduce/terrain-bridge/STATUS.md`

Do not modify base-engine forbidden paths.

## API

Add:

- `summarize_terrain_bridge_manifest(manifest, repo=None) -> dict`
- `terrain_metrics_gate(manifest, repo=None) -> tuple[bool, str]`

For `ascii_heightfield`, the summary returns:

- `ok`
- `issues`
- `manifest_id`
- `source_kind`
- `rows`
- `cols`
- `min_elevation`
- `max_elevation`
- `mean_elevation`
- `relief`
- `max_neighbor_delta`
- `boundary_note`

`max_neighbor_delta` is the maximum absolute difference between horizontal or
vertical neighboring cells. It is a cheap terrain-shape signal, not a slope
model.

For `dem_raster`, metrics fail clearly in Phase 1:

`terrain metrics currently supports ascii_heightfield only`

## Gate

The metrics gate passes only when:

- the manifest gate validates;
- source kind is `ascii_heightfield`;
- summary shape is positive;
- relief is positive;
- `max_neighbor_delta` is positive.

The success message must include:

- `not a 3D renderer`
- `not a physical simulation certificate`

## Tests

Extend `tests/test_terrain_bridge.py`:

- committed fixture summary returns expected 3x3 metrics;
- metrics gate passes with boundary text;
- flat heightfield fails metrics gate because relief is zero;
- `dem_raster` manifest fails metrics summary with a clear unsupported message;
- malformed ASCII values fail with a clear issue.

Final verification:

- `.venv/bin/python -m pytest tests/test_terrain_bridge.py -q`
- `.venv/bin/python engine_oracle.py --science`
- `.venv/bin/python engine_oracle.py --check`
- forbidden base-engine diff check must be empty.
