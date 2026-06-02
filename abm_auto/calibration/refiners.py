"""Refinement-stage optimization adapters.

A refiner takes the screening stage's best point estimate and runs a local
deterministic search downhill from there. This addresses the structural
limitation of screening-only calibration: with N=100 uniform prior draws,
even the closest sample sits ~10-20 distance from the true minimum (the
basin is small relative to the prior box). Local search closes that gap
in ~30-50 simulator calls.

Convention: refiners share the same signature shape as backends so the
orchestrator can swap them freely:

    refine_xxx(start_params, priors, targets, obs_stats, simulator, max_evals)
        -> CalibrationResult

Today: `nelder_mead_refine` is the only adapter. Future candidates:
BFGS (requires gradient via finite differences), Powell (also bounded),
CMA-ES (heavier, useful at higher dimensions).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from abm_auto.calibration.types import CalibrationResult

if TYPE_CHECKING:
    from abm_auto.calibration.simulator import SimulatorWrapper


def nelder_mead_refine(
    start_params: dict[str, float],
    priors: dict[str, dict],
    targets: list[str],
    obs_stats: np.ndarray,
    simulator: "SimulatorWrapper",
    max_evals: int = 50,
) -> CalibrationResult:
    """Local minimization via scipy Nelder-Mead with prior bounds.

    Walks downhill on ||sim_stats - obs_stats|| from start_params, clipped
    to the prior box. Uses scipy 1.7+ bounded NM with `adaptive=True` (Gao
    & Han 2012), which scales simplex moves with dimensionality and performs
    better than classic NM in 3+ dimensions.

    Tolerances (xatol, fatol) are deliberately loose: the simulator is
    stochastic so tightening below the noise floor wastes evaluations.
    `max_evals` is the primary stopping criterion.

    If start_params lies outside the prior bounds (defensive: screening
    sometimes returns boundary samples), it is clipped before NM begins.
    """
    from scipy.optimize import minimize

    param_names = list(priors.keys())
    bounds = [(float(priors[n]["min"]), float(priors[n]["max"])) for n in param_names]
    x0 = np.array([float(start_params[n]) for n in param_names], dtype=float)
    for i, (lo, hi) in enumerate(bounds):
        x0[i] = max(lo, min(hi, x0[i]))

    sim_count = {"n": 0}

    def objective(x: np.ndarray) -> float:
        sim_count["n"] += 1
        params = dict(zip(param_names, [float(v) for v in x]))
        sim_stats = simulator.simulate(params, targets)
        if sim_stats is None:
            return 1e9
        return float(np.linalg.norm(sim_stats - obs_stats))

    result = minimize(
        objective,
        x0,
        method="Nelder-Mead",
        bounds=bounds,
        options={
            "maxfev": max_evals,
            "xatol": 0.05,
            "fatol": 1.0,
            "adaptive": True,
        },
    )

    best_params = {n: float(v) for n, v in zip(param_names, result.x.tolist())}

    # Build a degenerate posterior_summary (refiner returns a point, not a
    # distribution). Orchestrator typically carries screening's posterior
    # forward; this is a fallback for direct calls.
    summary = pd.DataFrame(
        {n: {"mean": best_params[n], "std": 0.0,
             "2.5%": best_params[n], "50%": best_params[n], "97.5%": best_params[n]}
         for n in param_names}
    ).T

    return CalibrationResult(
        ok=True,
        backend="nelder-mead",
        n_simulator_calls=sim_count["n"],
        best_params=best_params,
        posterior_summary=summary,
    )
