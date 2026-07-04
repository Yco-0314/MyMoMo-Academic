"""Faithful-rule + determinism tests for the voter-model fixation reproduction.

These pin the voter copy rule (i adopts a random OTHER j's opinion), the binary
opinion state, the running up-tally vs an independent recount, the absorbing consensus
states, the initial up-fraction seeding, determinism (same seed -> identical run), and
the run-summary shape. They are faithfulness tests, NOT prediction tests (the locked
predictions P1-P3 are evaluated by examples/repro_voter_model/run.py).
"""
from __future__ import annotations

import pytest

from abm_auto.classics.voter import (
    VoterAgent,
    VoterModel,
    run_many_seeds,
    run_single,
)


def test_initial_seeding_and_baseline_counts():
    m = VoterModel(n=1000, u=0.2, seed=0)
    assert m.n_up0 == 200
    assert m.up_count() == 200
    assert m.up_count_recount() == 200
    # opinions are binary 0/1 only
    assert all(v.opinion in (0, 1) for v in m.voters)


def test_seeding_rounds_up_fraction():
    # round(u*N): 0.5*1000 = 500; 0.8*1000 = 800; 0.2*7 = 1.4 -> 1
    assert VoterModel(n=1000, u=0.5).n_up0 == 500
    assert VoterModel(n=1000, u=0.8).n_up0 == 800
    assert VoterModel(n=7, u=0.2).n_up0 == 1


def test_adopt_copies_only_other_local_opinion():
    m = VoterModel(n=4, u=0.5, seed=0)
    a, b = m.voters[0], m.voters[3]
    a.opinion, b.opinion = 1, 0
    a.adopt(b)
    assert a.opinion == 0  # a copied b's opinion, reading only b.opinion
    b.opinion = 1
    a.adopt(b)
    assert a.opinion == 1


def test_update_picks_distinct_pair_and_maintains_tally():
    # After many updates the incrementally-maintained _up tally must always match an
    # independent recount of agent state (the tally is never an input to a decision).
    m = VoterModel(n=50, u=0.5, seed=1)
    for _ in range(500):
        if m.at_consensus():
            break
        m.update()
        assert m.up_count() == m.up_count_recount()


def test_magnetization_formula():
    m = VoterModel(n=1000, u=0.5, seed=0)
    assert m.magnetization() == pytest.approx(0.0)          # 2*0.5 - 1
    m2 = VoterModel(n=1000, u=0.8, seed=0)
    assert m2.magnetization() == pytest.approx(0.6)         # 2*0.8 - 1
    m3 = VoterModel(n=1000, u=0.2, seed=0)
    assert m3.magnetization() == pytest.approx(-0.6)        # 2*0.2 - 1


def test_consensus_states_are_absorbing():
    # all-up: every copy leaves opinions unchanged; tally stays = n, never moves.
    up = VoterModel(n=10, u=1.0, seed=0)
    assert up.at_consensus()
    assert up.up_count() == 10
    for _ in range(100):
        up.update()
        assert up.up_count() == 10  # absorbing
    # all-down: tally stays = 0.
    down = VoterModel(n=10, u=0.0, seed=0)
    assert down.at_consensus()
    assert down.up_count() == 0
    for _ in range(100):
        down.update()
        assert down.up_count() == 0  # absorbing


def test_already_consensus_runs_terminate_immediately():
    # u=1.0 starts all-up -> consensus to all-up in zero updates.
    res_up = run_single(n=100, u=1.0, seed=0)
    assert res_up["reached_consensus"] is True
    assert res_up["consensus"] == 1
    assert res_up["all_up"] is True
    assert res_up["total_updates"] == 0
    # u=0.0 starts all-down -> consensus to all-down in zero updates.
    res_down = run_single(n=100, u=0.0, seed=0)
    assert res_down["reached_consensus"] is True
    assert res_down["consensus"] == 0
    assert res_down["all_up"] is False
    assert res_down["total_updates"] == 0


def test_run_reaches_absorbing_consensus():
    # Small N reaches consensus quickly; the final state must be all-0 or all-1.
    res = run_single(n=100, u=0.5, seed=3)
    assert res["reached_consensus"] is True
    assert res["capped"] is False
    assert res["final_up"] in (0, res["n"])
    assert res["consensus"] in (0, 1)
    # magnetization at consensus is exactly +1 (all up) or -1 (all down)
    assert res["final_magnetization"] in (1.0, -1.0)
    assert res["sweeps_to_consensus"] > 0


def test_determinism_same_seed_identical_run():
    a = run_single(n=200, u=0.5, seed=7)
    b = run_single(n=200, u=0.5, seed=7)
    assert a["consensus"] == b["consensus"]
    assert a["total_updates"] == b["total_updates"]
    assert a["sweeps_to_consensus"] == b["sweeps_to_consensus"]
    assert a["final_magnetization"] == b["final_magnetization"]


def test_different_seeds_can_differ():
    # The consensus outcome / time is stochastic across seeds.
    outcomes = {(run_single(n=200, u=0.5, seed=s)["consensus"],
                 run_single(n=200, u=0.5, seed=s)["total_updates"]) for s in range(12)}
    assert len(outcomes) > 1


def test_run_many_seeds_shape_and_determinism():
    a = run_many_seeds(n=200, u=0.5, n_runs=30, seed_base=0)
    b = run_many_seeds(n=200, u=0.5, n_runs=30, seed_base=0)
    assert a["p_all_up"] == b["p_all_up"]
    assert a["per_run"] == b["per_run"]
    assert a["n_runs"] == 30
    assert 0.0 <= a["p_all_up"] <= 1.0
    assert a["se_p_all_up"] >= 0.0
    # every run reaches consensus at this small N
    assert a["consensus_rate"] == 1.0
    # expected magnetization recorded as 2u-1
    assert a["expected_magnetization"] == pytest.approx(0.0)
    cts = a["consensus_time_sweeps"]
    assert cts["min"] <= cts["mean"] <= cts["max"]
    assert cts["n"] == 30


def test_fixation_tracks_initial_density_small_check():
    # Sanity (not the locked grid): at u=0.8, P(all-up) should be high and clearly
    # above u=0.2's. Faithful copy rule => fixation tracks initial density.
    hi = run_many_seeds(n=100, u=0.8, n_runs=80, seed_base=0)
    lo = run_many_seeds(n=100, u=0.2, n_runs=80, seed_base=0)
    assert hi["p_all_up"] > lo["p_all_up"]
    assert hi["p_all_up"] > 0.5
    assert lo["p_all_up"] < 0.5


def test_invalid_params_rejected():
    with pytest.raises(ValueError):
        VoterModel(n=1, u=0.5)
    with pytest.raises(ValueError):
        VoterModel(n=100, u=-0.1)
    with pytest.raises(ValueError):
        VoterModel(n=100, u=1.1)
