"""Flood-evacuation model — the first coupled (raster x network) GIS-ABM.

Flooded road edges (depth > threshold) become impassable; each agent routes to the
nearest reachable safe node on the remaining network. Deterministic.
"""
from __future__ import annotations

import networkx as nx

from abm_auto.gis._coupling import flood_depth_per_edge
from abm_auto.gis._temporal import RasterTimeline, _validate_raster_timeline_frames


def _require_raster_timeline(flood_timeline):
    if not isinstance(flood_timeline, RasterTimeline):
        raise TypeError("flood_timeline must be a RasterTimeline built with RasterTimeline.from_frames()")
    try:
        frames = flood_timeline._frames
    except AttributeError:
        raise ValueError("flood_timeline must contain validated RasterTimeline frames") from None
    _validate_raster_timeline_frames(frames)
    return flood_timeline


def run_flood_evacuation(geonet, flood, threshold, safe_nodes, agent_nodes,
                         n_samples: int = 8) -> dict:
    depths = flood_depth_per_edge(geonet, flood, n_samples)
    g = geonet.graph.copy()
    flooded = [e for e, d in depths.items() if d > threshold]
    g.remove_edges_from(flooded)

    sources = set(safe_nodes) & set(g.nodes)
    dist = nx.multi_source_dijkstra_path_length(g, sources, weight="length") if sources else {}

    detours, stranded, reached = [], 0, 0
    for a in agent_nodes:
        if a in dist:
            reached += 1
            detours.append(dist[a])
        else:
            stranded += 1
    return {
        "stranded": stranded,
        "n_agents": len(agent_nodes),
        "reached": reached,
        "mean_detour_m": (sum(detours) / len(detours)) if detours else 0.0,
        "n_flooded_edges": len(flooded),
    }


def run_temporal_flood_evacuation(geonet, flood_timeline, threshold, safe_nodes,
                                  agent_nodes, n_samples: int = 8) -> dict:
    flood_timeline = _require_raster_timeline(flood_timeline)
    safe_nodes = tuple(safe_nodes)
    agent_nodes = tuple(agent_nodes)
    steps = []

    for t in range(flood_timeline.n_steps):
        metrics = run_flood_evacuation(
            geonet,
            flood_timeline.at(t),
            threshold,
            safe_nodes,
            agent_nodes,
            n_samples=n_samples,
        )
        steps.append({"t": t, **metrics})

    worst = max(
        steps,
        key=lambda step: (
            step["stranded"],
            step["mean_detour_m"],
            step["n_flooded_edges"],
        ),
    )
    final = steps[-1]

    return {
        "steps": steps,
        "n_steps": flood_timeline.n_steps,
        "max_stranded": max(step["stranded"] for step in steps),
        "max_flooded_edges": max(step["n_flooded_edges"] for step in steps),
        "max_mean_detour_m": max(step["mean_detour_m"] for step in steps),
        "worst_t": worst["t"],
        "recovered": (
            final["stranded"] < worst["stranded"]
            or final["mean_detour_m"] < worst["mean_detour_m"]
            or final["n_flooded_edges"] < worst["n_flooded_edges"]
        ),
    }
