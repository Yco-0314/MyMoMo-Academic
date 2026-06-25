"""Flood gate: more flooding -> worse evacuation. Deterministic behavioural
signature for the coupled flood model."""
from __future__ import annotations

from abm_auto.gis._dynamic_flood import run_dynamic_flood_evacuation
from abm_auto.gis._flood_model import (
    _require_raster_timeline,
    run_flood_evacuation,
    run_temporal_flood_evacuation,
)


_TEMPORAL_METRICS = ("stranded", "mean_detour_m", "n_flooded_edges")


def _temporal_summary(step):
    return {
        "t": step["t"],
        "stranded": step["stranded"],
        "mean_detour_m": round(step["mean_detour_m"], 3),
        "n_flooded_edges": step["n_flooded_edges"],
    }


def _dynamic_reroute_summary(label, result):
    return (
        f"{label}(n_agents={result['n_agents']}, "
        f"arrived={result['arrived']}, stranded={result['stranded']}, "
        f"mean_arrival_t={result['mean_arrival_t']}, "
        f"total_reroutes={result['total_reroutes']})"
    )


def flood_gate(geonet, flood, safe_nodes, agent_nodes, thresholds):
    """Lower threshold = more edges flooded = more severe. Asserts:
      1. stranded is monotone non-decreasing as severity rises;
      2. flooding actually has an effect (stranded OR mean detour worsens).
    """
    sev = sorted(thresholds, reverse=True)   # high threshold first (least effect)
    runs = [run_flood_evacuation(geonet, flood, t, safe_nodes, agent_nodes) for t in sev]
    stranded = [r["stranded"] for r in runs]
    detour = [r["mean_detour_m"] for r in runs]

    if any(stranded[i] > stranded[i + 1] for i in range(len(stranded) - 1)):
        return False, f"stranded not monotone with flood severity: {stranded}"
    if stranded[-1] <= stranded[0] and detour[-1] <= detour[0]:
        return False, "flooding had no effect (stranded + detour unchanged)"
    return True, f"more flood -> worse: stranded {stranded}, detour {[round(d) for d in detour]}"


def temporal_flood_gate(geonet, flood_timeline, safe_nodes, agent_nodes, threshold):
    """Flood timeline should worsen, then recede, repeated evacuation outcomes."""
    flood_timeline = _require_raster_timeline(flood_timeline)
    if flood_timeline.n_steps < 3:
        return (
            False,
            f"temporal flood gate requires timeline length at least 3; got {flood_timeline.n_steps}",
        )

    result = run_temporal_flood_evacuation(
        geonet,
        flood_timeline,
        threshold,
        safe_nodes,
        agent_nodes,
    )
    steps = result["steps"]
    first = steps[0]
    worst = steps[result["worst_t"]]
    final = steps[-1]

    worsened = any(worst[metric] > first[metric] for metric in _TEMPORAL_METRICS)
    improved = any(final[metric] < worst[metric] for metric in _TEMPORAL_METRICS)

    evidence = (
        f"first {_temporal_summary(first)}, worst {_temporal_summary(worst)}, "
        f"final {_temporal_summary(final)}"
    )
    if not worsened:
        return False, f"temporal flood had no effect or did not worsen repeated evacuation outcomes: {evidence}"
    if not improved:
        return False, f"temporal flood worsened but did not improve by final frame: {evidence}"
    return True, f"temporal flood state got worse then recovered in repeated evacuation outcomes: {evidence}"


def dynamic_flood_reroute_gate(geonet, flood_timeline, safe_nodes, agent_nodes, threshold) -> tuple[bool, str]:
    """Rerouting should have a deterministic behavioural effect in dynamic flood."""
    safe_nodes = tuple(safe_nodes)
    agent_nodes = tuple(agent_nodes)

    reroute_run = run_dynamic_flood_evacuation(
        geonet,
        flood_timeline,
        threshold,
        safe_nodes,
        agent_nodes,
        reroute=True,
    )
    static_run = run_dynamic_flood_evacuation(
        geonet,
        flood_timeline,
        threshold,
        safe_nodes,
        agent_nodes,
        reroute=False,
    )

    evidence = (
        f"{_dynamic_reroute_summary('reroute', reroute_run)}, "
        f"{_dynamic_reroute_summary('static', static_run)}"
    )
    improved = (
        reroute_run["arrived"] > static_run["arrived"]
        or reroute_run["stranded"] < static_run["stranded"]
        or (
            reroute_run["arrived"] == static_run["arrived"]
            and reroute_run["stranded"] == static_run["stranded"]
            and reroute_run["mean_arrival_t"] is not None
            and static_run["mean_arrival_t"] is not None
            and reroute_run["mean_arrival_t"] < static_run["mean_arrival_t"]
        )
    )

    if reroute_run["total_reroutes"] <= 0:
        return False, f"dynamic flood reroute gate saw no successful reroutes: {evidence}"
    if not improved:
        return False, f"dynamic flood reroute gate saw reroutes but no outcome improvement: {evidence}"
    return (
        True,
        "dynamic flood reroute gate: moving-agent rerouting has a deterministic "
        f"behavioral impact on time-varying flood outcomes; this does not prove "
        f"real traffic flow or emergency evacuation optimality: {evidence}",
    )
