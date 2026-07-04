from __future__ import annotations

from pathlib import Path

from abm_auto.counterfactual_challenge import (
    counterfactual_challenge_gate,
    evaluate_counterfactual_challenge,
    load_counterfactual_challenge,
    validate_counterfactual_challenge,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_CHALLENGE = REPO_ROOT / "docs/reproduce/evidence-foundry/counterfactual-example/challenge.json"


def _challenge(**overrides):
    challenge = {
        "schema": "abm-auto/counterfactual-challenge/v1",
        "challenge_id": "evacuation-mechanism-counterfactual-v1",
        "claim": "Social contact mechanism explains evacuation lift better than null exposure.",
        "observed_metrics": {
            "evacuation_lift": 0.30,
            "contact_reach": 0.50,
        },
        "primary_id": "social_contact",
        "alternative_id": "null_exposure",
        "discriminating_metrics": ["evacuation_lift", "contact_reach"],
        "candidates": [
            {
                "id": "social_contact",
                "mechanism": "social contact lift",
                "metrics": {"evacuation_lift": 0.28, "contact_reach": 0.46},
            },
            {
                "id": "null_exposure",
                "mechanism": "no social exposure",
                "metrics": {"evacuation_lift": 0.05, "contact_reach": 0.10},
            },
        ],
        "boundary_note": "Counterfactual challenge compares recorded metrics; it is not causal proof.",
    }
    challenge.update(overrides)
    return challenge


def test_counterfactual_challenge_passes_when_primary_fits_better():
    result = evaluate_counterfactual_challenge(_challenge(), margin=0.05)

    assert result["ok"] is True
    assert result["verdict"] == "PASS"
    assert result["primary_error"] == 0.06
    assert result["alternative_error"] == 0.65


def test_close_candidates_are_inconclusive():
    challenge = _challenge(candidates=[
        {
            "id": "social_contact",
            "mechanism": "social contact lift",
            "metrics": {"evacuation_lift": 0.28, "contact_reach": 0.46},
        },
        {
            "id": "null_exposure",
            "mechanism": "no social exposure",
            "metrics": {"evacuation_lift": 0.27, "contact_reach": 0.45},
        },
    ])

    result = evaluate_counterfactual_challenge(challenge, margin=0.05)

    assert result["ok"] is False
    assert result["verdict"] == "INCONCLUSIVE"


def test_primary_worse_is_miss():
    challenge = _challenge(candidates=[
        {
            "id": "social_contact",
            "mechanism": "social contact lift",
            "metrics": {"evacuation_lift": 0.0, "contact_reach": 0.0},
        },
        {
            "id": "null_exposure",
            "mechanism": "no social exposure",
            "metrics": {"evacuation_lift": 0.28, "contact_reach": 0.46},
        },
    ])

    result = evaluate_counterfactual_challenge(challenge, margin=0.05)

    assert result["ok"] is False
    assert result["verdict"] == "MISS"


def test_missing_candidate_metric_fails_validation():
    challenge = _challenge(candidates=[
        {
            "id": "social_contact",
            "mechanism": "social contact lift",
            "metrics": {"evacuation_lift": 0.28},
        },
        {
            "id": "null_exposure",
            "mechanism": "no social exposure",
            "metrics": {"evacuation_lift": 0.05, "contact_reach": 0.10},
        },
    ])

    result = validate_counterfactual_challenge(challenge)

    assert result["ok"] is False
    assert "candidate social_contact missing metric contact_reach" in result["issues"]


def test_committed_counterfactual_challenge_loads_and_passes():
    challenge = load_counterfactual_challenge(SEED_CHALLENGE)

    result = evaluate_counterfactual_challenge(challenge)

    assert result["ok"] is True
    assert result["verdict"] == "PASS"


def test_counterfactual_gate_description_mentions_boundary():
    ok, desc = counterfactual_challenge_gate(_challenge())

    assert ok is True
    assert desc.startswith("Counterfactual challenge gate passed")
    assert "not causal proof" in desc
