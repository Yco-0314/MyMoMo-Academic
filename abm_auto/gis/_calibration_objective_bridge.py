"""Bridge GIS spatial loss into base calibration simulator contracts.

The base calibration machinery consumes objects with
``simulate(params, targets) -> np.ndarray`` and minimizes
``||sim_stats - obs_stats||``. This module exposes raster spatial loss through
that contract without editing ``abm_auto/calibration/``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from abm_auto.calibration import backends
from abm_auto.calibration.types import CalibrationResult
from abm_auto.gis._observed_raster_bridge import ObservedRasterTarget
from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._spatial_calibration import evaluate_raster_params

_TARGETS = ["spatial_loss"]


def raster_spatial_loss_targets() -> list[str]:
    """Return the base-calibration target name used by this adapter."""
    return list(_TARGETS)


def raster_spatial_loss_observed_stats() -> np.ndarray:
    """Observed stats for minimizing spatial loss: perfect fit is zero."""
    return np.array([0.0], dtype=float)


def _observed_data(observed: Any) -> Any:
    if isinstance(observed, ObservedRasterTarget):
        return observed.data
    if isinstance(observed, RasterSpace):
        return observed.field.data
    if isinstance(observed, RasterField):
        return observed.data
    return observed


@dataclass
class RasterSpatialLossObjective:
    """Simulator-like wrapper returning one stat: raster spatial loss."""

    raster_simulator: Callable[[dict[str, float]], Any]
    observed: Any
    threshold: float = 0.5
    evaluations: list[dict] = field(default_factory=list)

    @property
    def n_calls(self) -> int:
        return len(self.evaluations)

    def simulate(self, params: dict[str, float], targets=None) -> np.ndarray:
        if targets is not None and list(targets) != _TARGETS:
            raise ValueError("targets must be ['spatial_loss']")
        evaluation = evaluate_raster_params(
            self.raster_simulator,
            _observed_data(self.observed),
            params,
            threshold=self.threshold,
        )
        record = {
            "params": dict(evaluation["params"]),
            "loss": float(evaluation["loss"]),
            "metrics": dict(evaluation["metrics"]),
        }
        self.evaluations.append(record)
        return np.array([record["loss"]], dtype=float)

    def loss_for(self, params: dict[str, float]) -> float:
        return float(self.simulate(params, _TARGETS)[0])


def make_raster_spatial_loss_objective(
    raster_simulator: Callable[[dict[str, float]], Any],
    observed: Any,
    threshold: float = 0.5,
) -> RasterSpatialLossObjective:
    """Create a base-calibration-compatible GIS spatial loss objective."""
    return RasterSpatialLossObjective(
        raster_simulator=raster_simulator,
        observed=observed,
        threshold=threshold,
    )


def _with_optional_seed(seed, fn):
    if seed is None:
        return fn()
    state = np.random.get_state()
    try:
        np.random.seed(int(seed))
        return fn()
    finally:
        np.random.set_state(state)


def run_base_abc_raster_spatial_calibration(
    raster_simulator: Callable[[dict[str, float]], Any],
    observed: Any,
    priors: dict[str, dict],
    max_sims: int = 100,
    threshold: float = 0.5,
    seed: int | None = None,
) -> dict:
    """Run base ABC against GIS spatial loss without modifying base code."""
    objective = make_raster_spatial_loss_objective(
        raster_simulator,
        observed,
        threshold=threshold,
    )
    targets = raster_spatial_loss_targets()
    observed_stats = raster_spatial_loss_observed_stats()

    def run() -> CalibrationResult:
        return backends.run_abc(
            priors,
            targets,
            observed_stats,
            objective,
            max_sims,
        )

    calibration_result = _with_optional_seed(seed, run)
    best_loss = None
    if calibration_result.ok:
        best_loss = objective.loss_for(calibration_result.best_params)

    return {
        "ok": bool(calibration_result.ok),
        "backend": f"gis-spatial-loss+{calibration_result.backend}",
        "calibration_result": calibration_result,
        "best_params": dict(calibration_result.best_params),
        "best_loss": best_loss,
        "n_simulator_calls": calibration_result.n_simulator_calls,
        "targets": targets,
        "observed_stats": observed_stats,
        "objective_evaluations": list(objective.evaluations),
        "reason": calibration_result.reason,
    }


def _cluster(top: int, left: int, size: int = 2, shape=(6, 6)) -> np.ndarray:
    raster = np.zeros(shape, dtype=float)
    raster[top:top + size, left:left + size] = 1.0
    return raster


def base_calibration_objective_bridge_gate() -> tuple[bool, str]:
    """Gate proving base ABC can consume a GIS spatial-loss objective."""

    def simulator(params):
        return _cluster(int(params["row"]), int(params["col"]))

    result = run_base_abc_raster_spatial_calibration(
        simulator,
        _cluster(2, 3),
        {
            "row": {"min": 0.0, "max": 4.0},
            "col": {"min": 0.0, "max": 4.0},
        },
        max_sims=200,
        seed=42,
    )

    if not result["ok"]:
        return False, f"base ABC failed: {result['reason']}"
    if result["best_loss"] != 0.0:
        return False, f"base ABC best spatial loss too high ({result['best_loss']})"
    if int(result["best_params"]["row"]) != 2 or int(result["best_params"]["col"]) != 3:
        return False, f"base ABC chose {result['best_params']}"

    return (
        True,
        "base ABC consumed GIS spatial loss objective "
        f"(best_loss={result['best_loss']:.6f}, "
        f"n_calls={result['n_simulator_calls']}); "
        "abm_auto/calibration/ was not modified; this is not full "
        "BayesianCalibrator.run workspace calibration",
    )
