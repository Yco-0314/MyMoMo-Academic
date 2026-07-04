from __future__ import annotations

from pathlib import Path

from abm_auto.synthetic_survey_gate import (
    evaluate_synthetic_survey_gate,
    load_synthetic_survey_json,
    synthetic_survey_gate,
    validate_synthetic_survey_answer,
    validate_synthetic_survey_observed,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "docs/reproduce/synthetic-survey-gate/example-panel"
OBSERVED_PATH = FIXTURE_DIR / "observed.json"
ANSWER_PATH = FIXTURE_DIR / "synthetic-answer.json"


def _observed(**overrides):
    payload = {
        "schema": "abm-auto/synthetic-survey-observed/v1",
        "survey_id": "example-panel-survey-v1",
        "population_id": "example-panel-v1",
        "questions": [
            {"id": "q_support", "text": "Support evacuation?", "options": ["yes", "no"]},
            {"id": "q_trust", "text": "Trust warning?", "options": ["high", "low"]},
        ],
        "rows": [
            {"question_id": "q_support", "group": "all", "option": "yes", "share": 0.60},
            {"question_id": "q_support", "group": "all", "option": "no", "share": 0.40},
            {"question_id": "q_support", "group": "region:north", "option": "yes", "share": 0.70},
            {"question_id": "q_trust", "group": "all", "option": "high", "share": 0.55},
        ],
        "boundary_note": "Tiny held-out fixture for gate plumbing only.",
    }
    payload.update(overrides)
    return payload


def _answer(**overrides):
    payload = {
        "schema": "abm-auto/synthetic-survey-answer/v1",
        "survey_id": "example-panel-survey-v1",
        "population_id": "example-panel-v1",
        "rows": [
            {"question_id": "q_support", "group": "all", "option": "yes", "share": 0.56},
            {"question_id": "q_support", "group": "all", "option": "no", "share": 0.44},
            {"question_id": "q_support", "group": "region:north", "option": "yes", "share": 0.62},
            {"question_id": "q_trust", "group": "all", "option": "high", "share": 0.50},
        ],
        "boundary_note": "Synthetic answer fixture; not a human-validity proof.",
    }
    payload.update(overrides)
    return payload


def test_synthetic_survey_gate_passes_for_close_distributions():
    result = evaluate_synthetic_survey_gate(_observed(), _answer())

    assert result["ok"] is True
    assert result["verdict"] == "PASS"
    assert result["metrics"]["compared_rows"] == 4
    assert result["metrics"]["max_distribution_error"] == 0.05
    assert result["metrics"]["max_subgroup_error"] == 0.08
    assert "not validate synthetic people" in result["boundary_note"]


def test_high_aggregate_error_is_miss():
    answer = _answer(rows=[
        {"question_id": "q_support", "group": "all", "option": "yes", "share": 0.20},
        {"question_id": "q_support", "group": "all", "option": "no", "share": 0.80},
        {"question_id": "q_support", "group": "region:north", "option": "yes", "share": 0.62},
        {"question_id": "q_trust", "group": "all", "option": "high", "share": 0.50},
    ])

    result = evaluate_synthetic_survey_gate(_observed(), answer)

    assert result["ok"] is False
    assert result["verdict"] == "MISS"
    assert "aggregate distribution error exceeds threshold" in result["issues"]


def test_subgroup_only_error_is_partial():
    answer = _answer(rows=[
        {"question_id": "q_support", "group": "all", "option": "yes", "share": 0.56},
        {"question_id": "q_support", "group": "all", "option": "no", "share": 0.44},
        {"question_id": "q_support", "group": "region:north", "option": "yes", "share": 0.30},
        {"question_id": "q_trust", "group": "all", "option": "high", "share": 0.50},
    ])

    result = evaluate_synthetic_survey_gate(_observed(), answer)

    assert result["ok"] is False
    assert result["verdict"] == "PARTIAL"
    assert "subgroup error exceeds threshold" in result["issues"]


def test_survey_id_mismatch_fails():
    result = evaluate_synthetic_survey_gate(
        _observed(),
        _answer(survey_id="other-survey"),
    )

    assert result["ok"] is False
    assert result["verdict"] == "MISS"
    assert "survey_id mismatch" in result["issues"]


def test_duplicate_observed_rows_fail_validation():
    observed = _observed()
    observed["rows"].append(dict(observed["rows"][0]))

    result = validate_synthetic_survey_observed(observed)

    assert result["ok"] is False
    assert "duplicate row key q_support|all|yes" in result["issues"]


def test_invalid_answer_share_fails_validation():
    answer = _answer(rows=[
        {"question_id": "q_support", "group": "all", "option": "yes", "share": 1.2},
    ])

    result = validate_synthetic_survey_answer(answer)

    assert result["ok"] is False
    assert "rows[0].share must be between 0 and 1" in result["issues"]


def test_missing_synthetic_rows_are_miss():
    answer = _answer(rows=[
        {"question_id": "q_support", "group": "all", "option": "yes", "share": 0.56},
    ])

    result = evaluate_synthetic_survey_gate(_observed(), answer)

    assert result["ok"] is False
    assert result["verdict"] == "MISS"
    assert "missing synthetic row q_support|all|no" in result["issues"]


def test_committed_survey_gate_fixtures_load_and_pass():
    observed = load_synthetic_survey_json(OBSERVED_PATH)
    answer = load_synthetic_survey_json(ANSWER_PATH)

    result = evaluate_synthetic_survey_gate(observed, answer)

    assert result["ok"] is True
    assert result["verdict"] == "PASS"


def test_synthetic_survey_gate_description_mentions_boundary():
    ok, desc = synthetic_survey_gate(_observed(), _answer())

    assert ok is True
    assert desc.startswith("Synthetic survey gate passed")
    assert "does not validate synthetic people as human substitutes" in desc
