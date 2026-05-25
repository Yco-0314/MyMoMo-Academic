"""Shared result type for calibration backends."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class CalibrationResult:
    """What every inference backend returns.

    Carries enough info for the orchestrator to (a) decide if calibration
    succeeded, (b) write a posterior summary, (c) apply best_params back to
    the scenario CSV.
    """
    ok: bool
    backend: str                   # "abc-rejection" | "pymc-smc" | "skipped" | ...
    n_simulator_calls: int
    best_params: dict[str, float]  # point estimate (posterior mean by convention)
    posterior_summary: pd.DataFrame  # one row per param, columns: count/mean/std/2.5%/50%/97.5%
    reason: str = ""               # populated when ok=False
