# Validation And Calibration Codegen Template Phase 1 Design

**Date:** 2026-06-20
**Status:** Approved for implementation
**Scope:** GIS-only raster spatial validation/calibration codegen

## Summary

Register and render two existing layer-D GIS cells:

- `raster_spatial_validation`
- `raster_spatial_calibration`

Both already have deterministic runtime functions and gates. This phase adds
them to the GIS codegen capability registry and emits synthetic runnable
templates. It does not modify or import the base `abm_auto/calibration/`
package.

## Goals

- Register `raster_spatial_validation` as renderable.
- Register `raster_spatial_calibration` as renderable.
- Render a synthetic validation model that calls `raster_pattern_metrics`,
  `raster_spatial_loss`, and `raster_validation_gate`.
- Render a synthetic calibration model that calls
  `grid_search_raster_calibration`, `raster_spatial_loss`, and
  `raster_spatial_calibration_gate`.
- Update extractor, fidelity gate, self-extension preflight, and status docs.

## Non-Goals

- No base calibration package changes.
- No Bayesian posterior inference.
- No observed raster file I/O.
- No calibration scheduler, multi-fidelity execution, or real study dataset.
- No `CoupledModel` extraction.
- No edits under `abm_auto/runtime`, `abm_auto/codegen`,
  `abm_auto/calibration`, `abm_auto/agents`, or `abm_auto/pipeline`.

## Architecture

The validation template builds matching synthetic 2x2 clusters inside 6x6
rasters, computes metrics/loss, and verifies with `raster_validation_gate`.

The calibration template builds the same target cluster and runs a deterministic
grid search over row/col candidates. It verifies with
`raster_spatial_calibration_gate`, which states the limitation: deterministic
GIS spatial-loss calibration only, not Bayesian inference or real-data
validation.

## Testing

Update tests for:

- registry entries and renderable list;
- explicit spec validation for both capabilities;
- rendered structure and runnable `PASS` output;
- fidelity gate pass and required-token failure for both templates;
- extractor prompt and explicit extraction;
- self-extension preflight renderable classification.

Final verification:

```bash
.venv/bin/python -m pytest tests/gis/test_capabilities.py tests/gis/test_codegen.py tests/gis/test_codegen_gate.py tests/gis/test_extractor.py tests/gis/test_self_extension.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

## Expected Status Update

`docs/reproduce/coupled-seam/STATUS.md` should record validation/calibration
codegen as synthetic layer-D templates. Calibration remains GIS-only deterministic
grid search over spatial loss.
