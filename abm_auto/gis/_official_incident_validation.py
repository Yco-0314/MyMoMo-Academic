"""Official incident-event effect smoke for dynamic incident routing.

This module composes the manifest-backed incident intake bridge with the
dynamic incident moving-agent model. It is intentionally a smoke only: no
traffic-flow validity, no production map matching, no incident calibration, and
no route-optimality claim is made here.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from shapely.geometry import LineString

from abm_auto.gis._dynamic_incident import run_dynamic_incident_routing
from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._official_incident_intake import (
    DEFAULT_OFFICIAL_INCIDENT_EVENT_MANIFEST,
    official_incident_event_edge_match_report,
)


BOUNDARY_NOTE = (
    "Official dynamic incident event effect smoke proves manifest-backed "
    "incident closure events can affect a moving-agent dynamic incident model; "
    "not traffic-flow validity, not production map matching, not real incident "
    "calibration, not route optimality, and not optimal incident management."
)


def _default_validation_geonet() -> GeoNetwork:
    return GeoNetwork.from_lines(
        [
            LineString([(0, 0), (100, 0)]),
            LineString([(100, 0), (200, 0)]),
            LineString([(0, 100), (200, 0)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )


def _validate_nodes(name: str, graph, value, default: list[tuple]) -> list:
    raw = default if value is None else value
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Iterable):
        raise ValueError(f"{name} must be a non-empty iterable of graph nodes")
    nodes = list(raw)
    if not nodes:
        raise ValueError(f"{name} must be a non-empty iterable of graph nodes")
    missing = [node for node in nodes if node not in graph]
    if missing:
        raise ValueError(f"{name} must contain nodes present in geonet.graph")
    return nodes


def _params(*, n_steps, speed_m_per_tick, reroute, safe_nodes, agent_nodes) -> dict:
    return {
        "n_steps": n_steps,
        "speed_m_per_tick": speed_m_per_tick,
        "reroute": reroute,
        "safe_nodes": list(safe_nodes),
        "agent_nodes": list(agent_nodes),
    }


def _failure_report(reason: str, intake_report: dict | None, params: dict) -> dict:
    return {
        "ok": False,
        "reason": reason,
        "intake_report": intake_report,
        "params": params,
        "n_matched_incidents": 0,
        "baseline_result": None,
        "incident_result": None,
        "effect": None,
        "boundary_note": BOUNDARY_NOTE,
    }


def _total_waiting(result: dict) -> int:
    return int(sum(step["waiting"] for step in result["steps"]))


def _closed_edge_steps(result: dict) -> list[int]:
    return [
        int(step["t"])
        for step in result["steps"]
        if int(step.get("n_closed_edges", 0)) > 0
    ]


def _movement_signature(result: dict) -> list[tuple]:
    return [
        (
            step["t"],
            step["arrived"],
            step["moving"],
            step["waiting"],
            step["stranded"],
        )
        for step in result["steps"]
    ]


def _arrival_delay(baseline_t: Any, incident_t: Any):
    if baseline_t is None or incident_t is None:
        return None
    return incident_t - baseline_t


def _effect(baseline: dict, incident: dict) -> dict:
    baseline_waiting = _total_waiting(baseline)
    incident_waiting = _total_waiting(incident)
    baseline_t = baseline["mean_arrival_t"]
    incident_t = incident["mean_arrival_t"]
    closed_steps = _closed_edge_steps(incident)
    baseline_closed_steps = _closed_edge_steps(baseline)
    movement_changed = _movement_signature(baseline) != _movement_signature(incident)
    arrival_delay = _arrival_delay(baseline_t, incident_t)
    arrived_delta = incident["arrived"] - baseline["arrived"]
    stranded_delta = incident["stranded"] - baseline["stranded"]
    waiting_delta = incident_waiting - baseline_waiting
    changed = (
        arrival_delay not in (None, 0)
        or waiting_delta != 0
        or arrived_delta != 0
        or stranded_delta != 0
        or closed_steps != baseline_closed_steps
        or movement_changed
    )
    return {
        "changed": changed,
        "baseline_mean_arrival_t": baseline_t,
        "incident_mean_arrival_t": incident_t,
        "arrival_delay": arrival_delay,
        "baseline_total_waiting": baseline_waiting,
        "incident_total_waiting": incident_waiting,
        "waiting_delta": waiting_delta,
        "incident_steps_with_closed_edges": closed_steps,
        "max_closed_edges": incident["max_closed_edges"],
        "arrived_delta": arrived_delta,
        "stranded_delta": stranded_delta,
    }


def official_dynamic_incident_event_effect_report(
    manifest_path=DEFAULT_OFFICIAL_INCIDENT_EVENT_MANIFEST,
    *,
    geonet=None,
    safe_nodes=None,
    agent_nodes=None,
    n_steps=4,
    speed_m_per_tick=100.0,
    reroute=False,
) -> dict:
    """Compare no-incident and manifest-backed incident dynamic routing runs."""
    geonet = _default_validation_geonet() if geonet is None else geonet
    clean_safe_nodes = _validate_nodes(
        "safe_nodes",
        geonet.graph,
        safe_nodes,
        [(200, 0)],
    )
    clean_agent_nodes = _validate_nodes(
        "agent_nodes",
        geonet.graph,
        agent_nodes,
        [(0, 0)],
    )
    params = _params(
        n_steps=n_steps,
        speed_m_per_tick=speed_m_per_tick,
        reroute=reroute,
        safe_nodes=clean_safe_nodes,
        agent_nodes=clean_agent_nodes,
    )

    intake_report = official_incident_event_edge_match_report(
        manifest_path,
        geonet=geonet,
    )
    if not intake_report["ok"]:
        return _failure_report(
            "official incident event intake failed: " + intake_report["reason"],
            intake_report,
            params,
        )

    incidents = list(intake_report["matched_incidents"] or [])
    if not incidents:
        return _failure_report(
            "official incident event intake produced no matched incidents",
            intake_report,
            params,
        )

    baseline = run_dynamic_incident_routing(
        geonet,
        clean_safe_nodes,
        clean_agent_nodes,
        incidents=[],
        n_steps=n_steps,
        speed_m_per_tick=speed_m_per_tick,
        reroute=reroute,
    )
    incident = run_dynamic_incident_routing(
        geonet,
        clean_safe_nodes,
        clean_agent_nodes,
        incidents=incidents,
        n_steps=n_steps,
        speed_m_per_tick=speed_m_per_tick,
        reroute=reroute,
    )
    effect = _effect(baseline, incident)
    ok = effect["changed"] and effect["max_closed_edges"] > 0
    reason = "" if ok else "official incident events did not affect dynamic incident output"

    return {
        "ok": ok,
        "reason": reason,
        "intake_report": intake_report,
        "params": params,
        "n_matched_incidents": len(incidents),
        "baseline_result": baseline,
        "incident_result": incident,
        "effect": effect,
        "boundary_note": BOUNDARY_NOTE,
    }


def official_dynamic_incident_event_effect_gate(
    manifest_path=DEFAULT_OFFICIAL_INCIDENT_EVENT_MANIFEST,
) -> tuple[bool, str]:
    """Gate proving manifest-backed incident events affect dynamic routing output."""
    report = official_dynamic_incident_event_effect_report(manifest_path)
    if not report["ok"]:
        return False, report["reason"]

    effect = report["effect"]
    intake = report["intake_report"]
    return (
        True,
        "official dynamic incident event effect smoke passed "
        f"(dataset={intake['dataset']}, agency={intake['source_agency']}, "
        f"scope={intake['geographic_scope']}, "
        f"matched_incidents={report['n_matched_incidents']}, "
        f"closed_edge_steps={effect['incident_steps_with_closed_edges']}, "
        f"arrival_delay={effect['arrival_delay']}, "
        f"waiting_delta={effect['waiting_delta']}); "
        f"{BOUNDARY_NOTE}",
    )


__all__ = [
    "BOUNDARY_NOTE",
    "official_dynamic_incident_event_effect_gate",
    "official_dynamic_incident_event_effect_report",
]
