"""Faithful-rule + determinism tests for the noisy voter / Kirman reproduction.

These pin the elementary update: with probability a the target flips spontaneously,
otherwise it copies a random other agent. They are faithfulness tests, NOT prediction
tests; the locked predictions are evaluated by ``examples/repro_noisy_voter_kirman/run.py``.
"""
from __future__ import annotations

import pytest

from abm_auto.classics.noisy_voter_kirman import (
    NoisyVoterModel,
    edge_center_mass,
    run_stationary,
)


def test_spontaneous_flip_breaks_absorbing_state():
    m = NoisyVoterModel(n=5, u=1.0, a=1.0, seed=0)
    m.apply_update(target=0, source=1, spontaneous=True)
    assert m.opinions[0] == 0
    assert m.up_count() == 4


def test_copy_update_reads_other_agent():
    m = NoisyVoterModel(n=4, u=0.5, a=0.0, seed=0)
    m.opinions = [0, 1, 1, 0]
    m._up = 2
    m.apply_update(target=0, source=1, spontaneous=False)
    assert m.opinions[0] == 1
    assert m.up_count() == 3


def test_copy_update_rejects_missing_source():
    m = NoisyVoterModel(n=4, u=0.5, a=0.0, seed=0)
    with pytest.raises(ValueError):
        m.apply_update(target=0, source=None, spontaneous=False)


def test_sample_source_excludes_target():
    m = NoisyVoterModel(n=2, u=0.5, a=0.0, seed=0)
    assert m.sample_source(target=0) == 1


def test_edge_center_mass_counts_trace_regions():
    stats = edge_center_mass([-0.9, -0.7, 0.0, 0.1, 0.8])
    assert stats["edge_mass"] == 3 / 5
    assert stats["center_mass"] == 2 / 5
    assert stats["edge_center_ratio"] == pytest.approx(1.5)


def test_edge_center_mass_handles_no_center_mass():
    stats = edge_center_mass([-0.9, 0.9])
    assert stats["edge_mass"] == 1.0
    assert stats["center_mass"] == 0.0
    assert stats["edge_center_ratio"] == float("inf")


def test_stationary_run_shape_and_determinism():
    a = run_stationary(n=40, u=0.5, a=0.02, seed=3, burn_in=100,
                       samples=20, record_every=5)
    b = run_stationary(n=40, u=0.5, a=0.02, seed=3, burn_in=100,
                       samples=20, record_every=5)
    assert a == b
    assert len(a["magnetization_trace"]) == 20
    assert -1.0 <= a["mean_magnetization"] <= 1.0
    assert 0.0 <= a["edge_mass"] <= 1.0
    assert 0.0 <= a["center_mass"] <= 1.0


def test_spontaneous_noise_prevents_permanent_absorption():
    res = run_stationary(n=20, u=1.0, a=1.0, seed=1, burn_in=0,
                         samples=5, record_every=1)
    assert any(m < 1.0 for m in res["magnetization_trace"])


def test_invalid_params_rejected():
    invalid = [
        {"n": 1, "u": 0.5, "a": 0.1},
        {"n": 10, "u": 1.2, "a": 0.1},
        {"n": 10, "u": 0.5, "a": -0.1},
        {"n": 10, "u": 0.5, "a": 1.1},
    ]
    for kwargs in invalid:
        with pytest.raises(ValueError):
            NoisyVoterModel(**kwargs)


def test_invalid_trace_params_rejected():
    m = NoisyVoterModel(n=10, u=0.5, a=0.1)
    for kwargs in [
        {"burn_in": -1, "samples": 10, "record_every": 1},
        {"burn_in": 0, "samples": 0, "record_every": 1},
        {"burn_in": 0, "samples": 10, "record_every": 0},
    ]:
        with pytest.raises(ValueError):
            m.run_trace(**kwargs)
