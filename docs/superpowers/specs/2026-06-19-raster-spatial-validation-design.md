# Raster Spatial Validation Phase 1 Design

**Status:** Draft for review. **Date:** 2026-06-19. **Repo:** MyMoMo-GIS-Academic.
**Parent:** [ADR-019](../../decisions/ADR-019-gis-abm-platform-vision.md)
(layer D: calibration + spatial validation).

## Goal

Add the first GIS-only spatial validation layer: compare a simulated raster
pattern against an observed raster pattern with deterministic spatial metrics
and a gate. This phase creates the validation seam that later calibration can
optimize against, without changing `abm_auto/calibration/` or the base engine.

## Why Raster First

`run_raster_sir(...)` already returns `final_infected_field`, a raster pattern
with the same shape as the driving `RasterSpace`. That makes raster validation
the smallest useful layer-D cell:

- no edge-id alignment problem, unlike network traffic counts;
- no observed-data I/O format decision yet;
- direct reuse of existing `morans_i`;
- deterministic synthetic tests can prove good/poor spatial matches.

Network traffic-count validation and Bayesian calibration wiring are deferred
until this raster validation seam is stable.

## Architecture

Add `abm_auto/gis/_spatial_validation.py`.

The module is GIS-only and operates on 2-D numpy-compatible raster arrays. It
does not import or modify the base calibration package.

Public API:

```python
def raster_pattern_metrics(simulated, observed, threshold: float = 0.5) -> dict:
    ...

def raster_spatial_loss(metrics: dict) -> float:
    ...

def raster_validation_gate(
    simulated,
    observed,
    threshold: float = 0.5,
    min_jaccard: float = 0.5,
    max_centroid_distance_cells: float = 2.0,
) -> tuple[bool, str]:
    ...
```

### `raster_pattern_metrics`

Converts `simulated` and `observed` to float arrays, validates both are 2-D and
same shape, then thresholds them into binary masks using `value > threshold`.

Returned fields:

- `simulated_total`
- `observed_total`
- `intersection`
- `union`
- `jaccard`
- `precision`
- `recall`
- `simulated_morans_i`
- `observed_morans_i`
- `morans_i_abs_error`
- `centroid_distance_cells`
- `raster_diagonal_cells`

Definitions:

- `jaccard = intersection / union`
- `precision = intersection / simulated_total`
- `recall = intersection / observed_total`
- `centroid_distance_cells` is Euclidean distance between positive-cell
  centroids in row/column cell units.

Empty-denominator policy:

- if both masks are empty, `jaccard` is `1.0`;
- if only simulated is empty, `precision` is `0.0`;
- if only observed is empty, `recall` is `0.0`;
- if either centroid is undefined, `centroid_distance_cells` is `inf`.

The gate rejects empty observed signal, so the permissive both-empty metric
does not become a false validation pass.

### `raster_spatial_loss`

Returns a scalar loss for future calibration adapters:

```text
(1 - jaccard) + morans_i_abs_error + min(centroid_distance_cells, diag) / diag
```

where `diag = metrics["raster_diagonal_cells"]`. If centroid distance is
infinite, the centroid term is `1.0`.

This is intentionally simple and deterministic. It is not presented as a
statistical likelihood or a calibrated policy-validity score.

### `raster_validation_gate`

Passes only when:

- observed raster has at least one positive cell;
- simulated raster has at least one positive cell;
- `jaccard >= min_jaccard`;
- `centroid_distance_cells <= max_centroid_distance_cells`.

The gate description must be careful: it proves a simulated raster pattern
matches an observed raster pattern under deterministic spatial metrics. It does
not prove epidemiological validity, parameter identifiability, or calibration
quality.

## Tests

Create `tests/gis/test_spatial_validation.py`.

Coverage:

- identical clustered rasters produce `jaccard == 1.0`, perfect precision and
  recall, zero centroid distance, and zero Moran's I error;
- shifted observed/simulated clusters have lower Jaccard and nonzero centroid
  distance;
- shape mismatch fails deterministically;
- non-2-D rasters fail deterministically;
- empty observed signal makes `raster_validation_gate` fail;
- a close simulated cluster passes the gate;
- a far simulated cluster fails the gate.

## Documentation

Update `docs/reproduce/coupled-seam/STATUS.md` to record Raster Spatial
Validation Phase 1 as the first layer-D evidence:

- spatial validation is now a metric/gate seam over raster outputs;
- it is not yet Bayesian calibration;
- base calibration remains untouched.

## Out of Scope

- Modifying `abm_auto/calibration/`.
- Running Bayesian calibration over GIS models.
- Loading observed rasters from disk.
- Network traffic-count validation.
- CRS reprojection or raster resampling.
- A new `CoupledModel` abstraction.
- Codegen templates for spatial validation.

## Follow-On Phase

After this phase, a small GIS calibration adapter can wrap
`raster_spatial_loss(...)` as an objective over parameters such as SIR `beta`
and `gamma`, or bridge it into the existing base calibrator through a
GIS-specific summary function. That should be a separate spec because it will
need clearer parameter bounds, simulation budgets, and failure semantics.
