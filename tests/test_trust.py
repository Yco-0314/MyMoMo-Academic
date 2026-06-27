"""Tests for the per-run trust report (abm_auto.trust)."""
from __future__ import annotations

import json

from abm_auto.trust import build_trust_report


def _event(issue_id, event_type, phase, severity="MEDIUM", text="x"):
    return {
        "event_id": issue_id, "timestamp": "2026-06-26T00:00:00Z",
        "event_type": event_type, "issue_id": issue_id, "phase": phase,
        "severity": severity, "text": text, "structured": {}, "actor": "Gate",
    }


def _workspace(tmp_path, events, report=True):
    if report:
        (tmp_path / "REPORT.md").write_text("# report", encoding="utf-8")
    lines = "\n".join(json.dumps(e) for e in events)
    (tmp_path / "audit_ledger.jsonl").write_text(lines + ("\n" if lines else ""), encoding="utf-8")
    return tmp_path


def test_clean_when_completed_and_no_open_issues(tmp_path):
    _workspace(tmp_path, [_event("i1", "raise", "Phase 4"), _event("i1", "resolve", "Phase 4")])
    r = build_trust_report(tmp_path)
    assert r.cleanliness == "CLEAN"
    assert r.completed is True
    assert r.open_total == 0
    assert r.resolved_total == 1


def test_caveated_when_open_issue_remains(tmp_path):
    _workspace(tmp_path, [_event("i1", "raise", "Phase 4", severity="HIGH")])
    r = build_trust_report(tmp_path)
    assert r.cleanliness == "CAVEATED"
    assert r.open_total == 1
    assert r.open_high == 1


def test_failed_when_no_report(tmp_path):
    _workspace(tmp_path, [], report=False)
    r = build_trust_report(tmp_path)
    assert r.cleanliness == "FAILED"
    assert r.completed is False


def test_per_phase_breakdown_and_silent(tmp_path):
    _workspace(tmp_path, [
        _event("a", "raise", "Phase 4", severity="HIGH"),
        _event("b", "raise", "Phase 5"), _event("b", "resolve", "Phase 5"),
    ])
    r = build_trust_report(tmp_path)
    by_phase = {p.phase: p for p in r.phases}
    assert by_phase["Phase 4"].open_issues == 1 and by_phase["Phase 4"].resolved_issues == 0
    assert by_phase["Phase 5"].open_issues == 0 and by_phase["Phase 5"].resolved_issues == 1
    # A canonical phase that produced no events is reported as silent.
    assert "Phase 2" in r.silent_phases


import pytest


@pytest.mark.parametrize("score,thresh,expected", [
    (5.0, 10.0, "REPRO"), (10.0, 10.0, "REPRO"),
    (15.0, 10.0, "PARTIAL"), (20.0, 10.0, "PARTIAL"),
    (25.0, 10.0, "MISS"),
])
def test_fidelity_verdict(tmp_path, score, thresh, expected):
    _workspace(tmp_path, [])
    r = build_trust_report(tmp_path, repro_score=(score, thresh))
    assert r.fidelity == expected
    assert r.fidelity_detail == (score, thresh)


def test_fidelity_none_without_score(tmp_path):
    _workspace(tmp_path, [])
    assert build_trust_report(tmp_path).fidelity is None


def test_render_is_honest_no_verified(tmp_path):
    _workspace(tmp_path, [_event("a", "raise", "Phase 4", severity="HIGH")])
    r = build_trust_report(tmp_path)
    md = r.render_markdown()
    assert "CAVEATED" in md
    assert "verified" not in md.lower()   # ledger-centric: never claims "verified"
    assert r.render_console()             # non-empty


from typer.testing import CliRunner

from abm_auto.cli import app

_runner = CliRunner()


def test_trust_cli_renders(tmp_path):
    _workspace(tmp_path, [_event("a", "raise", "Phase 4", severity="HIGH")])
    result = _runner.invoke(app, ["trust", str(tmp_path)])
    assert result.exit_code == 0
    assert "CAVEATED" in result.stdout
    assert (tmp_path / "trust_report.md").exists()  # refreshes the file


def test_trust_cli_missing_path():
    result = _runner.invoke(app, ["trust", "/no/such/workspace"])
    assert result.exit_code != 0
