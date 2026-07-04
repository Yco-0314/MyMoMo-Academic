# GIS Base Calibration Objective Bridge Design

## Summary

Add a GIS-only adapter that exposes raster spatial validation loss as a
base-calibration-compatible simulator objective. Existing base calibration
backends consume simulators through `simulate(params, targets) -> np.ndarray`.
The bridge returns a one-dimensional statistic, `[spatial_loss]`, and pairs it
with observed stats `[0.0]`.

This proves the base calibration machinery can optimize GIS spatial loss without
editing `abm_auto/calibration/`.

## Architecture

Create `abm_auto/gis/_calibration_objective_bridge.py`.

The core object is `RasterSpatialLossObjective`:

- owns a raster-producing simulator callable;
- owns an observed raster target or array;
- implements `simulate(params, targets)` with the same shape expected by base
  calibration backends;
- delegates all loss calculation to existing `evaluate_raster_params(...)`;
- records deterministic evaluation metadata for inspection.

The module also exposes small helper functions:

- `raster_spatial_loss_targets() -> ["spatial_loss"]`;
- `raster_spatial_loss_observed_stats() -> np.array([0.0])`;
- `make_raster_spatial_loss_objective(...)`;
- `run_base_abc_raster_spatial_calibration(...)`;
- `base_calibration_objective_bridge_gate()`.

`run_base_abc_raster_spatial_calibration(...)` calls the existing
`abm_auto.calibration.backends.run_abc(...)` with the objective simulator. It
returns a GIS dict that includes the raw `CalibrationResult`, best spatial loss,
best params, targets, observed stats, and evaluation records.

## Why This Shape

The base calibration package already optimizes `||sim_stats - obs_stats||`.
By making `sim_stats = [spatial_loss]` and `obs_stats = [0.0]`, GIS spatial
calibration plugs into that contract with no base changes.

This is intentionally not a new general calibrator and not a change to
`BayesianCalibrator.fit`. It is an adapter proving compatibility.

## Validation Rules

- `targets` must be `["spatial_loss"]` when provided;
- `params` validation is delegated to existing spatial calibration validation;
- observed raster shape compatibility is delegated to existing raster metrics;
- optional seeded ABC calls restore NumPy random state after running;
- failed base backend results are reported without hiding the base reason.

## Out Of Scope

- modifying `abm_auto/calibration/`;
- full `BayesianCalibrator.run(...)` workspace artifact flow;
- RF/PyMC orchestration;
- base posterior report generation;
- vector/network calibration;
- remote observed data download;
- hidden raster resampling/reprojection.

## Success Criteria

- a GIS spatial-loss objective can be passed to base calibration functions that
  call `simulate(params, targets)`;
- matching raster parameters return `[0.0]`, shifted parameters return a larger
  one-dimensional statistic;
- seeded base ABC selects parameters with lower spatial loss than bad candidates;
- the gate states the boundary: base backend consumed GIS spatial loss, but base
  calibration source was not modified and this is not full pipeline calibration.
