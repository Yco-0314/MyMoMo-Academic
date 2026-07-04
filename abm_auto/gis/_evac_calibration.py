"""ADR-024 ladder #5 — outcome calibration for the Anshuka evacuation model.

Wires the evacuation OUTCOME (evac / incap counts) into the base ABC calibrator (a
Bayesian-posterior backend, stronger than grid-search) through the same
``simulate(params, targets) -> stats`` contract as ``_calibration_objective_bridge`` —
WITHOUT editing ``abm_auto/calibration/``.

Honest scope (per ADR-024 D3 step 5, Option A): this is the calibration CAPABILITY plus
its **parameter-recovery proof**, NOT a tuning of the candidate-#10 reproduction to the
paper (that would overfit the locked validation set and undermine the EARNED result). It
answers "is parameter X identifiable from evacuation outcomes?" so that, in the L1 engine,
a reproduction can calibrate to a paper's STATED targets and a residual MISS is
attributable to the paper, not to under-calibration.

Additive GIS module. Zero change to runtime/codegen/calibration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from abm_auto.calibration import backends
from abm_auto.gis._anshuka_2026 import mean_outcome

_TARGETS = ["evac", "incap"]


@dataclass
class EvacOutcomeObjective:
    """Base-calibration-compatible objective: params -> [evac, incap] outcome stats.

    ``fixed`` holds the non-calibrated scenario knobs (alarm_t, onset_steps, collaboration,
    n_agents, max_steps, and any lever held constant). Calibrated params (e.g. belief,
    mobility_good_frac) come in through ``simulate``."""

    fixed: dict
    n_iter: int = 6
    base_seed: int = 0
    evaluations: List[dict] = field(default_factory=list)

    @property
    def n_calls(self) -> int:
        return len(self.evaluations)

    def simulate(self, params: dict, targets=None) -> np.ndarray:
        if targets is not None and list(targets) != _TARGETS:
            raise ValueError("targets must be ['evac', 'incap']")
        kw = dict(self.fixed)
        kw["belief"] = float(params["belief"])
        if "mobility_good_frac" in params:
            kw["mobility_good_frac"] = float(params["mobility_good_frac"])
        r = mean_outcome(n_iter=self.n_iter, base_seed=self.base_seed, **kw)
        stats = np.array([r["evac"], r["incap"]], dtype=float)
        self.evaluations.append({"params": dict(params), "stats": stats.tolist()})
        return stats


def _with_optional_seed(seed, fn):
    if seed is None:
        return fn()
    state = np.random.get_state()
    try:
        np.random.seed(int(seed))
        return fn()
    finally:
        np.random.set_state(state)


def _as_observed_stats(observed_stats) -> np.ndarray:
    obs = np.asarray(observed_stats, dtype=float)
    if obs.shape != (2,):
        raise ValueError("observed_stats must be a length-2 [evac, incap] vector")
    if not np.all(np.isfinite(obs)):
        raise ValueError("observed_stats must contain finite values")
    return obs


def run_evac_calibration(
    observed_stats,
    priors: dict,
    fixed: dict,
    max_sims: int = 200,
    n_iter: int = 6,
    seed: Optional[int] = None,
) -> dict:
    """Calibrate evacuation-model params to an observed [evac, incap] via base ABC.

    ``priors`` is ``{param: {"min": ..., "max": ...}}``. Returns the best params + the
    backend result, without modifying base calibration code."""
    objective = EvacOutcomeObjective(fixed=fixed, n_iter=n_iter, base_seed=0)
    obs = _as_observed_stats(observed_stats)

    def run():
        return backends.run_abc(priors, _TARGETS, obs, objective, max_sims)

    res = _with_optional_seed(seed, run)
    return {
        "ok": bool(res.ok),
        "backend": f"evac-outcome+{res.backend}",
        "best_params": dict(res.best_params),
        "n_simulator_calls": res.n_simulator_calls,
        "reason": res.reason,
        "objective_evaluations": list(objective.evaluations),
        "result": res,
    }


def diagnose_evac_calibration(
    observed_stats,
    priors: dict,
    fixed: dict,
    max_sims: int = 200,
    n_iter: int = 6,
    seed: Optional[int] = None,
    residual_tol: float = 5.0,
) -> dict:
    """Run outcome calibration and report the post-calibration residual.

    This is a diagnostic wrapper around ``run_evac_calibration``. It answers whether
    the calibrated best parameter set actually matches the observed evacuation outcome
    within a declared tolerance. It does not change the model or fit the locked real
    Anshuka reproduction.
    """
    if residual_tol < 0:
        raise ValueError("residual_tol must be non-negative")
    obs = _as_observed_stats(observed_stats)
    calibration = run_evac_calibration(
        obs,
        priors,
        fixed,
        max_sims=max_sims,
        n_iter=n_iter,
        seed=seed,
    )
    if not calibration["ok"]:
        return {
            "ok": False,
            "calibration": calibration,
            "observed_stats": obs.tolist(),
            "best_fit_stats": [],
            "residuals": [],
            "mae": float("inf"),
            "rmse": float("inf"),
            "max_abs_error": float("inf"),
            "relative_rmse": float("inf"),
            "within_tolerance": False,
            "diagnostic": (
                "calibration failed before residual diagnosis; synthetic adapter evidence only, "
                "not a real Anshuka reproduction fix"
            ),
        }

    replay = EvacOutcomeObjective(fixed=fixed, n_iter=n_iter, base_seed=0)
    best_fit = replay.simulate(calibration["best_params"])
    residuals = best_fit - obs
    abs_residuals = np.abs(residuals)
    mae = float(np.mean(abs_residuals))
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    max_abs_error = float(np.max(abs_residuals))
    n_agents = float(fixed.get("n_agents", max(1.0, float(np.sum(obs)))))
    relative_rmse = rmse / max(1.0, n_agents)
    within_tolerance = max_abs_error <= float(residual_tol)
    status = "within" if within_tolerance else "outside"
    return {
        "ok": bool(within_tolerance),
        "calibration": calibration,
        "observed_stats": obs.tolist(),
        "best_fit_stats": best_fit.tolist(),
        "residuals": residuals.tolist(),
        "mae": mae,
        "rmse": rmse,
        "max_abs_error": max_abs_error,
        "relative_rmse": float(relative_rmse),
        "within_tolerance": bool(within_tolerance),
        "diagnostic": (
            f"synthetic evacuation calibration residual is {status} tolerance "
            f"(max_abs_error={max_abs_error:.3f}, tol={float(residual_tol):.3f}); "
            "not a real Anshuka reproduction fix, not a traffic-flow validity claim"
        ),
    }


def belief_recovery_gate(true_belief: float = 0.55, tol: float = 0.15,
                         max_sims: int = 250, n_iter: int = 8, seed: int = 42) -> tuple[bool, str]:
    """Parameter-recovery proof: generate an observed outcome from a KNOWN belief, then
    recover it with the ABC calibrator. Proves the calibration capability works (and that
    belief IS identifiable from evacuation outcomes) — on synthetic ground truth, NOT by
    fitting real data."""
    fixed = dict(alarm_t=0, onset_steps=20, mobility_good_frac=0.7,
                 collaboration=False, n_agents=100, max_steps=150)
    truth = EvacOutcomeObjective(fixed=fixed, n_iter=n_iter, base_seed=0)
    observed = truth.simulate({"belief": true_belief})
    out = run_evac_calibration(
        observed, {"belief": {"min": 0.0, "max": 1.0}}, fixed,
        max_sims=max_sims, n_iter=n_iter, seed=seed,
    )
    if not out["ok"]:
        return False, f"calibration failed: {out['reason']}"
    rec = float(out["best_params"]["belief"])
    if abs(rec - true_belief) > tol:
        return False, (f"belief NOT recovered: {rec:.3f} vs true {true_belief} (tol {tol}); "
                       f"observed=[{observed[0]:.1f},{observed[1]:.1f}]")
    return True, (f"belief recovered {rec:.3f} ~ true {true_belief} (tol {tol}); "
                  f"ABC over [evac,incap], {out['n_simulator_calls']} sims; "
                  "base calibration unmodified; belief is identifiable from evacuation outcomes")


def evac_calibration_diagnostic_gate(
    true_belief: float = 0.55,
    belief_tol: float = 0.15,
    residual_tol: float = 5.0,
    max_sims: int = 250,
    n_iter: int = 8,
    seed: int = 42,
) -> tuple[bool, str]:
    """Gate the calibrated residual, not just the recovered parameter.

    Synthetic truth is used deliberately: this proves calibration instrumentation and
    identifiability under known ground truth, not that the locked Anshuka real-data
    reproduction's remaining magnitude gaps are solved.
    """
    fixed = dict(alarm_t=0, onset_steps=20, mobility_good_frac=0.7,
                 collaboration=False, n_agents=100, max_steps=150)
    truth = EvacOutcomeObjective(fixed=fixed, n_iter=n_iter, base_seed=0)
    observed = truth.simulate({"belief": true_belief})
    out = diagnose_evac_calibration(
        observed,
        {"belief": {"min": 0.0, "max": 1.0}},
        fixed,
        max_sims=max_sims,
        n_iter=n_iter,
        seed=seed,
        residual_tol=residual_tol,
    )
    if not out["calibration"]["ok"]:
        return False, f"calibration failed: {out['calibration']['reason']}"
    rec = float(out["calibration"]["best_params"]["belief"])
    if abs(rec - true_belief) > belief_tol:
        return False, (
            f"belief NOT recovered: {rec:.3f} vs true {true_belief} "
            f"(tol {belief_tol}); residual max_abs_error={out['max_abs_error']:.3f}; "
            "not a real Anshuka reproduction fix"
        )
    if not out["within_tolerance"]:
        return False, (
            f"calibrated residual outside tolerance: max_abs_error={out['max_abs_error']:.3f} "
            f"vs tol {residual_tol}; not a real Anshuka reproduction fix"
        )
    return True, (
        f"calibrated residual within tolerance: max_abs_error={out['max_abs_error']:.3f} "
        f"vs tol {residual_tol}; belief recovered {rec:.3f} ~ true {true_belief}; "
        "synthetic adapter evidence only, not a real Anshuka reproduction fix, "
        "not traffic-flow or evacuation-validity proof"
    )
