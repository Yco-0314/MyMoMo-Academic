"""Unit tests for execution_verifier — trajectory classification + claim diff.

LLM extraction is mocked. Classification is tested on synthetic
trajectories with known shape (SIR-like, Schelling-like, edge cases).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from abm_auto.verification.execution_verifier import (
    DIRECTION_LABELS,
    QualitativeClaim,
    TrajectoryClassification,
    VerificationResult,
    classify_trajectory,
    classify_trajectory_csv,
    diff_claims_vs_actuals,
    extract_qualitative_claims,
    verify_execution,
)


# ── classify_trajectory (pure) ──────────────────────────────────────────


def test_classify_monotonic_decrease() -> None:
    arr = np.array([147, 134, 118, 99, 76, 59, 35, 13, 10, 9])
    result = classify_trajectory(arr)
    assert result.direction == "monotonic_decrease"


def test_classify_monotonic_increase() -> None:
    arr = np.array([0, 0, 2, 6, 11, 15, 28, 50, 75, 100])
    result = classify_trajectory(arr)
    assert result.direction == "monotonic_increase"


def test_classify_peak_then_decay() -> None:
    """SIR-like infected column: rises to 109 at tick ~7, decays to 27."""
    arr = np.array([3, 16, 30, 45, 63, 76, 99, 109, 107, 100, 94, 86, 78, 70, 63, 58, 50, 42, 35, 27])
    result = classify_trajectory(arr)
    assert result.direction == "peak_then_decay"
    assert result.peak_ratio > 1.5


def test_classify_stable() -> None:
    arr = np.full(50, 0.5)
    arr += np.random.RandomState(0).normal(0, 0.001, 50)  # tiny noise
    result = classify_trajectory(arr)
    assert result.direction == "stable"


def test_classify_unclear_for_noisy_oscillation() -> None:
    np.random.seed(42)
    arr = np.random.RandomState(0).uniform(0, 1, 30)
    result = classify_trajectory(arr)
    assert result.direction == "unclear"


def test_classify_empty_series() -> None:
    arr = np.array([5.0])
    result = classify_trajectory(arr)
    assert result.direction == "unclear"


# ── classify_trajectory_csv ──────────────────────────────────────────────


def test_classify_csv_with_sir_like_columns(tmp_path: Path) -> None:
    df = pd.DataFrame({
        "susceptible": [147 - i * 7 for i in range(20)],   # decreasing
        "infected":    [3, 16, 30, 45, 63, 76, 99, 109, 107, 100, 94, 86, 78, 70, 63, 58, 50, 42, 35, 27],
        "resistant":   list(range(0, 100, 5)),              # increasing
    })
    csv = tmp_path / "sim.csv"
    df.to_csv(csv, index=False)
    results = classify_trajectory_csv(csv, ["susceptible", "infected", "resistant"])
    by_target = {r.target: r.direction for r in results}
    assert by_target["susceptible"] == "monotonic_decrease"
    assert by_target["infected"] == "peak_then_decay"
    assert by_target["resistant"] == "monotonic_increase"


def test_classify_csv_with_missing_column(tmp_path: Path) -> None:
    df = pd.DataFrame({"a": [1, 2, 3]})
    csv = tmp_path / "sim.csv"
    df.to_csv(csv, index=False)
    results = classify_trajectory_csv(csv, ["a", "missing"])
    by_target = {r.target: r.direction for r in results}
    assert by_target["missing"] == "unclear"


# ── extract_qualitative_claims (LLM mocked) ─────────────────────────────


def test_extract_claims_parses_valid_json_block() -> None:
    """Mock LLM returns properly fenced JSON; verify parsing."""
    def fake_llm(system: str, user: str, max_tokens: int = 800, **_kw) -> str:
        return """Sure! Here is the JSON:
```json
{
  "claims": [
    {"target": "susceptible", "direction": "monotonic_decrease", "rationale": "SIR removes S"},
    {"target": "infected", "direction": "peak_then_decay", "rationale": "epidemic peak"}
  ]
}
```
"""
    claims = extract_qualitative_claims("dummy story", ["susceptible", "infected"], fake_llm)
    assert len(claims) == 2
    assert claims[0].target == "susceptible"
    assert claims[0].direction == "monotonic_decrease"


def test_extract_claims_returns_empty_on_parse_failure() -> None:
    """Mock LLM returns garbage — verifier degrades gracefully (skip)."""
    def fake_llm(system: str, user: str, max_tokens: int = 800, **_kw) -> str:
        return "I don't know how to answer that. Sorry."
    claims = extract_qualitative_claims("story", ["x"], fake_llm)
    assert claims == []


def test_extract_claims_skips_invalid_direction_labels() -> None:
    """LLM picks a label not in DIRECTION_LABELS → entry dropped, not crash."""
    def fake_llm(system: str, user: str, max_tokens: int = 800, **_kw) -> str:
        return '{"claims": [{"target": "a", "direction": "spaghetti"}, {"target": "b", "direction": "stable"}]}'
    claims = extract_qualitative_claims("story", ["a", "b"], fake_llm)
    assert len(claims) == 1
    assert claims[0].target == "b"


def test_extract_claims_skips_on_llm_exception() -> None:
    def fake_llm(system: str, user: str, max_tokens: int = 800, **_kw) -> str:
        raise RuntimeError("API down")
    claims = extract_qualitative_claims("story", ["a"], fake_llm)
    assert claims == []


def test_extract_claims_empty_targets_returns_empty() -> None:
    def fake_llm(*args, **kwargs):
        raise AssertionError("should not be called for empty targets")
    claims = extract_qualitative_claims("story", [], fake_llm)
    assert claims == []


# ── diff_claims_vs_actuals + verify_execution ───────────────────────────


def test_diff_detects_mismatch() -> None:
    claims = [
        QualitativeClaim(target="S", direction="monotonic_decrease"),
        QualitativeClaim(target="I", direction="peak_then_decay"),
    ]
    actuals = [
        TrajectoryClassification(target="S", direction="monotonic_increase", peak_ratio=1.0, monotonicity=0.9),
        TrajectoryClassification(target="I", direction="peak_then_decay", peak_ratio=2.0, monotonicity=0.5),
    ]
    result = diff_claims_vs_actuals(claims, actuals)
    assert not result.is_valid
    assert len(result.mismatches) == 1
    target, expected, actual = result.mismatches[0]
    assert target == "S" and expected == "monotonic_decrease" and actual == "monotonic_increase"


def test_diff_unclear_claim_skipped() -> None:
    """If story doesn't specify direction (claim='unclear'), don't fail."""
    claims = [QualitativeClaim(target="X", direction="unclear")]
    actuals = [TrajectoryClassification(target="X", direction="monotonic_increase", peak_ratio=1, monotonicity=0.9)]
    result = diff_claims_vs_actuals(claims, actuals)
    assert result.is_valid


def test_diff_unclear_actual_skipped() -> None:
    """If sim trajectory can't be classified (noisy), don't fail."""
    claims = [QualitativeClaim(target="X", direction="monotonic_increase")]
    actuals = [TrajectoryClassification(target="X", direction="unclear", peak_ratio=1, monotonicity=0.5)]
    result = diff_claims_vs_actuals(claims, actuals)
    assert result.is_valid


def test_verification_feedback_strings_useful_for_gvr() -> None:
    """Mismatch reasons should name target + expected + actual + actionable hint."""
    result = VerificationResult(
        claims=[QualitativeClaim(target="S", direction="monotonic_decrease")],
        actuals=[TrajectoryClassification(target="S", direction="monotonic_increase", peak_ratio=1, monotonicity=0.9)],
        mismatches=[("S", "monotonic_decrease", "monotonic_increase")],
    )
    feedback = result.feedback()
    assert len(feedback) == 1
    msg = feedback[0]
    assert "S" in msg
    assert "monotonic_decrease" in msg
    assert "monotonic_increase" in msg
    assert "environment.step()" in msg


def test_verify_execution_end_to_end(tmp_path: Path) -> None:
    """Compose: mock LLM + real sim CSV + diff."""
    df = pd.DataFrame({
        "S": [100 - i * 5 for i in range(20)],   # monotonic_decrease (correct)
        "I": list(range(0, 100, 5)),              # monotonic_increase, but story says peak_then_decay → mismatch
    })
    csv = tmp_path / "sim.csv"
    df.to_csv(csv, index=False)

    def fake_llm(system: str, user: str, max_tokens: int = 800, **_kw) -> str:
        return json.dumps({
            "claims": [
                {"target": "S", "direction": "monotonic_decrease", "rationale": "SIR"},
                {"target": "I", "direction": "peak_then_decay", "rationale": "epidemic"},
            ]
        })

    result = verify_execution("dummy story", csv, ["S", "I"], fake_llm)
    assert not result.is_valid
    assert len(result.mismatches) == 1
    assert result.mismatches[0][0] == "I"
