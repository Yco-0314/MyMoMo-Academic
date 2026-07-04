"""Faithful-rule + determinism tests for the Abrams-Strogatz language model.

These pin the two-language transition probabilities, unstable fixed-point helper,
outcome classification, and deterministic seeded ensembles. They are faithfulness tests,
NOT prediction tests; locked predictions are evaluated by the reproduction runner.
"""
from __future__ import annotations

import pytest

from abm_auto.classics.abrams_strogatz_language import (
    AbramsStrogatzModel,
    basin_boundary,
    classify_outcome,
    measured_boundary,
    run_many_seeds,
)


def test_basin_boundary_formula():
    x = basin_boundary(status_a=0.6, alpha=1.31)
    assert 0.0 < x < 0.5
    assert x == pytest.approx(0.2123, abs=0.01)


def test_equal_status_boundary_is_half():
    assert basin_boundary(status_a=0.5, alpha=1.31) == pytest.approx(0.5)


def test_classify_outcome_endpoints_and_interior():
    assert classify_outcome(0.98) == "A"
    assert classify_outcome(0.02) == "B"
    assert classify_outcome(0.50) == "interior"


def test_transition_probability_shape():
    m = AbramsStrogatzModel(n=100, initial_a=0.25, status_a=0.6, alpha=1.31, seed=0)
    p_to_a, p_to_b = m.switch_probabilities()
    assert 0.0 <= p_to_a <= 1.0
    assert 0.0 <= p_to_b <= 1.0
    assert p_to_b > p_to_a


def test_apply_update_converts_b_speaker_when_draw_is_below_probability():
    m = AbramsStrogatzModel(n=4, initial_a=0.5, status_a=0.6, alpha=1.31, seed=0)
    m.languages = [0, 1, 1, 0]
    m._a_count = 2
    m.apply_update(target=0, draw=0.0)
    assert m.languages[0] == 1
    assert m.a_count() == 3


def test_apply_update_keeps_speaker_when_draw_is_above_probability():
    m = AbramsStrogatzModel(n=4, initial_a=0.5, status_a=0.6, alpha=1.31, seed=0)
    m.languages = [0, 1, 1, 0]
    m._a_count = 2
    m.apply_update(target=0, draw=1.0)
    assert m.languages[0] == 0
    assert m.a_count() == 2


def test_measured_boundary_interpolates_crossing():
    rows = [
        {"initial_a": 0.1, "p_a_win": 0.0},
        {"initial_a": 0.2, "p_a_win": 0.25},
        {"initial_a": 0.3, "p_a_win": 0.75},
    ]
    assert measured_boundary(rows) == pytest.approx(0.25)


def test_determinism_same_seed_identical():
    a = run_many_seeds(n=120, initial_a=0.5, status_a=0.6, alpha=1.31,
                       n_runs=5, seed_base=0, max_sweeps=200)
    b = run_many_seeds(n=120, initial_a=0.5, status_a=0.6, alpha=1.31,
                       n_runs=5, seed_base=0, max_sweeps=200)
    assert a == b


def test_invalid_params_rejected():
    invalid = [
        {"n": 1, "initial_a": 0.5, "status_a": 0.6, "alpha": 1.31},
        {"n": 10, "initial_a": -0.1, "status_a": 0.6, "alpha": 1.31},
        {"n": 10, "initial_a": 1.1, "status_a": 0.6, "alpha": 1.31},
        {"n": 10, "initial_a": 0.5, "status_a": 0.0, "alpha": 1.31},
        {"n": 10, "initial_a": 0.5, "status_a": 1.0, "alpha": 1.31},
        {"n": 10, "initial_a": 0.5, "status_a": 0.6, "alpha": 1.0},
        {"n": 10, "initial_a": 0.5, "status_a": 0.6, "alpha": 1.31,
         "max_sweeps": 0},
    ]
    for kwargs in invalid:
        with pytest.raises(ValueError):
            AbramsStrogatzModel(**kwargs)


def test_invalid_ensemble_rejected():
    with pytest.raises(ValueError):
        run_many_seeds(n=100, initial_a=0.5, status_a=0.6, alpha=1.31, n_runs=0)
