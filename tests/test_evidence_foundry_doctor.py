from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from abm_auto.evidence_foundry_batch import (
    audit_evidence_foundry_batch_report,
    audit_evidence_foundry_naming,
    diagnose_evidence_foundry_workspace,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_BATCH = REPO_ROOT / "docs/reproduce/evidence-foundry/batch-registry.json"
CHALLENGE_REGISTRY = REPO_ROOT / "docs/reproduce/autodata-challenges/registry.json"
CHALLENGE_ROOT = REPO_ROOT / "docs/reproduce/autodata-challenges"
TEMPLATE_PATH = REPO_ROOT / "docs/agent-handoff-template.md"


def test_seed_workspace_doctor_passes():
    result = diagnose_evidence_foundry_workspace(
        SEED_BATCH,
        CHALLENGE_REGISTRY,
        CHALLENGE_ROOT,
        repo=REPO_ROOT,
    )

    assert result["ok"] is True
    assert result["summary"]["batch_entries"] == 13
    assert result["summary"]["batch_failed"] == 0
    assert result["summary"]["challenge_entries"] == 2
    assert result["summary"]["challenge_failed"] == 0
    assert result["summary"]["report_lines"] > 10
    assert result["summary"]["naming_issues"] == 0
    assert result["summary"]["report_matches_committed"] is True
    assert result["report"]["matches_committed"] is True
    assert result["naming_audit"]["ok"] is True
    assert result["naming_audit"]["checks"] == {
        "batch_report_title": True,
        "challenge_registry_title": True,
        "claude_bridge_no_private_cot": True,
        "claude_bridge_points_to_agents": True,
        "claude_bridge_points_to_protocol": True,
        "claude_bridge_thin": True,
        "handoff_protocol_heading": True,
        "handoff_protocol_gate_command": True,
        "handoff_template_heading": True,
        "handoff_template_structure": True,
        "mir_challenge_phase": True,
        "mir_producer_phase": True,
    }


def test_cli_doctor_prints_json_result():
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.evidence_foundry_batch",
            "doctor",
            "docs/reproduce/evidence-foundry/batch-registry.json",
            "--challenge-registry",
            "docs/reproduce/autodata-challenges/registry.json",
            "--challenge-root",
            "docs/reproduce/autodata-challenges",
            "--repo",
            str(REPO_ROOT),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)

    assert result["ok"] is True
    assert result["summary"]["batch_entries"] == 13
    assert result["summary"]["challenge_entries"] == 2
    assert result["summary"]["naming_issues"] == 0
    assert result["summary"]["report_matches_committed"] is True


def test_missing_batch_file_fails_doctor_with_readable_issue():
    result = diagnose_evidence_foundry_workspace(
        REPO_ROOT / "docs/reproduce/evidence-foundry/missing-batch.json",
        CHALLENGE_REGISTRY,
        CHALLENGE_ROOT,
        repo=REPO_ROOT,
    )

    assert result["ok"] is False
    assert result["batch_gate"]["ok"] is False
    assert "batch path does not exist" in result["batch_gate"]["issues"]


def test_report_audit_rejects_stale_committed_report(tmp_path):
    batch = {
        "schema": "abm-auto/evidence-foundry-batch/v1",
        "title": "Empty Batch",
        "entries": [],
        "boundary_note": "Batch gate checks artifact health only; it is not a scientific truth certificate.",
    }
    batch_path = tmp_path / "batch-registry.json"
    batch_path.write_text(json.dumps(batch), encoding="utf-8")
    (tmp_path / "BATCH-REPORT.md").write_text("# stale\n", encoding="utf-8")

    result = audit_evidence_foundry_batch_report(batch_path, repo=tmp_path)

    assert result["ok"] is False
    assert result["matches_committed"] is False
    assert "committed batch report does not match rendered report" in result["issues"]


def test_naming_audit_rejects_old_autodata_handoff_heading(tmp_path):
    (tmp_path / "docs/reproduce/evidence-foundry").mkdir(parents=True)
    (tmp_path / "docs/reproduce/evidence-foundry/BATCH-REPORT.md").write_text(
        "# MyMoMo Evidence Foundry Batch Report\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/reproduce/autodata-challenges").mkdir(parents=True)
    (tmp_path / "docs/reproduce/autodata-challenges/registry.json").write_text(
        json.dumps({"title": "MyMoMo Evidence Foundry Curriculum"}),
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs/agent-handoff-protocol.md").write_text(
        "## AutoData Challenge Handoff\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/agent-handoff-template.md").write_text(
        "## Evidence Foundry Challenge Handoff\n",
        encoding="utf-8",
    )
    dogfood_dir = tmp_path / "docs/reproduce/autodata-challenges/mir-v0-half-a"
    dogfood_dir.mkdir(parents=True)
    for name in ("challenge-pack.json", "producer-spec.json"):
        (dogfood_dir / name).write_text(
            json.dumps({
                "extra": {
                    "phase": "MyMoMo Evidence Foundry Challenge Harness Phase 1.1",
                },
            }),
            encoding="utf-8",
        )

    result = audit_evidence_foundry_naming(repo=tmp_path)

    assert result["ok"] is False
    assert result["checks"]["handoff_protocol_heading"] is False
    assert result["checks"]["handoff_protocol_gate_command"] is False
    assert result["checks"]["handoff_template_structure"] is False
    assert any("agent-handoff-protocol.md" in issue for issue in result["issues"])


def test_naming_audit_rejects_claude_bridge_drift(tmp_path):
    (tmp_path / "docs/reproduce/evidence-foundry").mkdir(parents=True)
    (tmp_path / "docs/reproduce/evidence-foundry/BATCH-REPORT.md").write_text(
        "# MyMoMo Evidence Foundry Batch Report\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/reproduce/autodata-challenges").mkdir(parents=True)
    (tmp_path / "docs/reproduce/autodata-challenges/registry.json").write_text(
        json.dumps({"title": "MyMoMo Evidence Foundry Curriculum"}),
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs/agent-handoff-protocol.md").write_text(
        "## Evidence Foundry Challenge Handoff\n"
        ".venv/bin/python -m abm_auto.agent_handoff gate <handoff-note.md>\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/agent-handoff-template.md").write_text(
        TEMPLATE_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "CLAUDE.md").write_text(
        "# CLAUDE.md\n\nDuplicated local rules live here.\n",
        encoding="utf-8",
    )
    dogfood_dir = tmp_path / "docs/reproduce/autodata-challenges/mir-v0-half-a"
    dogfood_dir.mkdir(parents=True)
    for name in ("challenge-pack.json", "producer-spec.json"):
        (dogfood_dir / name).write_text(
            json.dumps({
                "extra": {
                    "phase": "MyMoMo Evidence Foundry Challenge Harness Phase 1.1",
                },
            }),
            encoding="utf-8",
        )

    result = audit_evidence_foundry_naming(repo=tmp_path)

    assert result["ok"] is False
    assert result["checks"]["claude_bridge_thin"] is False
    assert result["checks"]["claude_bridge_points_to_agents"] is False
    assert result["checks"]["claude_bridge_points_to_protocol"] is False
    assert result["checks"]["claude_bridge_no_private_cot"] is False
    assert any("CLAUDE.md" in issue for issue in result["issues"])
