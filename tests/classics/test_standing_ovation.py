"""Faithful-rule + determinism tests for the Miller-Page (2004) standing-ovation
reproduction.

These pin the seeded quality draw (q = s + noise, reproducible), the INITIAL
quality-only stand rule (stand iff q > T), the Moore-8 conformity majority rule on
hand-built small grids (a known config -> a known next state), edge/corner
neighbourhoods (self excluded, hard edges), the SYNCHRONOUS fixed-point update (a
stable config does not change and the iteration halts), determinism (same seed ->
identical), and the no-conformity baseline (== the initial quality-only fraction).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(high signal -> ovation, low signal -> flop, conformity amplifies an intermediate
signal) are evaluated by examples/repro_standing_ovation/run.py.
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.standing_ovation import (
    AudienceAgent,
    StandingOvationModel,
    run_single,
    run_many_seeds,
)


# -- helper: build a model with a hand-set standing pattern -------------------

def _model(L: int, *, sigma: float = 0.0, s: float = 0.0, T: float = 0.5):
    """A noiseless model (sigma=0) so every agent's quality is exactly s; we then
    overwrite the ``standing`` field by hand to test the conformity rule in
    isolation."""
    return StandingOvationModel(L=L, s=s, sigma=sigma, T=T, seed=0)


def _set_pattern(m: StandingOvationModel, pattern):
    """Set the standing state of every cell from an L x L 0/1 pattern."""
    for r in range(m.L):
        for c in range(m.L):
            m.grid[r][c].standing = bool(pattern[r][c])
            m.grid[r][c]._next_standing = bool(pattern[r][c])


def _pattern(m: StandingOvationModel):
    return [[1 if m.grid[r][c].standing else 0 for c in range(m.L)]
            for r in range(m.L)]


# -- seeded quality draw + population shape -----------------------------------

def test_population_is_one_audience_agent_per_cell():
    m = StandingOvationModel(L=40, seed=0)
    assert m.n == 1600
    assert len(m.agent_list) == 1600
    assert all(isinstance(a, AudienceAgent) for a in m.agent_list)
    # one agent per grid cell, no holes
    for r in range(40):
        for c in range(40):
            assert isinstance(m.grid[r][c], AudienceAgent)
            assert m.grid[r][c].cell == (r, c)


def test_quality_draw_is_signal_plus_noise_and_seed_deterministic():
    # Same seed -> identical quality draw; different seed -> generally different.
    a = StandingOvationModel(L=20, s=0.5, sigma=0.3, seed=7)
    b = StandingOvationModel(L=20, s=0.5, sigma=0.3, seed=7)
    c = StandingOvationModel(L=20, s=0.5, sigma=0.3, seed=8)
    qa = [ag.q for ag in a.agent_list]
    qb = [ag.q for ag in b.agent_list]
    qc = [ag.q for ag in c.agent_list]
    assert qa == qb                      # same seed -> identical draw
    assert qa != qc                      # different seed -> different draw
    # the empirical mean of q sits near the signal s (noise has mean 0)
    assert abs(sum(qa) / len(qa) - 0.5) < 0.05


def test_zero_sigma_makes_every_quality_exactly_the_signal():
    m = StandingOvationModel(L=10, s=0.42, sigma=0.0, seed=3)
    assert all(ag.q == pytest.approx(0.42) for ag in m.agent_list)


# -- INITIAL (quality-only) stand rule: stand iff q > T -----------------------

def test_initial_stand_rule_is_quality_above_threshold():
    # noiseless: every q == s. s above T -> everyone stands initially; below -> none.
    above = StandingOvationModel(L=8, s=0.8, sigma=0.0, T=0.5, seed=0)
    below = StandingOvationModel(L=8, s=0.2, sigma=0.0, T=0.5, seed=0)
    assert all(a.standing for a in above.agent_list)
    assert above.initial_standing_fraction() == pytest.approx(1.0)
    assert not any(a.standing for a in below.agent_list)
    assert below.initial_standing_fraction() == pytest.approx(0.0)


def test_initial_stand_rule_strict_inequality_at_threshold():
    # q exactly == T must NOT stand (strict q > T).
    m = StandingOvationModel(L=4, s=0.5, sigma=0.0, T=0.5, seed=0)
    assert not any(a.standing for a in m.agent_list)
    assert m.initial_standing_fraction() == pytest.approx(0.0)


def test_initial_fraction_tracks_noise_for_balanced_signal():
    # At s == T, in expectation ~half exceed the threshold (noise is symmetric).
    m = StandingOvationModel(L=40, s=0.5, sigma=0.3, T=0.5, seed=1)
    frac = m.initial_standing_fraction()
    assert 0.35 < frac < 0.65            # near one-half, seed-dependent


# -- the Moore-8 conformity majority rule (hand-built grids) ------------------

def test_neighbourhood_excludes_self_and_uses_moore_8():
    # interior cell has 8 neighbours; we count standing neighbours, self excluded.
    m = _model(5)
    pat = [[0] * 5 for _ in range(5)]
    # surround the centre (2,2) with 3 standing neighbours; centre itself standing.
    pat[1][1] = 1
    pat[1][2] = 1
    pat[1][3] = 1
    pat[2][2] = 1                        # the centre is standing but is SELF-excluded
    _set_pattern(m, pat)
    standing, total = m.standing_neighbours(m.grid[2][2])
    assert total == 8                    # interior -> 8 neighbours
    assert standing == 3                 # the 3 in row 1; self not counted


def test_conformity_rule_at_least_half_interior():
    # interior cell (8 neighbours): needs >= ceil(8/2) = 4 standing to stand.
    m = _model(5)
    # 4 standing neighbours -> stands; 3 -> sits.
    pat3 = [[0] * 5 for _ in range(5)]
    pat3[1][1] = pat3[1][2] = pat3[1][3] = 1          # 3 standing neighbours
    _set_pattern(m, pat3)
    assert m.conformity_decision(m.grid[2][2]) is False

    pat4 = [[0] * 5 for _ in range(5)]
    pat4[1][1] = pat4[1][2] = pat4[1][3] = pat4[2][1] = 1   # 4 standing neighbours
    _set_pattern(m, pat4)
    assert m.conformity_decision(m.grid[2][2]) is True


def test_conformity_rule_does_not_depend_on_own_state():
    # The agent's own standing state must not enter its own decision (self excluded).
    m = _model(5)
    pat = [[0] * 5 for _ in range(5)]
    pat[1][1] = pat[1][2] = pat[1][3] = pat[2][1] = 1       # 4 standing neighbours
    _set_pattern(m, pat)
    # centre seated -> still stands (4 >= 4); centre standing -> still stands.
    m.grid[2][2].standing = False
    assert m.conformity_decision(m.grid[2][2]) is True
    m.grid[2][2].standing = True
    assert m.conformity_decision(m.grid[2][2]) is True


def test_all_seated_neighbours_make_agent_sit():
    m = _model(5)
    _set_pattern(m, [[0] * 5 for _ in range(5)])
    # standing centre with all-seated neighbours -> 0 >= ceil(8/2)=4 false -> sits.
    m.grid[2][2].standing = True
    assert m.conformity_decision(m.grid[2][2]) is False


# -- edge / corner neighbourhoods ---------------------------------------------

def test_corner_has_three_neighbours_and_needs_two():
    # corner (0,0) has neighbours (0,1),(1,0),(1,1) -> 3 neighbours.
    m = _model(5)
    pat = [[0] * 5 for _ in range(5)]
    pat[0][1] = pat[1][0] = 1            # 2 of the 3 corner neighbours standing
    _set_pattern(m, pat)
    standing, total = m.standing_neighbours(m.grid[0][0])
    assert total == 3
    assert standing == 2
    # ceil(3/2) = 2 -> 2 standing is "at least half" -> corner stands.
    assert m.conformity_decision(m.grid[0][0]) is True

    pat1 = [[0] * 5 for _ in range(5)]
    pat1[0][1] = 1                       # only 1 of 3 -> 1 < 2 -> sits.
    _set_pattern(m, pat1)
    assert m.conformity_decision(m.grid[0][0]) is False


def test_edge_has_five_neighbours_and_needs_three():
    # a top-edge non-corner cell (0,2) has 5 neighbours.
    m = _model(5)
    pat = [[0] * 5 for _ in range(5)]
    pat[0][1] = pat[0][3] = pat[1][2] = 1       # 3 of the 5 edge neighbours standing
    _set_pattern(m, pat)
    standing, total = m.standing_neighbours(m.grid[0][2])
    assert total == 5
    assert standing == 3
    # ceil(5/2) = 3 -> 3 standing -> stands.
    assert m.conformity_decision(m.grid[0][2]) is True

    pat2 = [[0] * 5 for _ in range(5)]
    pat2[0][1] = pat2[1][2] = 1                  # 2 of 5 -> 2 < 3 -> sits.
    _set_pattern(m, pat2)
    assert m.conformity_decision(m.grid[0][2]) is False


# -- synchronous fixed-point convergence --------------------------------------

def test_all_standing_is_a_fixed_point():
    # everyone standing: every agent sees all neighbours standing -> stays standing.
    m = _model(6)
    _set_pattern(m, [[1] * 6 for _ in range(6)])
    changed = m.conformity_step()
    assert changed is False
    assert all(a.standing for a in m.agent_list)


def test_all_seated_is_a_fixed_point():
    m = _model(6)
    _set_pattern(m, [[0] * 6 for _ in range(6)])
    changed = m.conformity_step()
    assert changed is False
    assert not any(a.standing for a in m.agent_list)


def test_synchronous_update_uses_one_snapshot():
    # A 1x3 standing block on row 2 of a 5x5 grid. Synchronous update: every agent
    # decides from the SAME start snapshot. Check the next state of one cell that is
    # known to flip, computed against the pre-update neighbour states.
    m = _model(5)
    pat = [[0] * 5 for _ in range(5)]
    pat[2][1] = pat[2][2] = pat[2][3] = 1       # a horizontal triple
    _set_pattern(m, pat)
    # cell (2,2): neighbours (2,1),(2,3) standing -> 2 of 8 -> 2 < 4 -> will SIT.
    before = m.conformity_decision(m.grid[2][2])
    assert before is False
    m.conformity_step()
    assert m.grid[2][2].standing is False       # the triple collapses (too sparse)


def test_run_halts_at_fixed_point_and_reports_convergence():
    # noiseless s well above T: everyone stands initially and stays -> converges in 1.
    res = run_single(L=10, s=0.9, sigma=0.0, T=0.5, seed=0)
    assert res["converged"] is True
    assert res["final_fraction"] == pytest.approx(1.0)
    assert res["initial_fraction"] == pytest.approx(1.0)
    # a fixed point is detected immediately (one no-change iteration).
    assert res["conformity_iters"] == 1


def test_run_respects_max_iters_cap():
    m = StandingOvationModel(L=20, s=0.5, sigma=0.3, seed=0, max_iters=3)
    res = m.run()
    assert res["conformity_iters"] <= 3


# -- no-conformity baseline ==  initial fraction ------------------------------

def test_baseline_equals_initial_quality_only_fraction():
    res = run_single(L=40, s=0.5, sigma=0.3, T=0.5, seed=2)
    # the no-conformity baseline IS the initial (pre-conformity) quality-only stand.
    assert res["baseline_fraction"] == pytest.approx(res["initial_fraction"])
    # and it equals the fraction of agents with q > T, computed independently.
    m = StandingOvationModel(L=40, s=0.5, sigma=0.3, T=0.5, seed=2)
    independent = sum(1 for a in m.agent_list if a.q > 0.5) / m.n
    assert res["baseline_fraction"] == pytest.approx(independent)


def test_fraction_series_starts_at_initial():
    res = run_single(L=20, s=0.5, sigma=0.3, seed=5)
    # the first recorded standing fraction is the pre-conformity (iteration 0) value.
    assert res["fraction_series"][0] == pytest.approx(res["initial_fraction"])
    assert res["fraction_series"][-1] == pytest.approx(res["final_fraction"])


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(L=40, s=0.5, sigma=0.3, seed=42)
    b = run_single(L=40, s=0.5, sigma=0.3, seed=42)
    assert a["fraction_series"] == b["fraction_series"]
    assert a["final_fraction"] == b["final_fraction"]
    assert a["conformity_iters"] == b["conformity_iters"]


def test_different_seeds_can_differ_but_stay_in_unit_interval():
    a = run_single(L=40, s=0.5, sigma=0.3, seed=1)
    b = run_single(L=40, s=0.5, sigma=0.3, seed=2)
    for res in (a, b):
        assert 0.0 <= res["initial_fraction"] <= 1.0
        assert 0.0 <= res["final_fraction"] <= 1.0
        assert all(0.0 <= x <= 1.0 for x in res["fraction_series"])


# -- multi-seed summary shape -------------------------------------------------

def test_run_many_seeds_summary_shape():
    out = run_many_seeds([0, 1, 2, 3, 4], L=40, s=0.8, sigma=0.3)
    assert len(out["per_seed_final"]) == 5
    assert len(out["per_seed_initial"]) == 5
    assert 0.0 <= out["mean_final_fraction"] <= 1.0
    assert out["min_final_fraction"] <= out["mean_final_fraction"] <= out["max_final_fraction"]


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        StandingOvationModel(L=0)
    with pytest.raises(ValueError):
        StandingOvationModel(L=10, sigma=-0.1)
    with pytest.raises(ValueError):
        StandingOvationModel(L=10, max_iters=0)
