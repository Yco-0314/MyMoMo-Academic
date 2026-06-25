"""GIS raster calibration adapters over spatial validation loss.

This module is GIS-only. It deliberately does not import abm_auto.calibration.
"""
from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from abm_auto.gis._spatial_validation import (
    raster_pattern_metrics,
    raster_spatial_loss,
)

_BACKEND = "gis-raster-grid-search"


def _finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be a finite number")
    return out


def _validate_param_name(name: Any) -> str:
    if not isinstance(name, str) or not name:
        raise ValueError("parameter names must be non-empty strings")
    return name


def _validate_params(params: Mapping[str, Any]) -> dict[str, float]:
    if not isinstance(params, Mapping) or not params:
        raise ValueError("params must be a non-empty dict")
    validated: dict[str, float] = {}
    for name, value in params.items():
        key = _validate_param_name(name)
        validated[key] = _finite_number(key, value)
    return validated


def _validate_grid(param_grid: Mapping[str, Sequence[Any]]) -> dict[str, list[float]]:
    if not isinstance(param_grid, Mapping) or not param_grid:
        raise ValueError("param_grid must be a non-empty dict")
    validated: dict[str, list[float]] = {}
    for name, values in param_grid.items():
        key = _validate_param_name(name)
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
            raise ValueError(f"parameter grid for {key} must be non-empty")
        if len(values) == 0:
            raise ValueError(f"parameter grid for {key} must be non-empty")
        validated[key] = [_finite_number(key, value) for value in values]
    return validated


def evaluate_raster_params(
    simulator: Callable[[dict[str, float]], Any],
    observed,
    params: dict[str, float],
    threshold: float = 0.5,
) -> dict:
    """Evaluate one parameter set against an observed raster pattern."""
    clean_params = _validate_params(params)
    clean_threshold = _finite_number("threshold", threshold)
    simulator_params = dict(clean_params)
    simulated = simulator(simulator_params)
    metrics = raster_pattern_metrics(simulated, observed, threshold=clean_threshold)
    loss = raster_spatial_loss(metrics)
    return {
        "params": dict(clean_params),
        "loss": float(loss),
        "metrics": metrics,
        "simulated": simulated,
    }


def _candidate_params(param_grid: dict[str, list[float]]):
    keys = list(param_grid)
    for values in itertools.product(*(param_grid[key] for key in keys)):
        yield dict(zip(keys, values))


def grid_search_raster_calibration(
    simulator: Callable[[dict[str, float]], Any],
    observed,
    param_grid: dict[str, list[float]],
    threshold: float = 0.5,
) -> dict:
    """Run deterministic grid-search calibration over raster spatial loss."""
    clean_grid = _validate_grid(param_grid)
    clean_threshold = _finite_number("threshold", threshold)
    evaluations = []
    best = None

    for rank, params in enumerate(_candidate_params(clean_grid)):
        evaluation = evaluate_raster_params(
            simulator,
            observed,
            params,
            threshold=clean_threshold,
        )
        evaluation["rank"] = rank
        evaluations.append(evaluation)
        if best is None or evaluation["loss"] < best["loss"]:
            best = evaluation

    assert best is not None
    return {
        "ok": True,
        "backend": _BACKEND,
        "best_params": dict(best["params"]),
        "best_loss": float(best["loss"]),
        "best_metrics": dict(best["metrics"]),
        "evaluations": evaluations,
        "n_evaluations": len(evaluations),
        "reason": "",
    }


def _cluster(top: int, left: int, size: int = 2, shape=(6, 6)):
    import numpy as np

    raster = np.zeros(shape, dtype=float)
    raster[top:top + size, left:left + size] = 1.0
    return raster


def raster_spatial_calibration_gate() -> tuple[bool, str]:
    """Gate proving raster spatial loss can drive deterministic calibration."""
    observed = _cluster(2, 3)

    def simulator(params: dict[str, float]):
        return _cluster(int(params["row"]), int(params["col"]))

    result = grid_search_raster_calibration(
        simulator,
        observed,
        {"row": [0.0, 2.0], "col": [0.0, 3.0]},
    )
    losses = [evaluation["loss"] for evaluation in result["evaluations"]]
    best_is_known_good = result["best_params"] == {"row": 2.0, "col": 3.0}
    has_bad_candidate = any(loss > result["best_loss"] for loss in losses)
    near_zero_best = result["best_loss"] <= 1e-12

    if result["n_evaluations"] < 2:
        return False, "spatial calibration gate needs at least two candidates"
    if not best_is_known_good:
        return False, f"spatial calibration chose {result['best_params']}"
    if not has_bad_candidate:
        return False, "spatial calibration produced no lower-loss improvement"
    if not near_zero_best:
        return False, f"best spatial calibration loss too high ({result['best_loss']:.6f})"

    return (
        True,
        "spatial calibration selected lower-loss raster parameters "
        f"(best_loss={result['best_loss']:.6f}, "
        f"n_evaluations={result['n_evaluations']}); "
        "this is deterministic GIS spatial-loss calibration, not Bayesian "
        "posterior inference or real-data validation",
    )
