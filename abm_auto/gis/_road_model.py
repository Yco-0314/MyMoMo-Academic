"""Handcrafted road-network reference model: agents route shortest-path from a
random source to a random destination; edge load accumulates. Deterministic
(seeded). The gateable reference for the GeoNetwork substrate."""
from __future__ import annotations

import random

import networkx as nx


def run_road_model(geonet, n_trips=40, seed=0):
    rng = random.Random(seed)
    g = geonet.graph
    nodes = list(g.nodes)
    edge_load = {tuple(sorted(e)): 0 for e in g.edges}
    reached = 0
    for _ in range(n_trips):
        s = rng.choice(nodes)
        d = rng.choice(nodes)
        if s == d:
            d = rng.choice(nodes)
        try:
            path = nx.shortest_path(g, s, d, weight="length")
        except nx.NetworkXNoPath:
            continue
        reached += 1
        for u, v in zip(path, path[1:]):
            edge_load[tuple(sorted((u, v)))] += 1
    return {"edge_load": edge_load, "reached": reached, "n_trips": n_trips}
