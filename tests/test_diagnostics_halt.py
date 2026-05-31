"""Tests for `maybe_halt_on_diagnostics` — the policy gate that converts
all-FLAT β or all-MISMATCH ε into a HALT + kill_memo.

The reliability sample on 2026-05-31 (docs/dogfood/2026-05-31-reliability-r*.md)
showed 2/5 Pipeline runs producing exit code 0 with broken simulators that
the diagnostics layer correctly flagged. Without this gate, those 2 runs
would appear successful to anyone not reading calibration_report.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from abm_auto.calibration.posterior import maybe_halt_on_diagnostics


class _FakeWorkspace:
    """Just enough workspace shape for posterior.maybe_halt_on_diagnostics."""
    def __init__(self, path: Path) -> None:
        self.path = path


def _write_signal(ws_path: Path, **fields) -> None:
    """Helper: write diagnostics_signal.json with the given fields,
    defaulting unspecified ones."""
    default = {
        "n_params": 3,
        "n_targets": 3,
        "n_flat_params": 0,
        "flat_params": [],
        "n_eps_claims": 0,
        "n_eps_mismatches": 0,
        "eps_mismatch_targets": [],
        "eps_verdict": "skipped",
    }
    default.update(fields)
    (ws_path / "diagnostics_signal.json").write_text(
        json.dumps(default), encoding="utf-8",
    )


def test_no_signal_file_means_no_halt(tmp_path: Path) -> None:
    """Missing diagnostics_signal.json → safe default: don't halt."""
    ws = _FakeWorkspace(tmp_path)
    should_halt, reason = maybe_halt_on_diagnostics(ws)
    assert should_halt is False
    assert reason == ""


def test_clean_diagnostics_dont_halt(tmp_path: Path) -> None:
    """All-identified β + all-match ε → don't halt."""
    _write_signal(
        tmp_path,
        n_flat_params=0,
        n_eps_claims=3,
        n_eps_mismatches=0,
        eps_verdict="PASS",
    )
    ws = _FakeWorkspace(tmp_path)
    should_halt, _ = maybe_halt_on_diagnostics(ws)
    assert should_halt is False
    # No kill memo written
    assert not (tmp_path / "kill_memo.md").exists()


def test_all_flat_profile_triggers_halt(tmp_path: Path) -> None:
    """The Wave-A scenario: all 3 params show curvature 0 (broken sim)."""
    _write_signal(
        tmp_path,
        n_params=3,
        n_flat_params=3,
        flat_params=["virus_spread", "recovery", "gain_resistance"],
        n_eps_claims=0,  # ε didn't run (no LLM key, for example)
    )
    ws = _FakeWorkspace(tmp_path)
    should_halt, reason = maybe_halt_on_diagnostics(ws)
    assert should_halt is True
    assert "FLAT" in reason
    assert "3" in reason
    # Kill memo written
    kill = tmp_path / "kill_memo.md"
    assert kill.exists()
    txt = kill.read_text(encoding="utf-8")
    assert "Calibration Diagnostics Failed" in txt
    assert "FLAT profile" in txt


def test_all_eps_mismatch_triggers_halt(tmp_path: Path) -> None:
    """The runs 2+4 scenario: all 3 targets show 'stable' vs story claims."""
    _write_signal(
        tmp_path,
        n_flat_params=0,  # β looked OK (or didn't run meaningfully)
        n_eps_claims=3,
        n_eps_mismatches=3,
        eps_mismatch_targets=["susceptible", "infected", "resistant"],
        eps_verdict="MISMATCH",
    )
    ws = _FakeWorkspace(tmp_path)
    should_halt, reason = maybe_halt_on_diagnostics(ws)
    assert should_halt is True
    assert "MISMATCH" in reason
    assert "susceptible" in reason
    kill = tmp_path / "kill_memo.md"
    assert kill.exists()
    assert "ε" in kill.read_text(encoding="utf-8") or "execution" in kill.read_text(encoding="utf-8")


def test_partial_flat_does_not_halt(tmp_path: Path) -> None:
    """One param FLAT out of three → identifiability concern, NOT halt.
    Calibration can still be useful even when one parameter is loose."""
    _write_signal(
        tmp_path,
        n_params=3,
        n_flat_params=1,
        flat_params=["gain_resistance"],
        n_eps_claims=3,
        n_eps_mismatches=0,
        eps_verdict="PASS",
    )
    ws = _FakeWorkspace(tmp_path)
    should_halt, _ = maybe_halt_on_diagnostics(ws)
    assert should_halt is False
    assert not (tmp_path / "kill_memo.md").exists()


def test_partial_mismatch_does_not_halt(tmp_path: Path) -> None:
    """One target mismatching out of three → real diagnostic concern, but
    not necessarily a totally broken model. Don't halt."""
    _write_signal(
        tmp_path,
        n_eps_claims=3,
        n_eps_mismatches=1,
        eps_mismatch_targets=["resistant"],
        eps_verdict="MISMATCH",
    )
    ws = _FakeWorkspace(tmp_path)
    should_halt, _ = maybe_halt_on_diagnostics(ws)
    assert should_halt is False


def test_both_all_flat_and_all_mismatch_compose(tmp_path: Path) -> None:
    """The worst case: both signals fully red. Kill memo lists both reasons."""
    _write_signal(
        tmp_path,
        n_params=3,
        n_flat_params=3,
        flat_params=["a", "b", "c"],
        n_eps_claims=3,
        n_eps_mismatches=3,
        eps_mismatch_targets=["a", "b", "c"],
        eps_verdict="MISMATCH",
    )
    ws = _FakeWorkspace(tmp_path)
    should_halt, reason = maybe_halt_on_diagnostics(ws)
    assert should_halt is True
    txt = (tmp_path / "kill_memo.md").read_text(encoding="utf-8")
    # Both reasons present
    assert "FLAT" in txt
    assert "MISMATCH" in txt


def test_corrupt_signal_file_does_not_crash(tmp_path: Path) -> None:
    """Malformed JSON → don't crash, safe default to don't halt."""
    (tmp_path / "diagnostics_signal.json").write_text("not json {", encoding="utf-8")
    ws = _FakeWorkspace(tmp_path)
    should_halt, _ = maybe_halt_on_diagnostics(ws)
    assert should_halt is False
