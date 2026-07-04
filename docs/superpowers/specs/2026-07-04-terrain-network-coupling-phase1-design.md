# Terrain-to-Network Coupling Phase 1 - Design Spec

## Summary

Add the first terrain-to-network coupling cell. Given a `GeoNetwork` and a valid
terrain bridge manifest for an ASCII heightfield, sample terrain along each road
edge and compute deterministic edge-level terrain metrics:

- `terrain_elevation_delta_per_edge`
- `terrain_grade_proxy_per_edge`
- `terrain_cost_per_edge`

Add a deterministic gate proving that a terrain heightfield can change network
edge cost. This is a bridge/coupling proof only. It does not render 3D, build a
mesh, run hydrology, model vehicle dynamics, or prove real traffic engineering.

## Why This Is Next

The terrain bridge now validates a heightfield manifest and computes derived
terrain metrics. The next useful step is to connect that terrain layer to an
existing ABM substrate. The smallest meaningful substrate is `GeoNetwork`,
because routing, flood evacuation, dynamic incident, and congestion models all
already depend on edge-level network costs.

This phase turns terrain from a passive artifact into a coupled spatial layer
without introducing a 3D engine.

## Scope

Modify:

- `abm_auto/gis/_coupling.py`
- `tests/gis/test_terrain_network_coupling.py`
- `docs/reproduce/coupled-seam/STATUS.md`

Optional fixture changes:

- `docs/reproduce/terrain-bridge/example-manifest.json` may add
  `coordinate_frame.extent` so the public seed manifest can be consumed by the
  coupling cell.

Do not modify base-engine forbidden paths.

## Terrain Contract For Coupling

The coupling functions accept a terrain bridge manifest dictionary, not a new
terrain runtime class.

The manifest must already pass `validate_terrain_bridge_manifest(...)` and must
have:

```json
"coordinate_frame": {
  "crs": "EPSG:3857",
  "grid_shape": [rows, cols],
  "extent": [min_x, min_y, max_x, max_y],
  "horizontal_units": "metre",
  "vertical_units": "metre",
  "vertical_datum": "..."
}
```

`extent` is required for this coupling phase because edge sampling needs a
world-coordinate to heightfield-cell mapping. The base terrain manifest validator
does not need to require `extent` globally; the coupling cell can be stricter.

Phase 1 supports only `terrain_source.kind == "ascii_heightfield"`. `dem_raster`
terrain manifests remain valid bridge contracts, but this coupling function
fails clearly until a later raster interop phase.

## API

Add to `abm_auto/gis/_coupling.py`:

```python
def terrain_elevation_delta_per_edge(geonet, terrain_manifest, *, repo=None, n_samples=8) -> dict:
    ...

def terrain_grade_proxy_per_edge(geonet, terrain_manifest, *, repo=None, n_samples=8) -> dict:
    ...

def terrain_cost_per_edge(geonet, terrain_manifest, *, repo=None, n_samples=8, grade_weight=1.0) -> dict:
    ...

def terrain_network_coupling_gate(geonet, terrain_manifest, *, repo=None, threshold=0.01) -> tuple[bool, str]:
    ...
```

Edge keys use deterministic undirected edge ids:

```python
tuple(sorted((u, v), key=repr))
```

Sampling:

- sample `n_samples` evenly along each edge, inclusive of endpoints;
- map `(x, y)` into `extent`;
- row 0 corresponds to the low-`y` band in Phase 1 ASCII fixtures;
- sample must be inside the extent, otherwise raise `ValueError`;
- elevation delta is `max(sampled_values) - min(sampled_values)`;
- grade proxy is `elevation_delta / edge_length`;
- terrain cost is `edge_length * (1 + grade_weight * grade_proxy)`.

Validation:

- `n_samples >= 2`, non-bool integer;
- `grade_weight >= 0`;
- `geonet.crs == terrain_manifest["coordinate_frame"]["crs"]`;
- extent is four numeric values with increasing x/y bounds;
- source kind must be `ascii_heightfield`;
- manifest must pass `validate_terrain_bridge_manifest`.

## Gate

`terrain_network_coupling_gate(...)` passes when at least one edge has grade
proxy above `threshold` and the max terrain cost is greater than the min terrain
cost.

Success message must include:

`terrain changes network edge cost`

and the boundary:

`not a 3D renderer or physical traffic model`

## Tests

Create `tests/gis/test_terrain_network_coupling.py`:

- synthetic 3x3 terrain + GeoNetwork edge crossing increasing elevation returns
  deterministic elevation delta;
- flat edge has zero grade proxy while diagonal/uphill edge has positive proxy;
- terrain cost is length plus grade penalty and preserves base length for flat
  edges;
- gate passes on mixed flat/uphill network;
- CRS mismatch fails;
- missing extent fails;
- `dem_raster` manifests fail clearly;
- invalid `n_samples` and negative `grade_weight` fail;
- out-of-extent edge sampling fails.

Final verification:

- `.venv/bin/python -m pytest tests/gis/test_terrain_network_coupling.py -q`
- `.venv/bin/python -m pytest tests/gis/test_terrain_network_coupling.py tests/test_terrain_bridge.py -q`
- `.venv/bin/python engine_oracle.py --science`
- `.venv/bin/python engine_oracle.py --check`
- forbidden base-engine diff check must be empty.

## Boundaries

Do not:

- create a 3D renderer;
- create meshes;
- run hydrology or traffic-flow physics;
- claim real-world slope or traffic validity;
- alter Anshuka real-DEM bundles;
- add a `CoupledModel` abstraction;
- touch base-engine forbidden paths.
