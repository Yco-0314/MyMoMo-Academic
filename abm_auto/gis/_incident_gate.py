"""Deterministic gate for dynamic incident rerouting."""
from __future__ import annotations

from abm_auto.gis._dynamic_incident import run_dynamic_incident_routing


def _incident_reroute_summary(label: str, result: dict) -> str:
    return (
        f"{label}(n_agents={result['n_agents']}, "
        f"arrived={result['arrived']}, stranded={result['stranded']}, "
        f"mean_arrival_t={result['mean_arrival_t']}, "
        f"total_reroutes={result['total_reroutes']})"
    )


def _improved(rerouted: dict, static: dict) -> bool:
    if rerouted["arrived"] > static["arrived"]:
        return True
    if rerouted["stranded"] < static["stranded"]:
        return True
    if (
        rerouted["arrived"] == static["arrived"]
        and rerouted["stranded"] == static["stranded"]
        and rerouted["mean_arrival_t"] is not None
        and static["mean_arrival_t"] is not None
        and rerouted["mean_arrival_t"] < static["mean_arrival_t"]
    ):
        return True
    return False


def dynamic_incident_reroute_gate(
    geonet,
    safe_nodes,
    agent_nodes,
    incidents,
    n_steps=6,
    speed_m_per_tick=100.0,
) -> tuple[bool, str]:
    """Compare rerouting and static routing under dynamic road incidents."""
    safe_nodes = tuple(safe_nodes)
    agent_nodes = tuple(agent_nodes)
    incidents = tuple(incidents)

    reroute_run = run_dynamic_incident_routing(
        geonet,
        safe_nodes=safe_nodes,
        agent_nodes=agent_nodes,
        incidents=incidents,
        n_steps=n_steps,
        speed_m_per_tick=speed_m_per_tick,
        reroute=True,
    )
    static_run = run_dynamic_incident_routing(
        geonet,
        safe_nodes=safe_nodes,
        agent_nodes=agent_nodes,
        incidents=incidents,
        n_steps=n_steps,
        speed_m_per_tick=speed_m_per_tick,
        reroute=False,
    )

    evidence = (
        f"{_incident_reroute_summary('reroute', reroute_run)}, "
        f"{_incident_reroute_summary('static', static_run)}"
    )
    if reroute_run["total_reroutes"] <= 0:
        return (
            False,
            f"dynamic incident reroute gate saw no successful incident reroute: {evidence}",
        )
    if not _improved(reroute_run, static_run):
        return (
            False,
            f"dynamic incident reroute gate saw reroutes but no outcome improvement: {evidence}",
        )
    return (
        True,
        "dynamic incident reroute gate: moving-agent incident rerouting changes "
        "deterministic outcomes; this does not prove real traffic flow or "
        f"optimal incident management: {evidence}",
    )
