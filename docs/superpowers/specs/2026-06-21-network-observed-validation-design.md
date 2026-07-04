# Network Observed Validation Design

## Summary

Add a minimal edge-level observed target for GeoNetwork outputs. This extends
layer-D beyond raster validation by comparing simulated edge values, such as
road-model `edge_load`, against observed edge values, such as traffic counts
after a separate map-matching step.

This phase does not download traffic data, parse shapefiles, map-match count
stations, model traffic flow, or modify the base engine. It provides the core
network validation and deterministic calibration seam over edge-keyed values.

## Runtime API

Create `abm_auto/gis/_network_validation.py`.

- `ObservedNetworkTarget`
  - stores normalized undirected edge keys and observed numeric values;
  - records `source`, `dataset`, and `metric` provenance;
  - exposes `provenance()`.
- `observed_network_from_mapping(edge_values, source, dataset, metric="edge_load")`
  - builds an observed target from a mapping.
- `network_edge_metrics(simulated, observed)`
  - compares simulated edge values against the observed subset;
  - returns coverage, MAE, RMSE, relative RMSE, bias, and top-edge match.
- `network_edge_loss(metrics)`
  - returns a scalar deterministic loss.
- `network_validation_gate(simulated, observed, ...)`
  - passes when observed edges are covered and error is below thresholds.
- `evaluate_network_params(simulator, observed, params)`
  - runs one parameter set through `simulator(params) -> edge_values`.
- `grid_search_network_calibration(simulator, observed, param_grid)`
  - deterministic grid search over `network_edge_loss`.
- `network_observed_validation_gate()`
  - proves calibration can select lower-loss edge-level parameters.

## Edge Key Rules

Edge keys are undirected and normalized with a stable `repr` sort. This supports
plain labels such as `"A"` and tuple node ids from `GeoNetwork`. The normalized
key is always a 2-tuple.

Observed validation evaluates only observed edges. Extra simulated edges are
allowed. Missing observed edges fail the gate and are reported explicitly.

## Out Of Scope

- count-station to edge map matching;
- real OSM/DFT/NYC TLC ingestion;
- CSV/GeoPackage loaders;
- congestion capacity/BPR calibration;
- dynamic traffic-flow validity;
- codegen templates;
- full `BayesianCalibrator.run` workspace flow.

## Success Criteria

- matching edge values produce zero loss;
- shifted edge values produce positive error and fail strict gates;
- missing observed edges are reported;
- deterministic grid search selects lower-loss network edge parameters;
- docs record that this is the first vector/network observed validation seam,
  not real traffic-count ingestion.
