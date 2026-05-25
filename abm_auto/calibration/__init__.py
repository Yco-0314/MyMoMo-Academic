"""
abm_auto.calibration — Bayesian parameter calibration package.

Decomposed (2026-05-25) from a 400-line BayesianCalibrator god class into
4 thin modules + orchestrator. Each piece has one responsibility and is
independently testable:

  backends.py  — Inference algorithms (ABC, PyMC SMC). Pure functions.
                 Adding a new algorithm (e.g. Random Forest per Carrella
                 2021) = adding a function, not editing the orchestrator.
  priors.py    — Building uniform priors from spec + scenario CSV.
                 Honours story-declared (min, max) over CSV-inferred ±50%.
  simulator.py — SimulatorWrapper. Stateful adapter: knows the workspace,
                 owns a run_id counter, exposes simulate(params) → stats.
  posterior.py — Output writing: posterior_summary.csv, best_params.json,
                 LLM markdown report, final validation sim.
  calibrator.py — BayesianCalibrator. ~80-line orchestrator that wires
                 the 4 modules together. Subclasses BaseAgent so it can
                 use self.call_llm for the calibration report.

Public surface (unchanged from the legacy single-file module):
  from abm_auto.calibration import BayesianCalibrator, CalibrationResult
"""
from abm_auto.calibration.types import CalibrationResult
from abm_auto.calibration.calibrator import BayesianCalibrator

__all__ = ["BayesianCalibrator", "CalibrationResult"]
