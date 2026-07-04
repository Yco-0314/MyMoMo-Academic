"""Faithful-rule + detector tests for the stochastic block model reproduction."""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.stochastic_block_model import (
    bethe_hessian_detect,
    detectability_threshold_epsilon,
    generate_matched_er,
    generate_sbm,
    overlap_score,
    run_sbm_detection,
    sbm_cin_cout,
)


def test_parameterization_matches_locked_threshold_formula():
    cin, cout = sbm_cin_cout(c=3.0, epsilon=0.5)
    assert cin + cout == pytest.approx(6.0)
    assert cout / cin == pytest.approx(0.5)
    eps_c = detectability_threshold_epsilon(c=3.0)
    assert eps_c == pytest.approx((math.sqrt(3.0) - 1.0) / (math.sqrt(3.0) + 1.0))


def test_generate_sbm_has_equal_groups_and_sparse_mean_degree():
    sample = generate_sbm(n=1000, c=3.0, epsilon=0.1, seed=0)
    assert len(sample.labels) == 1000
    assert sample.labels.count(0) == 500
    assert sample.labels.count(1) == 500
    assert sample.adjacency.shape == (1000, 1000)
    assert sample.adjacency.nnz % 2 == 0
    assert 2.0 <= sample.mean_degree <= 4.2


def test_generate_matched_er_has_no_planted_label_signal():
    sbm = generate_sbm(n=1000, c=3.0, epsilon=0.1, seed=1)
    er = generate_matched_er(n=1000, mean_degree=sbm.mean_degree, seed=1)
    assert er.adjacency.shape == (1000, 1000)
    assert abs(er.mean_degree - sbm.mean_degree) < 0.5


def test_overlap_score_handles_label_permutation_and_chance():
    truth = [0, 0, 1, 1]
    assert overlap_score(truth, [0, 0, 1, 1]) == pytest.approx(1.0)
    assert overlap_score(truth, [1, 1, 0, 0]) == pytest.approx(1.0)
    assert overlap_score(truth, [0, 1, 0, 1]) == pytest.approx(0.0)


def test_bethe_hessian_detector_recovers_deep_detectable_case():
    result = run_sbm_detection(n=2500, c=3.0, epsilon=0.1, seed=2)
    assert result["overlap"] > 0.45


def test_bethe_hessian_detector_fails_on_matched_er_control():
    sbm = generate_sbm(n=2500, c=3.0, epsilon=0.1, seed=3)
    er = generate_matched_er(n=2500, mean_degree=sbm.mean_degree, seed=3)
    pred = bethe_hessian_detect(er.adjacency, average_degree=er.mean_degree)
    # Compare against the SBM labels only as a no-signal control: ER has no planted
    # group structure, so any overlap with these labels should be near chance.
    assert overlap_score(sbm.labels, pred) < 0.2


def test_deep_undetectable_case_is_near_chance():
    result = run_sbm_detection(n=2500, c=3.0, epsilon=0.5, seed=4)
    assert result["overlap"] < 0.25


def test_determinism_same_seed_same_overlap_and_edges():
    a = run_sbm_detection(n=1200, c=3.0, epsilon=0.1, seed=7)
    b = run_sbm_detection(n=1200, c=3.0, epsilon=0.1, seed=7)
    assert a["overlap"] == pytest.approx(b["overlap"])
    assert a["n_edges"] == b["n_edges"]
