"""Unified ABM public bridge-contract helpers.

The contract records how public MyMoMo artifacts exchange model semantics and
evidence across MIR, GISABM, NetLogo semantic migration, Evidence Foundry,
transport, and closed extension bridge lines. The gate validates contract shape and
artifact paths only. It does not execute private backends, run reproductions, or
claim a unified runtime.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "abm-auto/unified-abm-bridge-contract/v1"
ALLOWED_DOMAINS = frozenset({
    "closed_extension",
    "evidence",
    "gis",
    "llm_society",
    "mir",
    "netlogo",
    "platform",
    "transport",
})
REQUIRED_PUBLIC_SURFACES = frozenset({
    "evidence_foundry",
    "gisabm",
    "mir_core",
    "netlogo_semantics",
})
REQUIRED_BOUNDARY_RULES = frozenset({
    "extensions_are_opaque",
    "gates_are_artifact_health_not_truth",
    "no_cross_runtime_equivalence_claim",
    "no_private_runtime_claim",
})


def _repo_root(repo: Path | None) -> Path:
    return Path.cwd().resolve() if repo is None else Path(repo).resolve()


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sorted_values(values: frozenset[str]) -> str:
    return ", ".join(sorted(values))


def _artifact_path(path_value: Any, repo: Path) -> Path:
    path = Path(str(path_value))
    return path if path.is_absolute() else repo / path


def _validate_repo_relative_existing_path(
    *,
    value: Any,
    prefix: str,
    repo: Path,
    issues: list[str],
) -> None:
    if not _is_nonempty_string(value):
        issues.append(f"{prefix}.path must be a repo-relative path string")
        return
    path = Path(str(value))
    if path.is_absolute():
        issues.append(f"{prefix}.path must be repo-relative")
        return
    if not _artifact_path(path, repo).exists():
        issues.append(f"{prefix}.path does not exist")


def _validate_string_list(value: Any, *, prefix: str, issues: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        issues.append(f"{prefix} must be a non-empty string list")
        return []
    items: list[str] = []
    for idx, item in enumerate(value):
        if not _is_nonempty_string(item):
            issues.append(f"{prefix}[{idx}] must be a non-empty string")
            continue
        items.append(str(item))
    return items


def _validate_boundary_note(note: Any, issues: list[str]) -> None:
    if not _is_nonempty_string(note):
        issues.append("boundary_note must be a non-empty string")
        return
    lower_note = str(note).lower()
    if "not a unified runtime" not in lower_note:
        issues.append("boundary_note must say this is not a unified runtime")
    if "not a scientific truth certificate" not in lower_note:
        issues.append("boundary_note must say this is not a scientific truth certificate")


def load_unified_abm_bridge_contract(path: Path) -> dict:
    """Load a unified ABM bridge contract JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_unified_abm_bridge_contract(
    contract: dict,
    *,
    repo: Path | None = None,
) -> dict:
    """Validate a unified ABM bridge contract without executing declared gates."""
    repo_root = _repo_root(repo)
    if not isinstance(contract, dict):
        return {
            "ok": False,
            "issues": ["contract must be a JSON object"],
            "contract_id": None,
            "participant_count": 0,
            "artifact_count": 0,
        }

    issues: list[str] = []
    if contract.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA!r}")
    if not _is_nonempty_string(contract.get("contract_id")):
        issues.append("contract_id must be a non-empty string")
    if not _is_nonempty_string(contract.get("title")):
        issues.append("title must be a non-empty string")
    _validate_boundary_note(contract.get("boundary_note"), issues)

    public_surface = contract.get("public_surface")
    if not isinstance(public_surface, dict):
        issues.append("public_surface must be an object")
        public_surface = {}
    for surface in sorted(REQUIRED_PUBLIC_SURFACES):
        if surface not in public_surface:
            issues.append(f"public_surface.{surface} is required")
            continue
        _validate_repo_relative_existing_path(
            value=public_surface.get(surface),
            prefix=f"public_surface.{surface}",
            repo=repo_root,
            issues=issues,
        )

    participant_ids = _validate_participants(contract.get("participants"), issues)
    artifact_ids = _validate_exchange_artifacts(
        contract.get("exchange_artifacts"),
        participant_ids=participant_ids,
        repo=repo_root,
        issues=issues,
    )
    _validate_participant_artifact_refs(
        contract.get("participants"),
        artifact_ids=artifact_ids,
        issues=issues,
    )
    _validate_boundary_rules(contract.get("boundary_rules"), issues)
    _validate_verification(contract.get("verification"), issues)

    participants = contract.get("participants") if isinstance(contract.get("participants"), list) else []
    artifacts = (
        contract.get("exchange_artifacts")
        if isinstance(contract.get("exchange_artifacts"), list)
        else []
    )
    return {
        "ok": not issues,
        "issues": issues,
        "contract_id": contract.get("contract_id"),
        "participant_count": len(participants),
        "artifact_count": len(artifacts),
    }


def _validate_participants(value: Any, issues: list[str]) -> set[str]:
    if not isinstance(value, list) or not value:
        issues.append("participants must be a non-empty list")
        return set()

    participant_ids: set[str] = set()
    for idx, participant in enumerate(value):
        prefix = f"participants[{idx}]"
        if not isinstance(participant, dict):
            issues.append(f"{prefix} must be an object")
            continue

        participant_id = participant.get("id")
        if not _is_nonempty_string(participant_id):
            issues.append(f"{prefix}.id must be a non-empty string")
        elif participant_id in participant_ids:
            issues.append(f"duplicate participant id {participant_id}")
        else:
            participant_ids.add(str(participant_id))

        domain = participant.get("domain")
        if domain not in ALLOWED_DOMAINS:
            issues.append(
                f"{prefix}.domain must be one of {_sorted_values(ALLOWED_DOMAINS)}"
            )
        if not _is_nonempty_string(participant.get("role")):
            issues.append(f"{prefix}.role must be a non-empty string")
        if not isinstance(participant.get("public"), bool):
            issues.append(f"{prefix}.public must be boolean")
        _validate_string_list(
            participant.get("artifact_refs"),
            prefix=f"{prefix}.artifact_refs",
            issues=issues,
        )
        if not _is_nonempty_string(participant.get("boundary_note")):
            issues.append(f"{prefix}.boundary_note must be a non-empty string")

    return participant_ids


def _validate_exchange_artifacts(
    value: Any,
    *,
    participant_ids: set[str],
    repo: Path,
    issues: list[str],
) -> set[str]:
    if not isinstance(value, list) or not value:
        issues.append("exchange_artifacts must be a non-empty list")
        return set()

    artifact_ids: set[str] = set()
    for idx, artifact in enumerate(value):
        prefix = f"exchange_artifacts[{idx}]"
        if not isinstance(artifact, dict):
            issues.append(f"{prefix} must be an object")
            continue

        artifact_id = artifact.get("id")
        if not _is_nonempty_string(artifact_id):
            issues.append(f"{prefix}.id must be a non-empty string")
        elif artifact_id in artifact_ids:
            issues.append(f"duplicate exchange artifact id {artifact_id}")
        else:
            artifact_ids.add(str(artifact_id))

        if not _is_nonempty_string(artifact.get("kind")):
            issues.append(f"{prefix}.kind must be a non-empty string")
        _validate_repo_relative_existing_path(
            value=artifact.get("path"),
            prefix=prefix,
            repo=repo,
            issues=issues,
        )
        for field in ("producer", "consumer"):
            ref = artifact.get(field)
            if not _is_nonempty_string(ref):
                issues.append(f"{prefix}.{field} must be a non-empty string")
            elif ref not in participant_ids:
                issues.append(f"{prefix}.{field} references unknown participant {ref!r}")
        if not _is_nonempty_string(artifact.get("boundary_note")):
            issues.append(f"{prefix}.boundary_note must be a non-empty string")

    return artifact_ids


def _validate_participant_artifact_refs(
    participants: Any,
    *,
    artifact_ids: set[str],
    issues: list[str],
) -> None:
    if not isinstance(participants, list):
        return
    for idx, participant in enumerate(participants):
        if not isinstance(participant, dict):
            continue
        refs = participant.get("artifact_refs")
        if not isinstance(refs, list):
            continue
        for ref in refs:
            if _is_nonempty_string(ref) and ref not in artifact_ids:
                issues.append(
                    f"participants[{idx}].artifact_refs references unknown exchange artifact {ref!r}"
                )


def _validate_boundary_rules(value: Any, issues: list[str]) -> None:
    if not isinstance(value, dict):
        issues.append("boundary_rules must be an object")
        value = {}
    for rule in sorted(REQUIRED_BOUNDARY_RULES):
        if rule not in value:
            issues.append(f"boundary_rules.{rule} is required")
            continue
        if not _is_nonempty_string(value.get(rule)):
            issues.append(f"boundary_rules.{rule} must be a non-empty string")


def _validate_verification(value: Any, issues: list[str]) -> None:
    if not isinstance(value, dict):
        issues.append("verification must be an object")
        return
    if not _is_nonempty_string(value.get("gate_command")):
        issues.append("verification.gate_command must be a non-empty string")
    if not _is_nonempty_string(value.get("expected_result")):
        issues.append("verification.expected_result must be a non-empty string")
    _validate_string_list(
        value.get("non_claims"),
        prefix="verification.non_claims",
        issues=issues,
    )


def unified_abm_bridge_gate(
    contract: dict,
    *,
    repo: Path | None = None,
) -> tuple[bool, str]:
    """Return a compact gate tuple for a unified ABM bridge contract."""
    validation = validate_unified_abm_bridge_contract(contract, repo=repo)
    status = "passed" if validation["ok"] else "failed"
    detail = (
        f"participants={validation['participant_count']}, "
        f"artifacts={validation['artifact_count']}"
    )
    if not validation["ok"]:
        detail = f"{detail}, issues={validation['issues'][:3]}"
    return (
        validation["ok"],
        f"Unified ABM bridge contract gate {status} ({detail}); "
        "not a unified runtime; not a scientific truth certificate",
    )


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    gate_parser = subparsers.add_parser("gate", help="validate a bridge contract")
    gate_parser.add_argument("path")
    gate_parser.add_argument("--repo", default=None)
    args = parser.parse_args(argv)

    if args.command == "gate":
        contract = load_unified_abm_bridge_contract(Path(args.path))
        repo = Path(args.repo) if args.repo is not None else None
        validation = validate_unified_abm_bridge_contract(contract, repo=repo)
        ok, message = unified_abm_bridge_gate(contract, repo=repo)
        payload = dict(validation)
        payload["message"] = message
        print(json.dumps(payload, sort_keys=True))
        return 0 if ok else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))


__all__ = [
    "ALLOWED_DOMAINS",
    "REQUIRED_BOUNDARY_RULES",
    "REQUIRED_PUBLIC_SURFACES",
    "SCHEMA",
    "load_unified_abm_bridge_contract",
    "unified_abm_bridge_gate",
    "validate_unified_abm_bridge_contract",
]
