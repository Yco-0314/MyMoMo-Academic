"""Scoped faithful reproduction of Ge & Polhill 2016 — the flexitime mechanism.

SIMPLIFICATION (stated honestly): the original TiPaC model is a car-following
micro-simulation. Here congestion is modelled with a BPR volume-delay function per
(edge, departure slot) rather than per-car following. We reproduce the AGGREGATE
finding — flexitime spreads the departure peak -> lower road volume -> lower
commute time and CO2 — not the micro car-following. CO2 is a speed/congestion proxy
(more stop-go -> more CO2), mirroring the model's speed/acceleration-based emission.
"""
from __future__ import annotations

import random
from collections import defaultdict
from typing import List, Tuple

import networkx as nx
import numpy as np


def route_commuters(geonet, od_pairs: List[Tuple], weight: str = "length"):
    """For each (home_node, work_node), shortest-path route -> edges + length.

    `weight` is the edge attribute minimised — "length" (shortest distance) or
    "time" (fastest, when edges carry a per-edge `time` = length/speed)."""
    g = geonet.graph
    routes = []
    for s, d in od_pairs:
        if s == d:
            continue
        try:
            path = nx.shortest_path(g, s, d, weight=weight)
        except nx.NetworkXNoPath:
            continue
        edges = [tuple(sorted((u, v))) for u, v in zip(path, path[1:])]
        length = sum(g.edges[u, v]["length"] for u, v in zip(path, path[1:]))
        if edges:
            routes.append({"edges": edges, "length": length})
    return routes


def departure_slots(n, spread, n_slots, rng):
    """spread in [0,1]: 0 -> everyone in the single peak slot (max congestion);
    1 -> spread across all slots (flexitime)."""
    peak = n_slots // 2
    width = max(1, int(round(spread * n_slots)))
    lo, hi = max(0, peak - width // 2), min(n_slots - 1, peak + width // 2)
    return np.array([rng.randint(lo, hi) for _ in range(n)])


def simulate(geonet, routes, slots, capacity=20.0, free_flow_mps=13.0,
             alpha=0.15, beta=4.0, weights=None):
    """BPR congestion per (edge, slot). Returns per-commuter (time_s, co2_proxy).

    `weights[i]` is commuter i's contribution to road volume (default 1.0). Use a
    fractional weight for cyclists (a bike congests less than a car it replaces)."""
    g = geonet.graph
    if weights is None:
        weights = [1.0] * len(routes)
    vol = defaultdict(float)
    for r, s, w in zip(routes, slots, weights):
        for e in r["edges"]:
            vol[(e, int(s))] += w

    times, co2 = [], []
    for r, s in zip(routes, slots):
        t = 0.0
        cong_sum = 0.0
        for e in r["edges"]:
            L = g.edges[e]["length"]
            speed = g.edges[e].get("speed", free_flow_mps)   # per-edge free-flow speed
            t0 = L / speed
            congestion = 1.0 + alpha * (vol[(e, int(s))] / capacity) ** beta
            t += t0 * congestion
            cong_sum += congestion
        times.append(t)
        avg_cong = cong_sum / max(len(r["edges"]), 1)
        # CO2 proxy: base per metre + congestion surcharge (stop-go burns more)
        co2.append(r["length"] * (0.15 + 0.10 * (avg_cong - 1.0)))
    return np.array(times), np.array(co2)


def flexitime_experiment(geonet, od_pairs, spreads, n_slots=12, seed=0,
                         capacity=20.0, routes=None):
    """Vary the departure spread (flexitime); measure mean commute time, its
    cross-commuter std (reliability proxy), and total CO2.

    `capacity` is the per-(edge, slot) BPR capacity — calibrate it to a realistic
    road throughput so magnitudes are sensible. Pass pre-computed `routes` to
    avoid re-routing across calls."""
    rng = random.Random(seed)
    if routes is None:
        routes = route_commuters(geonet, od_pairs)
    out = []
    for spread in spreads:
        slots = departure_slots(len(routes), spread, n_slots, rng)
        times, co2 = simulate(geonet, routes, slots, capacity=capacity)
        out.append({
            "spread": spread,
            "mean_time": float(times.mean()),
            "std_time": float(times.std()),
            "total_co2": float(co2.sum()),
            "n": len(routes),
        })
    return out
