"""Faithful-rule + determinism tests for the q-voter reproduction.

These pin the elementary q-panel rule: a unanimous q-neighbour panel converts the target,
a split panel only acts through epsilon noise, and q=1 with epsilon=0 is the ordinary
linear voter copying process. They are faithfulness tests, NOT prediction tests; the
locked predictions are evaluated by ``examples/repro_q_voter/run.py``.
"""
from __future__ import annotations

import pytest

from abm_auto.classics.q_voter import QVoterModel, run_many_seeds, run_single


def test_q_one_panel_copies_other_opinion():
    m = QVoterModel(n=4, u=0.5, q=1, epsilon=0.0, seed=0)
    m.opinions = [1, 0, 0, 0]
    m._up = 1
    m.apply_panel(target=0, panel=[1])
    assert m.opinions[0] == 0
    assert m.up_count() == 0


def test_unanimous_q_panel_converts_target():
    m = QVoterModel(n=5, u=0.0, q=3, epsilon=0.0, seed=0)
    m.opinions = [0, 1, 1, 1, 0]
    m._up = 3
    m.apply_panel(target=0, panel=[1, 2, 3])
    assert m.opinions[0] == 1
    assert m.up_count() == 4


def test_split_panel_without_noise_leaves_target_unchanged():
    m = QVoterModel(n=4, u=0.5, q=2, epsilon=0.0, seed=0)
    m.opinions = [0, 1, 0, 1]
    m._up = 2
    m.apply_panel(target=0, panel=[1, 2])
    assert m.opinions[0] == 0
    assert m.up_count() == 2


def test_split_panel_noise_can_flip_target():
    m = QVoterModel(n=4, u=0.5, q=2, epsilon=1.0, seed=0)
    m.opinions = [0, 1, 0, 1]
    m._up = 2
    m.apply_panel(target=0, panel=[1, 2])
    assert m.opinions[0] == 1
    assert m.up_count() == 3


def test_panel_cannot_include_target():
    m = QVoterModel(n=4, u=0.5, q=1, epsilon=0.0, seed=0)
    with pytest.raises(ValueError):
        m.apply_panel(target=0, panel=[0])


def test_sample_panel_excludes_target_and_allows_replacement():
    m = QVoterModel(n=2, u=0.5, q=3, epsilon=0.0, seed=0)
    panel = m.sample_panel(target=0)
    assert panel == [1, 1, 1]


def test_determinism_same_seed_identical_run():
    a = run_single(n=80, u=0.5, q=2, epsilon=0.05, seed=7, max_sweeps=200)
    b = run_single(n=80, u=0.5, q=2, epsilon=0.05, seed=7, max_sweeps=200)
    assert a == b


def test_run_many_seeds_shape_and_determinism():
    a = run_many_seeds(n=60, u=0.5, q=1, epsilon=0.0, n_runs=12,
                       seed_base=0, max_sweeps=400)
    b = run_many_seeds(n=60, u=0.5, q=1, epsilon=0.0, n_runs=12,
                       seed_base=0, max_sweeps=400)
    assert a == b
    assert a["n_runs"] == 12
    assert a["max_sweeps"] == 400
    assert 0.0 <= a["p_all_up"] <= 1.0
    assert 0.0 <= a["consensus_rate"] <= 1.0
    assert 0.0 <= a["capped_rate"] <= 1.0
    assert len(a["per_run"]) == 12


def test_run_many_seeds_reports_effective_default_cap():
    res = run_many_seeds(n=10, u=0.5, q=1, epsilon=0.0, n_runs=1, seed_base=0)
    assert res["max_sweeps"] == 2000


def test_q_one_tracks_linear_voter_small_check():
    hi = run_many_seeds(n=80, u=0.8, q=1, epsilon=0.0, n_runs=50,
                        seed_base=0, max_sweeps=800)
    lo = run_many_seeds(n=80, u=0.2, q=1, epsilon=0.0, n_runs=50,
                        seed_base=0, max_sweeps=800)
    assert hi["p_all_up"] > lo["p_all_up"]


def test_invalid_params_rejected():
    invalid = [
        {"n": 1, "u": 0.5, "q": 1, "epsilon": 0.0},
        {"n": 10, "u": -0.1, "q": 1, "epsilon": 0.0},
        {"n": 10, "u": 1.1, "q": 1, "epsilon": 0.0},
        {"n": 10, "u": 0.5, "q": 0, "epsilon": 0.0},
        {"n": 10, "u": 0.5, "q": 1, "epsilon": -0.1},
        {"n": 10, "u": 0.5, "q": 1, "epsilon": 1.1},
        {"n": 10, "u": 0.5, "q": 1, "epsilon": 0.0, "max_sweeps": 0},
    ]
    for kwargs in invalid:
        with pytest.raises(ValueError):
            QVoterModel(**kwargs)
