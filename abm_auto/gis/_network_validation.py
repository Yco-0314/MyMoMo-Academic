"""Observed network edge validation and deterministic calibration.

This module compares simulated edge-keyed values, such as road edge loads,
against observed edge-keyed targets. It is GIS-only and does not ingest or
map-match external traffic-count files.
"""
from __future__ import annotations

import itertools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

_BACKEND = "gis-network-grid-search"


def _non_empty_label(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be a finite number")
    return out


def _edge_key(edge: Any) -> tuple:
    try:
        nodes = tuple(edge)
    except TypeError as exc:
        raise ValueError("edge keys must contain exactly two nodes") from exc
    if len(nodes) != 2:
        raise ValueError("edge keys must contain exactly two nodes")
    return tuple(sorted(nodes, key=repr))


def _normalize_edge_values(edge_values: Mapping[Any, Any]) -> dict[tuple, float]:
    if not isinstance(edge_values, Mapping) or not edge_values:
        raise ValueError("edge_values must be a non-empty mapping")
    normalized: dict[tuple, float] = {}
    for edge, value in edge_values.items():
        normalized[_edge_key(edge)] = _finite_number("edge value", value)
    return normalized


def _validate_params(params: Mapping[str, Any]) -> dict[str, float]:
    if not isinstance(params, Mapping) or not params:
        raise ValueError("params must be a non-empty dict")
    out: dict[str, float] = {}
    for name, value in params.items():
        key = _non_empty_label("parameter names", name)
        out[key] = _finite_number(key, value)
    return out


def _validate_grid(param_grid: Mapping[str, Sequence[Any]]) -> dict[str, list[float]]:
    if not isinstance(param_grid, Mapping) or not param_grid:
        raise ValueError("param_grid must be a non-empty dict")
    out: dict[str, list[float]] = {}
    for name, values in param_grid.items():
        key = _non_empty_label("parameter names", name)
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
            raise ValueError(f"parameter grid for {key} must be non-empty")
        if len(values) == 0:
            raise ValueError(f"parameter grid for {key} must be non-empty")
        out[key] = [_finite_number(key, value) for value in values]
    return out


@dataclass(frozen=True)
class ObservedNetworkTarget:
    """Observed edge values with provenance."""

    edge_values: dict[tuple, float]
    source: str
    dataset: str
    metric: str = "edge_load"

    def __post_init__(self) -> None:
        object.__setattr__(self, "edge_values", _normalize_edge_values(self.edge_values))
        object.__setattr__(self, "source", _non_empty_label("source", self.source))
        object.__setattr__(self, "dataset", _non_empty_label("dataset", self.dataset))
        object.__setattr__(self, "metric", _non_empty_label("metric", self.metric))

    def provenance(self) -> dict:
        return {
            "source": self.source,
            "dataset": self.dataset,
            "metric": self.metric,
            "n_edges": len(self.edge_values),
        }


def observed_network_from_mapping(
    edge_values: Mapping[Any, Any],
    *,
    source: str,
    dataset: str,
    metric: str = "edge_load",
) -> ObservedNetworkTarget:
    """Build an observed network target from edge-keyed values."""
    return ObservedNetworkTarget(
        edge_values=dict(edge_values),
        source=source,
        dataset=dataset,
        metric=metric,
    )


def network_edge_metrics(simulated, observed: ObservedNetworkTarget) -> dict:
    """Compare simulated edge values against the observed edge subset."""
    if not isinstance(observed, ObservedNetworkTarget):
        raise ValueError("observed must be an ObservedNetworkTarget")
    sim = _normalize_edge_values(simulated)
    observed_values = observed.edge_values
    missing_edges = [edge for edge in observed_values if edge not in sim]
    matched_edges = [edge for edge in observed_values if edge in sim]

    if matched_edges:
        sim_arr = np.array([sim[edge] for edge in matched_edges], dtype=float)
        obs_arr = np.array([observed_values[edge] for edge in matched_edges], dtype=float)
        diff = sim_arr - obs_arr
        mae = float(np.mean(np.abs(diff)))
        rmse = float(np.sqrt(np.mean(diff ** 2)))
        bias = float(np.mean(diff))
        mean_abs_observed = float(np.mean(np.abs(obs_arr)))
        relative_rmse = rmse / mean_abs_observed if mean_abs_observed > 0 else (
            0.0 if rmse == 0 else math.inf
        )
        observed_top = matched_edges[int(np.argmax(obs_arr))]
        simulated_top = matched_edges[int(np.argmax(sim_arr))]
        top_edge_match = observed_top == simulated_top
    else:
        mae = math.inf
        rmse = math.inf
        bias = math.inf
        mean_abs_observed = 0.0
        relative_rmse = math.inf
        observed_top = None
        simulated_top = None
        top_edge_match = False

    return {
        "observed_total": len(observed_values),
        "matched_edges": len(matched_edges),
        "coverage": len(matched_edges) / len(observed_values),
        "missing_edges": missing_edges,
        "mae": mae,
        "rmse": rmse,
        "relative_rmse": float(relative_rmse),
        "bias": bias,
        "mean_abs_observed": mean_abs_observed,
        "top_edge_match": bool(top_edge_match),
        "observed_top_edge": observed_top,
        "simulated_top_edge": simulated_top,
    }


def network_edge_loss(metrics: dict) -> float:
    """Scalar network validation loss."""
    missing_penalty = 1.0 - float(metrics["coverage"])
    top_penalty = 0.0 if metrics["top_edge_match"] else 1.0
    relative_rmse = float(metrics["relative_rmse"])
    if math.isinf(relative_rmse):
        relative_rmse = 1e6
    return float(relative_rmse + missing_penalty + 0.1 * top_penalty)


def network_validation_gate(
    simulated,
    observed: ObservedNetworkTarget,
    max_relative_rmse: float = 0.25,
    require_top_edge_match: bool = True,
) -> tuple[bool, str]:
    """Deterministic gate for simulated-vs-observed edge values."""
    metrics = network_edge_metrics(simulated, observed)
    max_rmse = _finite_number("max_relative_rmse", max_relative_rmse)

    if metrics["missing_edges"]:
        return False, f"missing observed edges: {metrics['missing_edges']}"
    if require_top_edge_match and not metrics["top_edge_match"]:
        return False, "top observed edge does not match simulated top edge"
    if metrics["relative_rmse"] > max_rmse:
        return False, (
            "network edge relative RMSE above threshold "
            f"({metrics['relative_rmse']:.3f} > {max_rmse:.3f})"
        )

    return (
        True,
        "network edge values match observed target "
        f"(relative_rmse={metrics['relative_rmse']:.3f}, "
        f"mae={metrics['mae']:.3f}, matched={metrics['matched_edges']})",
    )


def evaluate_network_params(
    simulator,
    observed: ObservedNetworkTarget,
    params: dict[str, float],
) -> dict:
    """Evaluate one parameter set against observed edge values."""
    clean_params = _validate_params(params)
    simulated = _normalize_edge_values(simulator(dict(clean_params)))
    metrics = network_edge_metrics(simulated, observed)
    loss = network_edge_loss(metrics)
    return {
        "params": dict(clean_params),
        "loss": float(loss),
        "metrics": metrics,
        "simulated_edge_values": simulated,
    }


def _candidate_params(param_grid: dict[str, list[float]]):
    keys = list(param_grid)
    for values in itertools.product(*(param_grid[key] for key in keys)):
        yield dict(zip(keys, values))


def grid_search_network_calibration(
    simulator,
    observed: ObservedNetworkTarget,
    param_grid: dict[str, list[float]],
) -> dict:
    """Run deterministic grid-search calibration over network edge loss."""
    clean_grid = _validate_grid(param_grid)
    evaluations = []
    best = None

    for rank, params in enumerate(_candidate_params(clean_grid)):
        evaluation = evaluate_network_params(simulator, observed, params)
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
        **observed.provenance(),
    }


def network_observed_validation_gate() -> tuple[bool, str]:
    """Gate proving edge-level observed network validation can guide calibration."""
    observed = observed_network_from_mapping(
        {("A", "B"): 10.0, ("B", "C"): 2.0},
        source="local edge-count fixture",
        dataset="synthetic-network-counts",
        metric="edge_load",
    )

    def simulator(params):
        return {("A", "B"): params["main"], ("B", "C"): params["side"]}

    result = grid_search_network_calibration(
        simulator,
        observed,
        {"main": [5.0, 10.0], "side": [2.0, 8.0]},
    )
    losses = [evaluation["loss"] for evaluation in result["evaluations"]]
    has_improvement = any(loss > result["best_loss"] for loss in losses)

    if result["best_params"] != {"main": 10.0, "side": 2.0}:
        return False, f"network observed validation chose {result['best_params']}"
    if not has_improvement:
        return False, "network observed validation produced no lower-loss improvement"
    if result["best_loss"] != 0.0:
        return False, f"best network observed validation loss too high ({result['best_loss']})"

    return (
        True,
        "network observed validation selected lower-loss edge parameters "
        f"(best_loss={result['best_loss']:.6f}, n_edges={result['n_edges']}); "
        "this is edge-level observed network validation, not traffic-count "
        "ingestion and not traffic-flow calibration",
    )
