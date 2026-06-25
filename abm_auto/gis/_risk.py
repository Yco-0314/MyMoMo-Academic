"""Risk-exposure on a road network: where heavy traffic meets risk points.

edge_risk[e]      = how many risk points lie within `radius` of edge e
risk_exposure[e]  = edge_load[e] * edge_risk[e]   (busy roads near hazards)
"""
from __future__ import annotations

from typing import Dict, List, Tuple


def edge_risk_from_points(geonet, point_coords: List[Tuple[float, float]], radius: float) -> Dict:
    """Count risk points within radius (CRS metres) of each network edge."""
    from abm_auto.gis._coupling import point_risk_per_edge
    from abm_auto.gis._point_space import PointSpace

    points = PointSpace.from_coords(point_coords, crs=geonet.crs)
    return point_risk_per_edge(geonet, points, radius)


def risk_exposure(edge_load: Dict, edge_risk: Dict) -> Dict:
    """Per-edge exposure = traffic load x nearby-risk count."""
    keys = set(edge_load) | set(edge_risk)
    return {e: edge_load.get(e, 0) * edge_risk.get(e, 0) for e in keys}
