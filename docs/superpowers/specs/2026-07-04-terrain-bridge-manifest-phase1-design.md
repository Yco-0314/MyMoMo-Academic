# Terrain Bridge Manifest Phase 1 - Design Spec

## Summary

Add a small public terrain bridge manifest for the later 3D / physical-space
architecture lane. The manifest records how a DEM or heightfield artifact can be
shared between GISABM, future 3D rendering, and future physical-process models
without claiming that MyMoMo already has a 3D engine or physical terrain solver.

This phase is intentionally a bridge contract and gate only. It does not render
3D scenes, construct meshes, run hydrology, run physics, or validate real-world
terrain accuracy.

## Why This Exists

The roadmap's next lane is 3D terrain / physical-space architecture. The
load-bearing first step is not a renderer. It is a precise data boundary:

- what terrain artifact is being exchanged;
- what coordinate and vertical units it claims;
- what provenance and checksum protect it from silent replacement;
- what downstream consumers may use it for;
- what claims remain explicitly unsupported.

This matches the existing MyMoMo style: bridge first, deterministic gate second,
runtime later only when a reproduction or validation target needs it.

## Scope

Create:

- `abm_auto/terrain_bridge.py`
- `tests/test_terrain_bridge.py`
- `docs/reproduce/terrain-bridge/example-heightfield.asc`
- `docs/reproduce/terrain-bridge/example-manifest.json`
- `docs/reproduce/terrain-bridge/STATUS.md`

Modify:

- `abm_auto/evidence_foundry_batch.py`
- `tests/test_evidence_foundry_batch.py`
- `tests/test_evidence_foundry_doctor.py`
- `docs/reproduce/evidence-foundry/batch-registry.json`
- `docs/reproduce/evidence-foundry/BATCH-REPORT.md`
- `docs/reproduce/platform-capabilities/registry.json`
- `tests/test_platform_capabilities.py`

## Manifest Shape

Schema:

`abm-auto/terrain-bridge-manifest/v1`

Required top-level fields:

- `schema`
- `manifest_id`
- `title`
- `terrain_source`
- `coordinate_frame`
- `consumers`
- `boundary_rules`
- `verification`
- `boundary_note`

`terrain_source` requires:

- `kind`
- `path`
- `sha256`
- `provenance`
- `synthetic`

Allowed source kinds in Phase 1:

- `ascii_heightfield`
- `dem_raster`

`coordinate_frame` requires:

- `crs`
- `horizontal_units`
- `vertical_units`
- `vertical_datum`
- `grid_shape`

`grid_shape` is `[rows, cols]` with positive integers. Phase 1 does not parse
full raster formats, but it verifies a committed ASCII heightfield fixture by
shape and checksum.

Each consumer requires:

- `id`
- `domain`
- `role`
- `boundary_note`

Allowed consumer domains:

- `gisabm`
- `future_3d_renderer`
- `physical_process`
- `evidence`
- `platform`

Required boundary rules:

- `no_3d_renderer_claim`
- `no_physical_solver_claim`
- `no_real_world_accuracy_claim`
- `vertical_units_declared`

The top-level `boundary_note` must explicitly include:

- `not a 3D renderer`
- `not a physical simulation certificate`

## Gate

Expose:

- `load_terrain_bridge_manifest(path)`
- `validate_terrain_bridge_manifest(manifest, repo=None)`
- `terrain_bridge_gate(manifest, repo=None) -> tuple[bool, str]`

The gate checks:

- schema;
- required fields;
- allowed source kind;
- repo-relative existing source path;
- SHA-256 checksum;
- positive `grid_shape`;
- ASCII heightfield row/column shape for `ascii_heightfield`;
- consumer shape and allowed domains;
- required boundary rules;
- explicit non-claim boundary note.

The gate does not read GeoTIFF pixels in Phase 1 and does not construct a mesh.
`dem_raster` entries are schema/checksum contracts only until a later real DEM
runtime bridge needs raster parsing.

## Evidence Foundry Integration

Add batch artifact kind:

`terrain_bridge_manifest`

The seed Evidence Foundry batch should include the committed example manifest
and report it as artifact health only.

## Platform Capability Registry

Add:

- key: `terrain_bridge_manifest`
- domain: `platform`
- disposition: `bridge`
- evidence_level: `E0`

Boundary: records terrain exchange readiness; does not imply a 3D engine,
renderer, physical terrain model, or real DEM validity.

## Boundaries

Do not:

- edit base-engine forbidden paths;
- add rendering libraries;
- add Three.js, mesh generation, hydrology, or physics;
- require rasterio/GIS extras for the top-level manifest tests;
- claim real-world terrain accuracy from the synthetic fixture;
- alter Anshuka real-DEM reproduction bundles.

## Test Plan

Add `tests/test_terrain_bridge.py`:

- committed example manifest validates and gate passes;
- checksum mismatch fails;
- absolute or missing source path fails;
- invalid `grid_shape` fails;
- ASCII heightfield shape mismatch fails;
- unknown source kind fails;
- unknown consumer domain fails;
- missing required boundary rule fails;
- weak boundary note fails.

Extend Evidence Foundry tests:

- seed batch includes `terrain_bridge_manifest`;
- batch count increases by one;
- doctor count increases by one.

Extend platform capability tests:

- committed registry includes `terrain_bridge_manifest` as `platform/bridge`.

Final verification:

- `.venv/bin/python -m pytest tests/test_terrain_bridge.py tests/test_evidence_foundry_batch.py tests/test_evidence_foundry_doctor.py tests/test_platform_capabilities.py -q`
- `.venv/bin/python engine_oracle.py --science`
- `.venv/bin/python engine_oracle.py --check`
- forbidden base-engine diff check must be empty.
