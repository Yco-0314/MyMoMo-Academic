"""Faithful-rule + determinism tests for the Sznajd (2000) 2D opinion reproduction.

These pin the "united we stand" plaquette rule (unanimous 2x2 -> persuade the 8
edge-adjacent outer neighbours), the geometry (8 neighbours, no diagonal corners),
periodic wraparound, the frozen-state stop, and determinism (same seed -> identical
result). They are faithfulness tests, NOT prediction tests (the locked predictions
P1-P3 are evaluated by examples/repro_sznajd_opinion/run.py).
"""
from __future__ import annotations

from abm_auto.classics.sznajd import (
    SznajdModel,
    run_many_seeds,
    run_single,
)


def _set_all(model: SznajdModel, value: int) -> None:
    for r in range(model.L):
        for c in range(model.L):
            model.grid[r][c].opinion = value


def test_plaquette_cells_are_the_2x2_block_with_wraparound():
    m = SznajdModel(L=5, d=0.5, seed=0)
    # Anchor (1,1): block is (1,1),(1,2),(2,1),(2,2).
    assert set(m._plaquette_cells(1, 1)) == {(1, 1), (1, 2), (2, 1), (2, 2)}
    # Anchor at the bottom-right wraps: (4,4) -> (4,4),(4,0),(0,4),(0,0).
    assert set(m._plaquette_cells(4, 4)) == {(4, 4), (4, 0), (0, 4), (0, 0)}


def test_perimeter_is_eight_edge_neighbours_no_corners():
    m = SznajdModel(L=6, d=0.5, seed=0)
    peri = m._perimeter_cells(2, 2)
    plaq = set(m._plaquette_cells(2, 2))
    # Exactly 8, all distinct, none inside the plaquette.
    assert len(peri) == 8
    assert len(set(peri)) == 8
    assert plaq.isdisjoint(set(peri))
    # The four diagonal corners of the surrounding 4x4 frame are NOT persuaded.
    frame_corners = {(1, 1), (1, 4), (4, 1), (4, 4)}
    assert frame_corners.isdisjoint(set(peri))
    # They are exactly the edge-adjacent cells (2 above, 2 below, 2 left, 2 right).
    assert set(peri) == {
        (1, 2), (1, 3),   # above
        (4, 2), (4, 3),   # below
        (2, 1), (3, 1),   # left
        (2, 4), (3, 4),   # right
    }


def test_united_plaquette_persuades_its_eight_neighbours():
    # All-down lattice; force a unanimous +1 plaquette at (2,2). Applying the rule must
    # flip exactly the 8 edge-adjacent neighbours to +1 (the 4 plaquette cells already +1).
    m = SznajdModel(L=6, d=0.5, seed=0)
    _set_all(m, -1)
    for (rr, cc) in m._plaquette_cells(2, 2):
        m.grid[rr][cc].opinion = 1
    changes = m.apply_plaquette(2, 2)
    assert changes == 8
    ups = {(r, c) for r in range(6) for c in range(6) if m.grid[r][c].opinion == 1}
    # 4 plaquette + 8 perimeter = 12 cells now +1.
    assert len(ups) == 12
    assert set(m._plaquette_cells(2, 2)).issubset(ups)
    assert set(m._perimeter_cells(2, 2)).issubset(ups)


def test_divided_plaquette_changes_nothing():
    # A plaquette whose four cells DISAGREE must leave the lattice untouched.
    m = SznajdModel(L=6, d=0.5, seed=0)
    _set_all(m, -1)
    m.grid[2][2].opinion = 1   # break unanimity in the (2,2) plaquette
    before = [[m.grid[r][c].opinion for c in range(6)] for r in range(6)]
    changes = m.apply_plaquette(2, 2)
    after = [[m.grid[r][c].opinion for c in range(6)] for r in range(6)]
    assert changes == 0
    assert before == after


def test_already_aligned_neighbours_count_as_no_change():
    # Unanimous +1 plaquette in an all-+1 lattice: the rule "fires" but every neighbour
    # already holds +1, so zero changes are recorded (used for frozen-state detection).
    m = SznajdModel(L=6, d=0.5, seed=0)
    _set_all(m, 1)
    assert m.apply_plaquette(2, 2) == 0


def test_full_consensus_lattice_is_frozen():
    # A fully-aligned lattice produces zero changes over a whole sweep -> frozen at once.
    m = SznajdModel(L=10, d=0.5, seed=0, max_sweeps=50)
    _set_all(m, 1)
    res = m.run()
    assert res["frozen"] is True
    assert res["magnetization"] == 1.0
    assert res["consensus"] == 1
    assert res["all_up"] is True
    # No sweep should have been needed beyond the first (it was already frozen).
    assert res["sweeps"] == 1


def test_magnetization_and_up_fraction_consistent():
    m = SznajdModel(L=4, d=0.5, seed=0)
    _set_all(m, -1)
    # Make 4 of 16 cells +1 -> up_fraction 0.25 -> magnetization 2*0.25-1 = -0.5.
    for (r, c) in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        m.grid[r][c].opinion = 1
    assert m.up_fraction() == 0.25
    assert m.magnetization() == -0.5
    assert m.consensus() is None


def test_initial_up_density_matches_d_on_large_lattice():
    # Random placement: empirical up-fraction at construction ~ d (law of large numbers).
    m = SznajdModel(L=100, d=0.7, seed=1)
    assert abs(m.up_fraction() - 0.7) < 0.03


def test_determinism_same_seed_identical_result():
    a = run_single(L=30, d=0.5, seed=12, max_sweeps=1000)
    b = run_single(L=30, d=0.5, seed=12, max_sweeps=1000)
    assert a["magnetization"] == b["magnetization"]
    assert a["consensus"] == b["consensus"]
    assert a["sweeps"] == b["sweeps"]
    assert a["magnetization_series"] == b["magnetization_series"]


def test_different_seeds_can_differ():
    # Determinism is per-seed; the ensemble is not degenerate (at d=0.5 the all-up vs
    # all-down outcome depends on the seed).
    outcomes = {run_single(L=30, d=0.5, seed=s)["consensus"] for s in range(12)}
    assert outcomes.issubset({1, -1})
    assert len(outcomes) == 2   # both consensus types appear across seeds at d=0.5


def test_runs_reach_consensus_at_d_half():
    # The locked P1 territory: from d=0.5 the system freezes on a single opinion.
    r = run_many_seeds(L=30, d=0.5, n_seeds=10, seed_base=0, max_sweeps=1000)
    assert r["frozen_fraction"] == 1.0
    # Every frozen run is a FULL consensus (|m| = 1) for this rule/lattice.
    assert r["p_full_consensus"] == 1.0
    assert r["consensus_fraction"] == 1.0   # |m| >= 0.95


def test_phase_transition_direction():
    # P2/P3 direction: low density -> all-down, high density -> all-up.
    lo = run_many_seeds(L=30, d=0.3, n_seeds=10, seed_base=0)
    hi = run_many_seeds(L=30, d=0.7, n_seeds=10, seed_base=0)
    assert lo["p_all_up"] < 0.2
    assert hi["p_all_up"] > 0.8


def test_run_many_seeds_is_deterministic_and_shaped():
    a = run_many_seeds(L=30, d=0.5, n_seeds=6, seed_base=0)
    b = run_many_seeds(L=30, d=0.5, n_seeds=6, seed_base=0)
    assert a["p_all_up"] == b["p_all_up"]
    assert a["mean_magnetization"] == b["mean_magnetization"]
    assert [s["magnetization"] for s in a["per_seed"]] == \
           [s["magnetization"] for s in b["per_seed"]]
    assert len(a["per_seed"]) == 6
    assert 0.0 <= a["p_all_up"] <= 1.0
    assert a["var_magnetization"] >= 0.0
