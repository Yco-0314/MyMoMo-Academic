"""Faithful-rule + determinism tests for the Heider social balance / Antal-Krapivsky-Redner
(2005) constrained-triad-dynamics (CTD) reproduction.

These pin the triad-balance predicate (product of the three edge signs), the global energy
counter (imbalanced-triangle count) on hand-built tiny graphs, the incremental Delta for a
single edge flip equalling the brute-force recount, the AKR constraint (a CTD step never
INCREASES global energy), recognition of a known balanced configuration as absorbing
(energy 0) AND as a valid <=2-faction partition, all-+ paradise, and determinism (same
seed -> identical run).

They are FAITHFULNESS tests, NOT prediction tests — the locked predictions P1-P3 (reaches
balance; valid <=2-faction; frustration non-increasing) are evaluated by
examples/repro_heider_balance/run.py.
"""
from __future__ import annotations

from itertools import combinations

import pytest

from abm_auto.classics.heider_balance import (
    HeiderBalanceModel,
    count_imbalanced_triangles,
    faction_sizes,
    is_valid_two_faction_balance,
    recover_factions,
    run_single,
    triad_is_balanced,
)


# -- helpers ------------------------------------------------------------------

def _sym(n, pairs_minus):
    """Build an n-node all-+ symmetric sign matrix, then set the given pairs to -1."""
    s = [[0] * n for _ in range(n)]
    for i, j in combinations(range(n), 2):
        s[i][j] = s[j][i] = 1
    for i, j in pairs_minus:
        s[i][j] = s[j][i] = -1
    return s


# -- the triad-balance predicate (product of signs) ---------------------------

def test_triad_balanced_by_sign_product():
    # 0 negative edges (+,+,+) -> balanced.
    assert triad_is_balanced(1, 1, 1) is True
    # 2 negative edges -> balanced ("enemy of my enemy is my friend").
    assert triad_is_balanced(-1, -1, 1) is True
    assert triad_is_balanced(-1, 1, -1) is True
    assert triad_is_balanced(1, -1, -1) is True
    # 1 negative edge -> imbalanced.
    assert triad_is_balanced(-1, 1, 1) is False
    assert triad_is_balanced(1, -1, 1) is False
    assert triad_is_balanced(1, 1, -1) is False
    # 3 negative edges -> imbalanced (all-enemies triangle is frustrated).
    assert triad_is_balanced(-1, -1, -1) is False


# -- the global energy counter on hand-built tiny graphs ----------------------

def test_energy_all_positive_triangle_is_zero():
    s = _sym(3, [])
    assert count_imbalanced_triangles(s) == 0


def test_energy_single_negative_edge_triangle_is_one():
    # One negative edge in a triangle -> exactly one imbalanced triangle.
    s = _sym(3, [(0, 1)])
    assert count_imbalanced_triangles(s) == 1


def test_energy_two_factions_is_zero():
    # 4 nodes split {0,1} vs {2,3}: + within each pair, - across -> fully balanced.
    s = _sym(4, [(0, 2), (0, 3), (1, 2), (1, 3)])
    assert count_imbalanced_triangles(s) == 0
    # Every triangle here has exactly two minus edges -> balanced.


def test_energy_all_negative_K4_counts_all_triangles_imbalanced():
    # All-enemies K4: every triangle has 3 negative edges -> all C(4,3)=4 imbalanced.
    s = _sym(4, list(combinations(range(4), 2)))
    assert count_imbalanced_triangles(s) == 4


# -- incremental Delta == brute-force recount for a single flip ---------------

def test_incremental_delta_equals_bruteforce_recount():
    # Over many random graphs and every edge, the incremental Delta must equal the change
    # in the FULL imbalanced-triangle count produced by actually flipping that edge.
    for seed in range(8):
        m = HeiderBalanceModel(n=12, seed=seed)
        before = count_imbalanced_triangles(m.signs)
        assert m.energy == before
        for a, b in combinations(range(m.n), 2):
            delta = m.delta_for_flip(a, b)
            # Brute-force: flip, recount, flip back.
            m.signs[a][b] = -m.signs[a][b]
            m.signs[b][a] = m.signs[a][b]
            after = count_imbalanced_triangles(m.signs)
            m.signs[a][b] = -m.signs[a][b]
            m.signs[b][a] = m.signs[a][b]
            assert delta == after - before, f"seed={seed} edge=({a},{b})"


def test_apply_flip_keeps_energy_consistent_with_recount():
    # After committing a chosen flip, the incrementally-maintained energy must equal a fresh
    # brute-force recount.
    m = HeiderBalanceModel(n=10, seed=3)
    for _ in range(20):
        if m.is_balanced():
            break
        m.ctd_step()
        assert m.energy == count_imbalanced_triangles(m.signs)


# -- the CTD step never increases global energy (AKR constraint) --------------

def test_ctd_step_never_increases_energy():
    for seed in range(10):
        m = HeiderBalanceModel(n=14, seed=seed)
        prev = m.energy
        for _ in range(500):
            if m.is_balanced():
                break
            m.ctd_step()
            assert m.energy <= prev, f"energy rose: {prev} -> {m.energy} (seed {seed})"
            prev = m.energy


def test_full_run_energy_series_is_non_increasing():
    for seed in range(10):
        res = run_single(n=14, seed=seed)
        series = res["energy_series"]
        assert all(series[t + 1] <= series[t] for t in range(len(series) - 1))
        assert res["energy_non_increasing"] is True


# -- a known balanced configuration: absorbing + valid <=2-faction ------------

def test_two_faction_graph_is_absorbing_and_valid_partition():
    # Hand-built balanced two-faction graph on 6 nodes: {0,1,2} vs {3,4,5}.
    n = 6
    minus = [(i, j) for i in range(3) for j in range(3, 6)]
    s = _sym(n, minus)
    assert count_imbalanced_triangles(s) == 0           # absorbing (energy 0)
    assert is_valid_two_faction_balance(s) is True
    colour = recover_factions(s)
    assert colour is not None
    # The two recovered groups are exactly {0,1,2} and {3,4,5} (up to colour swap).
    g0 = {i for i in range(n) if colour[i] == colour[0]}
    assert g0 == {0, 1, 2} or g0 == {3, 4, 5}
    assert set(faction_sizes(s)) == {3, 3}


def test_model_recognises_injected_two_faction_state_as_absorbing():
    # Inject a balanced two-faction state into a model and confirm it reads as absorbing.
    m = HeiderBalanceModel(n=8, seed=0)
    colour = [0, 0, 0, 0, 1, 1, 1, 1]
    for i, j in combinations(range(8), 2):
        sign = 1 if colour[i] == colour[j] else -1
        m.signs[i][j] = m.signs[j][i] = sign
    m.energy = count_imbalanced_triangles(m.signs)
    assert m.energy == 0
    assert m.is_balanced() is True
    assert m.ctd_step() is False                        # nothing to do; absorbing


def test_imbalanced_configuration_is_not_a_valid_partition():
    # A single frustrated triangle has no valid <=2-faction colouring.
    s = _sym(3, [(0, 1)])
    assert is_valid_two_faction_balance(s) is False
    assert recover_factions(s) is None
    assert faction_sizes(s) is None


# -- all-+ graph is paradise --------------------------------------------------

def test_all_positive_graph_is_paradise():
    n = 7
    s = _sym(n, [])
    assert count_imbalanced_triangles(s) == 0
    assert is_valid_two_faction_balance(s) is True
    sizes = faction_sizes(s)
    # Paradise: one group holds everyone, the other is empty.
    assert set(sizes) == {n, 0}


def test_model_all_positive_is_paradise_and_absorbing():
    m = HeiderBalanceModel(n=9, seed=0)
    for i, j in combinations(range(9), 2):
        m.signs[i][j] = m.signs[j][i] = 1
    m.energy = count_imbalanced_triangles(m.signs)
    res = m.run()
    assert res["reached_balance"] is True
    assert res["is_paradise"] is True
    assert res["faction_sizes"] == [9, 0] or res["faction_sizes"] == [0, 9]
    assert res["n_steps"] == 0                          # already absorbing


# -- construction + invariants ------------------------------------------------

def test_signs_are_symmetric_pm1_with_zero_diagonal():
    m = HeiderBalanceModel(n=30, seed=1)
    for i in range(m.n):
        assert m.signs[i][i] == 0
        for j in range(i + 1, m.n):
            assert m.signs[i][j] in (-1, 1)
            assert m.signs[i][j] == m.signs[j][i]


def test_too_few_nodes_raises():
    with pytest.raises(ValueError):
        HeiderBalanceModel(n=2)


def test_run_summary_shape():
    res = run_single(n=30, seed=0)
    assert res["n"] == 30 and res["seed"] == 0
    assert res["energy_series"][0] == res["initial_energy"]
    assert isinstance(res["reached_balance"], bool)
    assert isinstance(res["final_signs"], list) and len(res["final_signs"]) == 30


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_run():
    a = run_single(n=30, seed=42)
    b = run_single(n=30, seed=42)
    assert a["energy_series"] == b["energy_series"]
    assert a["final_signs"] == b["final_signs"]
    assert a["n_steps"] == b["n_steps"]
    assert a["faction_partition"] == b["faction_partition"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(n=30, seed=1)
    b = run_single(n=30, seed=2)
    for res in (a, b):
        assert res["energy_series"][0] >= res["energy_series"][-1]   # non-increasing overall
        assert res["final_energy"] >= 0


# -- qualitative sanity (the locked grade lives in run.py) --------------------

def test_thirty_node_runs_reach_balance():
    # Faithfulness sanity, not the locked grade: CTD on a complete K30 graph reaches a
    # balanced absorbing state, which is a valid <=2-faction partition.
    res = run_single(n=30, seed=0)
    assert res["reached_balance"] is True
    assert res["final_energy"] == 0
    assert res["is_two_faction_balance"] is True
