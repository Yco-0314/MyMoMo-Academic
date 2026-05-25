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

# Optional sklearn — used by the Random Forest backend (Carrella 2021).
try:
    from sklearn.ensemble import RandomForestRegressor  # type: ignore
    HAS_SKLEARN = True
except Exception:
    HAS_SKLEARN = False


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


# ── Random Forest regression (optional) ─────────────────────────────────────


def run_rf(
    priors: dict[str, dict],
    targets: list[str],
    obs_stats: np.ndarray,
    simulator: "SimulatorWrapper",
    max_sims: int,
) -> CalibrationResult:
    """Posterior-mean inference via Random Forest regression.

    Adapted from Carrella 2021 "No Free Lunch in ABM Calibration" — RF
    consistently outperformed ABC in his cross-validated study. Method:

      1. Draw N parameter vectors from the priors (uniform).
      2. Run the simulator at each, get a summary-stat vector.
      3. Train a RandomForestRegressor: features = stats, targets = params.
      4. Predict params from the OBSERVED stats → point estimate.
      5. Quantify uncertainty via per-tree predictions (the RF ensemble
         gives a sample over predictions; report its mean/std/CI).

    Advantages over ABC rejection:
      - No acceptance threshold to tune (no top-K cutoff).
      - Uses ALL successful simulator calls, not just top 20%.
      - Naturally handles non-monotonic param→stat relationships.

    Raises ImportError when sklearn unavailable — orchestrator should check
    HAS_SKLEARN first and fall back to run_abc.
    """
    if not HAS_SKLEARN:
        raise ImportError("scikit-learn not installed")

    param_names = list(priors.keys())
    X: list[np.ndarray] = []   # summary stats per successful sim
    Y: list[list[float]] = []  # corresponding params

    for _ in range(max_sims):
        params = {
            name: float(np.random.uniform(p["min"], p["max"]))
            for name, p in priors.items()
        }
        sim_stats = simulator.simulate(params, targets)
        if sim_stats is None:
            continue
        X.append(sim_stats)
        Y.append([params[n] for n in param_names])

    if len(X) < max(5, len(param_names) + 1):
        return CalibrationResult(
            ok=False,
            backend="rf-regression",
            n_simulator_calls=len(X),
            best_params={},
            posterior_summary=pd.DataFrame(),
            reason=f"Too few successful sims ({len(X)}) to train RF",
        )

    X_arr = np.array(X)
    Y_arr = np.array(Y)

    # Train one RF regressor per parameter (avoids correlated multi-output).
    # 100 trees is a sane default; min_samples_leaf=2 prevents overfit on small N.
    posteriors_per_param: dict[str, np.ndarray] = {}
    for j, name in enumerate(param_names):
        rf = RandomForestRegressor(
            n_estimators=100,
            min_samples_leaf=2,
            random_state=None,  # let calling RNG drive
            n_jobs=1,
        )
        rf.fit(X_arr, Y_arr[:, j])
        # Per-tree predictions on observed stats → posterior sample
        per_tree = np.array([t.predict(obs_stats.reshape(1, -1))[0] for t in rf.estimators_])
        posteriors_per_param[name] = per_tree

    # Build posterior summary in the same shape as ABC / PyMC for downstream code
    post_df = pd.DataFrame(posteriors_per_param)
    summary = post_df.describe(percentiles=[0.025, 0.5, 0.975]).T

    # Point estimate: posterior mean across trees
    best_params = {n: float(posteriors_per_param[n].mean()) for n in param_names}

    return CalibrationResult(
        ok=True,
        backend="rf-regression",
        n_simulator_calls=len(X),
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
