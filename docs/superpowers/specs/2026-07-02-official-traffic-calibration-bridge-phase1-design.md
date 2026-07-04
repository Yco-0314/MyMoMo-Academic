# Official Traffic Calibration Bridge Phase 1

## Summary

Add a small GIS-only bridge that turns the existing Seattle SDOT official
count-to-centerline match pack into an `ObservedNetworkTarget`, then feeds that
target into the existing deterministic network calibration grid search.

This closes the gap between "official count points match official centerline
edges" and "official edge observations can drive a calibration/validation
objective." It does not claim traffic-flow validity, congestion calibration,
capacity inference, or production map matching.

## Scope

Phase 1 is a bridge and gate:

- load the existing Seattle centerline match manifest;
- verify the existing centerline match report passes;
- convert matched observed edge values into an `ObservedNetworkTarget`;
- run `grid_search_network_calibration(...)` with a small default demand-scale
  simulator;
- report calibration diagnostics, best parameters, losses, source provenance,
  station-to-street diagnostics, and boundary text.

The default simulator is deliberately simple:

```text
simulated_edge_value(edge) = observed_edge_value(edge) * demand_scale
```

It exists only to prove the official observed target can be consumed by the
network calibration seam. Callers can pass a custom simulator for future
traffic-model smoke tests.

## Key Changes

- Add `abm_auto/gis/_official_traffic_calibration.py`.
- Reuse:
  - `_official_centerline_match.official_centerline_edge_match_report`;
  - `_network_validation.observed_network_from_mapping`;
  - `_network_validation.grid_search_network_calibration`.
- Add `official_traffic_calibration_report(...)`.
- Add `official_traffic_calibration_gate(...)`.
- Update ADR-019 coupled-seam docs to record this as a layer-D real-data
  calibration bridge.

## API

```python
official_traffic_observed_target_from_centerline_match(
    manifest_path=SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
) -> dict
```

Returns:

- `observed`: `ObservedNetworkTarget`
- `centerline_report`: structured centerline match report
- `station_streets`
- `station_objectids`

```python
official_traffic_calibration_report(
    manifest_path=SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
    param_grid=None,
    simulator=None,
) -> dict
```

Defaults:

- `param_grid={"demand_scale": [0.5, 1.0, 1.5]}`
- `simulator=None` uses the proportional demand-scale simulator.

Returns a structured report with:

- `ok`
- `reason`
- `observed_provenance`
- `centerline_diagnostics`
- `station_streets`
- `station_objectids`
- `calibration`
- `best_params`
- `best_loss`
- `loss_improvement`
- `boundary_note`

```python
official_traffic_calibration_gate(...) -> tuple[bool, str]
```

Passes only when:

- centerline match report is OK;
- calibration grid has at least one non-best candidate;
- best params select `demand_scale=1.0` for the default simulator;
- best loss is zero;
- best metrics cover all observed edges.

## Non-Goals

- No new official data download.
- No full-city Seattle data.
- No observed traffic-flow validity claim.
- No congestion calibration claim.
- No capacity, BPR, speed, or assignment model.
- No hidden CRS reprojection.
- No edits under `abm_auto/runtime`, `abm_auto/codegen`,
  `abm_auto/calibration`, `abm_auto/agents`, or `abm_auto/pipeline`.

## Tests

- New `tests/gis/test_official_traffic_calibration.py`.
- Test that the observed target preserves official Seattle provenance and edge
  count.
- Test that the default demand-scale calibration selects `demand_scale=1.0` and
  reports positive improvement over worse candidates.
- Test that a custom simulator/grid can be passed through and evaluated.
- Test that a failing centerline match manifest returns a structured failure
  before calibration.
- Test that the gate passes with careful boundary text.

## Verification

- Target tests:
  `.venv/bin/python -m pytest tests/gis/test_official_traffic_calibration.py tests/gis/test_official_centerline_match.py tests/gis/test_network_validation.py -q`
- Full GIS:
  `.venv/bin/python -m pytest tests/gis -q`
- Oracles:
  `.venv/bin/python engine_oracle.py --science`
  `.venv/bin/python engine_oracle.py --check`
- Base suite:
  `.venv/bin/python -m pytest tests/ -q --ignore=tests/gis`
- Forbidden base-engine diff:
  `git diff --name-only <base>..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline`
