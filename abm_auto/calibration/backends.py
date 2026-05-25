"""Inference backends — the swappable strategy.

Each backend is a free function with the same signature:

    run_xxx(priors, targets, obs_stats, simulator, max_sims) -> CalibrationResult

The orchestrator picks one at runtime. Adding a new algorithm (e.g.
Random Forest regression per Carrella 2021 "No Free Lunch") = adding a
function here, not editing the orchestrator.

Two backends today:
  - run_abc:   numpy-only ABC rejection. Always available.
  - run_pymc:  PyMC SMC for likelihood-free inference. Optional dep.

Convention: both backends report POSTERIOR MEAN as `best_params` (not
single closest sample / MAP). Posterior mean has lower MSE for ABC
(Beaumont 2010, Marin et al. 2012) — single-closest-sample is a poor
estimator because it overweights one random draw.
"""
from __future__ import annotations

import math
from typing import Optional, TYPE_CHECKING

import numpy as np
import pandas as pd

from abm_auto.calibration.types import CalibrationResult

if TYPE_CHECKING:
    from abm_auto.calibration.simulator import SimulatorWrapper


# Optional PyMC — try once at module load; backends.HAS_PYMC tells orchestrator.
try:
    import pymc as pm     # type: ignore
    import arviz as az    # type: ignore
    HAS_PYMC = True
except Exception:
    HAS_PYMC = False


# Acceptance fraction for ABC rejection sampling (top K by distance).
_ABC_TOP_FRACTION = 0.20


# ── ABC rejection (always available) ────────────────────────────────────────


def run_abc(
    priors: dict[str, dict],
    targets: list[str],
    obs_stats: np.ndarray,
    simulator: "SimulatorWrapper",
    max_sims: int,
) -> CalibrationResult:
    """Approximate Bayesian Computation via rejection sampling.

    Samples uniformly from priors, runs the simulator, keeps the
    top _ABC_TOP_FRACTION by distance to observed stats. Posterior
    mean over the accepted samples is reported as best_params.
    """
    param_names = list(priors.keys())
    all_samples: list[tuple[dict, float]] = []

    for i in range(max_sims):
        params = {
            name: float(np.random.uniform(p["min"], p["max"]))
            for name, p in priors.items()
        }
        sim_stats = simulator.simulate(params, targets)
        if sim_stats is None:
            continue
        dist = float(np.linalg.norm(sim_stats - obs_stats))
        all_samples.append((params, dist))

    if not all_samples:
        return CalibrationResult(
            ok=False,
            backend="abc-rejection",
            n_simulator_calls=0,
            best_params={},
            posterior_summary=pd.DataFrame(),
            reason="All simulator runs failed",
        )

    # Keep top fraction by distance
    all_samples.sort(key=lambda x: x[1])
    n_keep = max(1, int(len(all_samples) * _ABC_TOP_FRACTION))
    accepted = all_samples[:n_keep]

    # Posterior summary
    post_df = pd.DataFrame([p for p, _ in accepted], columns=param_names)
    summary = post_df.describe(percentiles=[0.025, 0.5, 0.975]).T

    # Posterior mean as point estimate (better than closest sample for ABC)
    best_params = {name: float(post_df[name].mean()) for name in param_names}

    return CalibrationResult(
        ok=True,
        backend="abc-rejection",
        n_simulator_calls=len(all_samples),
        best_params=best_params,
        posterior_summary=summary,
    )


# ── PyMC SMC (optional) ──────────────────────────────────────────────────────


def run_pymc(
    priors: dict[str, dict],
    targets: list[str],
    obs_stats: np.ndarray,
    simulator: "SimulatorWrapper",
    max_sims: int,
) -> CalibrationResult:
    """Likelihood-free inference via pm.Simulator + sample_smc.

    PyMC SMC drives the simulator and produces a proper posterior. More
    expensive than ABC rejection (SMC's particle filter) but typically
    sharper posteriors for the same simulator-call budget.

    Raises ImportError if PyMC not installed — orchestrator catches this
    and falls back to run_abc.
    """
    if not HAS_PYMC:
        raise ImportError("PyMC not installed")

    draws = min(50, max(20, max_sims // 4))
    param_names = list(priors.keys())
    sim_count = {"n": 0}

    def simulator_fn(rng, *param_values, size=None):
        sim_count["n"] += 1
        params = dict(zip(param_names, [float(v) for v in param_values]))
        sim_stats = simulator.simulate(params, targets)
        if sim_stats is None:
            return obs_stats + 1e6  # large distance → SMC discards
        return sim_stats

    with pm.Model():
        param_vars = [
            pm.Uniform(name, lower=p["min"], upper=p["max"])
            for name, p in priors.items()
        ]
        pm.Simulator(
            "sim",
            simulator_fn,
            params=param_vars,
            distance="gaussian",
            sum_stat="identity",
            epsilon=1.0,
            observed=obs_stats,
        )
        idata = pm.sample_smc(draws=draws, chains=2, progressbar=False)

    summary = az.summary(idata, var_names=param_names)
    best_params = {n: float(summary.loc[n, "mean"]) for n in param_names}

    return CalibrationResult(
        ok=True,
        backend="pymc-smc",
        n_simulator_calls=sim_count["n"],
        best_params=best_params,
        posterior_summary=summary,
    )
