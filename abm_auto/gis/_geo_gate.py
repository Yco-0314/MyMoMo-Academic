"""GeoNetwork gate: deterministic behavioural signature of a road model.

  1. reachability — every routed trip reached its destination,
  2. load concentrates on central roads — corr(edge_load, edge_betweenness) > 0,
  3. (implied) the network is traversable.
"""
from __future__ import annotations

import networkx as nx
import numpy as np


def geo_network_gate(result, geonet):
    if result["reached"] != result["n_trips"]:
        return False, f"not all trips reached ({result['reached']}/{result['n_trips']})"

    bet = nx.edge_betweenness_centrality(geonet.graph, weight="length")

    def bet_of(e):
        return bet.get(e, bet.get((e[1], e[0]), 0.0))

    keys = list(result["edge_load"])
    loads = np.array([result["edge_load"][k] for k in keys], dtype=float)
    bets = np.array([bet_of(k) for k in keys], dtype=float)
    if loads.std() == 0 or bets.std() == 0:
        return False, "degenerate load or betweenness (no signal)"

    corr = float(np.corrcoef(loads, bets)[0, 1])
    if not (corr > 0.2):
        return False, f"load not concentrated on central edges (corr={corr:.2f})"
    return True, f"all trips reached + load~betweenness (corr={corr:.2f})"
