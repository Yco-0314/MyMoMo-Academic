"""Official traffic count calibration bridge.

This module turns the bounded Seattle SDOT count-to-centerline match pack into
an observed network calibration target. It does not implement traffic flow,
capacity calibration, or production map matching.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from abm_auto.gis._network_validation import (
    ObservedNetworkTarget,
    grid_search_network_calibration,
    observed_network_from_mapping,
)
from abm_auto.gis._official_centerline_match import (
    SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
    official_centerline_edge_match_report,
)


DEFAULT_TRAFFIC_CALIBRATION_GRID = {"demand_scale": [0.5, 1.0, 1.5]}
BOUNDARY_NOTE = (
    "Official traffic calibration bridge uses bounded Seattle SDOT observed "
    "edge targets only; not traffic-flow validity, not congestion calibration, "
    "not capacity inference, and not production map matching."
)


def official_traffic_observed_target_from_centerline_match(
    manifest_path=SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
) -> dict:
    """Convert a passed official centerline match report into an observed target."""
    centerline_report = official_centerline_edge_match_report(manifest_path)
    if not centerline_report["ok"]:
        return {
            "ok": False,
            "reason": (
                "official centerline edge match failed: "
                + centerline_report["reason"]
            ),
            "observed": None,
            "centerline_report": centerline_report,
            "station_streets": centerline_report.get("station_streets"),
            "station_objectids": centerline_report.get("station_objectids"),
        }

    observed = observed_network_from_mapping(
        centerline_report["observed_edge_values"],
        source=f"{centerline_report['dataset']}: {centerline_report['source_url']}",
        dataset=centerline_report["dataset"],
        metric="edge_load",
    )
    return {
        "ok": True,
        "reason": "",
        "observed": observed,
        "centerline_report": centerline_report,
        "station_streets": centerline_report["station_streets"],
        "station_objectids": centerline_report["station_objectids"],
    }


def _default_simulator(
    params: Mapping[str, float],
    observed: ObservedNetworkTarget,
) -> dict:
    scale = float(params["demand_scale"])
    return {
        edge: value * scale
        for edge, value in observed.edge_values.items()
    }


def _wrapped_simulator(simulator, observed: ObservedNetworkTarget):
    chosen = _default_simulator if simulator is None else simulator

    def wrapped(params):
        return chosen(params, observed)

    return wrapped


def _loss_improvement(calibration: dict) -> float:
    losses = [
        float(evaluation["loss"])
        for evaluation in calibration["evaluations"]
    ]
    return max(losses) - float(calibration["best_loss"]) if losses else 0.0


def _failure_report(loaded: dict) -> dict:
    centerline_report = loaded["centerline_report"]
    return {
        "ok": False,
        "reason": loaded["reason"],
        "centerline_report": centerline_report,
        "observed_provenance": None,
        "centerline_diagnostics": (
            centerline_report.get("diagnostics")
            if centerline_report
            else None
        ),
        "station_streets": loaded.get("station_streets"),
        "station_objectids": loaded.get("station_objectids"),
        "calibration": None,
        "best_params": None,
        "best_loss": None,
        "loss_improvement": None,
        "boundary_note": BOUNDARY_NOTE,
    }


def official_traffic_calibration_report(
    manifest_path=SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
    *,
    param_grid=None,
    simulator: Callable[
        [Mapping[str, float], ObservedNetworkTarget],
        Mapping[Any, float],
    ] | None = None,
) -> dict:
    """Run deterministic calibration against official traffic observed edges."""
    loaded = official_traffic_observed_target_from_centerline_match(manifest_path)
    if not loaded["ok"]:
        return _failure_report(loaded)

    observed = loaded["observed"]
    grid = DEFAULT_TRAFFIC_CALIBRATION_GRID if param_grid is None else param_grid
    calibration = grid_search_network_calibration(
        _wrapped_simulator(simulator, observed),
        observed,
        grid,
    )
    improvement = _loss_improvement(calibration)
    ok = (
        calibration["best_metrics"]["coverage"] == 1.0
        and improvement > 0.0
        and calibration["best_loss"] == 0.0
    )
    reason = "" if ok else "official traffic calibration did not improve to zero loss"
    return {
        "ok": ok,
        "reason": reason,
        "centerline_report": loaded["centerline_report"],
        "observed_provenance": observed.provenance(),
        "centerline_diagnostics": loaded["centerline_report"]["diagnostics"],
        "station_streets": loaded["station_streets"],
        "station_objectids": loaded["station_objectids"],
        "calibration": calibration,
        "best_params": calibration["best_params"],
        "best_loss": calibration["best_loss"],
        "loss_improvement": improvement,
        "boundary_note": BOUNDARY_NOTE,
    }


def official_traffic_calibration_gate(
    manifest_path=SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
) -> tuple[bool, str]:
    """Gate proving official observed edge targets can drive calibration loss."""
    report = official_traffic_calibration_report(manifest_path)
    if not report["ok"]:
        return False, report["reason"]
    if report["best_params"] != {"demand_scale": 1.0}:
        return False, f"official traffic calibration chose {report['best_params']}"

    return (
        True,
        "official traffic calibration bridge passed "
        f"(dataset={report['observed_provenance']['dataset']}, "
        f"n_edges={report['observed_provenance']['n_edges']}, "
        f"best_params={report['best_params']}, "
        f"best_loss={report['best_loss']:.6f}, "
        f"loss_improvement={report['loss_improvement']:.6f}); "
        f"{report['boundary_note']}",
    )


__all__ = [
    "BOUNDARY_NOTE",
    "DEFAULT_TRAFFIC_CALIBRATION_GRID",
    "official_traffic_calibration_gate",
    "official_traffic_calibration_report",
    "official_traffic_observed_target_from_centerline_match",
]
