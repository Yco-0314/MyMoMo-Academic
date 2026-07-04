from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from abm_auto.unified_abm_bridge import (
    load_unified_abm_bridge_contract,
    unified_abm_bridge_gate,
    validate_unified_abm_bridge_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "docs/reproduce/unified-abm-bridge/example-contract.json"


def _contract() -> dict:
    return load_unified_abm_bridge_contract(CONTRACT_PATH)


def test_committed_contract_validates_and_gate_passes():
    contract = _contract()

    validation = validate_unified_abm_bridge_contract(contract, repo=REPO_ROOT)
    ok, message = unified_abm_bridge_gate(contract, repo=REPO_ROOT)

    assert validation["ok"] is True
    assert validation["participant_count"] == 6
    assert validation["artifact_count"] == 6
    assert ok is True
    assert message.startswith("Unified ABM bridge contract gate passed")
    assert "not a unified runtime" in message
    assert "not a scientific truth certificate" in message


def test_missing_required_public_surface_fails():
    contract = _contract()
    del contract["public_surface"]["mir_core"]

    validation = validate_unified_abm_bridge_contract(contract, repo=REPO_ROOT)

    assert validation["ok"] is False
    assert "public_surface.mir_core is required" in validation["issues"]


def test_unknown_participant_domain_fails():
    contract = _contract()
    contract["participants"][0]["domain"] = "biology"

    validation = validate_unified_abm_bridge_contract(contract, repo=REPO_ROOT)

    assert validation["ok"] is False
    assert "participants[0].domain must be one of" in validation["issues"][0]


def test_artifact_path_must_be_repo_relative_and_existing():
    absolute_path_contract = _contract()
    absolute_path_contract["exchange_artifacts"][0]["path"] = str(
        REPO_ROOT / "docs/reproduce/mir-v0/FINDINGS.md"
    )

    absolute_validation = validate_unified_abm_bridge_contract(
        absolute_path_contract,
        repo=REPO_ROOT,
    )

    assert absolute_validation["ok"] is False
    assert "exchange_artifacts[0].path must be repo-relative" in absolute_validation["issues"]

    missing_path_contract = _contract()
    missing_path_contract["exchange_artifacts"][0]["path"] = "docs/reproduce/missing.json"

    missing_validation = validate_unified_abm_bridge_contract(
        missing_path_contract,
        repo=REPO_ROOT,
    )

    assert missing_validation["ok"] is False
    assert "exchange_artifacts[0].path does not exist" in missing_validation["issues"]


def test_unknown_artifact_producer_or_consumer_fails():
    producer_contract = _contract()
    producer_contract["exchange_artifacts"][0]["producer"] = "unknown-producer"

    producer_validation = validate_unified_abm_bridge_contract(
        producer_contract,
        repo=REPO_ROOT,
    )

    assert producer_validation["ok"] is False
    assert (
        "exchange_artifacts[0].producer references unknown participant 'unknown-producer'"
        in producer_validation["issues"]
    )

    consumer_contract = _contract()
    consumer_contract["exchange_artifacts"][0]["consumer"] = "unknown-consumer"

    consumer_validation = validate_unified_abm_bridge_contract(
        consumer_contract,
        repo=REPO_ROOT,
    )

    assert consumer_validation["ok"] is False
    assert (
        "exchange_artifacts[0].consumer references unknown participant 'unknown-consumer'"
        in consumer_validation["issues"]
    )


def test_missing_required_boundary_rule_fails():
    contract = _contract()
    del contract["boundary_rules"]["extensions_are_opaque"]

    validation = validate_unified_abm_bridge_contract(contract, repo=REPO_ROOT)

    assert validation["ok"] is False
    assert "boundary_rules.extensions_are_opaque is required" in validation["issues"]


def test_weak_boundary_note_fails():
    contract = _contract()
    contract["boundary_note"] = "This contract is useful."

    validation = validate_unified_abm_bridge_contract(contract, repo=REPO_ROOT)
    ok, message = unified_abm_bridge_gate(contract, repo=REPO_ROOT)

    assert validation["ok"] is False
    assert "boundary_note must say this is not a unified runtime" in validation["issues"]
    assert "boundary_note must say this is not a scientific truth certificate" in validation["issues"]
    assert ok is False
    assert message.startswith("Unified ABM bridge contract gate failed")


def test_duplicate_ids_fail():
    contract = _contract()
    duplicate_participant = deepcopy(contract["participants"][0])
    contract["participants"].append(duplicate_participant)
    duplicate_artifact = deepcopy(contract["exchange_artifacts"][0])
    contract["exchange_artifacts"].append(duplicate_artifact)

    validation = validate_unified_abm_bridge_contract(contract, repo=REPO_ROOT)

    assert validation["ok"] is False
    assert "duplicate participant id mir-core" in validation["issues"]
    assert "duplicate exchange artifact id mir-v0-findings" in validation["issues"]
