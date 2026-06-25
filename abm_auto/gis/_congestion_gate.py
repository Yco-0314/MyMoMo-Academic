"""Deterministic gate for dynamic congestion rerouting."""
from __future__ import annotations

from abm_auto.gis._dynamic_congestion import run_dynamic_congestion_routing


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


def dynamic_congestion_reroute_gate(
    geonet,
    safe_nodes,
    agent_nodes,
    n_steps=6,
    speed_m_per_tick=100.0,
    congestion_alpha=2.0,
) -> tuple[bool, str]:
    """Compare rerouting and static routing under dynamic congestion."""
    rerouted = run_dynamic_congestion_routing(
        geonet,
        safe_nodes=safe_nodes,
        agent_nodes=agent_nodes,
        n_steps=n_steps,
        speed_m_per_tick=speed_m_per_tick,
        congestion_alpha=congestion_alpha,
        reroute=True,
    )
    static = run_dynamic_congestion_routing(
        geonet,
        safe_nodes=safe_nodes,
        agent_nodes=agent_nodes,
        n_steps=n_steps,
        speed_m_per_tick=speed_m_per_tick,
        congestion_alpha=congestion_alpha,
        reroute=False,
    )

    if rerouted["total_reroutes"] <= 0:
        return False, "no successful congestion reroute was recorded"
    if not _improved(rerouted, static):
        return False, (
            "congestion rerouting did not improve deterministic outcomes; "
            f"rerouted arrived={rerouted['arrived']} stranded={rerouted['stranded']} "
            f"mean_arrival_t={rerouted['mean_arrival_t']} vs static "
            f"arrived={static['arrived']} stranded={static['stranded']} "
            f"mean_arrival_t={static['mean_arrival_t']}"
        )
    return (
        True,
        "moving-agent congestion rerouting changes deterministic outcomes; "
        "this is not a traffic-flow or congestion-validity claim",
    )
