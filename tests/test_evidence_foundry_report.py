from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from abm_auto.evidence_foundry_batch import (
    load_evidence_foundry_batch,
    render_evidence_foundry_batch_report,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_BATCH = REPO_ROOT / "docs/reproduce/evidence-foundry/batch-registry.json"
SEED_REPORT = REPO_ROOT / "docs/reproduce/evidence-foundry/BATCH-REPORT.md"


def test_batch_report_includes_summary_table_and_boundary():
    batch = load_evidence_foundry_batch(SEED_BATCH)

    report = render_evidence_foundry_batch_report(batch, repo=REPO_ROOT)

    assert report.startswith("# MyMoMo Evidence Foundry Batch Report")
    assert "- Overall gate: PASS" in report
    assert "- Entries: 13" in report
    assert "- Failed: 0" in report
    assert "| challenge-registry | repro_challenge_registry | PASS |" in report
    assert "| platform-capability-registry | platform_capability_registry | PASS |" in report
    assert "| unified-abm-bridge | unified_abm_bridge_contract | PASS |" in report
    assert "| terrain-bridge | terrain_bridge_manifest | PASS |" in report
    assert "| agent-handoff-note | agent_handoff_note | PASS |" in report
    assert "## Capability Classifications" in report
    assert "| Domain | Disposition | Evidence Level | Count |" in report
    assert "| evidence | native | E0 | 12 |" in report
    assert "| transport | bridge | E1 | 1 |" in report
    assert "not a scientific truth certificate" in report


def test_batch_report_renders_failed_entries():
    batch = {
        "schema": "abm-auto/evidence-foundry-batch/v1",
        "title": "Broken Batch",
        "entries": [
            {
                "id": "missing",
                "kind": "mechanism_challenge",
                "path": "docs/reproduce/evidence-foundry/missing/challenge.json",
                "boundary_note": "missing path",
            }
        ],
        "boundary_note": "Batch gate checks artifact health only; it is not a scientific truth certificate.",
    }

    report = render_evidence_foundry_batch_report(batch, repo=REPO_ROOT)

    assert "- Overall gate: FAIL" in report
    assert "- Failed: 1" in report
    assert "entries[0].path does not exist" in report


def test_cli_report_writes_markdown_file(tmp_path):
    out = tmp_path / "report.md"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.evidence_foundry_batch",
            "report",
            "docs/reproduce/evidence-foundry/batch-registry.json",
            "--repo",
            str(REPO_ROOT),
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == str(out)
    assert "# MyMoMo Evidence Foundry Batch Report" in out.read_text(encoding="utf-8")


def test_committed_seed_report_contains_evidence_foundry_title():
    assert "# MyMoMo Evidence Foundry Batch Report" in SEED_REPORT.read_text(encoding="utf-8")
