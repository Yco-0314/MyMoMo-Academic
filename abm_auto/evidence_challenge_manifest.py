"""Evidence Foundry challenge-manifest helpers.

The manifest is a pre-run contract: it records claims, accepted evidence,
allowed data, gate commands, verdict-bundle fields, and failure-reporting
requirements. The gate checks contract completeness only. It does not run a
reproduction or certify scientific truth.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "abm-auto/evidence-challenge-manifest/v1"
FAILURE_PACK_SCHEMA = "abm-auto/failure-pack/v1"
ALLOWED_VERDICTS = frozenset({"PASS", "MISS", "PARTIAL", "INCONCLUSIVE"})
ALLOWED_EVIDENCE_LEVELS = frozenset({"E0", "E1", "E2", "E3", "E4", "E5", "E6"})
REQUIRED_VERDICT_FIELDS = frozenset({
    "challenge_id",
    "claims",
    "failure_report",
    "scope_ceilings",
    "verdict",
})
REQUIRED_FAILURE_FIELDS = frozenset({
    "boundary_note",
    "claims",
    "residuals",
    "scope_ceilings",
})


def _repo_root(repo: Path | None) -> Path:
    return Path.cwd().resolve() if repo is None else Path(repo).resolve()


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_is_nonempty_string(item) for item in value)


def _artifact_path(path_value: Any, repo: Path) -> Path:
    path = Path(str(path_value))
    return path if path.is_absolute() else repo / path


def _validate_relative_existing_path(
    *,
    value: Any,
    prefix: str,
    repo: Path,
    issues: list[str],
    required: bool = True,
) -> None:
    if not _is_nonempty_string(value):
        issues.append(f"{prefix}.path must be a repo-relative path string")
        return
    path = Path(str(value))
    if path.is_absolute():
        issues.append(f"{prefix}.path must be repo-relative")
        return
    if required and not _artifact_path(path, repo).exists():
        issues.append(f"{prefix}.path does not exist")


def load_evidence_challenge_manifest(path: Path) -> dict:
    """Load an Evidence Foundry challenge manifest JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_evidence_challenge_manifest(
    manifest: dict,
    *,
    repo: Path | None = None,
) -> dict:
    """Validate a challenge manifest contract without running declared gates."""
    repo_root = _repo_root(repo)
    if not isinstance(manifest, dict):
        return {
            "ok": False,
            "issues": ["manifest must be a JSON object"],
            "challenge_id": None,
            "claim_count": 0,
            "expected_evidence_count": 0,
            "allowed_data_count": 0,
            "gate_command_count": 0,
        }

    issues: list[str] = []
    if manifest.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA!r}")
    if not _is_nonempty_string(manifest.get("challenge_id")):
        issues.append("challenge_id must be a non-empty string")
    if not _is_nonempty_string(manifest.get("title")):
        issues.append("title must be a non-empty string")
    if not _is_nonempty_string(manifest.get("domain")):
        issues.append("domain must be a non-empty string")
    if manifest.get("evidence_level") not in ALLOWED_EVIDENCE_LEVELS:
        issues.append("evidence_level must be E0-E6")
    if not _is_nonempty_string(manifest.get("boundary_note")):
        issues.append("boundary_note must be a non-empty string")

    expected_evidence = manifest.get("expected_evidence")
    if not isinstance(expected_evidence, list) or not expected_evidence:
        issues.append("expected_evidence must be a non-empty list")
        expected_evidence = []
    evidence_ids: set[str] = set()
    for idx, evidence in enumerate(expected_evidence):
        prefix = f"expected_evidence[{idx}]"
        if not isinstance(evidence, dict):
            issues.append(f"{prefix} must be an object")
            continue
        evidence_id = evidence.get("id")
        if not _is_nonempty_string(evidence_id):
            issues.append(f"{prefix}.id must be a non-empty string")
        elif evidence_id in evidence_ids:
            issues.append(f"{prefix}.id duplicates {evidence_id!r}")
        else:
            evidence_ids.add(evidence_id)
        if not _is_nonempty_string(evidence.get("kind")):
            issues.append(f"{prefix}.kind must be a non-empty string")
        required = evidence.get("required")
        if not isinstance(required, bool):
            issues.append(f"{prefix}.required must be boolean")
            required = True
        _validate_relative_existing_path(
            value=evidence.get("path"),
            prefix=prefix,
            repo=repo_root,
            issues=issues,
            required=required,
        )

    claims = manifest.get("claims")
    if not isinstance(claims, list) or not claims:
        issues.append("claims must be a non-empty list")
        claims = []
    claim_ids: set[str] = set()
    for idx, claim in enumerate(claims):
        prefix = f"claims[{idx}]"
        if not isinstance(claim, dict):
            issues.append(f"{prefix} must be an object")
            continue
        claim_id = claim.get("id")
        if not _is_nonempty_string(claim_id):
            issues.append(f"{prefix}.id must be a non-empty string")
        elif claim_id in claim_ids:
            issues.append(f"{prefix}.id duplicates {claim_id!r}")
        else:
            claim_ids.add(claim_id)
        if not _is_nonempty_string(claim.get("statement")):
            issues.append(f"{prefix}.statement must be a non-empty string")
        if claim.get("expected_verdict") not in ALLOWED_VERDICTS:
            issues.append(f"{prefix}.expected_verdict must be one of PASS, MISS, PARTIAL, INCONCLUSIVE")
        required_evidence = claim.get("required_evidence")
        if not _is_string_list(required_evidence):
            issues.append(f"{prefix}.required_evidence must be a non-empty string list")
            required_evidence = []
        for evidence_id in required_evidence:
            if evidence_id not in evidence_ids:
                issues.append(f"{prefix}.required_evidence references unknown evidence {evidence_id!r}")

    allowed_data = manifest.get("allowed_data")
    if not isinstance(allowed_data, list) or not allowed_data:
        issues.append("allowed_data must be a non-empty list")
        allowed_data = []
    data_ids: set[str] = set()
    for idx, item in enumerate(allowed_data):
        prefix = f"allowed_data[{idx}]"
        if not isinstance(item, dict):
            issues.append(f"{prefix} must be an object")
            continue
        item_id = item.get("id")
        if not _is_nonempty_string(item_id):
            issues.append(f"{prefix}.id must be a non-empty string")
        elif item_id in data_ids:
            issues.append(f"{prefix}.id duplicates {item_id!r}")
        else:
            data_ids.add(item_id)
        if not _is_nonempty_string(item.get("source")):
            issues.append(f"{prefix}.source must be a non-empty string")
        if not _is_nonempty_string(item.get("access")):
            issues.append(f"{prefix}.access must be a non-empty string")
        if "path" in item:
            _validate_relative_existing_path(
                value=item.get("path"),
                prefix=prefix,
                repo=repo_root,
                issues=issues,
                required=True,
            )

    if not _is_string_list(manifest.get("forbidden_data")):
        issues.append("forbidden_data must be a non-empty string list")

    gate_commands = manifest.get("gate_commands")
    if not isinstance(gate_commands, list) or not gate_commands:
        issues.append("gate_commands must be a non-empty list")
        gate_commands = []
    command_ids: set[str] = set()
    for idx, command in enumerate(gate_commands):
        prefix = f"gate_commands[{idx}]"
        if not isinstance(command, dict):
            issues.append(f"{prefix} must be an object")
            continue
        command_id = command.get("id")
        if not _is_nonempty_string(command_id):
            issues.append(f"{prefix}.id must be a non-empty string")
        elif command_id in command_ids:
            issues.append(f"{prefix}.id duplicates {command_id!r}")
        else:
            command_ids.add(command_id)
        if not _is_nonempty_string(command.get("command")):
            issues.append(f"{prefix}.command must be a non-empty string")
        if not _is_nonempty_string(command.get("expected_label")):
            issues.append(f"{prefix}.expected_label must be a non-empty string")

    verdict_bundle = manifest.get("verdict_bundle")
    if not isinstance(verdict_bundle, dict):
        issues.append("verdict_bundle must be an object")
        verdict_bundle = {}
    required_fields = verdict_bundle.get("required_fields")
    if not _is_string_list(required_fields):
        issues.append("verdict_bundle.required_fields must be a non-empty string list")
        required_fields = []
    for field in sorted(REQUIRED_VERDICT_FIELDS):
        if field not in required_fields:
            issues.append(f"verdict_bundle.required_fields must include {field}")
    allowed_verdicts = verdict_bundle.get("allowed_verdicts")
    if not _is_string_list(allowed_verdicts):
        issues.append("verdict_bundle.allowed_verdicts must be a non-empty string list")
        allowed_verdicts = []
    invalid_verdicts = sorted(set(allowed_verdicts) - ALLOWED_VERDICTS)
    if invalid_verdicts:
        issues.append(f"verdict_bundle.allowed_verdicts contains invalid verdicts {invalid_verdicts}")

    failure_reporting = manifest.get("failure_reporting")
    if not isinstance(failure_reporting, dict):
        issues.append("failure_reporting must be an object")
        failure_reporting = {}
    if failure_reporting.get("required") is not True:
        issues.append("failure_reporting.required must be true")
    if failure_reporting.get("failure_pack_schema") != FAILURE_PACK_SCHEMA:
        issues.append(f"failure_reporting.failure_pack_schema must be {FAILURE_PACK_SCHEMA!r}")
    failure_fields = failure_reporting.get("required_fields")
    if not _is_string_list(failure_fields):
        issues.append("failure_reporting.required_fields must be a non-empty string list")
        failure_fields = []
    for field in sorted(REQUIRED_FAILURE_FIELDS):
        if field not in failure_fields:
            issues.append(f"failure_reporting.required_fields must include {field}")

    if not _is_string_list(manifest.get("scope_ceilings")):
        issues.append("scope_ceilings must be a non-empty string list")

    return {
        "ok": not issues,
        "issues": issues,
        "challenge_id": manifest.get("challenge_id"),
        "claim_count": len(claims),
        "expected_evidence_count": len(expected_evidence),
        "allowed_data_count": len(allowed_data),
        "gate_command_count": len(gate_commands),
    }


def evidence_challenge_manifest_gate(
    manifest: dict,
    *,
    repo: Path | None = None,
) -> tuple[bool, str]:
    """Return a compact pass/fail gate for the manifest contract."""
    validation = validate_evidence_challenge_manifest(manifest, repo=repo)
    if not validation["ok"]:
        first = "; ".join(validation["issues"][:3])
        return False, f"Evidence Foundry challenge manifest gate failed: {first}"

    return (
        True,
        "Evidence Foundry challenge manifest gate passed "
        f"(challenge_id={validation['challenge_id']}, claims={validation['claim_count']}, "
        f"evidence={validation['expected_evidence_count']}, gates={validation['gate_command_count']}); "
        "contract completeness only, not a reproduction rerun and not a scientific truth certificate",
    )


def _emit_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m abm_auto.evidence_challenge_manifest",
        description="Validate MyMoMo Evidence Foundry challenge manifests.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate a challenge manifest")
    validate.add_argument("manifest", type=Path)
    validate.add_argument("--repo", type=Path, default=None)

    gate = subparsers.add_parser("gate", help="gate a challenge manifest")
    gate.add_argument("manifest", type=Path)
    gate.add_argument("--repo", type=Path, default=None)

    args = parser.parse_args(argv)
    manifest = load_evidence_challenge_manifest(args.manifest)
    if args.command == "validate":
        result = validate_evidence_challenge_manifest(manifest, repo=args.repo)
        _emit_json(result)
        return 0 if result["ok"] else 1
    if args.command == "gate":
        ok, desc = evidence_challenge_manifest_gate(manifest, repo=args.repo)
        _emit_json({"ok": ok, "description": desc})
        return 0 if ok else 1

    parser.error(f"unsupported command {args.command}")
    return 2


__all__ = [
    "ALLOWED_EVIDENCE_LEVELS",
    "ALLOWED_VERDICTS",
    "FAILURE_PACK_SCHEMA",
    "SCHEMA",
    "evidence_challenge_manifest_gate",
    "load_evidence_challenge_manifest",
    "validate_evidence_challenge_manifest",
]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
