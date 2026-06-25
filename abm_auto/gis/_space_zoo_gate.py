"""Deterministic gates for point/polygon space-zoo adapters."""
from __future__ import annotations

from abm_auto.gis._coupling import (
    assign_points_to_polygons,
    point_risk_per_edge,
)
from abm_auto.gis._risk import risk_exposure


def _sorted_edges(edges):
    return sorted(edges, key=repr)


def point_network_risk_gate(geonet, points, radius, edge_load) -> tuple[bool, str]:
    """Loaded edges near risk points should light up; loaded dry edges stay zero."""
    risk = point_risk_per_edge(geonet, points, radius)
    exposure = risk_exposure(edge_load, risk)
    loaded_edges = {edge for edge, load in edge_load.items() if load > 0}

    loaded_risky = [
        edge for edge in loaded_edges
        if risk.get(edge, 0) > 0 and exposure.get(edge, 0) > 0
    ]
    dry_loaded_nonzero = [
        edge for edge in loaded_edges
        if risk.get(edge, 0) == 0 and exposure.get(edge, 0) != 0
    ]

    if dry_loaded_nonzero:
        return (
            False,
            "point-network risk gate found exposure on loaded dry edges: "
            f"{_sorted_edges(dry_loaded_nonzero)}",
        )
    if not loaded_risky:
        return (
            False,
            "point-network risk gate found no loaded risky edge with positive exposure",
        )
    return (
        True,
        "point-network risk gate: loaded risky edge lights up and dry loaded "
        f"edges stay zero; exposure={exposure}",
    )


def _normalize_assignments(assignments):
    return {
        polygon_id: sorted(point_ids)
        for polygon_id, point_ids in sorted(assignments.items(), key=lambda item: repr(item[0]))
    }


def polygon_point_zoning_gate(points, polygons, expected) -> tuple[bool, str]:
    """Point-to-polygon assignments should match a known deterministic mapping."""
    observed = _normalize_assignments(assign_points_to_polygons(points, polygons))
    expected = _normalize_assignments(expected)
    if observed != expected:
        return (
            False,
            f"polygon-point zoning gate expected {expected} but observed {observed}",
        )
    return True, f"polygon-point zoning gate: assignments match {observed}"
