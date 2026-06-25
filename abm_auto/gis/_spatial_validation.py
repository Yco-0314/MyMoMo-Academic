"""Raster spatial validation metrics and gate.

This module compares simulated and observed raster patterns. It is GIS-only and
does not import the base calibration package.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from abm_auto.gis._ops import morans_i


def _as_2d_float(name: str, raster: Any) -> np.ndarray:
    arr = np.asarray(raster, dtype=float)
    if arr.ndim != 2:
        raise ValueError(f"{name} must be a 2-D raster")
    return arr


def _centroid(mask: np.ndarray) -> np.ndarray | None:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return None
    return coords.mean(axis=0)


def _ratio(numerator: int, denominator: int, empty_value: float) -> float:
    if denominator == 0:
        return empty_value
    return float(numerator / denominator)


def _finite_float(name: str, value) -> float:
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite")
    return out


def raster_pattern_metrics(
    simulated,
    observed,
    threshold: float = 0.5,
) -> dict:
    """Compare simulated and observed raster patterns after thresholding."""
    sim = _as_2d_float("simulated", simulated)
    obs = _as_2d_float("observed", observed)
    if sim.shape != obs.shape:
        raise ValueError(
            f"simulated and observed rasters must have the same shape "
            f"(got {sim.shape} vs {obs.shape})"
        )

    cutoff = float(threshold)
    sim_mask = sim > cutoff
    obs_mask = obs > cutoff

    simulated_total = int(sim_mask.sum())
    observed_total = int(obs_mask.sum())
    intersection = int(np.logical_and(sim_mask, obs_mask).sum())
    union = int(np.logical_or(sim_mask, obs_mask).sum())

    both_empty = simulated_total == 0 and observed_total == 0
    jaccard = _ratio(intersection, union, empty_value=1.0)
    precision = _ratio(
        intersection,
        simulated_total,
        empty_value=1.0 if both_empty else 0.0,
    )
    recall = _ratio(
        intersection,
        observed_total,
        empty_value=1.0 if both_empty else 0.0,
    )

    sim_centroid = _centroid(sim_mask)
    obs_centroid = _centroid(obs_mask)
    if both_empty:
        centroid_distance = 0.0
    elif sim_centroid is None or obs_centroid is None:
        centroid_distance = math.inf
    else:
        centroid_distance = float(np.linalg.norm(sim_centroid - obs_centroid))

    simulated_morans_i = float(morans_i(sim_mask.astype(float)))
    observed_morans_i = float(morans_i(obs_mask.astype(float)))
    rows, cols = sim.shape

    return {
        "simulated_total": simulated_total,
        "observed_total": observed_total,
        "intersection": intersection,
        "union": union,
        "jaccard": float(jaccard),
        "precision": float(precision),
        "recall": float(recall),
        "simulated_morans_i": simulated_morans_i,
        "observed_morans_i": observed_morans_i,
        "morans_i_abs_error": abs(simulated_morans_i - observed_morans_i),
        "centroid_distance_cells": centroid_distance,
        "raster_diagonal_cells": float(
            math.hypot(max(rows - 1, 0), max(cols - 1, 0))
        ),
    }


def raster_spatial_loss(metrics: dict) -> float:
    """Small deterministic scalar loss for future GIS calibration adapters."""
    centroid_distance = float(metrics["centroid_distance_cells"])
    diag = float(metrics["raster_diagonal_cells"])
    if math.isinf(centroid_distance):
        centroid_term = 1.0
    elif diag <= 0.0:
        centroid_term = 0.0 if centroid_distance == 0.0 else 1.0
    else:
        centroid_term = min(centroid_distance, diag) / diag

    return float(
        (1.0 - float(metrics["jaccard"]))
        + float(metrics["morans_i_abs_error"])
        + centroid_term
    )


def raster_validation_gate(
    simulated,
    observed,
    threshold: float = 0.5,
    min_jaccard: float = 0.5,
    max_centroid_distance_cells: float = 2.0,
) -> tuple[bool, str]:
    """Deterministic gate for simulated-vs-observed raster pattern agreement."""
    metrics = raster_pattern_metrics(simulated, observed, threshold=threshold)
    min_jaccard_value = _finite_float("min_jaccard", min_jaccard)
    max_centroid_value = _finite_float(
        "max_centroid_distance_cells",
        max_centroid_distance_cells,
    )

    if metrics["observed_total"] <= 0:
        return False, "observed raster has no positive cells"
    if metrics["simulated_total"] <= 0:
        return False, "simulated raster has no positive cells"
    if metrics["jaccard"] < min_jaccard_value:
        return False, (
            "raster pattern jaccard below threshold "
            f"({metrics['jaccard']:.3f} < {min_jaccard_value:.3f})"
        )
    if metrics["centroid_distance_cells"] > max_centroid_value:
        return False, (
            "raster pattern centroid distance too large "
            f"({metrics['centroid_distance_cells']:.3f} > "
            f"{max_centroid_value:.3f} cells)"
        )

    return (
        True,
        "simulated raster matches observed raster pattern "
        f"(jaccard={metrics['jaccard']:.3f}, "
        f"centroid={metrics['centroid_distance_cells']:.3f} cells, "
        f"Moran error={metrics['morans_i_abs_error']:.3f})",
    )
