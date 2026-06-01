"""Tests for ExecutionDiffGate — the deterministic half of ε (ADR-013 D-LLM).

The point under test: ε's judgement side, with the LLM removed, is a
sound deterministic Gate. The LLM claim-extraction half is NOT exercised
here (it's a generator, not a Gate) — these tests feed claims directly,
exactly as the harness's generate/judge split intends.
"""
from __future__ import annotations

from pathlib import Path

from abm_auto.verification.execution_diff_gate import (
    ExecutionDiffGate,
    ExecutionDiffInput,
)
from abm_auto.verification.execution_verifier import QualitativeClaim
from abm_auto.verification.gate import Gate, Verdict


def _decreasing_csv(tmp_path: Path) -> Path:
    rows = ["tick,susceptible"] + [f"{t},{100 - 4 * t}" for t in range(20)]
    csv = tmp_path / "sim.csv"
    csv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return csv


def test_gate_satisfies_protocol() -> None:
    g = ExecutionDiffGate()
    assert isinstance(g, Gate)
    assert g.name == "execution_diff"
    assert g.family == "trajectory_vs_claims"
    assert g.tier == "refutation"


def test_no_llm_in_judge() -> None:
    """The judge must be callable with no llm_caller anywhere — the whole
    point of the split. ExecutionDiffInput carries no LLM hook."""
    import inspect

    sig = inspect.signature(ExecutionDiffGate.judge)
    assert list(sig.parameters) == ["self", "x"]  # only the input, no llm


def test_matching_claim_not_refuted(tmp_path: Path) -> None:
    g = ExecutionDiffGate()
    x = ExecutionDiffInput(
        claims=[QualitativeClaim("susceptible", "monotonic_decrease")],
        sim_csv=_decreasing_csv(tmp_path),
        targets=["susceptible"],
    )
    v = g.judge(x)
    assert isinstance(v, Verdict)
    assert v.passed is True
    assert v.tier == "refutation"
    assert v.reasons == []


def test_contradicting_claim_refuted(tmp_path: Path) -> None:
    g = ExecutionDiffGate()
    x = ExecutionDiffInput(
        claims=[QualitativeClaim("susceptible", "monotonic_increase")],
        sim_csv=_decreasing_csv(tmp_path),
        targets=["susceptible"],
    )
    v = g.judge(x)
    assert v.passed is False
    assert any("susceptible" in r for r in v.reasons)
    assert v.salient_number == (1.0, 0.0)  # 1 mismatch


def test_passed_renders_not_refuted(tmp_path: Path) -> None:
    g = ExecutionDiffGate()
    x = ExecutionDiffInput(
        claims=[QualitativeClaim("susceptible", "monotonic_decrease")],
        sim_csv=_decreasing_csv(tmp_path),
        targets=["susceptible"],
    )
    rendered = g.judge(x).render()
    assert "not refuted" in rendered
    assert "verified" not in rendered


def test_unclear_claim_skipped(tmp_path: Path) -> None:
    """An 'unclear' claim can't refute anything → passes (matches the
    existing diff semantics)."""
    g = ExecutionDiffGate()
    x = ExecutionDiffInput(
        claims=[QualitativeClaim("susceptible", "unclear")],
        sim_csv=_decreasing_csv(tmp_path),
        targets=["susceptible"],
    )
    assert g.judge(x).passed is True


def test_self_test_passes() -> None:
    assert ExecutionDiffGate().self_test() is True
