from __future__ import annotations

from pathlib import Path

from abm_auto.mechanism_challenge import (
    evaluate_mechanism_challenge,
    load_mechanism_challenge,
    mechanism_challenge_gate,
    validate_mechanism_challenge,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_CHALLENGE = REPO_ROOT / "docs/reproduce/evidence-foundry/mechanism-example/challenge.json"


def _challenge(**overrides):
    challenge = {
        "schema": "abm-auto/mechanism-challenge/v1",
        "challenge_id": "social-contact-mechanism-signatures-v1",
        "mechanism_family": "social_contact_lift",
        "required_signatures": ["social_graph", "neighbor_exposure", "contact_lift"],
        "candidate": {
            "id": "social-contact-candidate",
            "present_signatures": [
                "social_graph",
                "neighbor_exposure",
                "contact_lift",
                "survey_distribution_gate",
            ],
            "evidence_refs": [
                "docs/reproduce/social-platform-environment/example-feed/scenario.json",
                "docs/reproduce/evidence-foundry/counterfactual-example/challenge.json",
            ],
        },
        "boundary_note": "Signature presence is mechanism evidence only; it does not prove scientific truth.",
    }
    challenge.update(overrides)
    return challenge


def test_mechanism_challenge_passes_when_required_signatures_present():
    result = evaluate_mechanism_challenge(_challenge())

    assert result["ok"] is True
    assert result["verdict"] == "PASS"
    assert result["missing_signatures"] == []
    assert result["matched_signatures"] == ["social_graph", "neighbor_exposure", "contact_lift"]
    assert result["required_count"] == 3
    assert result["present_count"] == 4


def test_missing_signature_is_miss():
    challenge = _challenge(candidate={
        "id": "social-contact-candidate",
        "present_signatures": ["social_graph", "neighbor_exposure"],
        "evidence_refs": ["docs/reproduce/social-platform-environment/example-feed/scenario.json"],
    })

    result = evaluate_mechanism_challenge(challenge)

    assert result["ok"] is False
    assert result["verdict"] == "MISS"
    assert result["missing_signatures"] == ["contact_lift"]
    assert "missing required signature contact_lift" in result["issues"]


def test_duplicate_required_signature_fails_validation():
    challenge = _challenge(required_signatures=["social_graph", "social_graph"])

    result = validate_mechanism_challenge(challenge)

    assert result["ok"] is False
    assert "duplicate required signature social_graph" in result["issues"]


def test_empty_evidence_refs_fail_validation():
    challenge = _challenge(candidate={
        "id": "social-contact-candidate",
        "present_signatures": ["social_graph", "neighbor_exposure", "contact_lift"],
        "evidence_refs": [],
    })

    result = validate_mechanism_challenge(challenge)

    assert result["ok"] is False
    assert "candidate.evidence_refs must be a non-empty list of strings" in result["issues"]


def test_committed_seed_mechanism_challenge_loads_and_passes():
    challenge = load_mechanism_challenge(SEED_CHALLENGE)

    result = evaluate_mechanism_challenge(challenge)

    assert result["ok"] is True
    assert result["verdict"] == "PASS"


def test_mechanism_gate_description_mentions_boundary():
    ok, desc = mechanism_challenge_gate(_challenge())

    assert ok is True
    assert desc.startswith("Mechanism challenge gate passed")
    assert "not scientific truth" in desc
