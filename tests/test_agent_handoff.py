from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from abm_auto.agent_handoff import (
    agent_handoff_gate,
    load_agent_handoff_note,
    validate_agent_handoff_note,
    validate_agent_handoff_template,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "docs/agent-handoff-template.md"


def _valid_note(*replacement_pairs: tuple[str, str]) -> str:
    note = """# Agent Handoff Note

## Status

- State: ready for verification
- Summary: Added a small handoff gate.

## Git

- Branch: main
- Current commit: abc1234
- Working tree: clean except ignored scratch files

## Changed Files

- Added: abm_auto/agent_handoff.py
- Modified: tests/test_agent_handoff.py
- Deleted: none

## Commits

- Created: abc1234 feat(repro): add handoff gate
- Pending: none

## Commands Run

- Command: .venv/bin/python -m pytest tests/test_agent_handoff.py -q
  - Result: 6 passed

## Verification

- Targeted tests: 6 passed
- Full GIS suite: not run; not GIS work
- Engine oracle science: PASS
- Engine oracle byte check: PASS
- Base suite: not run; targeted only
- Forbidden base-engine diff: empty

## Evidence Foundry Challenge Handoff

- Challenge pack: not applicable
- Answer manifest: not applicable
- Validate result: not applicable
- Grade result: not applicable
- Gate result: not applicable

## Remaining Work

- Next task: run full verification
- Files likely involved: none
- Next command: .venv/bin/python -m pytest tests/test_agent_handoff.py -q

## Resume Command

```bash
git status --short --branch
```

## Risks / Assumptions

- Risks: validator checks completeness, not factual truth
- Assumptions: current branch is main
"""
    for old, new in replacement_pairs:
        note = note.replace(old, new)
    return note


def test_valid_agent_handoff_note_passes():
    result = validate_agent_handoff_note(_valid_note())

    assert result == {
        "ok": True,
        "issues": [],
        "heading_count": 11,
        "field_count": 28,
    }


def test_blank_template_has_valid_structure_but_is_not_a_complete_note():
    template = load_agent_handoff_note(TEMPLATE_PATH)

    template_result = validate_agent_handoff_template(template)
    note_result = validate_agent_handoff_note(template)

    assert template_result["ok"] is True
    assert note_result["ok"] is False
    assert "field State must have a non-placeholder value" in note_result["issues"]
    assert template_result["field_count"] == 28


def test_missing_required_field_fails():
    note = _valid_note(("- Forbidden base-engine diff: empty", ""))

    result = validate_agent_handoff_note(note)

    assert result["ok"] is False
    assert "missing required field Forbidden base-engine diff" in result["issues"]


def test_missing_next_command_fails():
    note = _valid_note(("- Next command: .venv/bin/python -m pytest tests/test_agent_handoff.py -q", ""))

    result = validate_agent_handoff_note(note)

    assert result["ok"] is False
    assert "missing required field Next command" in result["issues"]


def test_placeholder_values_fail():
    note = _valid_note(("ready for verification", "TODO"))

    result = validate_agent_handoff_note(note)

    assert result["ok"] is False
    assert "field State must have a non-placeholder value" in result["issues"]


def test_agent_handoff_gate_reports_boundary():
    ok, desc = agent_handoff_gate(_valid_note())

    assert ok is True
    assert desc.startswith("Agent handoff gate passed")
    assert "not factual truth" in desc


def test_cli_template_validates_committed_template():
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.agent_handoff",
            "template",
            "docs/agent-handoff-template.md",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)

    assert result["ok"] is True
    assert result["field_count"] == 28


def test_cli_gate_accepts_completed_note(tmp_path: Path):
    note_path = tmp_path / "handoff.md"
    note_path.write_text(_valid_note(), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.agent_handoff",
            "gate",
            str(note_path),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)

    assert result["ok"] is True
    assert result["description"].startswith("Agent handoff gate passed")


def test_cli_gate_rejects_blank_template_as_completed_note():
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.agent_handoff",
            "gate",
            "docs/agent-handoff-template.md",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert result["ok"] is False
    assert "field State must have a non-placeholder value" in result["validation"]["issues"]
