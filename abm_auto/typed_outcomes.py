"""Closed structural schema for versioned typed outcome records."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any
from types import MappingProxyType


SCHEMA = "abm-auto/typed-outcome-record/v1"

STATEMENT_ORDER = (
    "clarification_halt",
    "capability_gap",
    "execution",
    "behavioral_equivalence",
    "validation",
    "scientific_claim",
    "construct_validity",
)

ALLOWED_STATUSES = MappingProxyType(
    {
        "clarification_halt": frozenset({"not_required", "halted", "not_assessed"}),
        "capability_gap": frozenset({"supported", "gap", "not_assessed"}),
        "execution": frozenset({"passed", "failed", "not_attempted", "not_assessed"}),
        "behavioral_equivalence": frozenset(
            {"passed", "mismatch", "not_assessed", "not_applicable"}
        ),
        "validation": frozenset({"passed", "failed", "not_assessed", "not_applicable"}),
        "scientific_claim": frozenset(
            {"passed", "miss", "not_assessed", "not_applicable"}
        ),
        "construct_validity": frozenset(
            {
                "sound",
                "uncertain",
                "mis_specified",
                "not_reviewed",
                "not_applicable",
            }
        ),
    }
)

SOURCE_ROLES = frozenset(
    {
        "scope_note",
        "clarification_record",
        "capability_record",
        "execution_receipt",
        "execution_diagnostic",
        "behavioral_receipt",
        "behavioral_diagnostic",
        "validation_evidence",
        "prediction_lock",
        "scientific_verdict",
        "construct_validity_review",
    }
)

REQUIRED_ROLES = MappingProxyType(
    {
        ("clarification_halt", "halted"): frozenset({"clarification_record"}),
        ("clarification_halt", "not_required"): frozenset({"clarification_record"}),
        ("capability_gap", "supported"): frozenset({"capability_record"}),
        ("capability_gap", "gap"): frozenset({"capability_record"}),
        ("execution", "passed"): frozenset({"execution_receipt"}),
        ("execution", "failed"): frozenset({"execution_diagnostic"}),
        ("behavioral_equivalence", "passed"): frozenset({"behavioral_receipt"}),
        ("behavioral_equivalence", "mismatch"): frozenset(
            {"behavioral_diagnostic"}
        ),
        ("validation", "passed"): frozenset({"validation_evidence"}),
        ("validation", "failed"): frozenset({"validation_evidence"}),
        ("scientific_claim", "passed"): frozenset(
            {"prediction_lock", "scientific_verdict"}
        ),
        ("scientific_claim", "miss"): frozenset(
            {"prediction_lock", "scientific_verdict"}
        ),
        ("construct_validity", "sound"): frozenset({"construct_validity_review"}),
        ("construct_validity", "uncertain"): frozenset(
            {"construct_validity_review"}
        ),
        ("construct_validity", "mis_specified"): frozenset(
            {"construct_validity_review"}
        ),
    }
)

DOWNSTREAM_KINDS = ("behavioral_equivalence", "validation", "scientific_claim")
NOT_RESULT_STATUSES = frozenset({"not_assessed", "not_applicable"})

ROOT_FIELDS = frozenset({
    "schema",
    "record_id",
    "subject",
    "sources",
    "statements",
    "boundary_note",
})
SUBJECT_FIELDS = frozenset({"model_id", "backend_id", "attempt_id"})
SOURCE_FIELDS = frozenset({"id", "role", "path", "sha256", "commit", "schema"})
STATEMENT_FIELDS = frozenset({"kind", "status", "reason", "source_ids"})

_RECORD_ID_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
_WINDOWS_DRIVE_PREFIX_RE = re.compile(r"[A-Za-z]:")


def build_typed_outcome_record(
    *,
    record_id: str,
    subject: dict,
    sources: list,
    statements: list,
    boundary_note: str,
) -> dict:
    """Build a v1 record without deriving an overall verdict."""
    return {
        "schema": SCHEMA,
        "record_id": record_id,
        "subject": subject,
        "sources": sources,
        "statements": statements,
        "boundary_note": boundary_note,
    }


def load_typed_outcome_record(path: Path) -> dict:
    """Load a JSON object from *path*."""
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("typed outcome record must be a JSON object")
    return record


def validate_typed_outcome_record(record: Any, *, repo: Path | None = None) -> dict:
    """Validate the closed v1 schema and optional committed-source provenance."""
    issues: list[str] = []
    statement_count = len(record.get("statements", [])) if isinstance(record, dict) and isinstance(record.get("statements"), list) else 0
    source_count = len(record.get("sources", [])) if isinstance(record, dict) and isinstance(record.get("sources"), list) else 0
    validated_repo = _validate_repo(repo, issues)

    if not isinstance(record, dict):
        return {
            "ok": False,
            "issues": [*issues, "record must be an object"],
            "statement_count": statement_count,
            "source_count": source_count,
        }

    _validate_exact_fields(record, ROOT_FIELDS, "root", issues)

    if record.get("schema") != SCHEMA:
        issues.append(f"schema must equal {SCHEMA!r}")

    record_id = record.get("record_id")
    if not isinstance(record_id, str) or not _RECORD_ID_RE.fullmatch(record_id):
        issues.append("record_id must be a nonempty lowercase-hyphen identifier")
    if not isinstance(record.get("boundary_note"), str) or not record[
        "boundary_note"
    ].strip():
        issues.append("boundary_note must be a nonempty string")

    _validate_subject(record.get("subject"), issues)
    source_roles_by_id = _validate_sources(record.get("sources"), validated_repo, issues)
    _validate_statements(record.get("statements"), source_roles_by_id, issues)

    return {
        "ok": not issues,
        "issues": issues,
        "statement_count": statement_count,
        "source_count": source_count,
    }


def _validate_repo(repo: Any, issues: list[str]) -> Path | None:
    if repo is None:
        return None
    if not isinstance(repo, Path):
        issues.append("repo must be a pathlib.Path")
        return None
    try:
        resolved_repo = repo.resolve()
        if not resolved_repo.is_dir():
            raise ValueError("repo must be a directory")
    except (OSError, RuntimeError, ValueError):
        issues.append("repo must resolve to a usable directory")
        return None
    return resolved_repo


def summarize_typed_outcome_record(record: Any) -> dict:
    """Return the record identity and ordered statement statuses only."""
    record_id = record.get("record_id") if isinstance(record, dict) else None
    subject = record.get("subject") if isinstance(record, dict) else None
    statements = record.get("statements") if isinstance(record, dict) else None
    statuses: dict[str, list[str]] = {kind: [] for kind in STATEMENT_ORDER}

    if isinstance(statements, list):
        for statement in statements:
            if not isinstance(statement, dict):
                continue
            kind = statement.get("kind")
            status = statement.get("status")
            if (
                isinstance(kind, str)
                and kind in ALLOWED_STATUSES
                and isinstance(status, str)
                and status in ALLOWED_STATUSES[kind]
            ):
                statuses[kind].append(status)

    return {
        "record_id": record_id,
        "subject": subject,
        "statements": {
            kind: values[0] if len(values) == 1 else None
            for kind, values in statuses.items()
        },
    }


def _validate_exact_fields(
    value: dict, expected: frozenset[str], label: str, issues: list[str]
) -> None:
    fields = {field for field in value if isinstance(field, str)}
    if len(fields) != len(value):
        issues.append(f"{label} field names must be strings")
    for field in sorted(fields - expected):
        issues.append(f"unknown {label} field: {field}")
    for field in sorted(expected - fields):
        issues.append(f"missing {label} field: {field}")


def _validate_subject(subject: Any, issues: list[str]) -> None:
    if not isinstance(subject, dict):
        issues.append("subject must be an object")
        return

    _validate_exact_fields(subject, SUBJECT_FIELDS, "subject", issues)
    for field in sorted(SUBJECT_FIELDS):
        if not isinstance(subject.get(field), str) or not subject[field].strip():
            issues.append(f"subject.{field} must be a nonempty string")


def _validate_sources(
    sources: Any, repo: Path | None, issues: list[str]
) -> dict[str, str]:
    if not isinstance(sources, list):
        issues.append("sources must be a list")
        return {}

    source_roles_by_id: dict[str, str] = {}
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            issues.append(f"sources[{index}] must be an object")
            continue

        _validate_exact_fields(source, SOURCE_FIELDS, f"sources[{index}]", issues)
        for field in sorted(SOURCE_FIELDS):
            if not isinstance(source.get(field), str) or not source[field].strip():
                issues.append(f"sources[{index}].{field} must be a nonempty string")

        valid_path = _validate_source_path(source.get("path"), index, repo, issues)
        valid_sha256 = _validate_source_sha256(source.get("sha256"), index, issues)
        valid_commit = _validate_source_commit(source.get("commit"), index, issues)
        if repo is not None and valid_path and valid_sha256 and valid_commit:
            _validate_source_provenance(source, index, repo, issues)

        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id.strip():
            continue
        elif source_id in source_roles_by_id:
            issues.append(f"sources[{index}].id must be unique")
        else:
            role = source.get("role")
            if isinstance(role, str) and role.strip() and role not in SOURCE_ROLES:
                issues.append(f"sources[{index}].role is not a recognized source role")
            source_roles_by_id[source_id] = role if isinstance(role, str) else ""
    return source_roles_by_id


def _validate_source_path(
    value: Any, index: int, repo: Path | None, issues: list[str]
) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    if not _is_canonical_repository_relative_path(value, repo):
        issues.append(
            f"sources[{index}].path must be a canonical POSIX repository-relative path"
        )
        return False
    return True


def _is_canonical_repository_relative_path(path: str, repo: Path | None) -> bool:
    if "\\" in path:
        return False
    if _WINDOWS_DRIVE_PREFIX_RE.match(path):
        return False
    posix_path = PurePosixPath(path)
    if posix_path.is_absolute() or str(posix_path) != path:
        return False
    if any(segment in {"", ".", ".."} for segment in path.split("/")):
        return False

    try:
        root = (repo if repo is not None else Path.cwd()).resolve()
        resolved = (root / path).resolve()
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _validate_source_sha256(value: Any, index: int, issues: list[str]) -> bool:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        issues.append(
            f"sources[{index}].sha256 must be a 64-character lowercase hexadecimal digest"
        )
        return False
    return True


def _validate_source_commit(value: Any, index: int, issues: list[str]) -> bool:
    if not isinstance(value, str) or not _COMMIT_RE.fullmatch(value):
        issues.append(
            f"sources[{index}].commit must be a 40-character lowercase hexadecimal commit"
        )
        return False
    return True


def _validate_source_provenance(
    source: dict, index: int, repo: Path, issues: list[str]
) -> None:
    commit = source["commit"]
    path = source["path"]
    declared_sha256 = source["sha256"]

    verified = _run_git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}")
    expected_commit_output = f"{commit}\n".encode()
    if verified is None or verified.returncode != 0 or verified.stdout != expected_commit_output:
        issues.append(f"sources[{index}].commit must resolve to a commit in the repository")
        return

    ancestor = _run_git(repo, "merge-base", "--is-ancestor", commit, "HEAD")
    if ancestor is None or ancestor.returncode != 0:
        issues.append(f"sources[{index}].commit must be an ancestor of HEAD")
        return

    object_type = _run_git(repo, "cat-file", "-t", f"{commit}:{path}")
    if object_type is None or object_type.returncode != 0:
        issues.append(f"sources[{index}].path is absent at declared commit")
        return
    if object_type.stdout != b"blob\n":
        issues.append(f"sources[{index}].path must name a blob at declared commit")
        return

    blob = _run_git(repo, "cat-file", "blob", f"{commit}:{path}")
    if blob is None or blob.returncode != 0:
        issues.append(f"sources[{index}].path must name a blob at declared commit")
        return

    if hashlib.sha256(blob.stdout).hexdigest() != declared_sha256:
        issues.append(f"sources[{index}].sha256 does not match committed blob bytes")


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=False,
        )
    except (OSError, ValueError):
        return None


def _validate_statements(
    statements: Any, source_roles_by_id: dict[str, str], issues: list[str]
) -> None:
    if not isinstance(statements, list):
        issues.append("statements must be a list")
        return

    if len(statements) != len(STATEMENT_ORDER):
        issues.append(f"statements must contain exactly {len(STATEMENT_ORDER)} items")
    elif all(isinstance(statement, dict) for statement in statements):
        kinds = tuple(statement.get("kind") for statement in statements)
        if kinds != STATEMENT_ORDER:
            issues.append("statements must follow canonical statement order")

    statuses_by_kind: dict[str, str] = {}
    for index, statement in enumerate(statements):
        if not isinstance(statement, dict):
            issues.append(f"statements[{index}] must be an object")
            continue

        _validate_exact_fields(statement, STATEMENT_FIELDS, f"statements[{index}]", issues)
        kind = statement.get("kind")
        status = statement.get("status")
        valid_kind = isinstance(kind, str) and kind in ALLOWED_STATUSES
        valid_status = valid_kind and isinstance(status, str) and status in ALLOWED_STATUSES[kind]
        if not valid_kind:
            issues.append(f"statements[{index}].kind is invalid")
        elif not valid_status:
            issues.append(f"statements[{index}].status is invalid for kind {kind}")
        else:
            statuses_by_kind[kind] = status

        if not isinstance(statement.get("reason"), str) or not statement["reason"].strip():
            issues.append(f"statements[{index}].reason must be a nonempty string")

        source_ids = statement.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids:
            issues.append(f"statements[{index}].source_ids must be a nonempty list")
        elif any(not isinstance(source_id, str) or not source_id.strip() for source_id in source_ids):
            issues.append(
                f"statements[{index}].source_ids must contain nonempty strings"
            )
        else:
            has_undeclared_source_id = False
            for source_id in source_ids:
                if source_id not in source_roles_by_id:
                    has_undeclared_source_id = True
                    issues.append(
                        f"statements[{index}].source_ids references undeclared source id: {source_id}"
                    )
            if valid_kind and valid_status and not has_undeclared_source_id:
                _validate_required_source_roles(
                    index, kind, status, source_ids, source_roles_by_id, issues
                )

    _validate_lifecycle(statuses_by_kind, issues)


def _validate_required_source_roles(
    index: int,
    kind: str,
    status: str,
    source_ids: list[str],
    source_roles_by_id: dict[str, str],
    issues: list[str],
) -> None:
    required_roles = REQUIRED_ROLES.get((kind, status), frozenset({"scope_note"}))
    cited_roles = {
        source_roles_by_id[source_id]
        for source_id in source_ids
        if source_id in source_roles_by_id
    }
    for required_role in sorted(required_roles - cited_roles):
        issues.append(f"statements[{index}] requires source role: {required_role}")


def _validate_lifecycle(statuses_by_kind: dict[str, str], issues: list[str]) -> None:
    if set(statuses_by_kind) != set(STATEMENT_ORDER):
        return

    for kind, status in (
        ("clarification_halt", "halted"),
        ("capability_gap", "gap"),
    ):
        if statuses_by_kind[kind] != status:
            continue
        if statuses_by_kind["execution"] != "not_attempted":
            issues.append(f"{kind}={status} requires execution=not_attempted")
        _require_not_result_statuses(kind, status, DOWNSTREAM_KINDS, statuses_by_kind, issues)

    execution_status = statuses_by_kind["execution"]
    blocked_before_execution = (
        statuses_by_kind["clarification_halt"] == "halted"
        or statuses_by_kind["capability_gap"] == "gap"
    )
    if execution_status == "failed" or (
        execution_status == "not_attempted" and not blocked_before_execution
    ):
        _require_not_result_statuses(
            "execution",
            execution_status,
            DOWNSTREAM_KINDS,
            statuses_by_kind,
            issues,
        )

    if statuses_by_kind["behavioral_equivalence"] == "mismatch":
        _require_not_result_statuses(
            "behavioral_equivalence",
            "mismatch",
            ("validation", "scientific_claim"),
            statuses_by_kind,
            issues,
        )

    if (
        statuses_by_kind["construct_validity"] == "mis_specified"
        and statuses_by_kind["scientific_claim"] == "passed"
    ):
        issues.append(
            "construct_validity=mis_specified cannot coexist with scientific_claim=passed"
        )


def _require_not_result_statuses(
    cause_kind: str,
    cause_status: str,
    dependent_kinds: tuple[str, ...],
    statuses_by_kind: dict[str, str],
    issues: list[str],
) -> None:
    for dependent_kind in dependent_kinds:
        if statuses_by_kind[dependent_kind] not in NOT_RESULT_STATUSES:
            issues.append(
                f"{cause_kind}={cause_status} requires {dependent_kind} to be "
                "not_assessed or not_applicable"
            )


__all__ = [
    "ALLOWED_STATUSES",
    "DOWNSTREAM_KINDS",
    "NOT_RESULT_STATUSES",
    "REQUIRED_ROLES",
    "ROOT_FIELDS",
    "SCHEMA",
    "SOURCE_ROLES",
    "SOURCE_FIELDS",
    "STATEMENT_FIELDS",
    "STATEMENT_ORDER",
    "SUBJECT_FIELDS",
    "build_typed_outcome_record",
    "load_typed_outcome_record",
    "summarize_typed_outcome_record",
    "validate_typed_outcome_record",
]
