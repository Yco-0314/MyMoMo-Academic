"""Spatial method-transfer runtime cell.

This module applies one graph-neighborhood method across multiple GIS spaces.
The first method is a deterministic Forman-style edge-curvature proxy; it is
not a full Ollivier-Ricci/TDA implementation.
"""
from __future__ import annotations

from numbers import Integral
from statistics import mean
from typing import Callable, Iterable

import numpy as np
from affine import Affine
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._mechanism_adapters import (
    geonetwork_node_neighbors,
    raster_cell_neighbors,
)
from abm_auto.gis._raster_space import RasterField, RasterSpace


NeighborsOf = Callable[[int], Iterable[int]]

BOUNDARY_NOTE = (
    "Forman-style graph-neighborhood method transfer across RasterSpace and "
    "GeoNetwork; not full ORC/TDA, not spatial validation, and not automatic "
    "scientific method discovery."
)


def _positive_n_nodes(value) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError("n_nodes must be a positive integer")
    return int(value)


def _neighbor_id(value, n_nodes: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError("neighbor ids must be integers")
    out = int(value)
    if out < 0 or out >= n_nodes:
        raise ValueError(f"neighbor ids must be in [0, {n_nodes})")
    return out


def _edges_and_degrees(n_nodes: int, neighbors_of: NeighborsOf):
    edges: set[tuple[int, int]] = set()
    degrees = [0] * n_nodes
    neighbor_sets: list[set[int]] = []
    for i in range(n_nodes):
        neighbors = set()
        for raw_neighbor in neighbors_of(i):
            j = _neighbor_id(raw_neighbor, n_nodes)
            if j == i:
                raise ValueError("self loops are not supported")
            neighbors.add(j)
        neighbor_sets.append(neighbors)
        degrees[i] = len(neighbors)
    for i, neighbors in enumerate(neighbor_sets):
        for j in neighbors:
            edges.add(tuple(sorted((i, j))))
    return sorted(edges), degrees


def forman_ricci_edge_scores(
    n_nodes,
    neighbors_of: NeighborsOf,
) -> dict[tuple[int, int], float]:
    """Return deterministic Forman-style edge scores for an undirected graph."""
    clean_n_nodes = _positive_n_nodes(n_nodes)
    edges, degrees = _edges_and_degrees(clean_n_nodes, neighbors_of)
    return {
        edge: float(4 - degrees[edge[0]] - degrees[edge[1]])
        for edge in edges
    }


def spatial_curvature_summary(n_nodes, neighbors_of: NeighborsOf) -> dict:
    """Summarize Forman-style curvature scores for a neighbor callable."""
    clean_n_nodes = _positive_n_nodes(n_nodes)
    scores = forman_ricci_edge_scores(clean_n_nodes, neighbors_of)
    if not scores:
        raise ValueError("at least one edge is required")
    values = list(scores.values())
    min_score = min(values)
    return {
        "n_nodes": clean_n_nodes,
        "n_edges": len(scores),
        "scores": scores,
        "score_signature": sorted(values),
        "min_score": min_score,
        "max_score": max(values),
        "mean_score": float(mean(values)),
        "min_edges": [
            edge for edge, score in scores.items()
            if score == min_score
        ],
    }


def raster_spatial_curvature_summary(space, moore: bool = False) -> dict:
    """Run the transfer method over RasterSpace cell adjacency."""
    adapted = raster_cell_neighbors(space, moore=moore)
    summary = spatial_curvature_summary(adapted["n_agents"], adapted["neighbors_of"])
    summary["space_type"] = "RasterSpace"
    return summary


def geonetwork_spatial_curvature_summary(geonet) -> dict:
    """Run the transfer method over GeoNetwork node adjacency."""
    adapted = geonetwork_node_neighbors(geonet)
    summary = spatial_curvature_summary(adapted["n_agents"], adapted["neighbors_of"])
    summary["space_type"] = "GeoNetwork"
    summary["index_to_node"] = adapted["index_to_node"]
    return summary


def _raster_chain() -> RasterSpace:
    return RasterSpace(
        RasterField(
            data=np.zeros((1, 4)),
            transform=Affine.identity(),
            crs="EPSG:3857",
        )
    )


def _geonetwork_chain() -> GeoNetwork:
    return GeoNetwork.from_lines(
        [
            LineString([(0, 0), (1, 0)]),
            LineString([(1, 0), (2, 0)]),
            LineString([(2, 0), (3, 0)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )


def spatial_method_transfer_report() -> dict:
    """Compare the same method over equivalent raster and network topologies."""
    raster_summary = raster_spatial_curvature_summary(_raster_chain(), moore=False)
    geonetwork_summary = geonetwork_spatial_curvature_summary(_geonetwork_chain())
    signatures_match = (
        raster_summary["score_signature"]
        == geonetwork_summary["score_signature"]
    )
    middle_edge_lowest = (
        raster_summary["min_edges"] == [(1, 2)]
        and geonetwork_summary["min_edges"] == [(1, 2)]
    )
    ok = (
        raster_summary["n_nodes"] == 4
        and raster_summary["n_edges"] == 3
        and geonetwork_summary["n_nodes"] == 4
        and geonetwork_summary["n_edges"] == 3
        and signatures_match
        and raster_summary["score_signature"] == [0.0, 1.0, 1.0]
        and middle_edge_lowest
    )
    reason = "" if ok else "spatial method transfer signatures did not match"
    return {
        "ok": ok,
        "reason": reason,
        "method": "forman_style_edge_curvature",
        "raster_summary": raster_summary,
        "geonetwork_summary": geonetwork_summary,
        "signatures_match": signatures_match,
        "middle_edge_lowest": middle_edge_lowest,
        "boundary_note": BOUNDARY_NOTE,
    }


def spatial_method_transfer_gate() -> tuple[bool, str]:
    """Gate for the first runtime method-transfer proof cell."""
    report = spatial_method_transfer_report()
    if not report["ok"]:
        return False, report["reason"]
    signature = report["raster_summary"]["score_signature"]
    return (
        True,
        "spatial method transfer passed "
        f"(method=Forman-style edge curvature, "
        f"RasterSpace signature={signature}, "
        f"GeoNetwork signature={signature}); "
        f"{BOUNDARY_NOTE}",
    )


__all__ = [
    "BOUNDARY_NOTE",
    "forman_ricci_edge_scores",
    "geonetwork_spatial_curvature_summary",
    "raster_spatial_curvature_summary",
    "spatial_curvature_summary",
    "spatial_method_transfer_gate",
    "spatial_method_transfer_report",
]
