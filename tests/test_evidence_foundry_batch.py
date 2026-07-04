from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from abm_auto.evidence_foundry_batch import (
    evidence_foundry_batch_gate,
    load_evidence_foundry_batch,
    run_evidence_foundry_batch,
    validate_evidence_foundry_batch,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_BATCH = REPO_ROOT / "docs/reproduce/evidence-foundry/batch-registry.json"


def _batch(entries):
    return {
        "schema": "abm-auto/evidence-foundry-batch/v1",
        "title": "MyMoMo Evidence Foundry Seed Batch",
        "entries": entries,
        "boundary_note": "Batch gate checks artifact health only; it is not a scientific truth certificate.",
    }


def _seed_entries():
    return [
        {
            "id": "challenge-registry",
            "kind": "repro_challenge_registry",
            "path": "docs/reproduce/autodata-challenges/registry.json",
            "boundary_note": "Checks answer/evidence alignment only.",
        },
        {
            "id": "failure-pack",
            "kind": "failure_pack",
            "path": "docs/reproduce/evidence-foundry/failure-pack-example/failure-pack.json",
            "boundary_note": "Validates failure artifact structure, not scientific success.",
        },
        {
            "id": "counterfactual",
            "kind": "counterfactual_challenge",
            "path": "docs/reproduce/evidence-foundry/counterfactual-example/challenge.json",
            "boundary_note": "Compares recorded metrics, not causal proof.",
        },
        {
            "id": "mechanism",
            "kind": "mechanism_challenge",
            "path": "docs/reproduce/evidence-foundry/mechanism-example/challenge.json",
            "boundary_note": "Checks declared signatures, not mechanism truth.",
        },
        {
            "id": "challenge-manifest",
            "kind": "evidence_challenge_manifest",
            "path": "docs/reproduce/evidence-foundry/challenge-manifest-example/challenge-manifest.json",
            "boundary_note": "Validates challenge contract completeness, not scientific truth.",
        },
        {
            "id": "synthetic-population",
            "kind": "synthetic_population_manifest",
            "path": "docs/reproduce/synthetic-population/example-panel/manifest.json",
            "boundary_note": "Validates provenance manifest only.",
        },
        {
            "id": "llm-replay",
            "kind": "llm_agent_replay",
            "path": "docs/reproduce/llm-agent-replay/fake-agent/events.jsonl",
            "boundary_note": "Validates replay trace shape only.",
        },
        {
            "id": "synthetic-survey",
            "kind": "synthetic_survey_gate",
            "observed": "docs/reproduce/synthetic-survey-gate/example-panel/observed.json",
            "answer": "docs/reproduce/synthetic-survey-gate/example-panel/synthetic-answer.json",
            "boundary_note": "Compares distributions, not human validity.",
        },
        {
            "id": "social-platform",
            "kind": "social_platform_environment",
            "path": "docs/reproduce/social-platform-environment/example-feed/scenario.json",
            "boundary_note": "Checks deterministic exposure fixture only.",
        },
        {
            "id": "transport-bridge",
            "kind": "transport_bridge_manifest",
            "path": "docs/reproduce/transport-bridge/synthetic-evacuation/bridge-manifest.json",
            "boundary_note": "Validates bridge manifest only.",
        },
        {
            "id": "platform-capability-registry",
            "kind": "platform_capability_registry",
            "path": "docs/reproduce/platform-capabilities/registry.json",
            "boundary_note": "Validates native/bridge/audit classification only.",
        },
        {
            "id": "unified-abm-bridge",
            "kind": "unified_abm_bridge_contract",
            "path": "docs/reproduce/unified-abm-bridge/example-contract.json",
            "boundary_note": "Validates public bridge contract shape only.",
        },
        {
            "id": "terrain-bridge",
            "kind": "terrain_bridge_manifest",
            "path": "docs/reproduce/terrain-bridge/example-manifest.json",
            "boundary_note": "Validates terrain exchange contract shape only.",
        },
        {
            "id": "agent-handoff-note",
            "kind": "agent_handoff_note",
            "path": "docs/reproduce/evidence-foundry/agent-handoff-example/handoff-note.md",
            "boundary_note": "Checks handoff note completeness, not factual truth.",
        },
    ]


def test_valid_batch_runs_all_seed_artifact_kinds():
    result = run_evidence_foundry_batch(_batch(_seed_entries()), repo=REPO_ROOT)

    assert result["ok"] is True
    assert result["entry_count"] == 14
    assert result["passed_count"] == 14
    assert result["failed_count"] == 0
    assert [entry["kind"] for entry in result["results"]] == [
        "repro_challenge_registry",
        "failure_pack",
        "counterfactual_challenge",
        "mechanism_challenge",
        "evidence_challenge_manifest",
        "synthetic_population_manifest",
        "llm_agent_replay",
        "synthetic_survey_gate",
        "social_platform_environment",
        "transport_bridge_manifest",
        "platform_capability_registry",
        "unified_abm_bridge_contract",
        "terrain_bridge_manifest",
        "agent_handoff_note",
    ]
    platform_result = next(result for result in result["results"] if result["kind"] == "platform_capability_registry")
    assert platform_result["classification_summary"]["groups"] == [
        {"domain": "closed_extension", "disposition": "bridge", "evidence_level": "E0", "count": 1},
        {"domain": "evidence", "disposition": "native", "evidence_level": "E0", "count": 12},
        {"domain": "gama", "disposition": "native", "evidence_level": "E0", "count": 1},
        {"domain": "gama", "disposition": "native", "evidence_level": "E2", "count": 1},
        {"domain": "gama", "disposition": "out_of_scope", "evidence_level": "E0", "count": 1},
        {"domain": "llm_society", "disposition": "native", "evidence_level": "E0", "count": 4},
        {"domain": "platform", "disposition": "audit_baseline", "evidence_level": "E0", "count": 1},
        {"domain": "platform", "disposition": "bridge", "evidence_level": "E0", "count": 2},
        {"domain": "transport", "disposition": "bridge", "evidence_level": "E1", "count": 1},
    ]


def test_unknown_kind_fails_validation():
    batch = _batch([
        {
            "id": "unknown",
            "kind": "not-a-kind",
            "path": "docs/reproduce/evidence-foundry/mechanism-example/challenge.json",
            "boundary_note": "bad kind",
        }
    ])

    result = validate_evidence_foundry_batch(batch, repo=REPO_ROOT)

    assert result["ok"] is False
    assert "entries[0].kind must be one of" in result["issues"][0]


def test_missing_path_fails_validation():
    batch = _batch([
        {
            "id": "missing",
            "kind": "mechanism_challenge",
            "path": "docs/reproduce/evidence-foundry/missing/challenge.json",
            "boundary_note": "missing path",
        }
    ])

    result = validate_evidence_foundry_batch(batch, repo=REPO_ROOT)

    assert result["ok"] is False
    assert "entries[0].path does not exist" in result["issues"]


def test_synthetic_survey_requires_observed_and_answer_paths():
    batch = _batch([
        {
            "id": "survey",
            "kind": "synthetic_survey_gate",
            "observed": "docs/reproduce/synthetic-survey-gate/example-panel/observed.json",
            "boundary_note": "missing answer",
        }
    ])

    result = validate_evidence_foundry_batch(batch, repo=REPO_ROOT)

    assert result["ok"] is False
    assert "entries[0].answer must be a repo-relative path string" in result["issues"]


def test_committed_seed_batch_loads_and_passes():
    batch = load_evidence_foundry_batch(SEED_BATCH)

    ok, desc = evidence_foundry_batch_gate(batch, repo=REPO_ROOT)

    assert ok is True
    assert desc.startswith("Evidence Foundry batch gate passed")
    assert "not a scientific truth certificate" in desc


def test_cli_gate_prints_json_result():
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.evidence_foundry_batch",
            "gate",
            "docs/reproduce/evidence-foundry/batch-registry.json",
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
    assert result["entry_count"] == 14
