"""Faithful-rule + determinism tests for the Independent Cascade + Influence
Maximization reproduction (Goldenberg-Libai-Muller 2001 / Kempe-Kleinberg-Tardos 2003).

These pin the IC mechanism (single-shot per-edge Bernoulli activation, synchronous
frontier spread to quiescence), the live-edge equivalence used by the fast estimator,
submodularity on a hand-verifiable instance, CELF == naive greedy, greedy > random, and
determinism (same seed -> identical result). They are faithfulness tests, NOT prediction
tests (the P1/P2/P3 predictions are evaluated by
examples/repro_independent_cascade/run.py).
"""
from __future__ import annotations

import random

import networkx as nx

from abm_auto.classics.independent_cascade import (
    ICModel,
    brute_force_opt,
    build_directed_er,
    find_transition_crossing,
    greedy_seed_set,
    influence_spread,
    random_seed_set,
    single_seed_reach_sweep,
    submodularity_test,
)


# ── IC mechanism (hand-verifiable) ────────────────────────────────────────────

def test_directed_path_p1_full_cascade_is_hand_verifiable():
    # Directed path 0 -> 1 -> 2 -> 3 -> 4, p = 1.0, seed {0}. With certain activation
    # the cascade marches down the path one node per synchronous step: all 5 activate.
    g = nx.DiGraph([(0, 1), (1, 2), (2, 3), (3, 4)])
    res = ICModel(g, p=1.0, seed_set=[0], seed=0).run()
    assert res["final_active_count"] == 5
    assert res["final_active_fraction"] == 1.0
    # Synchronous single-shot spread: seed(1) -> 2 -> 3 -> 4 -> 5, one new per step.
    assert res["active_series"] == [1, 2, 3, 4, 5, 5]


def test_p0_no_spread_seed_stays_alone():
    # p = 0.0: no edge ever fires; only the seed is ever active.
    g = nx.DiGraph([(0, 1), (1, 2), (2, 3), (3, 4)])
    res = ICModel(g, p=0.0, seed_set=[0], seed=0).run()
    assert res["final_active_count"] == 1
    assert res["active_series"] == [1, 1]


def test_single_shot_per_edge_one_attempt_only():
    # A single directed edge 0 -> 1. Node 0 gets EXACTLY ONE attempt on edge 0->1.
    # Over many RNG seeds the empirical activation frequency of node 1 must match p
    # (single-shot, not repeated-until-success): so with p = 0.3, roughly 30% activate,
    # NOT ~100% (which repeated attempts would give).
    g = nx.DiGraph([(0, 1)])
    p = 0.3
    trials = 4000
    activated = 0
    for s in range(trials):
        res = ICModel(g, p=p, seed_set=[0], seed=s).run()
        activated += 1 if res["final_active_count"] == 2 else 0
    freq = activated / trials
    assert abs(freq - p) < 0.03  # single-shot -> frequency ~ p (not ~1.0)


def test_direction_matters_no_backflow():
    # Edge only 0 -> 1 (no 1 -> 0). Seeding {1} with p=1.0 cannot reach 0.
    g = nx.DiGraph([(0, 1)])
    res = ICModel(g, p=1.0, seed_set=[1], seed=0).run()
    assert res["final_active_count"] == 1  # node 1 only; no back-flow to 0


def test_synchronous_not_chaining_within_a_step():
    # Directed path 0->1->2 with p=1.0. Activations must NOT chain within one step:
    # at step 1 only node 1 activates (from seed 0); node 2 activates at step 2.
    g = nx.DiGraph([(0, 1), (1, 2)])
    res = ICModel(g, p=1.0, seed_set=[0], seed=0).run()
    assert res["active_series"] == [1, 2, 3, 3]  # +1 per synchronous step


def test_seed_set_all_active_at_baseline():
    g = nx.DiGraph([(0, 1), (2, 3)])
    res = ICModel(g, p=0.0, seed_set=[0, 2], seed=0).run()
    assert res["active_series"][0] == 2  # both seeds active at t=0


# ── determinism ───────────────────────────────────────────────────────────────

def test_determinism_same_seed_identical_result():
    g = build_directed_er(500, z=4.0, seed=42)
    r1 = ICModel(g, p=0.4, seed_set=[7], seed=99).run()
    r2 = ICModel(g, p=0.4, seed_set=[7], seed=99).run()
    assert r1["final_active_count"] == r2["final_active_count"]
    assert r1["active_series"] == r2["active_series"]


def test_influence_spread_deterministic_given_rng():
    g = build_directed_er(300, z=6.0, seed=1)
    a = influence_spread(g, [0, 1], p=0.1, n_sims=200, rng=random.Random(3))
    b = influence_spread(g, [0, 1], p=0.1, n_sims=200, rng=random.Random(3))
    assert a == b


# ── graph builder ─────────────────────────────────────────────────────────────

def test_build_directed_er_mean_out_degree_matches_z():
    n, z = 3000, 8.0
    g = build_directed_er(n, z, seed=1)
    mean_out = g.number_of_edges() / n     # directed: each arc counts once
    assert abs(mean_out - z) < 0.3         # Bernoulli arc draw, close to z


def test_build_directed_er_is_directed():
    g = build_directed_er(100, z=5.0, seed=0)
    assert g.is_directed()


# ── influence spread is monotone and matches forward sim ──────────────────────

def test_influence_spread_matches_icmodel_forward_sim_at_p1():
    # At p=1.0 the estimator and the ICModel both give the deterministic reachable set.
    g = nx.DiGraph([(0, 1), (1, 2), (2, 3), (0, 4)])
    sig = influence_spread(g, [0], p=1.0, n_sims=5, rng=random.Random(0))
    res = ICModel(g, p=1.0, seed_set=[0], seed=0).run()
    assert sig == res["final_active_count"] == 5  # all reachable from 0


def test_influence_spread_monotone_in_seed_set():
    g = build_directed_er(200, z=6.0, seed=2)
    rng = random.Random(5)
    small = influence_spread(g, [0], p=0.15, n_sims=400, rng=rng)
    big = influence_spread(g, [0, 1, 2], p=0.15, n_sims=400, rng=rng)
    assert big >= small  # superset never spreads less (monotone)


# ── submodularity holds on a tiny hand-checkable instance ─────────────────────

def test_submodularity_holds_on_small_graph():
    g = build_directed_er(200, z=6.0, seed=7)
    res = submodularity_test(g, p=0.1, n_pairs=40, n_sims=400, rng=random.Random(11))
    # On a real IC instance submodularity should hold on the large majority of pairs.
    assert res["hold_fraction"] >= 0.9
    assert res["n_pairs"] >= 30


def test_submodularity_diminishing_returns_concrete():
    # Star out-hub: 0 -> {1,2,3,4,5}, plus 6 -> {1,2,3,4,5}. Adding hub 6 to A={0}
    # helps a lot, but adding hub 6 to a B that already reaches the leaves via other
    # seeds helps less -> diminishing returns. We just require the aggregate gate holds.
    edges = [(0, i) for i in range(1, 6)] + [(6, i) for i in range(1, 6)]
    g = nx.DiGraph(edges)
    res = submodularity_test(g, p=0.9, n_pairs=30, n_sims=600, rng=random.Random(4))
    assert res["hold_fraction"] >= 0.9


# ── greedy / CELF / random ────────────────────────────────────────────────────

def test_celf_equals_naive_greedy():
    # CELF is exact: it must return the SAME seed set as naive greedy on the same
    # instance with the same MC RNG stream reset for each run.
    g = build_directed_er(120, z=5.0, seed=3)
    naive, sig_n, _ = greedy_seed_set(g, 3, p=0.1, n_sims=300,
                                      rng=random.Random(0), use_celf=False)
    celf, sig_c, _ = greedy_seed_set(g, 3, p=0.1, n_sims=300,
                                     rng=random.Random(0), use_celf=True)
    assert set(naive) == set(celf)


def test_greedy_beats_random():
    g = build_directed_er(150, z=6.0, seed=8)
    greedy, sig_g, _ = greedy_seed_set(g, 3, p=0.1, n_sims=500, rng=random.Random(1))
    # Average several random k-sets so the comparison is not a lucky draw.
    rng = random.Random(2)
    rand_sigs = [random_seed_set(g, 3, p=0.1, n_sims=500, rng=rng)[1] for _ in range(5)]
    mean_rand = sum(rand_sigs) / len(rand_sigs)
    assert sig_g > mean_rand


def test_greedy_meets_1_minus_1_over_e_of_opt_small():
    # On a tiny instance where brute force is feasible, greedy must be within the
    # 1-1/e (~0.632) guarantee of OPT for k=2 (in practice far closer).
    g = build_directed_er(30, z=4.0, seed=5)
    greedy, sig_g, _ = greedy_seed_set(g, 2, p=0.2, n_sims=800, rng=random.Random(0))
    opt_set, sig_opt = brute_force_opt(g, 2, p=0.2, n_sims=800, rng=random.Random(0))
    assert sig_g >= 0.632 * sig_opt


# ── percolation sweep shape (not the P1 prediction, just the machinery) ───────

def test_sweep_shape_and_crossing_detector():
    sweep = single_seed_reach_sweep(400, [0.5, 1.0, 2.0], z=6.0, n_graphs=3)
    assert len(sweep) == 3
    for row in sweep:
        assert 0.0 <= row["mean_reached_fraction"] <= 1.0
    # sub-critical lambda=0.5 should reach less than super-critical lambda=2.0
    lo = next(r for r in sweep if r["lambda"] == 0.5)["mean_reached_fraction"]
    hi = next(r for r in sweep if r["lambda"] == 2.0)["mean_reached_fraction"]
    assert lo <= hi


def test_find_transition_crossing_interpolates():
    fake = [
        {"lambda": 0.5, "mean_reached_fraction": 0.01},
        {"lambda": 1.0, "mean_reached_fraction": 0.05},
        {"lambda": 1.5, "mean_reached_fraction": 0.30},
    ]
    cross = find_transition_crossing(fake, crossing_fraction=0.10)
    assert cross is not None and 1.0 < cross < 1.5
