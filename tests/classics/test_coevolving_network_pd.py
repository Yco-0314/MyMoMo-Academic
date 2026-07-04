"""Faithful-rule + determinism tests for the coevolving-network Prisoner's Dilemma
(Santos, Pacheco & Lenaerts 2006) reproduction.

These pin the homogeneous z-regular graph construction (every node degree z, edges
conserved), the accumulated-payoff PD fitness, the Fermi (pairwise-comparison)
imitation probability, the two entangled elementary steps (strategy update vs
cooperator-rewires-away-from-a-defector), the EDGE-COUNT + degree conservation under
rewiring, the W=0 static-graph control (structure never changes), the steady-state
estimator, and determinism (same seed -> identical result).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(W=0 collapse; W>=16 cooperation prevails + enhancement; monotone W-dependence) are
evaluated by examples/repro_coevolving_network_pd/run.py.
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.coevolving_network_pd import (
    COOPERATE,
    DEFECT,
    CoevolvingNetworkPD,
    PDNode,
    run_single,
    tail_mean,
)


# -- graph construction: homogeneous + edges conserved ------------------------

def test_regular_graph_every_node_has_degree_z():
    m = CoevolvingNetworkPD(n=200, z=10, seed=0)
    assert len(m.adj) == 200
    for s in m.adj:
        assert len(s) == 10           # homogeneous: exact degree z everywhere
    # no self-loops, symmetric adjacency
    for i, s in enumerate(m.adj):
        assert i not in s
        for j in s:
            assert i in m.adj[j]


def test_edge_count_is_n_times_z_over_two():
    m = CoevolvingNetworkPD(n=200, z=10, seed=1)
    assert m.n_edges == 200 * 10 // 2
    assert m.mean_degree() == pytest.approx(10.0)


def test_bad_params_raise():
    with pytest.raises(ValueError):
        CoevolvingNetworkPD(n=0)
    with pytest.raises(ValueError):
        CoevolvingNetworkPD(n=10, z=10)          # z must be < n
    with pytest.raises(ValueError):
        CoevolvingNetworkPD(n=5, z=3)            # n*z odd -> not z-regular
    with pytest.raises(ValueError):
        CoevolvingNetworkPD(n=100, z=10, W=-1.0)
    with pytest.raises(ValueError):
        CoevolvingNetworkPD(n=100, z=10, beta=-1.0)
    with pytest.raises(ValueError):
        CoevolvingNetworkPD(n=100, z=10, init_coop_fraction=1.5)


# -- accumulated-payoff PD fitness --------------------------------------------

def test_fitness_is_sum_over_neighbours_hardpoint():
    # T=2, R=1, P=0, S=-1. Build a tiny hand-set graph and check exact fitnesses.
    m = CoevolvingNetworkPD(n=4, z=2, T=2.0, R=1.0, P=0.0, S=-1.0, seed=0)
    # overwrite adjacency + strategies deterministically: a 4-cycle 0-1-2-3-0.
    m.adj = [set() for _ in range(4)]
    for a, b in [(0, 1), (1, 2), (2, 3), (3, 0)]:
        m.adj[a].add(b); m.adj[b].add(a)
    m.is_coop = [True, True, False, False]        # C C D D around the cycle
    for i, c in enumerate(m.is_coop):
        m.nodes[i].strategy = COOPERATE if c else DEFECT
    m.compute_fitnesses()
    # node0 (C) neighbours {1(C),3(D)} -> R + S = 1 + (-1) = 0
    assert m.fitness[0] == pytest.approx(0.0)
    # node1 (C) neighbours {0(C),2(D)} -> R + S = 0
    assert m.fitness[1] == pytest.approx(0.0)
    # node2 (D) neighbours {1(C),3(D)} -> T + P = 2 + 0 = 2
    assert m.fitness[2] == pytest.approx(2.0)
    # node3 (D) neighbours {2(D),0(C)} -> P + T = 0 + 2 = 2
    assert m.fitness[3] == pytest.approx(2.0)


# -- Fermi rule ---------------------------------------------------------------

def test_fermi_prob_is_logistic_and_monotone():
    m = CoevolvingNetworkPD(n=100, z=10, beta=1.0, seed=0)
    # equal fitness -> copy prob exactly 1/2
    assert m.fermi_prob(3.0, 3.0) == pytest.approx(0.5)
    # copying a fitter other is more likely than copying a worse other
    assert m.fermi_prob(0.0, 5.0) > 0.5
    assert m.fermi_prob(5.0, 0.0) < 0.5
    # matches the closed form 1/(1+exp(-beta*delta))
    p = m.fermi_prob(1.0, 3.0)
    assert p == pytest.approx(1.0 / (1.0 + math.exp(-1.0 * (3.0 - 1.0))))


def test_fermi_prob_saturates_without_overflow():
    m = CoevolvingNetworkPD(n=100, z=10, beta=10.0, seed=0)
    assert m.fermi_prob(0.0, 1e6) == pytest.approx(1.0)
    assert m.fermi_prob(1e6, 0.0) == pytest.approx(0.0)


# -- strategy step: only copies via Fermi -------------------------------------

def test_strategy_step_copies_a_definitively_fitter_neighbour():
    # Strong selection + a defector neighbour that is much fitter -> a cooperator
    # copies it with prob ~1. Deterministic tiny setup.
    m = CoevolvingNetworkPD(n=2, z=1, beta=10.0, W=0.0, seed=0)
    m.adj = [{1}, {0}]
    m.is_coop = [True, False]
    m.nodes[0].strategy, m.nodes[1].strategy = COOPERATE, DEFECT
    m.fitness = [0.0, 100.0]     # neighbour (node1, D) hugely fitter than node0 (C)
    # force A=node0, B=node1 by seeding the RNG draw; repeat until it flips.
    flipped = False
    for s in range(50):
        mm = CoevolvingNetworkPD(n=2, z=1, beta=10.0, W=0.0, seed=s)
        mm.adj = [{1}, {0}]
        mm.is_coop = [True, False]
        mm.nodes[0].strategy, mm.nodes[1].strategy = COOPERATE, DEFECT
        mm.fitness = [0.0, 100.0]
        mm.strategy_step()
        if mm.is_coop[0] is False or mm.is_coop[1] is True:
            flipped = True
            break
    assert flipped   # a hugely-fitter neighbour is copied under strong selection


# -- structural step: rewiring conserves edges + degree of the rewirer --------

def test_structural_step_conserves_edge_count_and_rewirer_degree():
    m = CoevolvingNetworkPD(n=50, z=6, W=10.0, beta=0.0, seed=3)
    edges_before = m.n_edges
    total_deg_before = sum(len(s) for s in m.adj)
    m.compute_fitnesses()
    # beta=0 -> Fermi prob is always 0.5; run many structural steps and re-check
    # that the global edge count is invariant (rewiring only MOVES endpoints).
    for _ in range(500):
        m.structural_step()
        assert sum(len(s) for s in m.adj) == total_deg_before   # sum of degrees fixed
    # recompute edge count from adjacency (each edge counted twice)
    assert sum(len(s) for s in m.adj) // 2 == edges_before
    # adjacency still symmetric + simple after all the rewiring
    for i, s in enumerate(m.adj):
        assert i not in s
        for j in s:
            assert i in m.adj[j]


def test_structural_step_moves_a_cooperators_tie_off_a_defector():
    # A single C with one D neighbour and free targets: with beta=0 (p_stay=0.5) the
    # rewire fires ~half the time; when it fires, the C-D edge is gone and the C's
    # degree is unchanged. Verify at least one rewire drops the specific C-D tie.
    dropped = False
    for s in range(40):
        m = CoevolvingNetworkPD(n=20, z=3, W=10.0, beta=0.0, seed=s)
        # set node 0 = C with a known defector neighbour; make all its neighbours D.
        a = 0
        m.is_coop = [False] * 20
        m.is_coop[a] = True
        for i, c in enumerate(m.is_coop):
            m.nodes[i].strategy = COOPERATE if c else DEFECT
        deg_a = len(m.adj[a])
        defect_neighbours = set(m.adj[a])
        m.compute_fitnesses()
        m.structural_step()
        if len(m.adj[a]) == deg_a and set(m.adj[a]) != defect_neighbours:
            dropped = True
            break
    assert dropped   # the dissatisfied cooperator redirected a tie off a defector


def test_defector_never_initiates_rewiring():
    # structural_step picks the focal node uniformly; if it lands on a defector it
    # must be a no-op (only exploited cooperators are dissatisfied). Force an all-D
    # population: no structural change is ever possible.
    m = CoevolvingNetworkPD(n=30, z=4, W=10.0, beta=0.0, seed=1)
    m.is_coop = [False] * 30
    for nd in m.nodes:
        nd.strategy = DEFECT
    adj_before = [set(s) for s in m.adj]
    m.compute_fitnesses()
    for _ in range(200):
        m.structural_step()
    assert [set(s) for s in m.adj] == adj_before   # all-D -> structure frozen


# -- W=0 static-graph control: structure never changes ------------------------

def test_static_graph_control_never_rewires():
    m = CoevolvingNetworkPD(n=100, z=8, W=0.0, seed=2)
    assert m.p_structural == 0.0
    adj_before = [frozenset(s) for s in m.adj]
    res = m.run(n_generations=30, measure_last=10)
    adj_after = [frozenset(s) for s in m.adj]
    assert adj_before == adj_after   # W=0 froze the graph for the whole run
    # every node still has its original degree (edges conserved trivially)
    for s in m.adj:
        assert len(s) == 8


def test_positive_W_can_change_structure():
    # With W>0 and a mixed population the graph is expected to change over a run.
    m = CoevolvingNetworkPD(n=200, z=10, W=16.0, seed=5)
    adj_before = [frozenset(s) for s in m.adj]
    m.run(n_generations=20, measure_last=5)
    adj_after = [frozenset(s) for s in m.adj]
    assert adj_before != adj_after   # rewiring actually happened
    # but the global edge count is still conserved
    assert sum(len(s) for s in m.adj) // 2 == m.n_edges


# -- metrics + run shape ------------------------------------------------------

def test_cooperator_fraction_matches_is_coop():
    m = CoevolvingNetworkPD(n=100, z=8, init_coop_fraction=0.5, seed=0)
    frac = m.cooperator_fraction()
    assert frac == pytest.approx(sum(m.is_coop) / 100)
    assert 0.0 <= frac <= 1.0


def test_run_summary_shape():
    res = run_single(n=200, z=10, W=2.0, seed=0, n_generations=25, measure_last=10)
    assert res["n"] == 200 and res["z"] == 10
    assert res["b_over_c"] == pytest.approx(2.0)
    assert res["n_edges"] == 200 * 10 // 2
    assert res["mean_degree"] == pytest.approx(10.0)
    assert 0.0 <= res["steady_coop_fraction"] <= 1.0
    assert 0.0 <= res["final_coop_fraction"] <= 1.0
    # the series has t=0 baseline + at most n_generations entries (early-stop allowed)
    assert 1 <= len(res["coop_series"]) <= 26
    assert res["generations_run"] <= 25


def test_run_rejects_bad_measure_window():
    m = CoevolvingNetworkPD(n=100, z=8, seed=0)
    with pytest.raises(ValueError):
        m.run(10, measure_last=0)
    with pytest.raises(ValueError):
        m.run(10, measure_last=50)


# -- steady-state estimator ---------------------------------------------------

def test_tail_mean_is_trailing_window_mean():
    series = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert tail_mean(series, window=2) == pytest.approx(0.45)   # mean(0.4, 0.5)
    assert tail_mean(series, window=100) == pytest.approx(0.3)  # whole series
    assert tail_mean([], window=5) == 0.0


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(n=200, z=10, W=8.0, seed=42, n_generations=40, measure_last=15)
    b = run_single(n=200, z=10, W=8.0, seed=42, n_generations=40, measure_last=15)
    assert a["coop_series"] == b["coop_series"]
    assert a["steady_coop_fraction"] == b["steady_coop_fraction"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(n=200, z=10, W=8.0, seed=1, n_generations=40, measure_last=15)
    b = run_single(n=200, z=10, W=8.0, seed=2, n_generations=40, measure_last=15)
    for res in (a, b):
        assert all(0.0 <= x <= 1.0 for x in res["coop_series"])


# -- qualitative sanity (the locked grade lives in run.py) --------------------

def test_agents_are_pd_nodes():
    m = CoevolvingNetworkPD(n=50, z=6, seed=0)
    assert len(m.nodes) == 50
    assert all(isinstance(nd, PDNode) for nd in m.nodes)
    assert all(nd.strategy in (COOPERATE, DEFECT) for nd in m.nodes)
