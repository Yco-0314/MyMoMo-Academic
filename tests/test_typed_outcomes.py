from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import subprocess

import pytest
import abm_auto.typed_outcomes as typed_outcomes

from abm_auto.typed_outcomes import (
    ALLOWED_STATUSES,
    ROOT_FIELDS,
    SCHEMA,
    SOURCE_FIELDS,
    STATEMENT_FIELDS,
    STATEMENT_ORDER,
    SUBJECT_FIELDS,
    build_typed_outcome_record,
    load_typed_outcome_record,
    summarize_typed_outcome_record,
    validate_typed_outcome_record,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_RECORD = (
    REPO_ROOT
    / "docs/reproduce/typed-outcomes/synthetic-worked-example/typed-outcomes.json"
)
_VALID_SHA256 = "a" * 64
_VALID_COMMIT = "b" * 40


_EXPECTED_SOURCE_ROLES = frozenset(
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
_EXPECTED_REQUIRED_ROLES = {
    ("clarification_halt", "halted"): frozenset({"clarification_record"}),
    ("clarification_halt", "not_required"): frozenset({"clarification_record"}),
    ("capability_gap", "supported"): frozenset({"capability_record"}),
    ("capability_gap", "gap"): frozenset({"capability_record"}),
    ("execution", "passed"): frozenset({"execution_receipt"}),
    ("execution", "failed"): frozenset({"execution_diagnostic"}),
    ("behavioral_equivalence", "passed"): frozenset({"behavioral_receipt"}),
    ("behavioral_equivalence", "mismatch"): frozenset({"behavioral_diagnostic"}),
    ("validation", "passed"): frozenset({"validation_evidence"}),
    ("validation", "failed"): frozenset({"validation_evidence"}),
    ("scientific_claim", "passed"): frozenset(
        {"prediction_lock", "scientific_verdict"}
    ),
    ("scientific_claim", "miss"): frozenset(
        {"prediction_lock", "scientific_verdict"}
    ),
    ("construct_validity", "sound"): frozenset({"construct_validity_review"}),
    ("construct_validity", "uncertain"): frozenset({"construct_validity_review"}),
    ("construct_validity", "mis_specified"): frozenset(
        {"construct_validity_review"}
    ),
}


def _record() -> dict:
    sources = [
        {
            "id": source_id,
            "role": role,
            "path": f"evidence/{source_id}.json",
            "sha256": _VALID_SHA256,
            "commit": _VALID_COMMIT,
            "schema": "abm-auto/evidence/v1",
        }
        for source_id, role in (
            ("clarification-record", "clarification_record"),
            ("capability-record", "capability_record"),
            ("execution-receipt", "execution_receipt"),
            ("behavioral-receipt", "behavioral_receipt"),
            ("validation-evidence", "validation_evidence"),
            ("prediction-lock", "prediction_lock"),
            ("scientific-verdict", "scientific_verdict"),
            ("construct-review", "construct_validity_review"),
        )
    ]
    statements = [
        {
            "kind": "clarification_halt",
            "status": "not_required",
            "reason": "The request is sufficiently specified.",
            "source_ids": ["clarification-record"],
        },
        {
            "kind": "capability_gap",
            "status": "supported",
            "reason": "The required capability is available.",
            "source_ids": ["capability-record"],
        },
        {
            "kind": "execution",
            "status": "passed",
            "reason": "The requested run completed successfully.",
            "source_ids": ["execution-receipt"],
        },
        {
            "kind": "behavioral_equivalence",
            "status": "passed",
            "reason": "The behavioral signature matched the reference.",
            "source_ids": ["behavioral-receipt"],
        },
        {
            "kind": "validation",
            "status": "passed",
            "reason": "The validation gate accepted the evidence.",
            "source_ids": ["validation-evidence"],
        },
        {
            "kind": "scientific_claim",
            "status": "miss",
            "reason": "The expected scientific effect was not observed.",
            "source_ids": ["prediction-lock", "scientific-verdict"],
        },
        {
            "kind": "construct_validity",
            "status": "sound",
            "reason": "The measure is a sound construct proxy.",
            "source_ids": ["construct-review"],
        },
    ]
    return build_typed_outcome_record(
        record_id="canonical-outcome-record",
        subject={
            "model_id": "canonical-model",
            "backend_id": "python",
            "attempt_id": "attempt-001",
        },
        sources=sources,
        statements=statements,
        boundary_note="Closed structural v1 schema only.",
    )


def _empty_statement_summary() -> dict[str, None]:
    return {kind: None for kind in STATEMENT_ORDER}


def _source_ids_for_roles(record: dict, roles: frozenset[str]) -> list[str]:
    return [source["id"] for source in record["sources"] if source["role"] in roles]


def _assign_required_sources(record: dict) -> None:
    for statement in record["statements"]:
        roles = _EXPECTED_REQUIRED_ROLES.get(
            (statement["kind"], statement["status"]), frozenset({"scope_note"})
        )
        statement["source_ids"] = _source_ids_for_roles(record, roles)


def _record_for_status(kind: str, status: str) -> dict:
    record = _record()
    record["sources"].extend(
        [
            {
                "id": "scope-note",
                "role": "scope_note",
                "path": "evidence/scope-note.json",
                "sha256": _VALID_SHA256,
                "commit": _VALID_COMMIT,
                "schema": "abm-auto/evidence/v1",
            },
            {
                "id": "execution-diagnostic",
                "role": "execution_diagnostic",
                "path": "evidence/execution-diagnostic.json",
                "sha256": _VALID_SHA256,
                "commit": _VALID_COMMIT,
                "schema": "abm-auto/evidence/v1",
            },
            {
                "id": "behavioral-diagnostic",
                "role": "behavioral_diagnostic",
                "path": "evidence/behavioral-diagnostic.json",
                "sha256": _VALID_SHA256,
                "commit": _VALID_COMMIT,
                "schema": "abm-auto/evidence/v1",
            },
        ]
    )
    statements = {statement["kind"]: statement for statement in record["statements"]}
    statements[kind]["status"] = status

    if kind in {"clarification_halt", "capability_gap"} and status in {"halted", "gap"}:
        statements["execution"]["status"] = "not_attempted"
        for downstream_kind in ("behavioral_equivalence", "validation", "scientific_claim"):
            statements[downstream_kind]["status"] = "not_assessed"
    elif kind == "execution" and status in {"failed", "not_attempted"}:
        for downstream_kind in ("behavioral_equivalence", "validation", "scientific_claim"):
            statements[downstream_kind]["status"] = "not_assessed"
    elif kind == "behavioral_equivalence" and status == "mismatch":
        for downstream_kind in ("validation", "scientific_claim"):
            statements[downstream_kind]["status"] = "not_assessed"
    elif kind == "construct_validity" and status == "mis_specified":
        statements["scientific_claim"]["status"] = "miss"

    _assign_required_sources(record)
    return record


def _git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
    ).stdout


def _committed_source_reference(
    repo: Path = REPO_ROOT, path: str = "README.md"
) -> dict[str, str]:
    """Return a source reference from exact bytes committed in *repo*."""
    commit = _git_bytes(repo, "rev-parse", "HEAD").decode().strip()
    blob_bytes = _git_bytes(repo, "show", f"{commit}:{path}")
    return {
        "path": path,
        "sha256": hashlib.sha256(blob_bytes).hexdigest(),
        "commit": commit,
    }


def _record_with_committed_source(repo: Path = REPO_ROOT, path: str = "README.md") -> dict:
    record = _record()
    reference = _committed_source_reference(repo, path)
    for source in record["sources"]:
        source.update(reference)
    return record


def _non_ancestor_source_reference(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    repo = tmp_path / "non-ancestor-repo"
    repo.mkdir()
    for args in (
        ("init", "--initial-branch=main"),
        ("config", "user.email", "tests@example.invalid"),
        ("config", "user.name", "Typed Outcome Tests"),
    ):
        _git_bytes(repo, *args)

    (repo / "README.md").write_text("main evidence\n", encoding="utf-8")
    _git_bytes(repo, "add", "README.md")
    _git_bytes(repo, "commit", "-m", "main evidence")
    _git_bytes(repo, "checkout", "--orphan", "side")
    _git_bytes(repo, "rm", "-rf", ".")
    (repo / "README.md").write_text("side evidence\n", encoding="utf-8")
    _git_bytes(repo, "add", "README.md")
    _git_bytes(repo, "commit", "-m", "side evidence")
    side_commit = _git_bytes(repo, "rev-parse", "HEAD").decode().strip()
    _git_bytes(repo, "checkout", "main")

    blob_bytes = _git_bytes(repo, "show", f"{side_commit}:README.md")
    return repo, {
        "path": "README.md",
        "sha256": hashlib.sha256(blob_bytes).hexdigest(),
        "commit": side_commit,
    }


def test_validate_canonical_typed_outcome_record_and_summarize() -> None:
    record = _record()

    assert validate_typed_outcome_record(record) == {
        "ok": True,
        "issues": [],
        "statement_count": 7,
        "source_count": 8,
    }
    assert summarize_typed_outcome_record(record)["statements"] == {
        "clarification_halt": "not_required",
        "capability_gap": "supported",
        "execution": "passed",
        "behavioral_equivalence": "passed",
        "validation": "passed",
        "scientific_claim": "miss",
        "construct_validity": "sound",
    }
    assert record["schema"] == SCHEMA
    assert set(record) == {
        "schema",
        "record_id",
        "subject",
        "sources",
        "statements",
        "boundary_note",
    }


def test_validate_published_synthetic_worked_example() -> None:
    record = load_typed_outcome_record(SEED_RECORD)

    assert record["subject"] == {
        "model_id": "synthetic-d7-example",
        "backend_id": "synthetic-fixture",
        "attempt_id": "d7-worked-example-001",
    }
    assert record["boundary_note"] == (
        "This is a synthetic schema fixture only, not evidence of real models, "
        "backend equivalence, external-runtime behavior, real-data validation, paper "
        "reproduction, or scientific results."
    )
    assert validate_typed_outcome_record(record, repo=REPO_ROOT) == {
        "ok": True,
        "issues": [],
        "statement_count": 7,
        "source_count": 8,
    }
    assert summarize_typed_outcome_record(record)["statements"] == {
        "clarification_halt": "not_required",
        "capability_gap": "supported",
        "execution": "passed",
        "behavioral_equivalence": "passed",
        "validation": "passed",
        "scientific_claim": "miss",
        "construct_validity": "sound",
    }


def test_validate_accepts_sources_with_exact_committed_blob_bytes() -> None:
    result = validate_typed_outcome_record(_record_with_committed_source(), repo=REPO_ROOT)

    assert result["ok"] is True, result["issues"]


def test_validate_accepts_forward_slash_docs_path_with_committed_blob_bytes() -> None:
    result = validate_typed_outcome_record(
        _record_with_committed_source(
            path="docs/reproduce/typed-outcomes/synthetic-worked-example/sources/clarification.md"
        ),
        repo=REPO_ROOT,
    )

    assert result["ok"] is True, result["issues"]


def test_validate_rejects_leading_dot_path_alias_despite_valid_blob_provenance() -> None:
    record = _record_with_committed_source()
    record["sources"][0]["path"] = "./README.md"

    result = validate_typed_outcome_record(record, repo=REPO_ROOT)

    assert result["ok"] is False
    assert "sources[0].path must be a canonical POSIX repository-relative path" in result[
        "issues"
    ]


@pytest.mark.parametrize(
    ("repo", "issue"),
    [
        (".", "repo must be a pathlib.Path"),
        (object(), "repo must be a pathlib.Path"),
        (Path("\0"), "repo must resolve to a usable directory"),
    ],
)
def test_validate_rejects_invalid_repo_without_running_provenance(
    repo: object, issue: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> None:
        pytest.fail("invalid repo must not run provenance subprocesses")

    monkeypatch.setattr(typed_outcomes.subprocess, "run", fail_if_called)

    result = validate_typed_outcome_record(_record(), repo=repo)  # type: ignore[arg-type]

    assert result["ok"] is False
    assert result["issues"] == [issue]


@pytest.mark.parametrize(
    ("field", "value", "issue"),
    [
        ("path", "/absolute/evidence.md", "must be a canonical POSIX repository-relative path"),
        ("path", r"\evidence.md", "must be a canonical POSIX repository-relative path"),
        ("path", r"\?\C:\evidence.md", "must be a canonical POSIX repository-relative path"),
        ("path", r"C:\\evidence.md", "must be a canonical POSIX repository-relative path"),
        ("path", "C:relative-evidence.md", "must be a canonical POSIX repository-relative path"),
        ("path", r"\\\\server\\share\\evidence.md", "must be a canonical POSIX repository-relative path"),
        ("path", r"evidence\nested.md", "must be a canonical POSIX repository-relative path"),
        ("path", "evidence/../evidence.md", "must be a canonical POSIX repository-relative path"),
        ("sha256", "a" * 63, "must be a 64-character lowercase hexadecimal digest"),
        ("sha256", "A" * 64, "must be a 64-character lowercase hexadecimal digest"),
        ("commit", "b" * 39, "must be a 40-character lowercase hexadecimal commit"),
        ("commit", "B" * 40, "must be a 40-character lowercase hexadecimal commit"),
    ],
)
def test_validate_rejects_unsafe_or_malformed_source_references_without_raising(
    field: str, value: str, issue: str
) -> None:
    record = _record()
    record["sources"][0][field] = value

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert f"sources[0].{field} {issue}" in result["issues"]


def test_validate_reports_unresolved_commit_as_an_issue_without_raising() -> None:
    record = _record_with_committed_source()
    record["sources"][0]["commit"] = "0" * 40

    result = validate_typed_outcome_record(record, repo=REPO_ROOT)

    assert result["ok"] is False
    assert "sources[0].commit must resolve to a commit in the repository" in result[
        "issues"
    ]


def test_validate_reports_non_ancestor_commit_as_an_issue_without_raising(
    tmp_path: Path,
) -> None:
    repo, reference = _non_ancestor_source_reference(tmp_path)
    record = _record_with_committed_source(repo)
    record["sources"][0].update(reference)

    result = validate_typed_outcome_record(record, repo=repo)

    assert result["ok"] is False
    assert "sources[0].commit must be an ancestor of HEAD" in result["issues"]


def test_validate_reports_path_absent_at_commit_as_an_issue_without_raising() -> None:
    record = _record_with_committed_source()
    record["sources"][0]["path"] = "missing-evidence.md"

    result = validate_typed_outcome_record(record, repo=REPO_ROOT)

    assert result["ok"] is False
    assert "sources[0].path is absent at declared commit" in result["issues"]


def test_validate_rejects_committed_directory_as_a_non_blob_source() -> None:
    record = _record_with_committed_source()
    commit = record["sources"][0]["commit"]
    tree_bytes = _git_bytes(REPO_ROOT, "show", f"{commit}:docs")
    record["sources"][0].update(
        {
            "path": "docs",
            "sha256": hashlib.sha256(tree_bytes).hexdigest(),
        }
    )

    result = validate_typed_outcome_record(record, repo=REPO_ROOT)

    assert result["ok"] is False
    assert "sources[0].path must name a blob at declared commit" in result["issues"]


def test_validate_reports_committed_blob_hash_mismatch_as_an_issue_without_raising() -> None:
    record = _record_with_committed_source()
    record["sources"][0]["sha256"] = "0" * 64

    result = validate_typed_outcome_record(record, repo=REPO_ROOT)

    assert result["ok"] is False
    assert "sources[0].sha256 does not match committed blob bytes" in result["issues"]


def test_validate_rejects_unknown_root_field() -> None:
    record = _record()
    record["overall_status"] = "passed"

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert "unknown root field: overall_status" in result["issues"]


def test_validate_rejects_missing_seventh_statement() -> None:
    record = _record()
    record["statements"] = record["statements"][:-1]

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert "statements must contain exactly 7 items" in result["issues"]


def test_validate_rejects_reversed_statement_order() -> None:
    record = deepcopy(_record())
    record["statements"].reverse()

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert "statements must follow canonical statement order" in result["issues"]


def test_validate_rejects_unhashable_statement_kind_without_raising() -> None:
    record = _record()
    record["statements"][0]["kind"] = []

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert result["issues"] == [
        "statements must follow canonical statement order",
        "statements[0].kind is invalid",
    ]


def test_validate_rejects_unhashable_statement_status_without_raising() -> None:
    record = _record()
    record["statements"][0]["status"] = {}

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert result["issues"] == [
        "statements[0].status is invalid for kind clarification_halt",
    ]


def test_summarize_rejects_non_dict_record_without_raising() -> None:
    assert summarize_typed_outcome_record([]) == {
        "record_id": None,
        "subject": None,
        "statements": _empty_statement_summary(),
    }


def test_summarize_handles_non_list_statements_without_raising() -> None:
    record = _record()
    record["statements"] = {"not": "a list"}

    assert summarize_typed_outcome_record(record) == {
        "record_id": "canonical-outcome-record",
        "subject": record["subject"],
        "statements": _empty_statement_summary(),
    }


def test_summarize_uses_none_for_missing_statement_status() -> None:
    record = _record()
    del record["statements"][0]["status"]
    expected = _empty_statement_summary()
    expected.update(
        {
            "capability_gap": "supported",
            "execution": "passed",
            "behavioral_equivalence": "passed",
            "validation": "passed",
            "scientific_claim": "miss",
            "construct_validity": "sound",
        }
    )

    summary = summarize_typed_outcome_record(record)

    assert summary["statements"] == expected
    assert list(summary["statements"]) == list(STATEMENT_ORDER)


def test_summarize_uses_none_for_duplicate_and_missing_kinds() -> None:
    record = _record()
    record["statements"][1]["kind"] = "clarification_halt"
    record["statements"][1]["status"] = "not_required"
    expected = _empty_statement_summary()
    expected.update(
        {
            "execution": "passed",
            "behavioral_equivalence": "passed",
            "validation": "passed",
            "scientific_claim": "miss",
            "construct_validity": "sound",
        }
    )

    summary = summarize_typed_outcome_record(record)

    assert summary["statements"] == expected
    assert list(summary["statements"]) == list(STATEMENT_ORDER)


def test_validate_requires_nonempty_string_for_every_source_field() -> None:
    for field in ("id", "role", "path", "sha256", "commit", "schema"):
        record = _record()
        record["sources"][0][field] = None

        result = validate_typed_outcome_record(record)

        assert result["ok"] is False
        assert f"sources[0].{field} must be a nonempty string" in result["issues"]


def test_validate_requires_nonempty_string_boundary_note() -> None:
    for boundary_note in (None, ""):
        record = _record()
        record["boundary_note"] = boundary_note

        result = validate_typed_outcome_record(record)

        assert result["ok"] is False
        assert result["issues"] == ["boundary_note must be a nonempty string"]


def test_validate_rejects_statement_source_ids_not_declared_at_root() -> None:
    record = _record()
    record["statements"][0]["source_ids"] = ["missing"]

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert result["issues"] == [
        "statements[0].source_ids references undeclared source id: missing"
    ]


def test_validate_rejects_non_string_root_field_name_without_raising() -> None:
    record = _record()
    record[1] = "not a valid field name"

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert result["issues"] == ["root field names must be strings"]


def test_validate_uses_closed_status_vocabulary() -> None:
    record = _record()
    record["statements"][2]["status"] = "invented"

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert result["issues"] == [
        "statements[2].status is invalid for kind execution",
    ]


def test_exported_schema_constants_cannot_be_mutated() -> None:
    with pytest.raises(TypeError):
        ALLOWED_STATUSES["new_kind"] = frozenset({"invented"})
    with pytest.raises((AttributeError, TypeError)):
        ALLOWED_STATUSES["execution"].add("invented")
    for fields in (ROOT_FIELDS, SUBJECT_FIELDS, SOURCE_FIELDS, STATEMENT_FIELDS):
        with pytest.raises((AttributeError, TypeError)):
            fields.add("not_allowed")


@pytest.mark.parametrize(
    ("kind", "status"),
    [
        (kind, status)
        for kind, statuses in ALLOWED_STATUSES.items()
        for status in sorted(statuses)
    ],
)
def test_validate_accepts_every_allowed_status_with_its_required_source_roles(
    kind: str, status: str
) -> None:
    result = validate_typed_outcome_record(_record_for_status(kind, status))

    assert result["ok"] is True, result["issues"]


def test_validate_rejects_determinate_status_without_its_required_role() -> None:
    record = _record()
    record["statements"][2]["source_ids"] = ["capability-record"]

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert "statements[2] requires source role: execution_receipt" in result["issues"]


def test_not_required_clarification_requires_a_clarification_record() -> None:
    record = _record_for_status("clarification_halt", "not_required")
    record["statements"][0]["source_ids"] = ["scope-note"]

    scope_note_result = validate_typed_outcome_record(record)

    assert scope_note_result["ok"] is False
    assert "statements[0] requires source role: clarification_record" in scope_note_result[
        "issues"
    ]

    record["statements"][0]["source_ids"] = ["clarification-record"]

    clarification_record_result = validate_typed_outcome_record(record)

    assert clarification_record_result["ok"] is True, clarification_record_result["issues"]


@pytest.mark.parametrize(
    ("kind", "status"),
    [
        ("clarification_halt", "not_assessed"),
        ("capability_gap", "not_assessed"),
        ("execution", "not_attempted"),
        ("execution", "not_assessed"),
        ("behavioral_equivalence", "not_assessed"),
        ("behavioral_equivalence", "not_applicable"),
        ("validation", "not_assessed"),
        ("validation", "not_applicable"),
        ("scientific_claim", "not_assessed"),
        ("scientific_claim", "not_applicable"),
        ("construct_validity", "not_reviewed"),
        ("construct_validity", "not_applicable"),
    ],
)
def test_validate_requires_scope_note_for_non_determinate_statuses(
    kind: str, status: str
) -> None:
    record = _record_for_status(kind, status)
    statement = next(item for item in record["statements"] if item["kind"] == kind)
    statement["source_ids"] = ["capability-record"]

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert f"statements[{STATEMENT_ORDER.index(kind)}] requires source role: scope_note" in result["issues"]


@pytest.mark.parametrize(
    ("kind", "status"),
    [("clarification_halt", "halted"), ("capability_gap", "gap")],
)
def test_halt_and_capability_gap_require_unattempted_execution_and_unassessed_downstream(
    kind: str, status: str
) -> None:
    record = _record_for_status(kind, status)
    record["statements"][2]["status"] = "passed"
    _assign_required_sources(record)

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert f"{kind}={status} requires execution=not_attempted" in result["issues"]


def test_halt_requires_every_downstream_statement_to_be_not_a_result() -> None:
    record = _record_for_status("clarification_halt", "halted")
    record["statements"][4]["status"] = "passed"
    _assign_required_sources(record)

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert "clarification_halt=halted requires validation to be not_assessed or not_applicable" in result["issues"]


def test_execution_failure_cannot_coexist_with_scientific_miss() -> None:
    record = _record_for_status("execution", "failed")
    record["statements"][5]["status"] = "miss"
    _assign_required_sources(record)

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert "execution=failed requires scientific_claim to be not_assessed or not_applicable" in result["issues"]


def test_unattempted_execution_accepts_not_result_downstream_statements() -> None:
    record = _record_for_status("execution", "not_attempted")
    record["statements"][4]["status"] = "not_applicable"
    _assign_required_sources(record)

    result = validate_typed_outcome_record(record)

    assert result["ok"] is True, result["issues"]


def test_unattempted_execution_cannot_coexist_with_a_scientific_miss() -> None:
    record = _record_for_status("execution", "not_attempted")
    record["statements"][5]["status"] = "miss"
    _assign_required_sources(record)

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert "execution=not_attempted requires scientific_claim to be not_assessed or not_applicable" in result[
        "issues"
    ]


def test_behavioral_mismatch_requires_unassessed_validation_and_scientific_claim() -> None:
    record = _record_for_status("behavioral_equivalence", "mismatch")
    record["statements"][4]["status"] = "passed"
    _assign_required_sources(record)

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert "behavioral_equivalence=mismatch requires validation to be not_assessed or not_applicable" in result["issues"]


def test_validation_failure_and_scientific_miss_are_independent_and_valid() -> None:
    record = _record()
    record["statements"][4]["status"] = "failed"
    _assign_required_sources(record)

    result = validate_typed_outcome_record(record)

    assert result["ok"] is True, result["issues"]


def test_mis_specified_construct_cannot_coexist_with_passed_scientific_claim() -> None:
    record = _record_for_status("construct_validity", "mis_specified")
    record["statements"][5]["status"] = "passed"
    _assign_required_sources(record)

    result = validate_typed_outcome_record(record)

    assert result["ok"] is False
    assert "construct_validity=mis_specified cannot coexist with scientific_claim=passed" in result["issues"]


def test_validate_rejects_unknown_and_non_string_source_roles_without_raising() -> None:
    unknown_role_record = _record()
    unknown_role_record["sources"][0]["role"] = "unrecognized_role"
    non_string_role_record = _record()
    non_string_role_record["sources"][0]["role"] = []

    unknown_result = validate_typed_outcome_record(unknown_role_record)
    non_string_result = validate_typed_outcome_record(non_string_role_record)

    assert "sources[0].role is not a recognized source role" in unknown_result["issues"]
    assert "sources[0].role must be a nonempty string" in non_string_result["issues"]


def test_source_role_policy_constants_are_closed_and_frozen() -> None:
    source_roles = getattr(typed_outcomes, "SOURCE_ROLES", None)
    required_roles = getattr(typed_outcomes, "REQUIRED_ROLES", None)

    assert source_roles == _EXPECTED_SOURCE_ROLES
    assert required_roles == _EXPECTED_REQUIRED_ROLES
    with pytest.raises((AttributeError, TypeError)):
        source_roles.add("unrecognized_role")
    with pytest.raises(TypeError):
        required_roles[("execution", "invented")] = frozenset({"scope_note"})
