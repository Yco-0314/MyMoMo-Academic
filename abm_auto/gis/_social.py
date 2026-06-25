"""Social-spatial contagion — the second coupled (GIS x social network) ABM.

A behaviour/disease/information spreads through agents via BOTH spatial proximity
and social ties. The core contagion mechanism is space-agnostic; this module
adapts GIS spatial neighbors and social ties into one neighbors_of callable.
"""
from __future__ import annotations

from abm_auto.gis._coupling import combined_neighbors
from abm_auto.gis._mechanisms import run_contagion as _run_neighbor_contagion


def run_contagion(n_agents, spatial_neighbors_of, social_graph, beta=0.2, steps=20,
                  seed=0, seeds=(0,), use_spatial=True, use_social=True) -> dict:
    def spatial(i):
        return spatial_neighbors_of(i) if use_spatial else ()

    empty = type(social_graph)()
    social = social_graph if use_social else empty

    def neighbors_of(i):
        return combined_neighbors(i, spatial, social)

    return _run_neighbor_contagion(
        n_agents,
        neighbors_of,
        beta=beta,
        steps=steps,
        seed=seed,
        seeds=seeds,
    )


def social_lift_gate(n_agents, spatial_neighbors_of, social_graph,
                     beta=0.2, steps=20, seed=0, seeds=(0,)):
    """Adding the social layer must EXTEND reach vs spatial-only (long-range ties
    bridge to regions the spatial wave hasn't reached in the same time)."""
    sp = run_contagion(n_agents, spatial_neighbors_of, social_graph, beta, steps,
                       seed, seeds, use_spatial=True, use_social=False)
    both = run_contagion(n_agents, spatial_neighbors_of, social_graph, beta, steps,
                         seed, seeds, use_spatial=True, use_social=True)
    if both["final"] < sp["final"]:
        return False, f"social REDUCED reach ({sp['final']} -> {both['final']}; impossible)"
    if both["final"] <= sp["final"]:
        return False, f"social ties had no effect (both {sp['final']})"
    return True, f"social lift: spatial-only {sp['final']} -> combined {both['final']}"
