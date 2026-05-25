"""Re-export shim.

The implementation was decomposed (2026-05-25) from a 400-line god class
into the `abm_auto.calibration` package — see that package's README for
the new module layout (backends / priors / simulator / posterior + thin
orchestrator). This file remains so existing imports continue to work::

    from abm_auto.agents.bayesian_calibrator import BayesianCalibrator, CalibrationResult

Both symbols are now defined in `abm_auto.calibration`; the names are
identical, the public signature `BayesianCalibrator(client, workspace).run(
executor, spec, max_sims) -> CalibrationResult` is unchanged.
"""
from abm_auto.calibration import BayesianCalibrator, CalibrationResult

__all__ = ["BayesianCalibrator", "CalibrationResult"]
