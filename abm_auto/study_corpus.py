"""Study corpus registry and doctor for committed reproduction bundles.

This module is an artifact-health layer over ``docs/studies``. It indexes locked
study bundles and reports prediction-only directories as pending work. It does
not rerun models and does not certify scientific truth.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from abm_auto.repro_bundle import validate_repro_bundle_file

SCHEMA = "abm-auto/study-corpus-registry/v1"
BOUNDARY_NOTE = (
    "Study corpus doctor checks committed artifact health only; "
    "it is not a scientific truth certificate."
)
COMPLETE_STATUS = "complete"
PENDING_STATUS = "pending_bundle"


def _repo_root(repo: Path | None) -> Path:
    return Path.cwd().resolve() if repo is None else Path(repo).resolve()


def _artifact_path(path_value: Any, repo: Path) -> Path:
    path = Path(str(path_value))
    return path if path.is_absolute() else repo / path


def _relative_path(path: Path, repo: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo).as_posix()
    except ValueError:
        return path.as_posix()


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _bundle_doc_path(bundle: dict, doc_name: str, fallback: str | None = None) -> str | None:
    docs = bundle.get("docs")
    if isinstance(docs, dict):
        artifact = docs.get(doc_name)
        if isinstance(artifact, dict) and _is_nonempty_string(artifact.get("path")):
            return artifact["path"]
    return fallback


def _verdict_counts(bundle: dict) -> dict:
    verdicts = bundle.get("verdicts")
    if not isinstance(verdicts, list):
        verdicts = []
    failed = sum(
        1
        for verdict in verdicts
        if isinstance(verdict, dict) and verdict.get("passed") is False
    )
    return {
        "verdict_count": len(verdicts),
        "failed_verdict_count": failed,
        "passed_verdict_count": len(verdicts) - failed,
    }


def _status_counts(entries: list[dict]) -> dict:
    counts = {COMPLETE_STATUS: 0, PENDING_STATUS: 0}
    for entry in entries:
        status = entry.get("status")
        if status in counts:
            counts[status] += 1
    return counts


def _study_dirs(studies_root: Path) -> list[Path]:
    return sorted(
        (path for path in studies_root.iterdir() if path.is_dir()),
        key=lambda path: path.name,
    )


def _git_tracked_paths_under(studies_root: Path, repo: Path) -> set[str] | None:
    try:
        root_rel = studies_root.resolve().relative_to(repo).as_posix()
    except ValueError:
        return None

    try:
        result = subprocess.run(
            ["git", "ls-files", "--", root_rel],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return {line for line in result.stdout.splitlines() if line.strip()}


def _is_committed_or_filesystem(path: Path, *, repo: Path, tracked_paths: set[str] | None) -> bool:
    if tracked_paths is None:
        return path.exists()
    return _relative_path(path, repo) in tracked_paths


def discover_study_corpus(studies_root: Path, *, repo: Path | None = None) -> dict:
    """Discover completed and pending study directories under ``docs/studies``."""
    repo_root = _repo_root(repo)
    root = _artifact_path(studies_root, repo_root)
    if not root.is_dir():
        return {
            "ok": False,
            "issues": ["studies root does not exist or is not a directory"],
            "study_root": _relative_path(root, repo_root),
            "complete": [],
            "pending": [],
            "complete_count": 0,
            "pending_count": 0,
        }

    complete: list[dict] = []
    pending: list[dict] = []
    tracked_paths = _git_tracked_paths_under(root, repo_root)
    for study_dir in _study_dirs(root):
        predictions = study_dir / "PREDICTIONS-locked.md"
        bundle = study_dir / "verdict-bundle.json"
        if bundle.exists() and _is_committed_or_filesystem(bundle, repo=repo_root, tracked_paths=tracked_paths):
            complete.append({
                "id": study_dir.name,
                "status": COMPLETE_STATUS,
                "study_dir": _relative_path(study_dir, repo_root),
                "bundle": _relative_path(bundle, repo_root),
                "predictions": _relative_path(predictions, repo_root) if predictions.exists() else None,
            })
        elif predictions.exists() and _is_committed_or_filesystem(predictions, repo=repo_root, tracked_paths=tracked_paths):
            pending.append({
                "id": study_dir.name,
                "status": PENDING_STATUS,
                "study_dir": _relative_path(study_dir, repo_root),
                "predictions": _relative_path(predictions, repo_root),
            })

    return {
        "ok": True,
        "issues": [],
        "study_root": _relative_path(root, repo_root),
        "complete": complete,
        "pending": pending,
        "complete_count": len(complete),
        "pending_count": len(pending),
    }


def _registry_entry_from_bundle(discovered: dict, *, repo: Path) -> dict:
    bundle = _load_json(_artifact_path(discovered["bundle"], repo))
    predictions_fallback = discovered.get("predictions")
    findings = _bundle_doc_path(bundle, "findings")
    design_spec = _bundle_doc_path(bundle, "design_spec")
    paper = bundle.get("paper") if isinstance(bundle.get("paper"), dict) else {}
    docs = bundle.get("docs") if isinstance(bundle.get("docs"), dict) else {}
    data = bundle.get("data") if isinstance(bundle.get("data"), dict) else {}

    return {
        "id": discovered["id"],
        "status": COMPLETE_STATUS,
        "study_dir": discovered["study_dir"],
        "bundle": discovered["bundle"],
        "predictions": _bundle_doc_path(bundle, "predictions_locked", predictions_fallback),
        "findings": findings,
        "design_spec": design_spec,
        "paper": paper,
        "headline": bundle.get("headline", ""),
        **_verdict_counts(bundle),
        "doc_fingerprint_count": len(docs),
        "data_fingerprint_count": len(data),
    }


def _registry_entry_from_pending(discovered: dict) -> dict:
    return {
        "id": discovered["id"],
        "status": PENDING_STATUS,
        "study_dir": discovered["study_dir"],
        "predictions": discovered["predictions"],
        "headline": "Predictions are locked; verdict bundle is not yet committed.",
        "verdict_count": 0,
        "failed_verdict_count": 0,
        "passed_verdict_count": 0,
    }


def build_study_registry(studies_root: Path, *, repo: Path | None = None) -> dict:
    """Build a deterministic registry for committed and pending study artifacts."""
    repo_root = _repo_root(repo)
    corpus = discover_study_corpus(studies_root, repo=repo_root)
    entries: list[dict] = []
    if corpus["ok"]:
        entries.extend(_registry_entry_from_bundle(entry, repo=repo_root) for entry in corpus["complete"])
        entries.extend(_registry_entry_from_pending(entry) for entry in corpus["pending"])
    entries.sort(key=lambda entry: entry["id"])

    total_verdicts = sum(int(entry.get("verdict_count", 0)) for entry in entries)
    failed_verdicts = sum(int(entry.get("failed_verdict_count", 0)) for entry in entries)
    status_counts = _status_counts(entries)
    return {
        "schema": SCHEMA,
        "title": "MyMoMo Study Corpus Registry",
        "boundary_note": BOUNDARY_NOTE,
        "study_root": corpus["study_root"],
        "summary": {
            "entry_count": len(entries),
            "complete_count": status_counts[COMPLETE_STATUS],
            "pending_count": status_counts[PENDING_STATUS],
            "status_counts": status_counts,
            "total_verdict_count": total_verdicts,
            "failed_verdict_count": failed_verdicts,
        },
        "entries": entries,
    }


def _validate_relative_path(
    entry: dict,
    *,
    field: str,
    prefix: str,
    repo: Path,
    issues: list[str],
    required: bool = True,
    must_exist: bool = True,
    expected_directory: bool | None = None,
) -> None:
    value = entry.get(field)
    if value is None and not required:
        return
    if not _is_nonempty_string(value) or Path(str(value)).is_absolute():
        issues.append(f"{prefix}.{field} must be a repo-relative path")
        return

    full_path = _artifact_path(value, repo)
    if must_exist and not full_path.exists():
        issues.append(f"{prefix}.{field} does not exist")
        return
    if expected_directory is True and full_path.exists() and not full_path.is_dir():
        issues.append(f"{prefix}.{field} must point to a directory")
    if expected_directory is False and full_path.exists() and not full_path.is_file():
        issues.append(f"{prefix}.{field} must point to a file")


def validate_study_registry(registry: dict, *, repo: Path | None = None) -> dict:
    """Validate a study corpus registry and its referenced committed paths."""
    repo_root = _repo_root(repo)
    if not isinstance(registry, dict):
        return {"ok": False, "issues": ["registry must be a JSON object"], "entry_count": 0}

    issues: list[str] = []
    if registry.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA}")
    if not _is_nonempty_string(registry.get("title")):
        issues.append("title must be a non-empty string")
    if not _is_nonempty_string(registry.get("boundary_note")):
        issues.append("boundary_note must be a non-empty string")
    if not _is_nonempty_string(registry.get("study_root")) or Path(str(registry.get("study_root"))).is_absolute():
        issues.append("study_root must be a repo-relative path")

    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        issues.append("entries must be a non-empty list")
        entries = []

    seen_ids: set[str] = set()
    status_counts = {COMPLETE_STATUS: 0, PENDING_STATUS: 0}
    for idx, entry in enumerate(entries):
        prefix = f"entries[{idx}]"
        if not isinstance(entry, dict):
            issues.append(f"{prefix} must be an object")
            continue

        entry_id = entry.get("id")
        if not _is_nonempty_string(entry_id):
            issues.append(f"{prefix}.id must be a non-empty string")
        elif entry_id in seen_ids:
            issues.append(f"duplicate entry id {entry_id}")
        else:
            seen_ids.add(entry_id)

        status = entry.get("status")
        if status not in {COMPLETE_STATUS, PENDING_STATUS}:
            issues.append(f"{prefix}.status must be {COMPLETE_STATUS!r} or {PENDING_STATUS!r}")
        else:
            status_counts[status] += 1

        _validate_relative_path(
            entry,
            field="study_dir",
            prefix=prefix,
            repo=repo_root,
            issues=issues,
            expected_directory=True,
        )
        _validate_relative_path(
            entry,
            field="predictions",
            prefix=prefix,
            repo=repo_root,
            issues=issues,
            expected_directory=False,
        )

        if status == COMPLETE_STATUS:
            _validate_relative_path(
                entry,
                field="bundle",
                prefix=prefix,
                repo=repo_root,
                issues=issues,
                expected_directory=False,
            )
            _validate_relative_path(
                entry,
                field="findings",
                prefix=prefix,
                repo=repo_root,
                issues=issues,
                required=False,
                expected_directory=False,
            )
            _validate_relative_path(
                entry,
                field="design_spec",
                prefix=prefix,
                repo=repo_root,
                issues=issues,
                required=False,
                expected_directory=False,
            )
            if not isinstance(entry.get("paper"), dict) or not _is_nonempty_string(entry["paper"].get("title")):
                issues.append(f"{prefix}.paper.title is required for complete studies")
        elif status == PENDING_STATUS and "bundle" in entry:
            issues.append(f"{prefix}.bundle must be absent for pending studies")

        for field in ("verdict_count", "failed_verdict_count", "passed_verdict_count"):
            value = entry.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                issues.append(f"{prefix}.{field} must be a non-negative integer")

    summary = registry.get("summary")
    if not isinstance(summary, dict):
        issues.append("summary must be an object")
    else:
        if summary.get("entry_count") != len(entries):
            issues.append("summary.entry_count must match entries length")
        if summary.get("complete_count") != status_counts[COMPLETE_STATUS]:
            issues.append("summary.complete_count must match complete entries")
        if summary.get("pending_count") != status_counts[PENDING_STATUS]:
            issues.append("summary.pending_count must match pending entries")
        if summary.get("status_counts") != status_counts:
            issues.append("summary.status_counts must match entries")

    return {"ok": not issues, "issues": issues, "entry_count": len(entries)}


def diagnose_study_corpus(
    studies_root: Path,
    *,
    repo: Path | None = None,
    registry_path: Path | None = None,
    index_path: Path | None = None,
) -> dict:
    """Run the standard study corpus artifact-health checks."""
    repo_root = _repo_root(repo)
    root = _artifact_path(studies_root, repo_root)
    if not root.is_dir():
        return {
            "ok": False,
            "issues": ["studies root does not exist or is not a directory"],
            "summary": {
                "complete_count": 0,
                "pending_count": 0,
                "failed_bundle_count": 0,
                "failed_registry_issue_count": 1,
                "registry_matches_committed": False,
                "index_matches_committed": False,
            },
            "pending_ids": [],
            "bundle_results": [],
        }

    registry = build_study_registry(root, repo=repo_root)
    registry_validation = validate_study_registry(registry, repo=repo_root)
    registry_issues = list(registry_validation["issues"])
    registry_matches_committed: bool | None = None
    index_matches_committed: bool | None = None

    if registry_path is not None:
        full_registry_path = _artifact_path(registry_path, repo_root)
        if not full_registry_path.exists():
            registry_issues.append("registry path does not exist")
            registry_matches_committed = False
        else:
            committed_registry = _load_json(full_registry_path)
            committed_validation = validate_study_registry(committed_registry, repo=repo_root)
            registry_issues.extend(f"committed registry: {issue}" for issue in committed_validation["issues"])
            registry_matches_committed = committed_validation["ok"] and committed_registry == registry
            if committed_validation["ok"] and not registry_matches_committed:
                registry_issues.append("committed registry does not match current study corpus")

    if index_path is not None:
        full_index_path = _artifact_path(index_path, repo_root)
        if not full_index_path.exists():
            registry_issues.append("index path does not exist")
            index_matches_committed = False
        else:
            expected_index = render_study_index_markdown(registry)
            index_matches_committed = full_index_path.read_text(encoding="utf-8") == expected_index
            if not index_matches_committed:
                registry_issues.append("committed index does not match current study corpus")

    bundle_results: list[dict] = []
    for entry in registry["entries"]:
        if entry["status"] != COMPLETE_STATUS:
            continue
        validation = validate_repro_bundle_file(
            _artifact_path(entry["bundle"], repo_root),
            repo=repo_root,
            check_doc_hashes=True,
            check_data_hashes=False,
        )
        bundle_results.append({
            "id": entry["id"],
            "bundle": entry["bundle"],
            "ok": validation["ok"],
            "issues": validation["issues"],
            "verdict_count": validation.get("verdict_count", 0),
            "failed_verdict_count": validation.get("failed_verdict_count", 0),
            "doc_hashes_checked": validation.get("doc_hashes_checked", 0),
            "data_fingerprint_count": validation.get("data_fingerprint_count", 0),
        })

    failed_bundles = [result for result in bundle_results if not result["ok"]]
    pending_ids = [
        entry["id"]
        for entry in registry["entries"]
        if entry["status"] == PENDING_STATUS
    ]
    ok = not registry_issues and not failed_bundles
    return {
        "ok": ok,
        "issues": registry_issues + [
            f"{result['id']}: {result['issues'][:3]}" for result in failed_bundles
        ],
        "registry_validation": {
            "ok": not registry_issues,
            "issues": registry_issues,
            "entry_count": registry_validation["entry_count"],
        },
        "bundle_results": bundle_results,
        "pending_ids": pending_ids,
        "summary": {
            "complete_count": registry["summary"]["complete_count"],
            "pending_count": registry["summary"]["pending_count"],
            "entry_count": registry["summary"]["entry_count"],
            "failed_bundle_count": len(failed_bundles),
            "failed_registry_issue_count": len(registry_issues),
            "total_verdict_count": registry["summary"]["total_verdict_count"],
            "failed_verdict_count": registry["summary"]["failed_verdict_count"],
            "registry_matches_committed": registry_matches_committed,
            "index_matches_committed": index_matches_committed,
        },
        "boundary_note": BOUNDARY_NOTE,
    }


def _md_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_study_index_markdown(registry: dict) -> str:
    """Render a deterministic Markdown index for the study corpus registry."""
    summary = registry["summary"]
    lines = [
        "# MyMoMo Study Corpus Index",
        "",
        BOUNDARY_NOTE,
        "",
        "## Summary",
        "",
        f"- Complete bundles: {summary['complete_count']}",
        f"- Pending prediction locks: {summary['pending_count']}",
        f"- Total verdict clauses: {summary['total_verdict_count']}",
        f"- Failed verdict clauses: {summary['failed_verdict_count']}",
        "",
        "## Studies",
        "",
        "| Study | Status | Verdicts | Failed | Headline |",
        "|---|---:|---:|---:|---|",
    ]
    for entry in registry["entries"]:
        lines.append(
            "| "
            f"`{_md_cell(entry['id'])}` | "
            f"{_md_cell(entry['status'])} | "
            f"{entry['verdict_count']} | "
            f"{entry['failed_verdict_count']} | "
            f"{_md_cell(entry.get('headline', ''))} |"
        )

    pending = [entry for entry in registry["entries"] if entry["status"] == PENDING_STATUS]
    if pending:
        lines.extend(["", "## Pending Bundles", ""])
        for entry in pending:
            lines.append(f"- `{entry['id']}`: {entry['predictions']}")

    lines.append("")
    return "\n".join(lines)


def write_study_registry(registry: dict, path: Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def write_study_index(registry: dict, path: Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_study_index_markdown(registry), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and validate the MyMoMo study corpus registry.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Build registry and Markdown index artifacts.")
    build.add_argument("studies_root", type=Path)
    build.add_argument("--repo", type=Path, default=None)
    build.add_argument("--registry", type=Path, required=True)
    build.add_argument("--index", type=Path, required=True)

    doctor = subparsers.add_parser("doctor", help="Validate the study corpus and optional committed artifacts.")
    doctor.add_argument("studies_root", type=Path)
    doctor.add_argument("--repo", type=Path, default=None)
    doctor.add_argument("--registry", type=Path, default=None)
    doctor.add_argument("--index", type=Path, default=None)

    report = subparsers.add_parser("report", help="Print the study corpus Markdown index.")
    report.add_argument("studies_root", type=Path)
    report.add_argument("--repo", type=Path, default=None)

    args = parser.parse_args(argv)
    if args.command == "build":
        repo_root = _repo_root(args.repo)
        registry = build_study_registry(args.studies_root, repo=repo_root)
        validation = validate_study_registry(registry, repo=repo_root)
        registry_out = _artifact_path(args.registry, repo_root)
        index_out = _artifact_path(args.index, repo_root)
        if validation["ok"]:
            write_study_registry(registry, registry_out)
            write_study_index(registry, index_out)
        result = {
            "ok": validation["ok"],
            "issues": validation["issues"],
            "summary": registry["summary"],
            "registry": _relative_path(registry_out, repo_root),
            "index": _relative_path(index_out, repo_root),
            "boundary_note": BOUNDARY_NOTE,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1

    if args.command == "doctor":
        result = diagnose_study_corpus(
            args.studies_root,
            repo=args.repo,
            registry_path=args.registry,
            index_path=args.index,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1

    if args.command == "report":
        registry = build_study_registry(args.studies_root, repo=args.repo)
        print(render_study_index_markdown(registry))
        return 0

    parser.error(f"unsupported command {args.command}")
    return 2


__all__ = [
    "BOUNDARY_NOTE",
    "COMPLETE_STATUS",
    "PENDING_STATUS",
    "SCHEMA",
    "build_study_registry",
    "diagnose_study_corpus",
    "discover_study_corpus",
    "render_study_index_markdown",
    "validate_study_registry",
    "write_study_index",
    "write_study_registry",
]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
