# Anshuka P5 Real-DEM Prior Calibration Phase 1

## Summary

Use the newly added `prior_experience_frac` knob on the real Ba DEM P5 target:
collaboration should have approximately null effect at low/medium/high belief
levels (`|evac(collab on) - evac(collab off)| < 5`), matching the locked P5
criterion.

This phase adds a small, explicit scanner and gate. It does not rewrite the
existing real-DEM verdict bundle and does not claim a new paper reproduction
headline unless a future locked rerun updates the reproduction package.

## Scope

- Add `abm_auto/gis/_anshuka_p5_calibration.py`.
- Evaluate real-DEM P5 collaboration deltas for each belief level.
- Search candidate `prior_experience_frac` values.
- Select the **least restrictive passing prior**: the highest candidate whose
  max absolute collaboration delta is within target.
- Gate against the local Ba DEM when available.
- Keep data dependency explicit; no hidden download or synthetic fallback.

## Non-Goals

- No edit to `docs/reproduce/anshuka-2026-real-dem/verdict-bundle.json`.
- No claim that the original locked run is retroactively changed.
- No calibration to every Anshuka figure or all levers.
- No traffic-flow, congestion, road-routing, or evacuation-validity claim.
- No edits to base-engine paths.

## API

`evaluate_p5_collaboration_deltas(world, prior_experience_frac, n_iter=10, ...)`

Returns per-belief off/on evacuation means, delta, and `max_abs_delta_evac`.

`calibrate_p5_prior_experience(world, candidates=(0.0, 0.25, 0.5, 0.75, 1.0),
target_abs_delta=5.0, ...)`

Returns the baseline default-prior result, all candidate results, and the selected
best candidate.

`p5_prior_experience_real_dem_gate(dem_path="data/anshuka_ba/ba_dem_utm.tif", ...)`

Builds the real world from the local DEM, runs the scan, and passes only if the
default-prior baseline exceeds the target while the selected prior meets it.

Gate text must say this is a real-DEM P5 calibration diagnostic, not a verdict
rewrite.

## Tests

- Real DEM gate passes when `data/anshuka_ba/ba_dem_utm.tif` is present; skip
  explicitly if the local real-data artifact is absent.
- Selection chooses the least restrictive passing prior.
- Missing DEM path fails clearly rather than falling back to synthetic data.

## Verification

Run:

```bash
.venv/bin/python -m pytest tests/gis/test_anshuka_p5_calibration.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```
