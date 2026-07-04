# GIS Spatial Calibration Adapter Phase 1 Design

**Status:** Draft for implementation. **Date:** 2026-06-19. **Repo:**
MyMoMo-GIS-Academic. **Parent:**
[ADR-019](../../decisions/ADR-019-gis-abm-platform-vision.md) layer D
(calibration + spatial validation).

## Goal

Add the first GIS-only calibration adapter over the raster spatial validation
loss. This phase proves that a simulated raster output can be optimized against
an observed raster pattern with deterministic parameter search, without
modifying `abm_auto/calibration/` or any base-engine directory.

## Scope

This phase builds a small grid-search adapter around the existing
`raster_pattern_metrics(...)` and `raster_spatial_loss(...)` functions.

It does not run the base `BayesianCalibrator`, does not load observed rasters
from disk, does not calibrate traffic counts, and does not add codegen
templates. The point is to establish a clean objective seam:

```text
params -> simulator(params) -> simulated raster -> spatial metrics -> scalar loss
```

## Architecture

Add `abm_auto/gis/_spatial_calibration.py`.

Public API:

```python
def evaluate_raster_params(
    simulator,
    observed,
    params: dict[str, float],
    threshold: float = 0.5,
) -> dict:
    ...


def grid_search_raster_calibration(
    simulator,
    observed,
    param_grid: dict[str, list[float]],
    threshold: float = 0.5,
) -> dict:
    ...


def raster_spatial_calibration_gate() -> tuple[bool, str]:
    ...
```

### `evaluate_raster_params`

Runs `simulator(params)` once, compares the returned raster with `observed`,
and returns:

- `params`
- `loss`
- `metrics`
- `simulated`

Validation rules:

- `params` must be a non-empty dict;
- every parameter name must be a non-empty string;
- every parameter value must be a finite `int` or `float`;
- bool values are rejected even though `bool` is a Python `int` subclass;
- simulator output must be accepted by `raster_pattern_metrics`, which means it
  must be 2-D and shape-compatible with `observed`.

The function makes a defensive shallow copy of `params` before passing it to the
simulator and before returning it, so caller mutations do not rewrite recorded
evaluations.

### `grid_search_raster_calibration`

Enumerates the Cartesian product of `param_grid` in deterministic insertion
order. Each candidate calls `evaluate_raster_params(...)`.

Return shape:

- `ok`
- `backend`: always `"gis-raster-grid-search"` when the search runs;
- `best_params`
- `best_loss`
- `best_metrics`
- `evaluations`
- `n_evaluations`
- `reason`

Sorting and tie-breaking:

- primary order: lowest loss;
- tie-breaker: first candidate in deterministic enumeration order;
- `evaluations` preserve enumeration order and include an `rank` field starting
  at zero.

Validation rules:

- `param_grid` must be a non-empty dict;
- every parameter name must be a non-empty string;
- every parameter value list must be non-empty;
- every candidate value must be finite numeric and not bool;
- no hidden random sampling or optimizer state is allowed.

When validation fails, raise `ValueError` with a deterministic message. When a
simulator call itself raises, let that exception propagate; this phase is a
low-level adapter, not a retrying orchestration layer.

### `raster_spatial_calibration_gate`

The gate uses a deterministic synthetic simulator whose parameters map to a
small raster cluster location. It compares an observed cluster against a grid
that includes the correct location and clearly wrong locations.

The gate passes only when:

- the grid search runs at least two candidates;
- `best_params` select the known good location;
- `best_loss` is strictly lower than at least one bad candidate;
- the best candidate has a zero or near-zero spatial loss.

Gate text must be precise: it proves that GIS spatial calibration can choose a
better raster-producing parameter set under deterministic spatial loss. It does
not prove Bayesian posterior quality, identifiability, real-data validity, or
epidemiological validity.

## Tests

Create `tests/gis/test_spatial_calibration.py`.

Coverage:

- `evaluate_raster_params` returns copied params, metrics, loss, and simulated
  raster for a matching cluster;
- grid search finds the known best synthetic parameters;
- evaluation order is deterministic and ties keep the first candidate;
- empty grid, empty parameter values, empty parameter names, bool values,
  non-numeric values, NaN, and inf fail deterministically;
- simulator output with wrong shape or non-2-D shape fails via the spatial
  validation layer;
- simulator receives a defensive params copy;
- `raster_spatial_calibration_gate` passes for the synthetic recovery case;
- a no-effect simulator/grid case fails a helper gate check if one is exposed,
  or is covered by asserting grid search cannot produce an improvement.

## Documentation

Update `docs/reproduce/coupled-seam/STATUS.md`:

- record GIS Spatial Calibration Adapter Phase 1 as the next layer-D cell after
  raster spatial validation;
- say it is deterministic grid-search calibration over spatial loss;
- keep the boundary explicit: base Bayesian calibration remains untouched;
- update the next sequence to coupled codegen templates and self-extension
  gap/halt.

## Out of Scope

- Modifying `abm_auto/calibration/`.
- Importing `BayesianCalibrator` from GIS code.
- Multi-fidelity scheduling.
- Posterior summaries.
- Real observed raster loading.
- Network traffic-count calibration.
- CRS reprojection, resampling, or raster alignment.
- Codegen templates.
- A new `CoupledModel` abstraction.

## Follow-On

After this phase, a later GIS calibration phase can bridge this objective into
the existing base calibration stack by adapting the simulator/summary interface.
That bridge should be a separate spec because it will need lifecycle decisions
around simulation budgets, posterior reporting, and whether GIS outputs should
be summarized as trajectories, raster losses, or mixed spatial-temporal
features.
