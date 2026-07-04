"""Faithful-rule + determinism tests for the Watts (2002) cascade reproduction.

These pin the LOCAL threshold rule (fraction >= phi), the degree-0 convention, a
hand-verifiable cascade on a tiny graph, and determinism (same seed -> identical
result). They are faithfulness tests, NOT prediction tests (the predictions are
evaluated by examples/repro_watts_cascades/run.py).
"""
from __future__ import annotations

import networkx as nx

from abm_auto.classics.watts_cascade import (
    CascadeModel,
    build_er_graph,
    is_bimodal,
    run_many_seeds,
    run_single,
    vulnerable_degree_bound,
)


def test_path_graph_full_cascade_is_hand_verifiable():
    # Path 0-1-2-3-4, phi=0.18, seed node 0.
    # Every interior node has 2 neighbours; one active neighbour => fraction 0.5
    # >= 0.18, so adoption marches down the path until all 5 are active.
    g = nx.path_graph(5)
    res = CascadeModel(g, phi=0.18, seed_node=0).run()
    assert res["final_active_count"] == 5
    assert res["final_active_fraction"] == 1.0
    # Synchronous spread: 0 (seed) -> 1 -> 2 -> 3 -> 4, one new node per tick.
    assert res["active_series"] == [1, 2, 3, 4, 5, 5]


def test_high_degree_hub_blocks_on_fraction_rule():
    # Star: hub 0 with 10 leaves. Seed one leaf. The hub's active-neighbour fraction
    # is 1/10 = 0.10 < 0.18, so the hub never flips and the cascade is stuck at 1.
    g = nx.star_graph(10)  # node 0 = hub, nodes 1..10 = leaves
    res = CascadeModel(g, phi=0.18, seed_node=1).run()
    assert res["final_active_count"] == 1
    assert res["final_active_fraction"] == 1 / 11


def test_hub_flips_once_two_neighbours_active():
    # Same star, but with TWO active leaves the hub's fraction is 2/10 = 0.20 >= 0.18
    # and it flips; then every remaining leaf (fraction 1/1 = 1.0) flips too -> all.
    g = nx.star_graph(10)
    model = CascadeModel(g, phi=0.18, seed_node=1)
    model.agent_by_id[2].active = True  # second seed leaf, by hand
    res = model.run()
    assert res["final_active_count"] == 11  # hub + all 10 leaves


def test_active_fraction_rule_exact_boundary():
    # phi=0.18; a degree-5 node needs fraction >= 0.18 -> ceil(0.18*5)=ceil(0.9)=1
    # active neighbour suffices (1/5 = 0.20 >= 0.18). A degree-6 node needs >= 1.08,
    # i.e. 2 (1/6 = 0.1667 < 0.18). Verify the agent's fraction computation directly.
    g = nx.star_graph(5)  # hub degree 5
    model = CascadeModel(g, phi=0.18, seed_node=1)
    hub = model.agent_by_id[0]
    assert hub.active_fraction() == 1 / 5
    assert hub.active_fraction() >= 0.18  # would flip


def test_degree_zero_node_never_activates_unless_seeded():
    # Two isolated nodes 0 and 1. Seed node 0. Node 1 has no neighbours -> fraction
    # 0.0 -> never flips. Final active set = {0} only.
    g = nx.Graph()
    g.add_nodes_from([0, 1])
    model = CascadeModel(g, phi=0.18, seed_node=0)
    res = model.run()
    assert res["final_active_count"] == 1
    # And the seed itself stays active even with no neighbours.
    assert res["final_active_fraction"] == 0.5
    # Sanity: the unseeded isolated agent reports active-fraction 0.
    assert model.agent_by_id[1].active_fraction() == 0.0


def test_monotone_once_active_stays_active():
    g = nx.path_graph(4)
    model = CascadeModel(g, phi=0.18, seed_node=0)
    model.run()
    # All active at the end; a further manual step must not deactivate anyone.
    for a in model.agent_by_id.values():
        a.step()
    for a in model.agent_by_id.values():
        assert a._next_active is True


def test_determinism_same_seed_identical_result():
    # Same graph seed + same seed node -> byte-identical summary.
    g1 = build_er_graph(500, z=3.0, seed=42)
    g2 = build_er_graph(500, z=3.0, seed=42)
    r1 = run_single(g1, phi=0.18, seed_node=7)
    r2 = run_single(g2, phi=0.18, seed_node=7)
    assert r1["final_active_count"] == r2["final_active_count"]
    assert r1["active_series"] == r2["active_series"]


def test_build_er_graph_mean_degree_matches_z():
    n, z = 2000, 4.0
    g = build_er_graph(n, z, seed=1)
    mean_deg = 2 * g.number_of_edges() / n
    assert abs(mean_deg - z) < 0.05  # exact up to integer rounding of edge count


def test_run_many_seeds_is_deterministic_and_shaped():
    a = run_many_seeds(800, z=2.0, phi=0.18, n_seeds=20, graph_seed_base=0)
    b = run_many_seeds(800, z=2.0, phi=0.18, n_seeds=20, graph_seed_base=0)
    assert a["cascade_frequency"] == b["cascade_frequency"]
    assert a["sizes"] == b["sizes"]
    assert 0.0 <= a["cascade_frequency"] <= 1.0
    assert len(a["sizes"]) == 20


def test_vulnerable_degree_bound():
    assert vulnerable_degree_bound(0.18) == 5  # floor(1/0.18) = floor(5.55) = 5


def test_is_bimodal_detects_two_modes():
    # A mix of tiny (local) and large (global) final fractions, with empty middle.
    sizes = [0.001, 0.002, 0.0005, 0.4, 0.5, 0.45]
    bimodal, counts = is_bimodal(sizes)
    assert bimodal is True
    assert counts["low_mode"] >= 1 and counts["high_mode"] >= 1
    # All-tiny is NOT bimodal.
    bimodal2, _ = is_bimodal([0.001, 0.002, 0.003])
    assert bimodal2 is False
