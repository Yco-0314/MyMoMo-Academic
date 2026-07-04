# NetLogo GIS Parity — Focal (Phase 2) — Design Spec

**Status:** Draft. **Date:** 2026-06-22. **Repo:** MyMoMo-GIS-Academic.
**Parent:** [ADR-019](../../decisions/ADR-019-gis-abm-platform-vision.md);
companion to [Phase 1 topology](2026-06-22-netlogo-parity-topology-design.md)
(branch `feat/netlogo-parity-topology`, ready for review). This phase ships on
its own independent branch off `main`.

## Why

NetLogo's GIS extension exposes raster focal operations we currently lack:
`gis:convolve` (kernel focal stat), `gis:resample` (re-grid with sampling method),
`gis:raster-sample` (point or box). We only have `value_at` + per-edge max
sampling. Adding these closes a second NetLogo parity gap and feeds the
mechanism library (diffusion, terrain analysis, focal hot-spot detection).

## Hard constraints

1. Zero-change to `abm_auto/runtime/`, `codegen/`, `calibration/`, `agents/`,
   `pipeline/`. Additive only.
2. **No new dependency.** `scipy.ndimage.convolve` is already available
   (scipy 1.17.1 confirmed at branch creation).
3. Lazy-import `scipy` inside `_focal.py` so the base import stays light.
4. **No conflict with Codex's `codex/real-data-validation-pack-v2*` branches
   or with `feat/netlogo-parity-topology`.** This work lands on a separate
   `feat/netlogo-parity-focal` branched off `main` (14e668a).
5. Predictions locked: every test asserts a known-kernel-on-known-field gives
   the known answer; a no-op kernel returns the field unchanged.

## Scope (this branch ships)

A new module `abm_auto/gis/_focal.py` with three pure functions on `RasterField`:

### F1 `convolve(field, kernel, mode='reflect') -> RasterField`
Wraps `scipy.ndimage.convolve` over `field.data`; preserves `transform`, `crs`,
`nodata`. `mode` covers edge handling ('reflect' default, 'constant', 'nearest',
'wrap'). NaN-aware path: if `nodata` is set, nodata cells participate as zeros
in the sum and are propagated back to the output (the simplest, deterministic
choice; richer nodata-as-NaN handling is a Phase 2.1 follow-up if needed).

### F2 `resample(field, new_width, new_height, method='nearest') -> RasterField`
Returns a new `RasterField` of shape `(new_height, new_width)` covering the
**same world envelope** as the input. Methods: `'nearest'` (NetLogo default for
discrete data) and `'bilinear'` (continuous data). Affine transform is rescaled
so that pixel-centre world coordinates of the corners match. Resampling to the
same shape with `'nearest'` is byte-identical to the input (the identity check).

### F3 `raster_sample(field, geom) -> float`
Returns the raster value sampled at a `(x, y)` point (uses `world_to_cell`) OR
the **mean** value across an envelope `(xmin, ymin, xmax, ymax)`. NetLogo's
`gis:raster-sample` accepts both forms; we mirror that. Out-of-bounds returns
the field's `nodata` (or `nan` if `nodata is None`).

### F4 `focal_gate(field) -> (bool, str)`
Deterministic signature pinning the focal-operator contract:
1. **identity convolution**: convolving with a 1-cell kernel `[[1]]` returns the
   input array exactly;
2. **mean smoothing reduces variance**: a 3×3 mean kernel on a noisy field
   strictly lowers variance;
3. **resample-to-same-shape is identity**: `resample(field, W, H, 'nearest')`
   with the original `(W, H)` returns the input array exactly.

The gate must FAIL on a broken implementation (e.g. one that returns the kernel
sum instead of the convolved field).

## Decomposition (TDD, bite-sized)

1. F1 convolve + identity + mean-smoothing tests
2. F2 resample + identity + downsample-shape test
3. F3 raster_sample (point + envelope + out-of-bounds)
4. F4 focal_gate (passes on real, fails on broken stub)
5. STATUS.md update (no new adapter row — these are operators on the existing
   raster layer, not a new coupling cell)

## Validation

```
.venv/bin/python -m pytest tests/gis/test_focal.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline   # must be EMPTY
```

## Non-goals

- No new coupling adapter / new STATUS row (focal ops live next to existing
  raster operators, not as a new cross-layer cell).
- No registry / codegen template for focal operations (deferred — keep PR focused).
- No real GIS data; synthetic rasters only.
- No `nodata=NaN` math (deferred). nodata cells participate as zeros in convolve.
- No `apply-coverage` (that is Phase 3, separate branch).
- No edits to `feat/netlogo-parity-topology` or
  `codex/real-data-validation-pack-v2*`.
