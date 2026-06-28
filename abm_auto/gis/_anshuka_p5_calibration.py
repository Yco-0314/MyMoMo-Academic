"""Real-DEM P5 prior-experience calibration diagnostics for Anshuka 2026.

This module uses the default-off ``prior_experience_frac`` knob to scan the P5
collaboration target on the local Ba DEM. It is a diagnostic/calibration bridge:
it does not rewrite the locked real-DEM verdict bundle.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import numpy as np

from abm_auto.gis._anshuka_2026 import _validate_prior_experience_frac
from abm_auto.gis._anshuka_real import build_world_from_dem, mean_outcome_real

_BELIEFS = (("low", 0.10), ("med", 0.40), ("high", 0.70))
_DEFAULT_SCENARIO = dict(
    alarm_t=0,
    onset_steps=10,
    mobility_good_frac=0.70,
    n_agents=100,
    max_steps=600,
)
_DEFAULT_CANDIDATES = (0.0, 0.25, 0.5, 0.75, 1.0)


def evaluate_p5_collaboration_deltas(
    world,
    *,
    prior_experience_frac: Optional[float],
    beliefs: Iterable[tuple[str, float]] = _BELIEFS,
    n_iter: int = 10,
    base_seed: int = 0,
    scenario_kwargs: Optional[dict] = None,
) -> dict:
    """Evaluate P5 collaboration deltas for one prior-experience value."""
    prior = _validate_prior_experience_frac(prior_experience_frac)
    scenario = dict(_DEFAULT_SCENARIO)
    if scenario_kwargs:
        scenario.update(scenario_kwargs)
    rows = {}
    max_abs_delta = 0.0
    for label, belief in beliefs:
        off = mean_outcome_real(
            world=world,
            n_iter=n_iter,
            base_seed=base_seed,
            belief=float(belief),
            collaboration=False,
            prior_experience_frac=prior,
            **scenario,
        )
        on = mean_outcome_real(
            world=world,
            n_iter=n_iter,
            base_seed=base_seed,
            belief=float(belief),
            collaboration=True,
            prior_experience_frac=prior,
            **scenario,
        )
        delta = float(on["evac"] - off["evac"])
        max_abs_delta = max(max_abs_delta, abs(delta))
        rows[label] = {
            "belief": float(belief),
            "evac_off": float(off["evac"]),
            "evac_on": float(on["evac"]),
            "delta_evac": delta,
            "incap_off": float(off["incap"]),
            "incap_on": float(on["incap"]),
        }
    return {
        "prior_experience_frac": prior,
        "beliefs": rows,
        "max_abs_delta_evac": float(max_abs_delta),
        "n_iter": int(n_iter),
        "base_seed": int(base_seed),
    }


def calibrate_p5_prior_experience(
    world,
    *,
    candidates: Iterable[float] = _DEFAULT_CANDIDATES,
    target_abs_delta: float = 5.0,
    beliefs: Iterable[tuple[str, float]] = _BELIEFS,
    n_iter: int = 10,
    base_seed: int = 0,
    scenario_kwargs: Optional[dict] = None,
) -> dict:
    """Search prior-experience candidates for the real-DEM P5 null target.

    Selection is intentionally conservative: choose the highest candidate that
    satisfies the target, i.e. the least restrictive prior-experience gate. If no
    candidate passes, report the lowest-loss candidate without claiming success.
    """
    if target_abs_delta < 0 or not np.isfinite(float(target_abs_delta)):
        raise ValueError("target_abs_delta must be a finite non-negative number")
    baseline = evaluate_p5_collaboration_deltas(
        world,
        prior_experience_frac=None,
        beliefs=beliefs,
        n_iter=n_iter,
        base_seed=base_seed,
        scenario_kwargs=scenario_kwargs,
    )
    results = [
        evaluate_p5_collaboration_deltas(
            world,
            prior_experience_frac=c,
            beliefs=beliefs,
            n_iter=n_iter,
            base_seed=base_seed,
            scenario_kwargs=scenario_kwargs,
        )
        for c in candidates
    ]
    passing = [r for r in results if r["max_abs_delta_evac"] <= float(target_abs_delta)]
    if passing:
        best = max(passing, key=lambda r: float(r["prior_experience_frac"]))
    else:
        best = min(results, key=lambda r: r["max_abs_delta_evac"])
    return {
        "baseline": baseline,
        "candidates": results,
        "best": best,
        "target_abs_delta": float(target_abs_delta),
        "baseline_exceeds_target": baseline["max_abs_delta_evac"] > float(target_abs_delta),
        "meets_target": best["max_abs_delta_evac"] <= float(target_abs_delta),
    }


def p5_prior_experience_real_dem_gate(
    dem_path="data/anshuka_ba/ba_dem_utm.tif",
    *,
    grid_size: int = 100,
    n_iter: int = 10,
    target_abs_delta: float = 5.0,
    candidates: Iterable[float] = _DEFAULT_CANDIDATES,
) -> tuple[bool, str]:
    """Gate the P5 prior-experience scan on the local Ba DEM."""
    path = Path(dem_path)
    if not path.exists():
        return False, f"DEM not found: {path}; no synthetic fallback"
    try:
        world = build_world_from_dem(path, grid_size=grid_size, source=f"SRTM:{path.name}")
        out = calibrate_p5_prior_experience(
            world,
            candidates=candidates,
            target_abs_delta=target_abs_delta,
            n_iter=n_iter,
        )
    except Exception as exc:  # pragma: no cover - message is the public gate surface.
        return False, f"real-DEM P5 prior-experience gate failed: {exc}; no synthetic fallback"

    baseline_max = out["baseline"]["max_abs_delta_evac"]
    best = out["best"]
    best_prior = best["prior_experience_frac"]
    best_max = best["max_abs_delta_evac"]
    if not out["baseline_exceeds_target"]:
        return False, (
            f"real-DEM P5 baseline already within target: baseline_max={baseline_max:.3f} "
            f"<= {target_abs_delta}; no calibration lift proven; not a verdict rewrite"
        )
    if not out["meets_target"]:
        return False, (
            f"real-DEM P5 prior scan did not meet target: baseline_max={baseline_max:.3f}, "
            f"best_prior={best_prior}, best_max={best_max:.3f}, target={target_abs_delta}; "
            "not a verdict rewrite"
        )
    return True, (
        f"real-DEM P5 prior scan passes: baseline_max={baseline_max:.3f}, "
        f"best_prior={best_prior}, best_max={best_max:.3f}, target={target_abs_delta}; "
        "calibration diagnostic only, not a verdict rewrite or evacuation-validity proof"
    )
