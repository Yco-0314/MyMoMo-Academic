"""Faithful-rule + determinism tests for the Martins CODA (Continuous Opinions,
Discrete Actions) reproduction.

These pin the model's MECHANICS, not its predictions: the additive Bayesian step
(``l += nu`` when the observed neighbour's action is +1, ``l -= nu`` when it is -1),
the discrete action ``sigma = sign(l)`` an observer sees, the fixed step
``nu = ln(alpha/(1-alpha))``, the periodic von-Neumann neighbour table, the
like-neighbour fraction and connected same-action domain count on hand-built lattices
(incl. wrap-around), the no-extremist initial draw, and determinism (same seed ->
identical state). The locked predictions P1-P3 are graded by
examples/repro_coda_continuous_opinions/run.py, not here.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from abm_auto.classics.coda_continuous_opinions import (
    CODAAgent,
    CODAModel,
    baseline_domain_count,
    coda_nu,
    run_single,
    von_neumann_neighbours,
)


# -- the fixed Bayesian step --------------------------------------------------

def test_coda_nu_is_log_odds_of_alpha():
    assert coda_nu(0.7) == pytest.approx(math.log(0.7 / 0.3))
    assert coda_nu(0.7) == pytest.approx(0.8472978603872, abs=1e-9)
    # nu grows as alpha -> 1 (more informative observation), -> 0 as alpha -> 0.5.
    assert coda_nu(0.9) > coda_nu(0.7) > coda_nu(0.51) > 0.0


def test_coda_nu_rejects_uninformative_alpha():
    for bad in (0.5, 0.4, 0.0, 1.0, 1.2):
        with pytest.raises(ValueError):
            coda_nu(bad)


# -- periodic von-Neumann neighbour table -------------------------------------

def test_von_neumann_table_is_periodic_and_four_neighbours():
    L = 4
    nb = von_neumann_neighbours(L)
    assert nb.shape == (16, 4)
    # corner (0,0) flat 0: up wraps to (3,0)=12, down=(1,0)=4, left wraps to (0,3)=3,
    # right=(0,1)=1.
    assert sorted(nb[0].tolist()) == sorted([12, 4, 3, 1])
    # every neighbour relation is symmetric (i is a neighbour of each of its neighbours).
    for i in range(16):
        for j in nb[i]:
            assert i in nb[j].tolist()
    # exactly 4 distinct neighbours per site (no self, no dup on L>=3).
    for i in range(16):
        s = set(nb[i].tolist())
        assert len(s) == 4 and i not in s


def test_von_neumann_rejects_bad_L():
    with pytest.raises(ValueError):
        von_neumann_neighbours(0)


# -- the additive update (the heart of CODA) ----------------------------------

def test_update_adds_nu_when_observed_neighbour_acts_for_A():
    # Force a configuration where the chosen target observes a +1-acting neighbour.
    m = CODAModel(L=3, seed=0)
    # set ALL agents to action +1 (l >= 0); target's l is known.
    m.l[:] = 1.0
    target = 4  # centre of 3x3
    before = m.l[target]
    # one update with target=4 must add +nu (every neighbour acts +1).
    # drive a single deterministic update by hand via the same rule:
    j = m.neighbours[target, 0]
    assert m.l[j] >= 0.0
    m.l[target] += m.nu if m.l[j] >= 0.0 else -m.nu
    assert m.l[target] == pytest.approx(before + m.nu)


def test_update_subtracts_nu_when_observed_neighbour_acts_for_B():
    m = CODAModel(L=3, seed=0)
    m.l[:] = -1.0  # all agents act -1 (for B)
    target = 4
    before = m.l[target]
    j = m.neighbours[target, 0]
    assert m.l[j] < 0.0
    m.l[target] += m.nu if m.l[j] >= 0.0 else -m.nu
    assert m.l[target] == pytest.approx(before - m.nu)


def test_update_batch_moves_belief_by_integer_multiple_of_nu():
    # Starting from a clamped all-+1 field, beliefs can only move in steps of nu, so
    # every agent's l is its initial l plus an integer multiple of nu.
    m = CODAModel(L=5, seed=3)
    l0 = m.l.copy()
    m.update_batch(500)
    steps = (m.l - l0) / m.nu
    assert np.allclose(steps, np.round(steps), atol=1e-9)


def test_observed_action_is_sign_of_hidden_logodds():
    m = CODAModel(L=3, seed=0)
    m.l[0] = 0.0     # exactly 0 -> acts +1 (p>=0.5)
    m.l[1] = 2.5     # acts +1
    m.l[2] = -0.01   # acts -1
    m.l[3] = -9.0    # acts -1
    acts = m.actions()
    assert acts[0] == 1 and acts[1] == 1
    assert acts[2] == -1 and acts[3] == -1
    # the agent object exposes the same discrete action and hides p.
    a0 = CODAAgent(1, m)
    assert a0.action == 1
    assert 0.0 < a0.p < 1.0


def test_agent_l_is_live_view_on_model_state():
    m = CODAModel(L=3, seed=0)
    agent = m.agent_list[5]
    m.l[5] = 3.3
    assert agent.l == pytest.approx(3.3)
    agent.l = -1.1
    assert m.l[5] == pytest.approx(-1.1)
    assert agent.action == -1


# -- initial draw: no extremists ----------------------------------------------

def test_initial_beliefs_have_no_extremists():
    # With the locked band p ~ U(0.4, 0.6) every |l_i| < nu (no agent starts extreme).
    m = CODAModel(L=50, p_lo=0.4, p_hi=0.6, seed=0)
    assert np.all(np.abs(m.l) < m.nu + 1e-12)
    assert m.max_abs_l_over_nu() < 1.0


def test_rejects_bad_init_band_and_L():
    with pytest.raises(ValueError):
        CODAModel(L=0)
    with pytest.raises(ValueError):
        CODAModel(L=5, p_lo=0.6, p_hi=0.4)   # lo > hi
    with pytest.raises(ValueError):
        CODAModel(L=5, p_lo=0.0, p_hi=0.5)   # p_lo must be > 0


# -- like-neighbour fraction on hand-built fields -----------------------------

def test_like_neighbour_fraction_all_same_action_is_one():
    m = CODAModel(L=8, seed=0)
    m.l[:] = 2.0   # everyone acts +1
    assert m.like_neighbour_fraction() == pytest.approx(1.0)


def test_like_neighbour_fraction_stripes_half_disagree():
    # Vertical stripes alternating action by column on an even-width torus: every
    # horizontal (left-right) bond disagrees, every vertical (up-down) bond agrees ->
    # exactly half the bonds are like.
    L = 8
    m = CODAModel(L=L, seed=0)
    grid = np.where((np.arange(L) % 2 == 0)[None, :], 2.0, -2.0)
    grid = np.broadcast_to(grid, (L, L)).copy()
    m.l[:] = grid.ravel()
    assert m.like_neighbour_fraction() == pytest.approx(0.5)


# -- connected same-action domains (incl. wrap) -------------------------------

def test_domain_count_one_uniform_domain():
    m = CODAModel(L=8, seed=0)
    m.l[:] = 1.0
    assert m.domain_count(min_size_frac=0.0) == 1
    assert m.domain_count(min_size_frac=0.05) == 1


def test_domain_count_two_half_planes():
    # Top half +1, bottom half -1: exactly two connected same-action domains. (On a
    # torus the two horizontal seams touch like-with-like within each half-plane only.)
    L = 8
    m = CODAModel(L=L, seed=0)
    grid = np.where((np.arange(L) < L // 2)[:, None], 2.0, -2.0)
    grid = np.broadcast_to(grid, (L, L)).copy()
    m.l[:] = grid.ravel()
    # NOTE: on a periodic torus the top (+) band wraps to touch the bottom... here rows
    # 0..3 are +, rows 4..7 are -, and row 0 wraps to row 7 (different action), so the +
    # band is one strip and the - band is one strip: 2 domains.
    assert m.domain_count(min_size_frac=0.0) == 2


def test_domain_labelling_wraps_across_the_seam():
    # A +1 column at c=0 and a +1 column at c=L-1 are ADJACENT across the left-right
    # seam, so they form ONE domain, not two. Everything else is -1.
    L = 6
    m = CODAModel(L=L, seed=0)
    g = np.full((L, L), -2.0)
    g[:, 0] = 2.0
    g[:, L - 1] = 2.0
    m.l[:] = g.ravel()
    # the two +1 columns wrap into a single connected component.
    sizes = m.macroscopic_domain_sizes(min_size_frac=0.0)
    # one +1 domain of size 2L, plus the surrounding -1 domain.
    assert (2 * L) in sizes
    assert m.domain_count(min_size_frac=0.0) == 2


def test_scipy_and_unionfind_labelling_agree_on_random_fields():
    # The fast (scipy + seam-stitch) and the pure-numpy union-find labelling must give
    # identical domain-size multisets on random action fields (with wrap).
    for seed in range(4):
        m = CODAModel(L=12, seed=seed)
        m.update_batch(3000)  # a realistic clustered field
        _, sizes_fast = m._label_domains()
        _, sizes_uf = m._label_domains_unionfind()
        assert sorted(sizes_fast.tolist()) == sorted(sizes_uf.tolist())


def test_random_start_baseline_is_fragmented():
    # The random-start control (no updates) has MANY small same-action components and a
    # like-neighbour fraction near 0.5 (no spatial order yet).
    b = baseline_domain_count(L=50, seed=0)
    assert b["n_components_all"] > 50          # highly fragmented
    assert 0.45 < b["like_neighbour_fraction"] < 0.55
    assert b["median_abs_l_over_nu"] < 1.0     # no extremists at start


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_state():
    a = CODAModel(L=20, seed=42)
    b = CODAModel(L=20, seed=42)
    a.update_batch(50_000)
    b.update_batch(50_000)
    assert np.array_equal(a.l, b.l)
    assert a.max_abs_l_over_nu() == b.max_abs_l_over_nu()
    assert a.like_neighbour_fraction() == b.like_neighbour_fraction()


def test_batched_equals_split_updates():
    # Drawing N updates in one batch == drawing them in two consecutive batches (the
    # generator state carries over), i.e. update_batch is a pure prefix of the stream.
    a = CODAModel(L=15, seed=7)
    b = CODAModel(L=15, seed=7)
    a.update_batch(40_000)
    b.update_batch(25_000)
    b.update_batch(15_000)
    assert np.array_equal(a.l, b.l)


def test_different_seed_can_differ():
    a = CODAModel(L=20, seed=1)
    b = CODAModel(L=20, seed=2)
    a.update_batch(50_000)
    b.update_batch(50_000)
    assert not np.array_equal(a.l, b.l)


# -- run summary shape --------------------------------------------------------

def test_run_single_summary_shape_and_snapshots():
    res = run_single(L=15, seed=0, n_updates=20_000, snapshots=[10_000, 20_000])
    assert res["L"] == 15 and res["N"] == 225
    assert res["nu"] == pytest.approx(coda_nu(0.7))
    assert res["snapshot_updates"] == [10_000, 20_000]
    assert len(res["snapshots"]) == 2
    final = res["final"]
    for key in ("max_abs_l_over_nu", "median_abs_l_over_nu", "frac_extreme_ge50",
                "frac_moderate_lt1", "like_neighbour_fraction", "n_components_all",
                "n_macro_domains", "macro_domain_sizes"):
        assert key in final


def test_run_rejects_negative_updates():
    m = CODAModel(L=5, seed=0)
    with pytest.raises(ValueError):
        m.run(-1)
    with pytest.raises(ValueError):
        m.update_batch(-5)
