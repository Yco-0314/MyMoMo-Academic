# Observed Raster Calibration Bridge Design

## Summary

Add a minimal GIS-only bridge from real observed raster files into the existing
raster spatial validation and calibration adapters. The bridge loads or wraps an
observed GeoTIFF/RasterSpace/RasterField, preserves provenance metadata, and
passes only the observed array into the existing deterministic metrics and grid
search.

This is the first real-data step for ADR-019 layer D. It does not download
remote data, resample rasters, use the base Bayesian calibrator, add network
traffic calibration, or change codegen templates.

## Data Source Strategy

The first practical observed targets are GHSL or WorldPop style raster clips:

- they are naturally raster-shaped;
- they carry CRS, transform, nodata, and source metadata;
- they match the current `raster_pattern_metrics(...)` API after clipping;
- they avoid map-matching and vector aggregation work required by traffic counts.

The runtime should accept local observed rasters only. Fetching and clipping
official source tiles remains an external reproducibility step, documented by
metadata rather than hidden inside calibration.

## Runtime API

Create `abm_auto/gis/_observed_raster_bridge.py`.

- `ObservedRasterTarget`
  - immutable metadata record with `data`, `transform`, `crs`, `nodata`,
    `source`, and `dataset`.
  - stores a defensive float array copy.
- `observed_raster_from_array(...)`
  - constructs an observed target from an in-memory array and explicit georef.
- `observed_raster_from_field(...)`
  - wraps a `RasterField`.
- `observed_raster_from_space(...)`
  - wraps a `RasterSpace`.
- `load_observed_raster(path, band=1, source=None, dataset="observed-raster")`
  - calls existing `load_raster(...)`, then wraps the field.
- `validate_observed_raster(simulated, observed, ...)`
  - unwraps simulated raster data and calls `raster_pattern_metrics`,
    `raster_spatial_loss`, and `raster_validation_gate`.
- `calibrate_observed_raster(simulator, observed, param_grid, ...)`
  - calls `grid_search_raster_calibration` and attaches observed-source metadata.
- `observed_raster_bridge_gate()`
  - deterministic gate showing a provenance-bearing observed target changes the
    selected grid-search parameter from worse candidates to the observed cluster.

## Validation Rules

- observed data must be 2-D;
- source and dataset labels must be non-empty strings;
- no silent reprojection, clipping, masking, or resampling;
- simulated/observed shape compatibility remains enforced by
  `raster_pattern_metrics`;
- provenance metadata must survive validation and calibration outputs.

## Out Of Scope

- remote downloads;
- committing large GHSL/WorldPop tiles;
- vector/network validation;
- traffic-count map matching;
- flood extent validation;
- Bayesian posterior inference;
- modifying `abm_auto/calibration`.

## Success Criteria

- a temp GeoTIFF can be loaded as an observed raster target with provenance;
- validation against that observed target returns metrics, scalar loss, gate
  result, and provenance;
- calibration against that observed target selects the lower-loss parameters;
- a gate states this is a real observed-raster bridge, not remote-data download
  or Bayesian calibration;
- GIS and base-engine zero-change checks remain green.
