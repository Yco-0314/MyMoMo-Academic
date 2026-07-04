"""Official observed-edge validation smoke for dynamic congestion routing.

This module composes existing official Seattle count-to-centerline fixtures,
the dynamic congestion moving-agent model, and network edge validation metrics.
It is intentionally a validation smoke only: no traffic-flow validity, no
capacity inference, and no congestion calibration is claimed here.
"""
from __future__ import annotations

from numbers import Integral
from typing import Any

from abm_auto.gis._dynamic_congestion import run_dynamic_congestion_routing
from abm_auto.gis._network_validation import network_edge_loss, network_edge_metrics
from abm_auto.gis._official_centerline_match import (
    SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
    load_official_centerline_geonet,
    load_official_centerline_match_manifest,
)
from abm_auto.gis._official_traffic_calibration import (
    official_traffic_observed_target_from_centerline_match,
)


BOUNDARY_NOTE = (
    "Official dynamic congestion validation smoke compares dynamic congestion "
    "edge-load output against bounded Seattle SDOT observed edge targets only; "
    "not traffic-flow validity, not congestion calibration, not capacity "
    "inference, and not production map matching."
)


def _validate_agents_per_edge(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError("agents_per_edge must be a positive integer")
    return int(value)


def _edge_key(edge: Any) -> tuple:
    nodes = tuple(edge)
    if len(nodes) != 2:
        raise ValueError("edge keys must contain exactly two nodes")
    return tuple(sorted(nodes, key=repr))


def _params(
    *,
    agents_per_edge: int,
    n_steps,
    speed_m_per_tick,
    congestion_alpha,
    reroute,
) -> dict:
    return {
        "agents_per_edge": agents_per_edge,
        "n_steps": n_steps,
        "speed_m_per_tick": speed_m_per_tick,
        "congestion_alpha": congestion_alpha,
        "reroute": reroute,
    }


def _failure_report(loaded: dict, params: dict) -> dict:
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
        "params": params,
        "simulated_edge_values": None,
        "simulated_total": None,
        "metrics": None,
        "loss": None,
        "dynamic_result": None,
        "edge_diagnostics": None,
        "worst_edge": None,
        "boundary_note": BOUNDARY_NOTE,
    }


def _scenario_from_observed_edges(observed_edges, agents_per_edge: int) -> tuple:
    safe_nodes = set()
    agent_nodes = []
    for edge in observed_edges:
        u, v = _edge_key(edge)
        safe_nodes.add(v)
        agent_nodes.extend([u] * agents_per_edge)
    return safe_nodes, agent_nodes


def _aggregate_observed_edge_loads(dynamic_result: dict, observed_edges) -> dict:
    observed_edge_set = {_edge_key(edge) for edge in observed_edges}
    aggregated = {edge: 0.0 for edge in observed_edge_set}
    for step in dynamic_result["steps"]:
        for edge, load in step.get("edge_loads", {}).items():
            key = _edge_key(edge)
            if key in aggregated:
                aggregated[key] += float(load)
    return dict(sorted(aggregated.items(), key=lambda item: repr(item[0])))


def _json_node(node):
    return list(node) if isinstance(node, tuple) else node


def _json_edge(edge) -> list:
    u, v = _edge_key(edge)
    return [_json_node(u), _json_node(v)]


def _relative_error(abs_error: float, observed_value: float) -> float:
    if observed_value == 0.0:
        return 0.0 if abs_error == 0.0 else float("inf")
    return abs_error / abs(observed_value)


def _edge_diagnostics(simulated: dict, observed, edge_metadata: dict) -> list[dict]:
    rows = []
    for edge, observed_value in observed.edge_values.items():
        key = _edge_key(edge)
        simulated_value = float(simulated.get(key, 0.0))
        observed_value = float(observed_value)
        residual = simulated_value - observed_value
        abs_error = abs(residual)
        metadata = edge_metadata.get(key, {})
        rows.append(
            {
                "edge": _json_edge(key),
                "edge_key": repr(key),
                "street": metadata.get("street"),
                "objectid": metadata.get("objectid"),
                "observed_value": observed_value,
                "simulated_value": simulated_value,
                "residual": residual,
                "absolute_error": abs_error,
                "relative_error": _relative_error(abs_error, observed_value),
            }
        )
    return sorted(rows, key=lambda row: row["edge_key"])


def official_dynamic_congestion_validation_report(
    manifest_path=SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
    *,
    agents_per_edge=1,
    n_steps=2,
    speed_m_per_tick=1000.0,
    congestion_alpha=0.0,
    reroute=True,
) -> dict:
    """Evaluate dynamic congestion edge loads against official observed edges."""
    clean_agents_per_edge = _validate_agents_per_edge(agents_per_edge)
    params = _params(
        agents_per_edge=clean_agents_per_edge,
        n_steps=n_steps,
        speed_m_per_tick=speed_m_per_tick,
        congestion_alpha=congestion_alpha,
        reroute=reroute,
    )

    loaded = official_traffic_observed_target_from_centerline_match(manifest_path)
    if not loaded["ok"]:
        return _failure_report(loaded, params)

    observed = loaded["observed"]
    observed_edges = list(observed.edge_values)
    manifest = load_official_centerline_match_manifest(manifest_path)
    loaded_centerline = load_official_centerline_geonet(manifest)
    geonet = loaded_centerline["geonet"]
    safe_nodes, agent_nodes = _scenario_from_observed_edges(
        observed_edges,
        clean_agents_per_edge,
    )

    dynamic_result = run_dynamic_congestion_routing(
        geonet,
        safe_nodes,
        agent_nodes,
        n_steps=n_steps,
        speed_m_per_tick=speed_m_per_tick,
        congestion_alpha=congestion_alpha,
        reroute=reroute,
    )
    simulated = _aggregate_observed_edge_loads(dynamic_result, observed_edges)
    edge_diagnostics = _edge_diagnostics(
        simulated,
        observed,
        loaded_centerline["edge_metadata"],
    )
    worst_edge = max(
        edge_diagnostics,
        key=lambda row: row["absolute_error"],
        default=None,
    )
    metrics = network_edge_metrics(simulated, observed)
    loss = network_edge_loss(metrics)
    simulated_total = float(sum(simulated.values()))
    ok = (
        metrics["coverage"] == 1.0
        and not metrics["missing_edges"]
        and simulated_total > 0.0
    )
    reason = "" if ok else "dynamic congestion output did not cover observed edges"

    return {
        "ok": ok,
        "reason": reason,
        "centerline_report": loaded["centerline_report"],
        "observed_provenance": observed.provenance(),
        "centerline_diagnostics": loaded["centerline_report"]["diagnostics"],
        "station_streets": loaded["station_streets"],
        "station_objectids": loaded["station_objectids"],
        "params": params,
        "simulated_edge_values": simulated,
        "simulated_total": simulated_total,
        "metrics": metrics,
        "loss": float(loss),
        "dynamic_result": dynamic_result,
        "edge_diagnostics": edge_diagnostics,
        "worst_edge": worst_edge,
        "boundary_note": BOUNDARY_NOTE,
    }


def official_dynamic_congestion_validation_gate(
    manifest_path=SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
) -> tuple[bool, str]:
    """Gate proving official observed edges can evaluate dynamic congestion output."""
    low = official_dynamic_congestion_validation_report(
        manifest_path,
        agents_per_edge=1,
    )
    if not low["ok"]:
        return False, low["reason"]
    high = official_dynamic_congestion_validation_report(
        manifest_path,
        agents_per_edge=2,
    )
    if not high["ok"]:
        return False, high["reason"]
    if high["simulated_total"] == low["simulated_total"]:
        return False, "dynamic congestion simulated total did not change"
    if high["loss"] == low["loss"]:
        return False, "dynamic congestion validation loss did not change"

    return (
        True,
        "official dynamic congestion validation smoke passed "
        f"(dataset={low['observed_provenance']['dataset']}, "
        f"n_edges={low['observed_provenance']['n_edges']}, "
        f"coverage={low['metrics']['coverage']}, "
        f"loss_agents_1={low['loss']:.6f}, "
        f"loss_agents_2={high['loss']:.6f}, "
        f"worst_edge_street={low['worst_edge']['street']}, "
        f"max_absolute_error={low['worst_edge']['absolute_error']:.3f}, "
        f"simulated_total_agents_1={low['simulated_total']:.1f}, "
        f"simulated_total_agents_2={high['simulated_total']:.1f}); "
        f"{BOUNDARY_NOTE}",
    )


__all__ = [
    "BOUNDARY_NOTE",
    "official_dynamic_congestion_validation_gate",
    "official_dynamic_congestion_validation_report",
]
