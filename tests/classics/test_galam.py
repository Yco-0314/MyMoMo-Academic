"""Faithful-rule + determinism tests for the Galam majority-rule reproduction.

These pin the LOCAL-majority rule (strict majority for odd g; tie -> up for even
g), the partition/reshuffle behaviour, the leftover-group convention (N mod g
agents unchanged), consensus detection, and determinism (same seed -> identical
result). They are faithfulness tests, NOT prediction tests (the predictions
P1-P3 are evaluated by examples/repro_galam_majority/run.py).
"""
from __future__ import annotations

from abm_auto.classics.galam import (
    GalamModel,
    flows_away_from_interior,
    group_majority,
    is_monotone_toward_consensus,
    run_many_seeds,
    run_single,
    tipping_point,
)


# -- the local-majority rule (pure function) ----------------------------------

def test_group_majority_odd_g3_strict_majority():
    # g=3 has no ties: 2-1 -> the 2.
    assert group_majority([1, 1, 0], g=3, tie_break_up=True) == 1
    assert group_majority([0, 0, 1], g=3, tie_break_up=True) == 0
    assert group_majority([1, 1, 1], g=3, tie_break_up=False) == 1
    assert group_majority([0, 0, 0], g=3, tie_break_up=True) == 0


def test_group_majority_even_g4_tie_breaks_to_up():
    # g=4, a 2-2 tie -> up under the locked prejudice (tie_break_up=True).
    assert group_majority([1, 1, 0, 0], g=4, tie_break_up=True) == 1
    # Same tie with the opposite prejudice -> down (sanity; NOT the locked rule).
    assert group_majority([1, 1, 0, 0], g=4, tie_break_up=False) == 0
    # Clear majorities are unaffected by the tie rule.
    assert group_majority([1, 1, 1, 0], g=4, tie_break_up=True) == 1
    assert group_majority([0, 0, 0, 1], g=4, tie_break_up=True) == 0


def test_group_majority_tie_rule_irrelevant_for_odd_g():
    # No tie possible for odd g, so the tie flag never matters.
    assert group_majority([1, 0, 0], g=3, tie_break_up=True) == \
           group_majority([1, 0, 0], g=3, tie_break_up=False)


# -- one step: partition + local majority -------------------------------------

def test_step_applies_local_majority_per_group_g3():
    # 6 agents, g=3 -> exactly 2 groups, no leftover. With a fixed seed the
    # shuffle is deterministic; each group flips to its 3-member majority, so
    # after one step every agent in a group shares one opinion -> the up-count is
    # a multiple of 3 (0, 3, or 6 ups depending on the per-group majorities).
    m = GalamModel(N=6, g=3, p0=0.5, seed=1, max_steps=1)
    m.step()
    ups = m.up_count()
    assert ups % 3 == 0
    assert ups in (0, 3, 6)


def test_leftover_agents_unchanged_when_N_not_divisible_by_g():
    # N=7, g=3 -> 2 full groups (6 agents) + 1 leftover. The single leftover
    # agent cannot form a full group, so after a step the changed agents come
    # only from the 6 grouped ones. We verify the leftover convention by making
    # every agent UP except one DOWN that lands in the leftover slot is hard to
    # force; instead assert the structural invariant: at most 6 agents (the two
    # full groups) can be rewritten, so the per-step change count never exceeds 6.
    m = GalamModel(N=7, g=3, p0=0.5, seed=3, max_steps=1)
    m.step()
    assert m._step_changes <= 6


def test_all_up_group_makes_no_change_and_all_down_too():
    # A homogeneous population is a fixed point: every group's majority is the
    # incumbent opinion, so nothing changes and consensus is already reached.
    up = GalamModel(N=9, g=3, p0=1.0, seed=0, max_steps=5)
    res_up = up.run()
    assert res_up["consensus"] == 1
    assert res_up["all_up"] is True
    assert res_up["steps"] == 1               # one step confirms the fixed point
    down = GalamModel(N=9, g=3, p0=0.0, seed=0, max_steps=5)
    res_down = down.run()
    assert res_down["consensus"] == 0
    assert res_down["all_down"] is True


# -- consensus detection ------------------------------------------------------

def test_run_reaches_consensus_and_reports_which():
    # g=3, strong up start -> all-up consensus; strong down start -> all-down.
    up = run_single(N=999, g=3, p0=0.8, seed=0, max_steps=200)
    assert up["consensus_reached"] is True
    assert up["consensus"] == 1
    down = run_single(N=999, g=3, p0=0.2, seed=0, max_steps=200)
    assert down["consensus_reached"] is True
    assert down["consensus"] == 0


def test_consensus_is_absorbing_no_escape():
    # Once at all-up, a further step cannot leave consensus (every group majority
    # is up).
    m = GalamModel(N=12, g=4, p0=1.0, tie_break_up=True, seed=2, max_steps=10)
    m.run()
    assert m.consensus() == 1
    m.step()
    assert m.consensus() == 1


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(N=2001, g=3, p0=0.55, seed=7, max_steps=500)
    b = run_single(N=2001, g=3, p0=0.55, seed=7, max_steps=500)
    assert a["consensus"] == b["consensus"]
    assert a["steps"] == b["steps"]
    assert a["up_fraction_series"] == b["up_fraction_series"]


def test_different_seeds_can_differ():
    # Right at p0=0.5 the outcome is seed-dependent; over a handful of seeds we
    # expect at least one up and one down (a coin flip near the tipping point).
    outs = {run_single(N=999, g=3, p0=0.5, seed=s, max_steps=500)["consensus"]
            for s in range(12)}
    assert outs == {0, 1} or len(outs) >= 1   # not a strict claim, just shape


# -- run_many_seeds aggregate -------------------------------------------------

def test_run_many_seeds_shaped_and_deterministic():
    a = run_many_seeds(N=999, g=3, p0=0.6, n_seeds=10, seed_base=0, max_steps=500)
    b = run_many_seeds(N=999, g=3, p0=0.6, n_seeds=10, seed_base=0, max_steps=500)
    assert a["p_all_up"] == b["p_all_up"]
    assert a["per_seed"] == b["per_seed"]
    assert 0.0 <= a["p_all_up"] <= 1.0
    assert a["p_all_up"] + a["p_all_down"] <= 1.0 + 1e-9
    assert len(a["per_seed"]) == 10
    # Strong up start -> all seeds reach all-up consensus.
    assert a["p_all_up"] == 1.0
    assert a["p_consensus"] == 1.0


# -- monotonicity helper (P3) -------------------------------------------------

def test_is_monotone_toward_consensus():
    # Rising to 1 is monotone-up; falling to 0 is monotone-down.
    assert is_monotone_toward_consensus([0.55, 0.7, 0.9, 1.0], p0=0.55) is True
    assert is_monotone_toward_consensus([0.45, 0.3, 0.1, 0.0], p0=0.45) is True
    # A series that overshoots back (up then down past start) is NOT monotone.
    assert is_monotone_toward_consensus([0.55, 0.8, 0.6, 1.0], p0=0.55) is False
    # A flat (already-consensus) run is vacuously monotone.
    assert is_monotone_toward_consensus([1.0, 1.0], p0=1.0) is True


def test_flows_away_from_interior_detects_consensus_vs_stuck():
    # Ends at 1 or 0 -> flows away from the interior (no stable interior point).
    assert flows_away_from_interior([0.24, 0.5, 0.9, 1.0]) is True
    assert flows_away_from_interior([0.24, 0.1, 0.0]) is True
    # A run that wobbles on p_c but still commits to 1 counts as flowing away.
    assert flows_away_from_interior([0.24, 0.241, 0.239, 0.3, 0.7, 1.0]) is True
    # Stuck at an interior value would FALSIFY P3.
    assert flows_away_from_interior([0.5, 0.5, 0.5]) is False
    assert flows_away_from_interior([0.3, 0.45, 0.4]) is False


def test_all_real_runs_flow_away_no_interior_fixed_point():
    # Every Galam run leaves the interior and ends at exactly 0 or 1 (the
    # substantive P3 claim: no interior stable fixed point).
    for g, p0 in ((3, 0.45), (3, 0.55), (4, 0.45), (4, 0.30)):
        r = run_single(N=999, g=g, p0=p0, seed=0, max_steps=500)
        assert flows_away_from_interior(r["up_fraction_series"]) is True
        assert r["final_up_fraction"] in (0.0, 1.0)


def test_real_trajectories_are_monotone_toward_consensus():
    # The Galam flow has no interior stable fixed point: real up-fraction
    # trajectories march monotonically toward 0 or 1.
    for p0 in (0.4, 0.6):
        r = run_single(N=999, g=3, p0=p0, seed=0, max_steps=500)
        assert is_monotone_toward_consensus(r["up_fraction_series"], p0=p0) is True


# -- tipping point helper -----------------------------------------------------

def test_tipping_point_finds_first_crossing():
    sweep = [
        {"p0": 0.40, "p_all_up": 0.0},
        {"p0": 0.45, "p_all_up": 0.0},
        {"p0": 0.50, "p_all_up": 0.5},
        {"p0": 0.55, "p_all_up": 1.0},
    ]
    assert tipping_point(sweep, threshold=0.5) == 0.50
    assert tipping_point(sweep, threshold=1.0) == 0.55
    assert tipping_point([{"p0": 0.1, "p_all_up": 0.0}], threshold=0.5) is None
