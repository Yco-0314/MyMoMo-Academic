"""Shared routing primitive for the dynamic GIS evacuation models.

The congestion and flood models share ONE genuinely-identical piece: the
cost-weighted shortest-route search (a deterministic Dijkstra with stable
tie-breaking by node `repr`). Everything else around it differs — congestion
keys edges with `key=repr` and reduces speed by a congestion multiplier; flood
keys edges naturally and removes flooded edges before routing — so only this
search is extracted (the other primitives stay per-model on purpose; folding
them together would be a leaky abstraction, ponytail).

`edge_cost(u, v, length) -> float` injects the per-edge cost:
- flood passes None  -> the cost is the edge length (plain distance).
- congestion passes a closure that looks up the congested cost, falling back to
  the edge length when an edge has no recorded cost.
"""
from __future__ import annotations

import heapq
from itertools import count


def dijkstra_route(graph, start, safe_nodes, edge_cost=None) -> list:
    """Lowest-cost route (list of nodes after `start`) from `start` to the nearest
    node in `safe_nodes`, or [] if none is reachable. Deterministic: ties broken by
    the `repr`-keyed path so the route is reproducible regardless of dict/heap order."""
    if start not in graph or not safe_nodes:
        return []
    reachable_safe_nodes = {node for node in safe_nodes if node in graph}
    if not reachable_safe_nodes:
        return []

    if edge_cost is None:
        def edge_cost(u, v, length):
            return length

    serial = count()
    start_key = (repr(start),)
    queue = [(0.0, start_key, next(serial), start, [start])]
    best = {}
    while queue:
        distance, path_key, _, node, path = heapq.heappop(queue)
        if node in best and best[node] <= (distance, path_key):
            continue
        best[node] = (distance, path_key)
        if node in reachable_safe_nodes:
            return list(path[1:])
        for neighbor in sorted(graph.neighbors(node), key=repr):
            edge = graph.edges[node, neighbor]
            length = float(edge.get("length", 1.0))
            cost = edge_cost(node, neighbor, length)
            new_path = [*path, neighbor]
            new_key = (*path_key, repr(neighbor))
            heapq.heappush(
                queue,
                (distance + cost, new_key, next(serial), neighbor, new_path),
            )
    return []
