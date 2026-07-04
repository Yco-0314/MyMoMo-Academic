from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from abm_auto.evidence_challenge_manifest import (
    SCHEMA,
    evidence_challenge_manifest_gate,
    load_evidence_challenge_manifest,
    validate_evidence_challenge_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_MANIFEST = (
    REPO_ROOT
    / "docs/reproduce/evidence-foundry/challenge-manifest-example/challenge-manifest.json"
)


def _valid_manifest(tmp_path: Path) -> dict:
    repo = tmp_path
    source_manifest = repo / "evidence/source-manifest.json"
    raw_sample = repo / "data/raw.json"
    source_manifest.parent.mkdir(parents=True, exist_ok=True)
    raw_sample.parent.mkdir(parents=True, exist_ok=True)
    source_manifest.write_text('{"source": "fixture"}\n', encoding="utf-8")
    raw_sample.write_text('{"features": []}\n', encoding="utf-8")
    return {
        "schema": SCHEMA,
        "challenge_id": "synthetic-contract-v1",
        "title": "Synthetic Evidence Contract",
        "domain": "gis",
        "evidence_level": "E2",
        "claims": [
            {
                "id": "C1",
                "statement": "The sample is manifest-backed.",
                "expected_verdict": "PASS",
                "required_evidence": ["source_manifest"],
            },
            {
                "id": "C2",
                "statement": "Failures must be recorded as failure packs.",
                "expected_verdict": "INCONCLUSIVE",
                "required_evidence": ["source_manifest"],
            },
        ],
        "expected_evidence": [
            {
                "id": "source_manifest",
                "path": "evidence/source-manifest.json",
                "kind": "manifest",
                "required": True,
            }
        ],
        "allowed_data": [
            {
                "id": "official_sample",
                "source": "Synthetic local fixture",
                "access": "committed_sample",
                "path": "data/raw.json",
            }
        ],
        "forbidden_data": [
            "private paper reproduction payloads",
            "uncommitted chat transcript claims",
        ],
        "gate_commands": [
            {
                "id": "manifest_gate",
                "command": ".venv/bin/python -m abm_auto.evidence_challenge_manifest gate evidence/challenge-manifest.json --repo .",
                "expected_label": "Evidence Foundry challenge manifest gate passed",
            }
        ],
        "verdict_bundle": {
            "required_fields": [
                "challenge_id",
                "claims",
                "verdict",
                "scope_ceilings",
                "failure_report",
            ],
            "allowed_verdicts": ["PASS", "MISS", "PARTIAL", "INCONCLUSIVE"],
        },
        "failure_reporting": {
            "required": True,
            "failure_pack_schema": "abm-auto/failure-pack/v1",
            "required_fields": ["claims", "residuals", "scope_ceilings", "boundary_note"],
        },
        "scope_ceilings": [
            "This manifest validates a public evidence contract only.",
            "It does not rerun a paper reproduction or certify scientific truth.",
        ],
        "boundary_note": "Challenge manifest gates contract completeness only.",
    }


def test_valid_manifest_validates_and_gates(tmp_path):
    manifest = _valid_manifest(tmp_path)

    validation = validate_evidence_challenge_manifest(manifest, repo=tmp_path)
    ok, desc = evidence_challenge_manifest_gate(manifest, repo=tmp_path)

    assert validation == {
        "ok": True,
        "issues": [],
        "challenge_id": "synthetic-contract-v1",
        "claim_count": 2,
        "expected_evidence_count": 1,
        "allowed_data_count": 1,
        "gate_command_count": 1,
    }
    assert ok, desc
    assert desc.startswith("Evidence Foundry challenge manifest gate passed")
    assert "contract completeness only" in desc
    assert "not a reproduction rerun" in desc
    assert "not a scientific truth certificate" in desc


def test_manifest_rejects_schema_evidence_level_and_duplicate_claim(tmp_path):
    manifest = _valid_manifest(tmp_path)
    manifest["schema"] = "wrong"
    manifest["evidence_level"] = "E9"
    manifest["claims"].append(dict(manifest["claims"][0]))

    result = validate_evidence_challenge_manifest(manifest, repo=tmp_path)

    assert not result["ok"]
    assert "schema must be 'abm-auto/evidence-challenge-manifest/v1'" in result["issues"]
    assert "evidence_level must be E0-E6" in result["issues"]
    assert "claims[2].id duplicates 'C1'" in result["issues"]


def test_manifest_rejects_unknown_evidence_and_absolute_paths(tmp_path):
    manifest = _valid_manifest(tmp_path)
    manifest["claims"][0]["required_evidence"] = ["missing_evidence"]
    manifest["expected_evidence"][0]["path"] = str(tmp_path / "evidence/source-manifest.json")

    result = validate_evidence_challenge_manifest(manifest, repo=tmp_path)

    assert not result["ok"]
    assert "claims[0].required_evidence references unknown evidence 'missing_evidence'" in result["issues"]
    assert "expected_evidence[0].path must be repo-relative" in result["issues"]


def test_manifest_rejects_missing_required_evidence_and_allowed_data(tmp_path):
    manifest = _valid_manifest(tmp_path)
    (tmp_path / "evidence/source-manifest.json").unlink()
    (tmp_path / "data/raw.json").unlink()

    result = validate_evidence_challenge_manifest(manifest, repo=tmp_path)

    assert not result["ok"]
    assert "expected_evidence[0].path does not exist" in result["issues"]
    assert "allowed_data[0].path does not exist" in result["issues"]


def test_manifest_rejects_missing_verdict_bundle_and_failure_reporting(tmp_path):
    manifest = _valid_manifest(tmp_path)
    manifest["verdict_bundle"]["required_fields"].remove("failure_report")
    manifest["failure_reporting"]["required"] = False

    result = validate_evidence_challenge_manifest(manifest, repo=tmp_path)

    assert not result["ok"]
    assert "verdict_bundle.required_fields must include failure_report" in result["issues"]
    assert "failure_reporting.required must be true" in result["issues"]


def test_committed_seed_manifest_validates_and_gates():
    manifest = load_evidence_challenge_manifest(SEED_MANIFEST)

    validation = validate_evidence_challenge_manifest(manifest, repo=REPO_ROOT)
    ok, desc = evidence_challenge_manifest_gate(manifest, repo=REPO_ROOT)

    assert validation["ok"], validation["issues"]
    assert validation["challenge_id"] == "official-incident-real-sample-evidence-contract-v1"
    assert validation["claim_count"] == 3
    assert ok, desc


def test_cli_validate_and_gate_seed_manifest():
    validate = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.evidence_challenge_manifest",
            "validate",
            str(SEED_MANIFEST),
            "--repo",
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert validate.returncode == 0, validate.stderr
    assert json.loads(validate.stdout)["ok"] is True

    gate = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.evidence_challenge_manifest",
            "gate",
            str(SEED_MANIFEST),
            "--repo",
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert gate.returncode == 0, gate.stderr
    payload = json.loads(gate.stdout)
    assert payload["ok"] is True
    assert "contract completeness only" in payload["description"]
