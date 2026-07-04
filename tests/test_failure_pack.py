from __future__ import annotations

from pathlib import Path

from abm_auto.failure_pack import (
    build_failure_pack,
    load_failure_pack,
    summarize_failure_pack,
    validate_failure_pack,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_PACK = REPO_ROOT / "docs/reproduce/evidence-foundry/failure-pack-example/failure-pack.json"


def _pack(**overrides):
    pack = {
        "schema": "abm-auto/failure-pack/v1",
        "source_id": "synthetic-miss-v1",
        "claims": [
            {
                "id": "P1",
                "verdict": "MISS",
                "reason": "Observed evacuation did not increase under intervention.",
                "evidence_refs": ["findings", "results"],
            }
        ],
        "scope_ceilings": [
            "Synthetic fixture only; no real-world external validity claim."
        ],
        "residuals": [
            {
                "metric": "evacuation_lift",
                "observed": 0.0,
                "predicted": 0.25,
                "error": 0.25,
            }
        ],
        "boundary_note": "Failure pack records a MISS; it does not turn it into a pass.",
    }
    pack.update(overrides)
    return pack


def test_valid_failure_pack_passes():
    result = validate_failure_pack(_pack())

    assert result == {"ok": True, "issues": [], "claim_count": 1}


def test_build_failure_pack_output_validates():
    pack = build_failure_pack(
        source_id="synthetic-miss-v1",
        claims=_pack()["claims"],
        scope_ceilings=_pack()["scope_ceilings"],
        residuals=_pack()["residuals"],
        boundary_note="Failure pack records a MISS; it does not turn it into a pass.",
    )

    result = validate_failure_pack(pack)

    assert result["ok"] is True
    assert pack["schema"] == "abm-auto/failure-pack/v1"


def test_pass_verdict_is_rejected():
    pack = _pack(claims=[
        {
            "id": "P1",
            "verdict": "PASS",
            "reason": "not a failure",
            "evidence_refs": ["findings"],
        }
    ])

    result = validate_failure_pack(pack)

    assert result["ok"] is False
    assert "claims[0].verdict must be one of BLOCKED, INCONCLUSIVE, MISS, PARTIAL" in result["issues"]


def test_claim_without_evidence_refs_is_rejected():
    pack = _pack(claims=[
        {
            "id": "P1",
            "verdict": "MISS",
            "reason": "missing citations",
            "evidence_refs": [],
        }
    ])

    result = validate_failure_pack(pack)

    assert result["ok"] is False
    assert "claims[0].evidence_refs must be a non-empty list of strings" in result["issues"]


def test_residual_without_numeric_error_is_rejected():
    pack = _pack(residuals=[
        {
            "metric": "evacuation_lift",
            "observed": 0.0,
            "predicted": 0.25,
            "error": "large",
        }
    ])

    result = validate_failure_pack(pack)

    assert result["ok"] is False
    assert "residuals[0].error must be numeric" in result["issues"]


def test_committed_seed_failure_pack_validates():
    pack = load_failure_pack(SEED_PACK)

    result = validate_failure_pack(pack)

    assert result["ok"] is True


def test_failure_pack_summary_counts_content():
    summary = summarize_failure_pack(_pack())

    assert summary == {
        "source_id": "synthetic-miss-v1",
        "claims": 1,
        "residuals": 1,
        "scope_ceilings": 1,
        "verdicts": {"MISS": 1},
    }
