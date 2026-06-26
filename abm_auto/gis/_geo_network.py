"""GeoNetwork: a geo-referenced road graph (networkx-backed).

Nodes are road intersections/endpoints snapped to a tolerance; node attrs carry
real (x, y) coordinates in `crs`. Edges are road segments with a metric `length`.
networkx is a base dependency, so this is additive — it touches no runtime file.
Agents (NetworkAgent) can be placed on nodes later for agent dynamics.
"""
from __future__ import annotations

from typing import List

import networkx as nx


class GeoNetwork:
    def __init__(self, graph: "nx.Graph", crs: str) -> None:
        self.graph = graph
        self.crs = crs

    @classmethod
    def from_lines(cls, lines: List, crs: str, snap_tol: float = 1.0) -> "GeoNetwork":
        g = nx.Graph()

        def snap(pt):
            return (round(pt[0] / snap_tol), round(pt[1] / snap_tol))

        for line in lines:
            coords = list(line.coords)
            start, end = coords[0], coords[-1]
            a, b = snap(start), snap(end)
            for nid, pt in ((a, start), (b, end)):
                if nid not in g:
                    g.add_node(nid, x=float(pt[0]), y=float(pt[1]))
            if a != b:
                g.add_edge(a, b, length=float(line.length))
        return cls(g, crs)

    def node_coord(self, node) -> tuple[float, float]:
        """The (x, y) world coordinate of a node. Concentrates the node-attribute
        schema so callers don't reach into graph.nodes[node]['x']/['y'] — node
        storage (e.g. adding elevation) then changes in one place."""
        attrs = self.graph.nodes[node]
        return float(attrs["x"]), float(attrs["y"])

    def edge_geom(self, u, v) -> "LineString":
        """The straight-line geometry of edge (u, v) as a shapely LineString,
        built from the two node coordinates — the single home for the
        edge->LineString derivation otherwise duplicated across callers."""
        from shapely.geometry import LineString
        return LineString([self.node_coord(u), self.node_coord(v)])

    def nearest_node(self, x: float, y: float):
        def _dist2(n):
            nx_, ny_ = self.node_coord(n)
            return (nx_ - x) ** 2 + (ny_ - y) ** 2

        return min(self.graph.nodes, key=_dist2)

    def network_distance(self, a, b) -> float:
        return nx.shortest_path_length(self.graph, a, b, weight="length")
