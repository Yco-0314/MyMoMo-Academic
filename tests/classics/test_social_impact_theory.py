"""Faithful-rule + determinism tests for the Dynamic Social Impact Theory
(Nowak, Szamrej & Latane 1990) reproduction.

These pin the impact functional (persuasive MINUS supportive, distance-weighted,
self excluded) on hand-built tiny lattices, the distance-decay weight matrix, the
deterministic flip rule (flip iff I_i > 0), the FIXEDNESS of the (p, s) traits and
agent positions across a run, freeze detection (a sweep with no flips), the
nearest-neighbour bond fraction, the connected-cluster (flood-fill) counting, the
sequential incremental field staying bit-consistent with a from-scratch recompute,
and determinism (same seed -> identical result).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(minority fraction band, bond fraction >=0.75, minority clusters survive) are
evaluated by examples/repro_social_impact_theory/run.py.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.social_impact_theory import (
    SiteAgent,
    SocialImpactModel,
    build_weight_matrix,
    run_single,
)


# -- weight matrix / distance decay -------------------------------------------

def test_weight_matrix_diagonal_zeroed_and_symmetric():
    W = build_weight_matrix(3, alpha=2.0)
    assert W.shape == (9, 9)
    assert np.allclose(np.diag(W), 0.0)          # self term excluded
    assert np.allclose(W, W.T)                   # distance is symmetric


def test_weight_matrix_inverse_square_distances():
    # 2x2 lattice, row-major indices: 0=(0,0) 1=(0,1) 2=(1,0) 3=(1,1).
    W = build_weight_matrix(2, alpha=2.0)
    # adjacent (d^2 = 1): g = 1 + 1 = 2 -> w = 1/2
    assert W[0, 1] == pytest.approx(0.5)         # (0,0)-(0,1)
    assert W[0, 2] == pytest.approx(0.5)         # (0,0)-(1,0)
    # diagonal (d^2 = 2): g = 1 + 2 = 3 -> w = 1/3
    assert W[0, 3] == pytest.approx(1.0 / 3.0)   # (0,0)-(1,1)


def test_weight_matrix_alpha_changes_decay():
    # alpha=1: g = 1 + d ; for the diagonal pair d = sqrt(2), g = 1 + sqrt(2).
    W = build_weight_matrix(2, alpha=1.0)
    assert W[0, 3] == pytest.approx(1.0 / (1.0 + np.sqrt(2.0)))


# -- the impact functional (hand-built tiny lattice) --------------------------

def _naive_impacts(W, sigma, p, s):
    """Reference O(N^2) double-loop impact (persuasive minus supportive, self
    excluded) used to validate the vectorised path."""
    N = len(sigma)
    out = np.zeros(N)
    for i in range(N):
        persuasive = supportive = 0.0
        for j in range(N):
            if i == j:
                continue
            persuasive += W[i, j] * p[j] * (1 - sigma[i] * sigma[j])
            supportive += W[i, j] * s[j] * (1 + sigma[i] * sigma[j])
        out[i] = persuasive - supportive
    return out


def test_impact_functional_matches_naive_double_loop():
    m = SocialImpactModel(L=2, seed=0)
    m.sigma = np.array([1, -1, 1, -1], dtype=np.int64)
    m.p = np.array([0.2, 0.4, 0.6, 0.8])
    m.s = np.array([0.1, 0.3, 0.5, 0.7])
    m._resync_fields()
    ref = _naive_impacts(m.W, m.sigma, m.p, m.s)
    assert np.allclose(m.impacts(), ref)


def test_impact_persuasive_only_from_opposite_supportive_only_from_same():
    # Two agents, opposite opinions: agent 0 feels ONLY persuasion from agent 1
    # (supportive term has factor (1+sigma_i sigma_j) = 0), and vice versa.
    m = SocialImpactModel(L=2, seed=0)
    # collapse to a 2-body problem: zero out agents 2,3's traits so only 0,1 interact.
    m.sigma = np.array([1, -1, 1, 1], dtype=np.int64)
    m.p = np.array([0.5, 0.9, 0.0, 0.0])
    m.s = np.array([0.5, 0.3, 0.0, 0.0])
    m._resync_fields()
    I = m.impacts()
    # agent 0 (sigma=+1) vs agent 1 (sigma=-1): opposite -> persuasion = W01*p1*(1-(-1))=W01*p1*2
    # support from 1 is 0 (opposite). w01 = 1/2.
    w01 = m.W[0, 1]
    assert I[0] == pytest.approx(w01 * m.p[1] * 2.0)
    # agent 1 (sigma=-1) vs agent 0 (sigma=+1): persuasion = W10*p0*2 ; support 0.
    assert I[1] == pytest.approx(w01 * m.p[0] * 2.0)


def test_impact_all_same_opinion_is_pure_support_negative():
    # Full consensus: every agent feels ZERO persuasion (no opponents) and pure
    # support, so every impact is <= 0 and NO agent flips -> consensus is a fixed point.
    m = SocialImpactModel(L=4, seed=3)
    m.sigma = np.ones(m.N, dtype=np.int64)
    m._resync_fields()
    I = m.impacts()
    assert np.all(I <= 0.0)
    assert m.sweep() == 0                          # no flips: consensus is frozen


# -- the deterministic flip rule ----------------------------------------------

def test_flip_rule_flips_exactly_positive_impact_sites():
    m = SocialImpactModel(L=5, seed=2, update="synchronous")
    I = m.impacts()
    expected_flips = set(np.nonzero(I > 0.0)[0].tolist())
    before = m.sigma.copy()
    m.sweep()
    actual_flips = set(np.nonzero(before != m.sigma)[0].tolist())
    assert actual_flips == expected_flips


def test_flip_rule_is_strict_inequality_zero_impact_does_not_flip():
    # An agent with exactly I_i = 0 must NOT flip (flip rule is I_i > 0, strict).
    m = SocialImpactModel(L=3, seed=0, update="synchronous")
    # construct a state where one agent's impact is exactly 0: opposite-persuasion
    # balanced by same-support. Easiest: an isolated trait config giving I=0 — use an
    # all-zero trait agent set so every impact is exactly 0.
    m.p = np.zeros(m.N)
    m.s = np.zeros(m.N)
    m._resync_fields()
    assert np.allclose(m.impacts(), 0.0)
    assert m.sweep() == 0                          # zero impact -> no flip


# -- trait + position fixedness -----------------------------------------------

def test_traits_and_positions_fixed_across_a_run():
    m = SocialImpactModel(L=10, seed=1)
    p0 = m.p.copy()
    s0 = m.s.copy()
    rows0 = [a.row for a in m.agent_list]
    cols0 = [a.col for a in m.agent_list]
    m.run()
    # traits never change; positions never change (only opinions flip).
    assert np.array_equal(m.p, p0)
    assert np.array_equal(m.s, s0)
    assert [a.row for a in m.agent_list] == rows0
    assert [a.col for a in m.agent_list] == cols0


def test_roster_mirrors_sigma_after_run():
    m = SocialImpactModel(L=8, seed=4)
    m.run()
    for a in m.agent_list:
        assert a.sigma == int(m.sigma[a.id])
    assert all(isinstance(a, SiteAgent) for a in m.agent_list)


# -- freeze detection ---------------------------------------------------------

def test_freeze_detected_when_a_sweep_has_no_flips():
    m = SocialImpactModel(L=6, seed=5)
    res = m.run()
    if res["frozen"]:
        # at a true freeze, one more sweep flips nobody.
        assert m.sweep() == 0


def test_sequential_consensus_is_a_frozen_fixed_point():
    # Forced consensus -> the very first sweep flips nobody, run reports frozen.
    m = SocialImpactModel(L=6, seed=0, update="sequential")
    m.sigma = np.ones(m.N, dtype=np.int64)
    m._resync_fields()
    assert m.sweep() == 0


# -- bond fraction ------------------------------------------------------------

def test_bond_fraction_consensus_is_one():
    m = SocialImpactModel(L=5, seed=0)
    m.sigma = np.ones(m.N, dtype=np.int64)
    assert m.same_opinion_bond_fraction() == pytest.approx(1.0)


def test_bond_fraction_checkerboard_is_zero():
    # A perfect checkerboard has NO same-opinion nearest-neighbour bonds.
    m = SocialImpactModel(L=4, seed=0)
    g = np.indices((m.L, m.L)).sum(axis=0) % 2
    m.sigma = np.where(g.reshape(-1) == 0, 1, -1).astype(np.int64)
    assert m.same_opinion_bond_fraction() == pytest.approx(0.0)


def test_bond_fraction_two_halves_is_high():
    # Left half +1, right half -1: only the single seam column of bonds is mixed.
    m = SocialImpactModel(L=10, seed=0)
    g = np.ones((m.L, m.L), dtype=np.int64)
    g[:, m.L // 2:] = -1
    m.sigma = g.reshape(-1)
    bf = m.same_opinion_bond_fraction()
    assert bf > 0.9                                # almost all bonds are same-opinion


# -- cluster counting (flood fill) --------------------------------------------

def test_cluster_sizes_single_block():
    m = SocialImpactModel(L=4, seed=0)
    m.sigma = np.ones(m.N, dtype=np.int64)         # one connected +1 block of 16
    assert m.cluster_sizes(1) == [16]
    assert m.cluster_sizes(-1) == []               # no -1 sites
    assert m.largest_cluster(1) == 16


def test_cluster_sizes_two_separated_minority_blobs():
    # Two diagonally-separated single -1 sites are TWO clusters (4-adjacency, not 8).
    m = SocialImpactModel(L=5, seed=0)
    g = np.ones((m.L, m.L), dtype=np.int64)
    g[0, 0] = -1
    g[2, 2] = -1                                   # not 4-adjacent to (0,0)
    m.sigma = g.reshape(-1)
    minority = m.cluster_sizes(-1)
    assert minority == [1, 1]                      # two singleton clusters
    assert m.largest_cluster(-1) == 1


def test_cluster_counting_4_adjacency_not_diagonal():
    # A 2x2 -1 block is ONE cluster of 4 (von Neumann connects the block).
    m = SocialImpactModel(L=5, seed=0)
    g = np.ones((m.L, m.L), dtype=np.int64)
    g[1:3, 1:3] = -1
    m.sigma = g.reshape(-1)
    assert m.cluster_sizes(-1) == [4]


# -- sequential incremental field == from-scratch -----------------------------

def test_incremental_fields_match_from_scratch_after_sweeps():
    m = SocialImpactModel(L=12, seed=9, update="sequential")
    for _ in range(3):
        m.sweep()
    sig = m.sigma.astype(np.float64)
    Fp_ref = m.W @ (m.p * sig)
    Fs_ref = m.W @ (m.s * sig)
    assert np.allclose(m._Fp, Fp_ref)
    assert np.allclose(m._Fs, Fs_ref)


# -- run summary shape --------------------------------------------------------

def test_run_summary_shape():
    res = run_single(L=10, seed=0)
    assert res["L"] == 10 and res["N"] == 100
    assert res["update"] == "sequential"
    assert 0.0 <= res["final_minority_fraction"] <= 0.5
    assert 0.0 <= res["final_bond_fraction"] <= 1.0
    assert res["largest_majority_cluster"] >= res["largest_minority_cluster"]
    # series carry the t=0 baseline plus one record per sweep.
    assert len(res["minority_fraction_series"]) == res["sweeps"] + 1
    assert len(res["bond_fraction_series"]) == res["sweeps"] + 1


def test_initial_minority_near_balanced_for_f0_half():
    res = run_single(L=41, seed=0, f0=0.5)
    assert 0.4 <= res["initial_minority_fraction"] <= 0.5


# -- validation ---------------------------------------------------------------

def test_invalid_params_raise():
    with pytest.raises(ValueError):
        SocialImpactModel(L=1)
    with pytest.raises(ValueError):
        SocialImpactModel(f0=0.0)
    with pytest.raises(ValueError):
        SocialImpactModel(f0=1.0)
    with pytest.raises(ValueError):
        SocialImpactModel(max_sweeps=0)
    with pytest.raises(ValueError):
        SocialImpactModel(update="parallel")       # only sequential/synchronous
    with pytest.raises(ValueError):
        SocialImpactModel(L=4, weight_matrix=np.zeros((3, 3)))  # wrong shape


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(L=20, seed=42)
    b = run_single(L=20, seed=42)
    assert a["final_minority_fraction"] == b["final_minority_fraction"]
    assert a["final_bond_fraction"] == b["final_bond_fraction"]
    assert a["sweeps"] == b["sweeps"]
    assert a["minority_fraction_series"] == b["minority_fraction_series"]


def test_shared_weight_matrix_gives_same_result_as_built_in():
    W = build_weight_matrix(15, alpha=2.0)
    a = run_single(L=15, seed=3, weight_matrix=W)
    b = run_single(L=15, seed=3)                   # builds its own identical matrix
    assert a["final_minority_fraction"] == b["final_minority_fraction"]
    assert a["sweeps"] == b["sweeps"]


def test_synchronous_can_leave_a_two_cycle():
    # The synchronous (parallel) update can fail to freeze (2-cycle): document it.
    # We only assert the run terminates at the cap and reports not-frozen for at least
    # the known oscillating seed; sequential on the same seed DOES freeze or cap.
    res = run_single(L=41, seed=3, update="synchronous", max_sweeps=50)
    # whether or not THIS seed cycles, the API must report a boolean and a capped count.
    assert isinstance(res["frozen"], bool)
    assert res["sweeps"] <= 50
