# Observed Raster Repro Pack Design

## Summary

Add a small reproducibility pack for the observed-raster validation/calibration
bridge. The pack standardizes how a local GHSL/WorldPop-style GeoTIFF clip is
described, loaded, validated, and used in deterministic calibration gates.

This phase does not ship or download official GHSL/WorldPop pixels. It provides
the manifest schema, fixture loader, source instructions, and a local test
fixture path so real observed clips can be dropped in without changing runtime
code. Tests use a tiny generated GeoTIFF fixture and label it as local test data,
not official source data.

## Source Strategy

The target real-data workflow is:

1. download an official GHSL or WorldPop raster tile outside the test suite;
2. clip a small city window with existing `data/fixtures/fetch_clip.py` or
   `abm_auto.gis._fixtures.clip_window`;
3. write a manifest beside the clipped GeoTIFF with source URL, dataset label,
   license/attribution, CRS expectation, threshold, and calibration search grid;
4. load the manifest through the new repro adapter;
5. run observed-raster validation/calibration without hidden download,
   reprojection, resampling, or base-engine changes.

## Runtime API

Create `abm_auto/gis/_observed_raster_repro.py`.

- `load_observed_raster_manifest(path)`
  - reads a JSON manifest;
  - resolves `raster_path` relative to the manifest file;
  - validates required fields;
  - returns a plain dict with normalized absolute `raster_path`.
- `load_observed_raster_from_manifest(path)`
  - loads the manifest and calls `load_observed_raster(...)`;
  - source string should combine dataset and source URL for traceability;
  - returns an `ObservedRasterTarget`.
- `calibrate_observed_raster_from_manifest(simulator, manifest_path)`
  - loads observed target;
  - uses `param_grid` and `threshold` from manifest;
  - returns `calibrate_observed_raster(...)` output plus manifest metadata.
- `observed_raster_repro_gate(manifest_path)`
  - loads a manifest-backed local GeoTIFF;
  - runs deterministic row/col calibration;
  - passes only if best params match manifest `expected_best_params` and
    provenance is present.

## Manifest Schema

Required fields:

- `raster_path`: relative or absolute path to a local GeoTIFF;
- `dataset`: non-empty dataset label;
- `source_url`: official or local provenance URL/string;
- `license`: non-empty attribution/license text;
- `threshold`: finite numeric threshold;
- `param_grid`: non-empty numeric grid compatible with existing calibration;
- `expected_best_params`: non-empty numeric dict for the deterministic gate.

Optional fields:

- `description`;
- `crs`;
- `window`;
- `source_download_page`;
- `notes`.

## Data Files

Add `data/fixtures/observed-raster/`.

- `README.md`: exact real-data workflow and caveats.
- `manifest.example.json`: GHSL/WorldPop-style manifest template.
- `test_manifest.json`: tiny local test manifest for automated tests.
- `test_observed.tif`: tiny local test GeoTIFF generated deterministically for
  tests; explicitly not official GHSL/WorldPop data.

## Out Of Scope

- remote download in tests;
- shipping large official tiles;
- claiming synthetic test data is official source data;
- hidden reprojection/resampling;
- vector/network validation;
- Bayesian calibration;
- modifications to `abm_auto/calibration`.

## Success Criteria

- manifest loader resolves local raster paths and rejects malformed manifests;
- manifest-backed observed raster loads through the existing observed bridge;
- manifest-backed calibration selects expected lower-loss parameters;
- repro gate states the boundary: reproducible local observed-raster pack, not
  remote download or Bayesian inference;
- docs tell a human exactly how to replace the test fixture with a real
  GHSL/WorldPop clip.
