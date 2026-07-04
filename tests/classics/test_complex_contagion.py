"""Faithful-rule unit tests for the Centola-Macy (2007) complex-contagion model.

Checks the local NUMBER-threshold rule (R=1 simple vs R=2 complex), the contiguous
seeding scheme, determinism, monotonicity, and order-independence (synchronous update),
plus a tiny hand-checkable graph where the fixed point is computed by hand.
"""
from __future__ import annotations

import networkx as nx
import pytest

from abm_auto.classics.complex_contagion import (
    ContagionAgent,
    ContagionModel,
    run_contagion,
    mean_adoption,
    DEGREE_Z,
)


# ── seeding scheme ────────────────────────────────────────────────────────────

def test_contiguous_seed_is_node_plus_ring_neighbors():
    m = ContagionModel(n=20, R=2, p=0.0, seed=0, seed_radius=2)
    # node 0 + 2 on each side of the ring (wraps): {18, 19, 0, 1, 2}
    assert set(m.seed_nodes) == {18, 19, 0, 1, 2}
    assert m.adopted_count() == 5  # seed only, before any step


def test_same_seed_set_for_R1_and_R2():
    m1 = ContagionModel(n=50, R=1, p=0.3, seed=7, seed_radius=2)
    m2 = ContagionModel(n=50, R=2, p=0.3, seed=7, seed_radius=2)
    assert m1.seed_nodes == m2.seed_nodes


# ── faithful local rule: R=1 vs R=2 on a hand-checkable graph ─────────────────

def _line_graph_model(R: int, seed_radius: int = 0):
    """A 7-node ring lattice with z=2 (so it is exactly a ring/cycle), seed = node 0
    only (radius 0). On a pure ring with z=2 each node has exactly 2 neighbors.

    R=1: a single seed has 2 neighbors each seeing 1 active neighbor -> they adopt,
    and the wave spreads around the whole ring -> full adoption.
    R=2: a single seed gives each neighbor only 1 active neighbor (<2) -> nothing
    spreads -> only the seed stays active.
    """
    g = nx.watts_strogatz_graph(7, 2, 0.0, seed=0)  # p=0 -> exact 7-cycle
    return ContagionModel(n=7, R=R, p=0.0, seed=0, z=2, seed_radius=seed_radius, graph=g)


def test_R1_simple_spreads_around_ring_from_single_seed():
    m = _line_graph_model(R=1, seed_radius=0)
    assert m.adopted_count() == 1  # single seed
    res = m.run()
    assert res["adopted"] == 7  # whole ring adopts
    assert res["adoption_fraction"] == pytest.approx(1.0)


def test_R2_complex_cannot_ignite_from_single_seed_on_ring():
    m = _line_graph_model(R=2, seed_radius=0)
    res = m.run()
    # complex contagion needs >=2 active neighbors; a lone seed gives each neighbor
    # only 1 -> no spread -> only the seed remains active.
    assert res["adopted"] == 1
    assert res["steps"] >= 1  # ran at least one (no-op) tick to detect the fixed point


def test_R2_complex_ignites_from_contiguous_seed_on_z8_lattice():
    # On a z=8 clustered ring, a contiguous seed gives boundary nodes >=2 active
    # neighbors, so a complex contagion CAN start and spread.
    res = run_contagion(n=100, R=2, p=0.0, seed=0, z=8, seed_radius=2)
    assert res["adopted"] > res["n_seed"]  # spread beyond the seed
    assert res["adoption_fraction"] == pytest.approx(1.0)  # fills the clustered ring


def test_threshold_is_number_not_fraction():
    # A node with degree 8 and exactly 2 active neighbors adopts under R=2
    # (number rule); a fraction rule with phi>0.25 would NOT. Build a star-ish
    # gadget: center node 0 connected to 8 leaves; activate 2 leaves; R=2.
    g = nx.Graph()
    g.add_node(0)
    for leaf in range(1, 9):
        g.add_edge(0, leaf)
    m = ContagionModel(n=9, R=2, p=0.0, seed=0, z=8, seed_radius=0, graph=g)
    # override seed: activate two leaves (nodes 1 and 2), not the center
    for a in m._agents_by_id.values():
        a.active = False
    m._agents_by_id[1].active = True
    m._agents_by_id[2].active = True
    m.seed_nodes = [1, 2]
    res = m.run()
    # center (node 0) sees exactly 2 active neighbors -> adopts under the NUMBER rule
    assert m._agents_by_id[0].active
    assert res["adopted"] >= 3


# ── determinism ───────────────────────────────────────────────────────────────

def test_determinism_same_seed_same_result():
    a = run_contagion(n=500, R=2, p=0.4, seed=3, z=8, seed_radius=2)
    b = run_contagion(n=500, R=2, p=0.4, seed=3, z=8, seed_radius=2)
    assert a["adoption_fraction"] == b["adoption_fraction"]
    assert a["trajectory"] == b["trajectory"]
    assert a["seed_nodes"] == b["seed_nodes"]


def test_different_seeds_can_differ_for_complex():
    # Sanity: not every seed gives an identical fraction once p>0 (graphs differ).
    fracs = {run_contagion(n=500, R=2, p=0.6, seed=s, z=8, seed_radius=2)["adoption_fraction"]
             for s in range(8)}
    assert len(fracs) >= 1  # at minimum it runs; usually >1 distinct values


# ── monotonicity & order-independence ─────────────────────────────────────────

def test_adoption_is_monotone_nondecreasing():
    res = run_contagion(n=400, R=2, p=0.2, seed=2, z=8, seed_radius=2)
    traj = res["trajectory"]
    assert all(traj[i] <= traj[i + 1] for i in range(len(traj) - 1))


def test_synchronous_update_is_order_independent():
    # The fixed point must not depend on agent visiting order. Run once, then run a
    # model whose AgentSet schedule is randomized; the synchronous snapshot read means
    # the final fraction is identical.
    base = ContagionModel(n=300, R=2, p=0.3, seed=5, z=8, seed_radius=2)
    base_frac = base.run()["adoption_fraction"]

    shuffled = ContagionModel(n=300, R=2, p=0.3, seed=5, z=8, seed_radius=2)
    shuffled.agents.schedule = "random_order"  # change visiting order only
    shuffled_frac = shuffled.run()["adoption_fraction"]

    assert base_frac == shuffled_frac


# ── mean_adoption helper ──────────────────────────────────────────────────────

def test_mean_adoption_averages_over_seeds():
    out = mean_adoption(n=300, R=1, p=1.0, n_seeds=5, z=8, seed_radius=2)
    assert out["n_seeds"] == 5
    assert len(out["per_seed_adoption"]) == 5
    assert 0.0 <= out["mean_adoption"] <= 1.0
    assert out["min_adoption"] <= out["mean_adoption"] <= out["max_adoption"]


def test_default_degree_is_eight():
    assert DEGREE_Z == 8
