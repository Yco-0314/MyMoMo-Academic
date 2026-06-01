"""Tests for DiagnosticsHaltGate — the polarity-inverting Gate (ADR-013).

The thing under test: the seam absorbs a validator whose native polarity
is inverted (halt=True means BAD), and the adapter's judgment does not
drift from the wrapped maybe_halt_on_diagnostics.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from abm_auto.calibration.diagnostics_halt_gate import DiagnosticsHaltGate
from abm_auto.calibration.posterior import maybe_halt_on_diagnostics
from abm_auto.verification.gate import Gate, Verdict

CLEAN = {"n_params": 3, "n_flat_params": 0, "n_eps_claims": 3, "n_eps_mismatches": 0}
ALL_FLAT = {"n_params": 3, "n_flat_params": 3, "n_eps_claims": 0, "n_eps_mismatches": 0}
ALL_MISMATCH = {"n_params": 3, "n_flat_params": 0, "n_eps_claims": 3,
                "n_eps_mismatches": 3, "eps_mismatch_targets": ["s", "i", "r"]}
PARTIAL = {"n_params": 3, "n_flat_params": 1, "n_eps_claims": 3, "n_eps_mismatches": 1}


def test_gate_satisfies_protocol() -> None:
    g = DiagnosticsHaltGate()
    assert isinstance(g, Gate)
    assert g.name == "diagnostics_halt"
    assert g.family == "diagnostics_signal"
    assert g.tier == "refutation"


def test_clean_not_refuted() -> None:
    v = DiagnosticsHaltGate().judge(CLEAN)
    assert isinstance(v, Verdict)
    assert v.passed is True       # not halted = not refuted as broken
    assert v.reasons == []


def test_all_flat_refuted() -> None:
    v = DiagnosticsHaltGate().judge(ALL_FLAT)
    assert v.passed is False      # halt = refuted
    assert any("FLAT" in r for r in v.reasons)


def test_all_mismatch_refuted() -> None:
    v = DiagnosticsHaltGate().judge(ALL_MISMATCH)
    assert v.passed is False
    assert any("MISMATCH" in r for r in v.reasons)


def test_partial_does_not_over_fire() -> None:
    """The policy's deliberate conservatism: partial signals don't halt."""
    assert DiagnosticsHaltGate().judge(PARTIAL).passed is True


def test_polarity_inverted_vs_wrapped(tmp_path: Path) -> None:
    """passed must equal (not should_halt) of the original, on every case —
    the adapter must not drift from what it wraps."""
    g = DiagnosticsHaltGate()
    for sig in (CLEAN, ALL_FLAT, ALL_MISMATCH, PARTIAL):
        ws = SimpleNamespace(path=tmp_path)
        (tmp_path / "diagnostics_signal.json").write_text(json.dumps(sig))
        halt, _ = maybe_halt_on_diagnostics(ws)
        assert g.judge(sig).passed == (not halt)


def test_passed_renders_not_refuted() -> None:
    rendered = DiagnosticsHaltGate().judge(CLEAN).render()
    assert "not refuted" in rendered
    assert "verified" not in rendered


def test_judge_is_pure_no_kill_memo(tmp_path: Path) -> None:
    """The Gate's judge must write nothing (the kill_memo side effect
    belongs to the caller, not the judgment)."""
    DiagnosticsHaltGate().judge(ALL_FLAT)
    assert not (tmp_path / "kill_memo.md").exists()


def test_self_test_passes() -> None:
    assert DiagnosticsHaltGate().self_test() is True
