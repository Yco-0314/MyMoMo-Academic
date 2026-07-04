# Evacuation Calibration Diagnostics Phase 1

## Summary

Add a small GIS-only diagnostic layer on top of the existing Anshuka evacuation
outcome calibration adapter. The current adapter already proves synthetic
parameter recovery for `belief`; this phase records the post-calibration residual
against the observed `[evac, incap]` target and exposes a deterministic gate that
checks whether calibration actually reduces the outcome gap.

This is calibration instrumentation, not a new evacuation mechanism and not a
retuning of the locked Anshuka real-DEM reproduction.

## Scope

- Add `diagnose_evac_calibration(...)` to `abm_auto/gis/_evac_calibration.py`.
- Add `evac_calibration_diagnostic_gate(...)`.
- Keep using the existing base ABC backend through the existing adapter.
- Do not edit `abm_auto/calibration/` or any base-engine path.
- Do not change the Anshuka reproduction findings, paper verdict, or locked
  predictions.

## API

`diagnose_evac_calibration(observed_stats, priors, fixed, max_sims=200, n_iter=6,
seed=None, residual_tol=5.0) -> dict`

The function:

- calls `run_evac_calibration(...)`;
- replays the best parameters through `EvacOutcomeObjective`;
- reports `observed_stats`, `best_fit_stats`, `residuals`, `mae`, `rmse`,
  `max_abs_error`, `relative_rmse`, `within_tolerance`, and a cautious
  `diagnostic` string;
- preserves `calibration` output for auditability.

`evac_calibration_diagnostic_gate(true_belief=0.55, residual_tol=5.0, ...)`

The gate builds a synthetic observed outcome from known truth, calibrates against
it, and passes only when:

- calibration succeeds;
- the calibrated best fit is within the residual tolerance;
- the recovered `belief` remains close enough to the known value.

Gate text must say what is proven and what is not: it proves the GIS calibration
adapter can reduce observed evacuation-outcome residuals on synthetic truth; it
does not prove the real Anshuka magnitude gaps are solved or that the evacuation
model is a real traffic-flow model.

## Tests

Extend `tests/gis/test_evac_calibration.py`:

- diagnostics return best-fit stats, residual metrics, tolerance flag, and the
  embedded calibration audit output;
- diagnostics reject invalid observed target shape;
- diagnostic gate passes on synthetic truth and includes the boundary wording.

## Verification

Run:

```bash
.venv/bin/python -m pytest tests/gis/test_evac_calibration.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```
