"""Tests for outcome_from_verdict — the single Verdict→ValidationOutcome
adapter (ADR-013 task 1, candidate 1).

Pins the one canonical translation that replaced the hand-rolled
per-validator wrapping: tier→severity policy, lossless salient_number,
and pass→ok=True.
"""
from __future__ import annotations

from abm_auto.refinement import ValidationOutcome
from abm_auto.verification.gate import Verdict, outcome_from_verdict


def test_passed_verdict_is_ok() -> None:
    v = Verdict(passed=True, tier="verification", gate_name="g")
    out = outcome_from_verdict(v)
    assert isinstance(out, ValidationOutcome)
    assert out.ok is True


def test_verification_fail_is_fatal() -> None:
    v = Verdict(passed=False, tier="verification", gate_name="anti_pattern",
                reasons=["bad import"])
    out = outcome_from_verdict(v)
    assert out.ok is False
    assert out.severity == "fatal"          # verification fail blocks retry
    assert out.reasons == ["bad import"]
    assert out.structured["tier"] == "verification"


def test_refutation_fail_is_soft_by_default() -> None:
    """Default policy: only verification is fatal. A refutation fail (no
    signal) is soft — it must not, by default, block a codegen retry."""
    v = Verdict(passed=False, tier="refutation", gate_name="surrogate_null",
                reasons=["no signal"], salient_number=(0.9, 0.05))
    out = outcome_from_verdict(v)
    assert out.ok is False
    assert out.severity == "soft"


def test_fatal_tiers_override() -> None:
    """A consumer can choose to treat refutation as fatal too."""
    v = Verdict(passed=False, tier="refutation", gate_name="x", reasons=["r"])
    out = outcome_from_verdict(v, fatal_tiers=frozenset({"verification", "refutation"}))
    assert out.severity == "fatal"


def test_salient_number_preserved_losslessly() -> None:
    """salient_number has no ValidationOutcome field; it must survive in
    structured (the Demo-1 lesson — margin is informative)."""
    v = Verdict(passed=False, tier="refutation", gate_name="null",
                reasons=["no signal"], salient_number=(0.144, 0.05))
    out = outcome_from_verdict(v)
    assert out.structured["salient_score"] == 0.144
    assert out.structured["salient_threshold"] == 0.05


def test_evidence_dict_merged_into_structured() -> None:
    v = Verdict(passed=False, tier="verification", gate_name="g",
                reasons=["r"], evidence={"issue_count": 3})
    out = outcome_from_verdict(v)
    assert out.structured["issue_count"] == 3


def test_passed_verdict_carries_no_noise() -> None:
    """A passing verdict → clean ok=True outcome, no reasons leaked."""
    v = Verdict(passed=True, tier="refutation", gate_name="g",
                salient_number=(0.01, 0.05))
    out = outcome_from_verdict(v)
    assert out.ok is True
    assert out.reasons == []
