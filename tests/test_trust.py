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
