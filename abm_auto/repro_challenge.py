"""MyMoMo Evidence Foundry reproduction challenge packs.

This module is a small trust-layer utility: it turns already-existing evidence
artifacts into a deterministic challenge for another agent, then grades the
answer against locked claims and citations. It does not run simulations or
certify scientific truth.
"""
from __future__ import annotations

import argparse
import json
import string
import sys
from pathlib import Path
from typing import Any, Optional

from abm_auto.verification.provenance import fingerprint

SCHEMA = "abm-auto/repro-challenge/v1"
ANSWER_SCHEMA = "abm-auto/repro-challenge-answer/v1"
PRODUCER_SCHEMA = "abm-auto/repro-challenge-producer/v1"
REGISTRY_SCHEMA = "abm-auto/repro-challenge-registry/v1"
CHALLENGE_MODE = "evidence_answering"
EVIDENCE_FOUNDRY_TITLE = "MyMoMo Evidence Foundry Curriculum"
EVIDENCE_FOUNDRY_REPORT_TITLE = "MyMoMo Evidence Foundry Registry Report"
ALLOWED_VERDICTS = frozenset({"PASS", "MISS", "PARTIAL", "INCONCLUSIVE"})
ALLOWED_DIFFICULTIES = frozenset({"intro", "intermediate", "advanced", "regression"})


def _repo_root(repo: Optional[Path]) -> Path:
    return Path.cwd().resolve() if repo is None else Path(repo).resolve()


def _artifact_path(path_value: Any, repo: Path) -> Path:
    path = Path(str(path_value))
    return path if path.is_absolute() else repo / path


def _portable_path(path: Path, repo: Path) -> str:
    try:
        return path.resolve().relative_to(repo).as_posix()
    except ValueError:
        return str(path)


def _fingerprint_file(path: Path, repo: Path) -> dict:
    full_path = _artifact_path(path, repo)
    fp = fingerprint(full_path)
    fp["path"] = _portable_path(full_path, repo)
    return fp


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in string.hexdigits for ch in value)
    )


def _list_of_strings(value: Any) -> bool:
    return isinstance(value, list) and all(_is_nonempty_string(item) for item in value)


def build_challenge_pack(
    *,
    challenge_id: str,
    title: str,
    source: dict,
    artifacts: dict[str, Path],
    tasks: list[dict],
    repo: Optional[Path] = None,
    extra: Optional[dict] = None,
) -> dict:
    """Build a portable challenge pack from existing evidence artifacts."""
    repo_root = _repo_root(repo)
    pack = {
        "schema": SCHEMA,
        "challenge_mode": CHALLENGE_MODE,
        "challenge_id": challenge_id,
        "title": title,
        "source": dict(source),
        "artifacts": {
            key: _fingerprint_file(Path(path), repo_root)
            for key, path in artifacts.items()
        },
        "tasks": json.loads(json.dumps(tasks, default=str)),
    }
    if extra is not None:
        pack["extra"] = extra
    return pack


def write_challenge_pack(pack: dict, path) -> Path:
    out = Path(path)
    out.write_text(json.dumps(pack, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return out


def validate_challenge_pack(
    pack: dict,
    *,
    repo: Optional[Path] = None,
    check_hashes: bool = True,
) -> dict:
    """Validate schema, portability, artifact hashes, and task references."""
    repo_root = _repo_root(repo)
    issues: list[str] = []
    artifact_hashes_checked = 0
    expected_claim_count = 0

    if not isinstance(pack, dict):
        return {"ok": False, "issues": ["challenge pack must be a JSON object"]}

    if pack.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA!r}")
    if pack.get("challenge_mode") != CHALLENGE_MODE:
        issues.append(f"challenge_mode must be {CHALLENGE_MODE!r}")
    if not _is_nonempty_string(pack.get("challenge_id")):
        issues.append("challenge_id is required")
    if not _is_nonempty_string(pack.get("title")):
        issues.append("title is required")
    if not isinstance(pack.get("source"), dict) or not pack["source"]:
        issues.append("source must be a non-empty object")

    artifacts = pack.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        issues.append("artifacts must be a non-empty object")
        artifacts = {}

    for key, artifact in artifacts.items():
        prefix = f"artifacts.{key}"
        if not _is_nonempty_string(key):
            issues.append("artifact keys must be non-empty strings")
        if not isinstance(artifact, dict):
            issues.append(f"{prefix} must be an object")
            continue
        path_value = artifact.get("path")
        if not _is_nonempty_string(path_value):
            issues.append(f"{prefix}.path is required")
            continue
        path = Path(path_value)
        if path.is_absolute():
            issues.append(f"{prefix}.path uses absolute local path: {path_value}")
        if artifact.get("kind") != "file":
            issues.append(f"{prefix}.kind must be 'file'")
        if artifact.get("replay") != "strong":
            issues.append(f"{prefix}.replay must be 'strong'")
        sha = artifact.get("sha256")
        if not _is_sha256(sha):
            issues.append(f"{prefix}.sha256 must be a 64-char hex string")
        if check_hashes and not path.is_absolute():
            full_path = _artifact_path(path_value, repo_root)
            if not full_path.exists():
                issues.append(f"{prefix}.path does not exist: {path_value}")
            elif _is_sha256(sha):
                artifact_hashes_checked += 1
                actual = fingerprint(full_path).get("sha256")
                if sha != actual:
                    issues.append(f"{prefix}.sha256 mismatch")

    tasks = pack.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        issues.append("tasks must be a non-empty list")
        tasks = []

    known_artifacts = set(artifacts)
    for idx, task in enumerate(tasks):
        prefix = f"tasks[{idx}]"
        if not isinstance(task, dict):
            issues.append(f"{prefix} must be an object")
            continue
        if not _is_nonempty_string(task.get("id")):
            issues.append(f"{prefix}.id is required")
        if not _is_nonempty_string(task.get("prompt")):
            issues.append(f"{prefix}.prompt is required")
        required = task.get("required_artifacts")
        if not _list_of_strings(required) or not required:
            issues.append(f"{prefix}.required_artifacts must be a non-empty string list")
            required = []
        for artifact_key in required:
            if artifact_key not in known_artifacts:
                issues.append(f"{prefix}.required_artifacts references unknown artifact {artifact_key!r}")

        claims = task.get("expected_claims")
        if not isinstance(claims, list) or not claims:
            issues.append(f"{prefix}.expected_claims must be a non-empty list")
            claims = []
        expected_claim_count += len(claims)
        seen_claim_ids: set[str] = set()
        for claim_idx, claim in enumerate(claims):
            claim_prefix = f"{prefix}.expected_claims[{claim_idx}]"
            if not isinstance(claim, dict):
                issues.append(f"{claim_prefix} must be an object")
                continue
            claim_id = claim.get("id")
            if not _is_nonempty_string(claim_id):
                issues.append(f"{claim_prefix}.id is required")
            elif claim_id in seen_claim_ids:
                issues.append(f"{claim_prefix}.id duplicates {claim_id!r}")
            else:
                seen_claim_ids.add(claim_id)
            verdict = claim.get("verdict")
            if verdict not in ALLOWED_VERDICTS:
                issues.append(f"{claim_prefix}.verdict has invalid verdict {verdict!r}")

    return {
        "ok": not issues,
        "issues": issues,
        "schema": pack.get("schema"),
        "challenge_id": pack.get("challenge_id"),
        "artifact_count": len(artifacts),
        "artifact_hashes_checked": artifact_hashes_checked,
        "task_count": len(tasks),
        "expected_claim_count": expected_claim_count,
    }


def validate_challenge_pack_file(path, *, repo: Optional[Path] = None, **kwargs) -> dict:
    pack_path = Path(path)
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    return validate_challenge_pack(pack, repo=repo, **kwargs)


def validate_challenge_producer_spec(
    spec: dict,
    *,
    repo: Optional[Path] = None,
    check_artifacts: bool = True,
) -> dict:
    """Validate a producer spec before it is rendered into a challenge pack."""
    repo_root = _repo_root(repo)
    issues: list[str] = []
    expected_claim_count = 0

    if not isinstance(spec, dict):
        return {"ok": False, "issues": ["producer spec must be a JSON object"]}

    if spec.get("schema") != PRODUCER_SCHEMA:
        issues.append(f"schema must be {PRODUCER_SCHEMA!r}")
    if not _is_nonempty_string(spec.get("challenge_id")):
        issues.append("challenge_id is required")
    if not _is_nonempty_string(spec.get("title")):
        issues.append("title is required")
    if not isinstance(spec.get("source"), dict) or not spec["source"]:
        issues.append("source must be a non-empty object")

    artifacts = spec.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        issues.append("artifacts must be a non-empty object")
        artifacts = {}

    for key, path_value in artifacts.items():
        prefix = f"artifacts.{key}"
        if not _is_nonempty_string(key):
            issues.append("artifact keys must be non-empty strings")
        if not _is_nonempty_string(path_value):
            issues.append(f"{prefix} must be a non-empty path string")
            continue
        path = Path(path_value)
        if path.is_absolute():
            issues.append(f"{prefix} uses absolute local path: {path_value}")
        elif check_artifacts and not _artifact_path(path, repo_root).exists():
            issues.append(f"{prefix} does not exist: {path_value}")

    tasks = spec.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        issues.append("tasks must be a non-empty list")
        tasks = []

    known_artifacts = set(artifacts)
    for idx, task in enumerate(tasks):
        prefix = f"tasks[{idx}]"
        if not isinstance(task, dict):
            issues.append(f"{prefix} must be an object")
            continue
        if not _is_nonempty_string(task.get("id")):
            issues.append(f"{prefix}.id is required")
        if not _is_nonempty_string(task.get("prompt")):
            issues.append(f"{prefix}.prompt is required")
        required = task.get("required_artifacts")
        if not _list_of_strings(required) or not required:
            issues.append(f"{prefix}.required_artifacts must be a non-empty string list")
            required = []
        for artifact_key in required:
            if artifact_key not in known_artifacts:
                issues.append(f"{prefix}.required_artifacts references unknown artifact {artifact_key!r}")
        claims = task.get("expected_claims")
        if not isinstance(claims, list) or not claims:
            issues.append(f"{prefix}.expected_claims must be a non-empty list")
            claims = []
        expected_claim_count += len(claims)
        seen_claim_ids: set[str] = set()
        for claim_idx, claim in enumerate(claims):
            claim_prefix = f"{prefix}.expected_claims[{claim_idx}]"
            if not isinstance(claim, dict):
                issues.append(f"{claim_prefix} must be an object")
                continue
            claim_id = claim.get("id")
            if not _is_nonempty_string(claim_id):
                issues.append(f"{claim_prefix}.id is required")
            elif claim_id in seen_claim_ids:
                issues.append(f"{claim_prefix}.id duplicates {claim_id!r}")
            else:
                seen_claim_ids.add(claim_id)
            verdict = claim.get("verdict")
            if verdict not in ALLOWED_VERDICTS:
                issues.append(f"{claim_prefix}.verdict has invalid verdict {verdict!r}")

    if "extra" in spec and not isinstance(spec["extra"], dict):
        issues.append("extra must be an object when present")
    if "registry" in spec:
        registry_meta = spec["registry"]
        if not isinstance(registry_meta, dict):
            issues.append("registry must be an object when present")
        else:
            if not _is_nonempty_string(registry_meta.get("domain")):
                issues.append("registry.domain is required")
            difficulty = registry_meta.get("difficulty")
            if difficulty not in ALLOWED_DIFFICULTIES:
                issues.append(f"registry.difficulty has invalid difficulty {difficulty!r}")
            if not _list_of_strings(registry_meta.get("tags")):
                issues.append("registry.tags must be a string list")
            if "owner" in registry_meta and not _is_nonempty_string(registry_meta.get("owner")):
                issues.append("registry.owner must be a non-empty string when present")
            if "summary" in registry_meta and not _is_nonempty_string(registry_meta.get("summary")):
                issues.append("registry.summary must be a non-empty string when present")

    return {
        "ok": not issues,
        "issues": issues,
        "schema": spec.get("schema"),
        "challenge_id": spec.get("challenge_id"),
        "artifact_count": len(artifacts),
        "task_count": len(tasks),
        "expected_claim_count": expected_claim_count,
    }


def validate_challenge_producer_spec_file(path, *, repo: Optional[Path] = None, **kwargs) -> dict:
    spec = _load_json(path)
    return validate_challenge_producer_spec(spec, repo=repo, **kwargs)


def build_challenge_pack_from_producer_spec(
    spec: dict,
    *,
    repo: Optional[Path] = None,
) -> dict:
    """Render a producer spec into a hash-addressed challenge pack."""
    result = validate_challenge_producer_spec(spec, repo=repo)
    if not result["ok"]:
        first = "; ".join(result["issues"][:3])
        raise ValueError(f"invalid challenge producer spec: {first}")

    artifacts = {
        key: Path(path)
        for key, path in spec["artifacts"].items()
    }
    return build_challenge_pack(
        challenge_id=spec["challenge_id"],
        title=spec["title"],
        source=spec["source"],
        artifacts=artifacts,
        tasks=spec["tasks"],
        repo=repo,
        extra=spec.get("extra"),
    )


def _relative_to_repo(path: Path, repo: Path) -> str:
    try:
        return path.resolve().relative_to(repo).as_posix()
    except ValueError:
        return path.as_posix()


def _entry_from_producer_spec_path(spec_path: Path, repo: Path) -> dict:
    spec = _load_json(spec_path)
    result = validate_challenge_producer_spec(spec, repo=repo)
    if not result["ok"]:
        first = "; ".join(result["issues"][:3])
        raise ValueError(f"invalid challenge producer spec {spec_path}: {first}")

    meta = spec.get("registry", {})
    entry = {
        "id": spec["challenge_id"],
        "pack": _relative_to_repo(spec_path.parent / "challenge-pack.json", repo),
        "domain": meta.get("domain", "unclassified"),
        "difficulty": meta.get("difficulty", "intro"),
        "tags": list(meta.get("tags", [])),
    }
    answer = spec_path.parent / "answer-codex.json"
    if answer.exists():
        entry["answer"] = _relative_to_repo(answer, repo)
    if _is_nonempty_string(meta.get("owner")):
        entry["owner"] = meta["owner"]
    if _is_nonempty_string(meta.get("summary")):
        entry["summary"] = meta["summary"]
    return entry


def discover_challenge_registry(
    challenge_root: Path,
    *,
    repo: Optional[Path] = None,
    title: str = EVIDENCE_FOUNDRY_TITLE,
) -> dict:
    """Discover committed producer specs and return a registry-shaped object."""
    repo_root = _repo_root(repo)
    root = _artifact_path(challenge_root, repo_root)
    entries = [
        _entry_from_producer_spec_path(path, repo_root)
        for path in sorted(root.rglob("producer-spec.json"))
    ]
    return {
        "entries": entries,
        "schema": REGISTRY_SCHEMA,
        "title": title,
    }


def audit_registry_discovery(
    registry: dict,
    challenge_root: Path,
    *,
    repo: Optional[Path] = None,
) -> dict:
    """Compare a committed registry against producer-spec discovery."""
    discovered = discover_challenge_registry(
        challenge_root,
        repo=repo,
        title=registry.get("title", EVIDENCE_FOUNDRY_TITLE)
        if isinstance(registry, dict)
        else EVIDENCE_FOUNDRY_TITLE,
    )
    registered_entries = registry.get("entries", []) if isinstance(registry, dict) else []
    if not isinstance(registered_entries, list):
        registered_entries = []

    discovered_by_id = {
        entry["id"]: entry
        for entry in discovered["entries"]
        if isinstance(entry, dict) and _is_nonempty_string(entry.get("id"))
    }
    registered_by_id = {
        entry["id"]: entry
        for entry in registered_entries
        if isinstance(entry, dict) and _is_nonempty_string(entry.get("id"))
    }
    missing_ids = sorted(set(discovered_by_id) - set(registered_by_id))
    extra_ids = sorted(set(registered_by_id) - set(discovered_by_id))
    issues = [
        f"missing registered challenge {challenge_id}"
        for challenge_id in missing_ids
    ] + [
        f"extra registered challenge {challenge_id}"
        for challenge_id in extra_ids
    ]

    for challenge_id in sorted(set(discovered_by_id) & set(registered_by_id)):
        if discovered_by_id[challenge_id] != registered_by_id[challenge_id]:
            issues.append(f"registered challenge {challenge_id} differs from discovery")

    return {
        "ok": not issues,
        "issues": issues,
        "discovered_count": len(discovered_by_id),
        "registered_count": len(registered_by_id),
        "missing_ids": missing_ids,
        "extra_ids": extra_ids,
    }


def run_challenge_registry(
    registry: dict,
    *,
    repo: Optional[Path] = None,
) -> dict:
    """Validate and gate every registered challenge answer."""
    repo_root = _repo_root(repo)
    results: list[dict] = []
    entries = registry.get("entries", []) if isinstance(registry, dict) else []
    if not isinstance(entries, list):
        entries = []

    for idx, entry in enumerate(entries):
        entry_id = entry.get("id", f"entries[{idx}]") if isinstance(entry, dict) else f"entries[{idx}]"
        if not isinstance(entry, dict):
            results.append({
                "id": entry_id,
                "ok": False,
                "description": f"entries[{idx}] must be an object",
            })
            continue
        pack_value = entry.get("pack")
        answer_value = entry.get("answer")
        if not _is_nonempty_string(pack_value):
            results.append({
                "id": entry_id,
                "ok": False,
                "description": "registered challenge is missing pack path",
            })
            continue
        if not _is_nonempty_string(answer_value):
            results.append({
                "id": entry_id,
                "ok": False,
                "description": "registered challenge is missing answer path",
            })
            continue

        pack_path = _artifact_path(pack_value, repo_root)
        answer_path = _artifact_path(answer_value, repo_root)
        if not pack_path.exists():
            results.append({
                "id": entry_id,
                "ok": False,
                "description": f"pack path does not exist: {pack_value}",
            })
            continue
        if not answer_path.exists():
            results.append({
                "id": entry_id,
                "ok": False,
                "description": f"answer path does not exist: {answer_value}",
            })
            continue

        pack = _load_json(pack_path)
        answer = _load_json(answer_path)
        ok, desc = repro_challenge_gate(pack, answer, repo=repo_root)
        results.append({
            "id": entry_id,
            "ok": ok,
            "description": desc,
        })

    failed_count = sum(1 for result in results if not result["ok"])
    return {
        "ok": failed_count == 0,
        "entry_count": len(entries),
        "gated_count": len(results),
        "failed_count": failed_count,
        "results": results,
    }


def render_challenge_registry_report(
    registry: dict,
    *,
    repo: Optional[Path] = None,
) -> str:
    """Render a concise Markdown report for a challenge registry gate run."""
    gate = run_challenge_registry(registry, repo=repo)
    entries = registry.get("entries", []) if isinstance(registry, dict) else []
    entry_by_id = {
        entry.get("id"): entry
        for entry in entries
        if isinstance(entry, dict)
    }
    lines = [
        f"# {EVIDENCE_FOUNDRY_REPORT_TITLE}",
        "",
        f"- Registry: {registry.get('title', 'Untitled') if isinstance(registry, dict) else 'Untitled'}",
        f"- Overall gate: {'PASS' if gate['ok'] else 'FAIL'}",
        f"- Entries: {gate['entry_count']}",
        f"- Failed: {gate['failed_count']}",
        "",
        "| Challenge | Domain | Difficulty | Gate |",
        "|---|---|---|---|",
    ]
    for result in gate["results"]:
        entry = entry_by_id.get(result["id"], {})
        lines.append(
            "| "
            f"{result['id']} | "
            f"{entry.get('domain', '')} | "
            f"{entry.get('difficulty', '')} | "
            f"{'PASS' if result['ok'] else 'FAIL'} |"
        )
    lines.extend(["", "## Notes", ""])
    for result in gate["results"]:
        lines.append(f"- `{result['id']}`: {result['description']}")
    lines.append("")
    lines.append(
        "This report checks answer/evidence alignment only; it is not a reproduction rerun "
        "and not a scientific truth certificate."
    )
    lines.append("")
    return "\n".join(lines)


def diagnose_challenge_workspace(
    registry_path: Path,
    challenge_root: Path,
    *,
    repo: Optional[Path] = None,
) -> dict:
    """Run the standard Evidence Foundry challenge workspace health checks."""
    registry = _load_json(registry_path)
    registry_validation = validate_challenge_registry(
        registry,
        repo=repo,
        grade_answers=True,
    )
    discovery_audit = audit_registry_discovery(
        registry,
        challenge_root,
        repo=repo,
    )
    registry_gate = run_challenge_registry(registry, repo=repo)
    ok = (
        registry_validation["ok"]
        and discovery_audit["ok"]
        and registry_gate["ok"]
    )
    return {
        "ok": ok,
        "registry_validation": registry_validation,
        "discovery_audit": discovery_audit,
        "registry_gate": registry_gate,
        "summary": {
            "entries": registry_validation["entry_count"],
            "gated": registry_gate["gated_count"],
            "failed": registry_gate["failed_count"],
            "missing": len(discovery_audit["missing_ids"]),
            "extra": len(discovery_audit["extra_ids"]),
        },
    }


def _task_for_answer(pack: dict, task_id: Any) -> dict | None:
    for task in pack.get("tasks", []):
        if isinstance(task, dict) and task.get("id") == task_id:
            return task
    return None


def grade_challenge_answer(pack: dict, answer: dict) -> dict:
    """Grade one answer manifest against the locked claims in a challenge pack."""
    issues: list[str] = []
    matched_claims = 0

    if not isinstance(answer, dict):
        return {"ok": False, "issues": ["answer must be a JSON object"]}
    if answer.get("schema") != ANSWER_SCHEMA:
        issues.append(f"answer.schema must be {ANSWER_SCHEMA!r}")

    task_id = answer.get("task_id")
    task = _task_for_answer(pack, task_id)
    if task is None:
        issues.append(f"unknown task_id {task_id!r}")
        return {
            "ok": False,
            "issues": issues,
            "task_id": task_id,
            "matched_claims": 0,
            "required_claims": 0,
            "salient_number": [0.0, 0.0],
        }

    expected = {
        claim["id"]: claim
        for claim in task.get("expected_claims", [])
        if isinstance(claim, dict) and _is_nonempty_string(claim.get("id"))
    }
    required_artifacts = set(task.get("required_artifacts", []))

    claims = answer.get("claims")
    if not isinstance(claims, list):
        issues.append("answer.claims must be a list")
        claims = []

    actual: dict[str, dict] = {}
    for claim in claims:
        if not isinstance(claim, dict):
            issues.append("answer.claims entries must be objects")
            continue
        claim_id = claim.get("id")
        if not _is_nonempty_string(claim_id):
            issues.append("answer claim id is required")
            continue
        if claim_id in actual:
            issues.append(f"duplicate claim {claim_id}")
            continue
        verdict = claim.get("verdict")
        if verdict not in ALLOWED_VERDICTS:
            issues.append(f"claim {claim_id} has invalid verdict {verdict!r}")
        actual[claim_id] = claim

    for claim_id in actual:
        if claim_id not in expected:
            issues.append(f"unexpected claim {claim_id}")

    citations = answer.get("citations")
    if not isinstance(citations, dict):
        issues.append("answer.citations must be an object")
        citations = {}

    for claim_id, expected_claim in expected.items():
        claim = actual.get(claim_id)
        if claim is None:
            issues.append(f"missing claim {claim_id}")
            continue
        expected_verdict = expected_claim.get("verdict")
        actual_verdict = claim.get("verdict")
        if actual_verdict == expected_verdict:
            matched_claims += 1
        else:
            issues.append(f"claim {claim_id} expected {expected_verdict}, got {actual_verdict}")

        claim_citations = citations.get(claim_id)
        cited_required = (
            isinstance(claim_citations, list)
            and any(citation in required_artifacts for citation in claim_citations)
        )
        if not cited_required:
            issues.append(f"claim {claim_id} lacks citation to required artifact")

    required_claims = len(expected)
    return {
        "ok": not issues,
        "issues": issues,
        "task_id": task_id,
        "matched_claims": matched_claims,
        "required_claims": required_claims,
        "salient_number": [float(matched_claims), float(required_claims)],
    }


def build_answer_template(
    pack: dict,
    *,
    task_id: str | None = None,
    default_verdict: str = "INCONCLUSIVE",
) -> dict:
    """Create a blank answer manifest for a challenge task."""
    tasks = pack.get("tasks", []) if isinstance(pack, dict) else []
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("challenge pack has no tasks")
    task = _task_for_answer(pack, task_id) if task_id is not None else tasks[0]
    if task is None or not isinstance(task, dict):
        raise ValueError(f"unknown task_id {task_id!r}")
    claims = task.get("expected_claims", [])
    if not isinstance(claims, list) or not claims:
        raise ValueError("challenge task has no expected claims")

    claim_ids = [
        claim["id"]
        for claim in claims
        if isinstance(claim, dict) and _is_nonempty_string(claim.get("id"))
    ]
    return {
        "schema": ANSWER_SCHEMA,
        "task_id": task.get("id"),
        "claims": [
            {"id": claim_id, "verdict": default_verdict}
            for claim_id in claim_ids
        ],
        "citations": {
            claim_id: []
            for claim_id in claim_ids
        },
    }


def repro_challenge_gate(
    pack: dict,
    answer: dict,
    *,
    repo: Optional[Path] = None,
) -> tuple[bool, str]:
    validation = validate_challenge_pack(pack, repo=repo)
    if not validation["ok"]:
        first = "; ".join(validation["issues"][:3])
        return False, f"Evidence Foundry challenge gate failed pack validation: {first}"

    grade = grade_challenge_answer(pack, answer)
    if not grade["ok"]:
        first = "; ".join(grade["issues"][:3])
        return False, f"Evidence Foundry challenge gate failed answer grading: {first}"

    return (
        True,
        "Evidence Foundry challenge gate passed "
        f"(task_id={grade['task_id']}, "
        f"matched_claims={grade['matched_claims']}/{grade['required_claims']}); "
        "this checks answer/evidence alignment, not a reproduction rerun and "
        "not a scientific truth certificate",
    )


def validate_challenge_registry(
    registry: dict,
    *,
    repo: Optional[Path] = None,
    validate_packs: bool = True,
    grade_answers: bool = False,
) -> dict:
    """Validate a curriculum registry of challenge packs."""
    repo_root = _repo_root(repo)
    issues: list[str] = []
    pack_validated_count = 0
    answer_graded_count = 0

    if not isinstance(registry, dict):
        return {"ok": False, "issues": ["challenge registry must be a JSON object"]}

    if registry.get("schema") != REGISTRY_SCHEMA:
        issues.append(f"schema must be {REGISTRY_SCHEMA!r}")
    if not _is_nonempty_string(registry.get("title")):
        issues.append("title is required")

    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        issues.append("entries must be a non-empty list")
        entries = []

    seen_ids: set[str] = set()
    for idx, entry in enumerate(entries):
        prefix = f"entries[{idx}]"
        if not isinstance(entry, dict):
            issues.append(f"{prefix} must be an object")
            continue

        entry_id = entry.get("id")
        if not _is_nonempty_string(entry_id):
            issues.append(f"{prefix}.id is required")
        elif entry_id in seen_ids:
            issues.append(f"{prefix}.id duplicate id {entry_id!r}")
        else:
            seen_ids.add(entry_id)

        pack_path_value = entry.get("pack")
        pack_path: Path | None = None
        if not _is_nonempty_string(pack_path_value):
            issues.append(f"{prefix}.pack is required")
        else:
            pack_path = Path(pack_path_value)
            if pack_path.is_absolute():
                issues.append(f"{prefix}.pack uses absolute local path: {pack_path_value}")

        answer_path_value = entry.get("answer")
        answer_path: Path | None = None
        if answer_path_value is not None:
            if not _is_nonempty_string(answer_path_value):
                issues.append(f"{prefix}.answer must be a non-empty string when present")
            else:
                answer_path = Path(answer_path_value)
                if answer_path.is_absolute():
                    issues.append(f"{prefix}.answer uses absolute local path: {answer_path_value}")

        if not _is_nonempty_string(entry.get("domain")):
            issues.append(f"{prefix}.domain is required")
        difficulty = entry.get("difficulty")
        if difficulty not in ALLOWED_DIFFICULTIES:
            issues.append(f"{prefix}.difficulty has invalid difficulty {difficulty!r}")
        tags = entry.get("tags")
        if not _list_of_strings(tags):
            issues.append(f"{prefix}.tags must be a string list")

        pack: dict | None = None
        if validate_packs and pack_path is not None and not pack_path.is_absolute():
            full_pack_path = _artifact_path(pack_path, repo_root)
            if not full_pack_path.exists():
                issues.append(f"{prefix}.pack does not exist: {pack_path_value}")
            else:
                pack = _load_json(full_pack_path)
                pack_result = validate_challenge_pack(pack, repo=repo_root)
                if pack_result["ok"]:
                    pack_validated_count += 1
                else:
                    first = "; ".join(pack_result["issues"][:3])
                    issues.append(f"{prefix}.pack invalid: {first}")
                if _is_nonempty_string(entry_id) and pack.get("challenge_id") != entry_id:
                    issues.append(
                        f"{prefix}.id {entry_id!r} does not match pack challenge_id "
                        f"{pack.get('challenge_id')!r}"
                    )

        if grade_answers and pack is not None and answer_path is not None and not answer_path.is_absolute():
            full_answer_path = _artifact_path(answer_path, repo_root)
            if not full_answer_path.exists():
                issues.append(f"{prefix}.answer does not exist: {answer_path_value}")
            else:
                answer = _load_json(full_answer_path)
                grade = grade_challenge_answer(pack, answer)
                if grade["ok"]:
                    answer_graded_count += 1
                else:
                    first = "; ".join(grade["issues"][:3])
                    issues.append(f"{prefix}.answer invalid: {first}")

    return {
        "ok": not issues,
        "issues": issues,
        "schema": registry.get("schema"),
        "entry_count": len(entries),
        "pack_validated_count": pack_validated_count,
        "answer_graded_count": answer_graded_count,
    }


def validate_challenge_registry_file(path, *, repo: Optional[Path] = None, **kwargs) -> dict:
    registry = _load_json(path)
    return validate_challenge_registry(registry, repo=repo, **kwargs)


def list_challenge_registry(
    registry: dict,
    *,
    domain: str | None = None,
    tag: str | None = None,
    difficulty: str | None = None,
) -> list[dict]:
    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        return []

    result: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if domain is not None and entry.get("domain") != domain:
            continue
        if difficulty is not None and entry.get("difficulty") != difficulty:
            continue
        tags = entry.get("tags", [])
        if tag is not None and (not isinstance(tags, list) or tag not in tags):
            continue
        result.append(dict(entry))
    return result


def _load_json(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _emit_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m abm_auto.repro_challenge",
        description="Validate and grade MyMoMo Evidence Foundry challenge packs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate a challenge pack")
    validate_parser.add_argument("pack")
    validate_parser.add_argument("--repo", default=None)

    produce_parser = subparsers.add_parser("produce", help="produce a challenge pack from a producer spec")
    produce_parser.add_argument("spec")
    produce_parser.add_argument("--repo", default=None)
    produce_parser.add_argument("--out", required=True)

    answer_template_parser = subparsers.add_parser(
        "answer-template",
        help="write a blank answer manifest for a challenge pack",
    )
    answer_template_parser.add_argument("pack")
    answer_template_parser.add_argument("--task-id", default=None)
    answer_template_parser.add_argument("--out", required=True)

    grade_parser = subparsers.add_parser("grade", help="grade an answer manifest")
    grade_parser.add_argument("pack")
    grade_parser.add_argument("answer")
    grade_parser.add_argument("--repo", default=None)

    gate_parser = subparsers.add_parser("gate", help="validate pack and grade answer")
    gate_parser.add_argument("pack")
    gate_parser.add_argument("answer")
    gate_parser.add_argument("--repo", default=None)

    registry_validate_parser = subparsers.add_parser(
        "registry-validate",
        help="validate a challenge registry and its packs",
    )
    registry_validate_parser.add_argument("registry")
    registry_validate_parser.add_argument("--repo", default=None)
    registry_validate_parser.add_argument("--grade-answers", action="store_true")

    registry_list_parser = subparsers.add_parser(
        "registry-list",
        help="list registered challenges with optional filters",
    )
    registry_list_parser.add_argument("registry")
    registry_list_parser.add_argument("--domain", default=None)
    registry_list_parser.add_argument("--tag", default=None)
    registry_list_parser.add_argument("--difficulty", default=None)

    registry_discover_parser = subparsers.add_parser(
        "registry-discover",
        help="discover a registry from producer specs under a challenge root",
    )
    registry_discover_parser.add_argument("challenge_root")
    registry_discover_parser.add_argument("--repo", default=None)
    registry_discover_parser.add_argument(
        "--title",
        default=EVIDENCE_FOUNDRY_TITLE,
    )

    registry_audit_parser = subparsers.add_parser(
        "registry-audit",
        help="compare a registry against producer-spec discovery",
    )
    registry_audit_parser.add_argument("registry")
    registry_audit_parser.add_argument("challenge_root")
    registry_audit_parser.add_argument("--repo", default=None)

    registry_gate_parser = subparsers.add_parser(
        "registry-gate",
        help="gate every registered challenge answer",
    )
    registry_gate_parser.add_argument("registry")
    registry_gate_parser.add_argument("--repo", default=None)

    registry_report_parser = subparsers.add_parser(
        "registry-report",
        help="write a Markdown report for a challenge registry gate run",
    )
    registry_report_parser.add_argument("registry")
    registry_report_parser.add_argument("--repo", default=None)
    registry_report_parser.add_argument("--out", required=True)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="run registry validation, discovery audit, and registry gate",
    )
    doctor_parser.add_argument("registry")
    doctor_parser.add_argument("challenge_root")
    doctor_parser.add_argument("--repo", default=None)

    args = parser.parse_args(argv)
    repo_value = getattr(args, "repo", None)
    repo = Path(repo_value) if repo_value else None

    if args.command == "validate":
        result = validate_challenge_pack_file(args.pack, repo=repo)
        _emit_json(result)
        return 0 if result["ok"] else 1

    if args.command == "produce":
        spec = _load_json(args.spec)
        spec_result = validate_challenge_producer_spec(spec, repo=repo)
        if not spec_result["ok"]:
            _emit_json(spec_result)
            return 1
        pack = build_challenge_pack_from_producer_spec(spec, repo=repo)
        path = write_challenge_pack(pack, args.out)
        pack_result = validate_challenge_pack(pack, repo=repo)
        _emit_json({
            "ok": pack_result["ok"],
            "issues": pack_result["issues"],
            "path": str(path),
            "challenge_id": pack.get("challenge_id"),
            "artifact_count": pack_result["artifact_count"],
            "expected_claim_count": pack_result["expected_claim_count"],
        })
        return 0 if pack_result["ok"] else 1

    if args.command == "answer-template":
        pack = _load_json(args.pack)
        answer = build_answer_template(pack, task_id=args.task_id)
        path = Path(args.out)
        path.write_text(json.dumps(answer, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _emit_json({"ok": True, "path": str(path), "task_id": answer["task_id"]})
        return 0

    if args.command == "registry-validate":
        result = validate_challenge_registry_file(
            args.registry,
            repo=repo,
            grade_answers=args.grade_answers,
        )
        _emit_json(result)
        return 0 if result["ok"] else 1

    if args.command == "registry-list":
        registry = _load_json(args.registry)
        entries = list_challenge_registry(
            registry,
            domain=args.domain,
            tag=args.tag,
            difficulty=args.difficulty,
        )
        _emit_json({"entries": entries, "count": len(entries)})
        return 0

    if args.command == "registry-discover":
        registry = discover_challenge_registry(
            Path(args.challenge_root),
            repo=repo,
            title=args.title,
        )
        _emit_json(registry)
        return 0

    if args.command == "registry-audit":
        registry = _load_json(args.registry)
        result = audit_registry_discovery(
            registry,
            Path(args.challenge_root),
            repo=repo,
        )
        _emit_json(result)
        return 0 if result["ok"] else 1

    if args.command == "registry-gate":
        registry = _load_json(args.registry)
        result = run_challenge_registry(registry, repo=repo)
        _emit_json(result)
        return 0 if result["ok"] else 1

    if args.command == "registry-report":
        registry = _load_json(args.registry)
        report = render_challenge_registry_report(registry, repo=repo)
        path = Path(args.out)
        path.write_text(report, encoding="utf-8")
        gate = run_challenge_registry(registry, repo=repo)
        _emit_json({"ok": gate["ok"], "path": str(path), "entry_count": gate["entry_count"]})
        return 0 if gate["ok"] else 1

    if args.command == "doctor":
        result = diagnose_challenge_workspace(
            Path(args.registry),
            Path(args.challenge_root),
            repo=repo,
        )
        _emit_json(result)
        return 0 if result["ok"] else 1

    pack = _load_json(args.pack)
    answer = _load_json(args.answer)

    if args.command == "grade":
        result = grade_challenge_answer(pack, answer)
        _emit_json(result)
        return 0 if result["ok"] else 1

    if args.command == "gate":
        ok, desc = repro_challenge_gate(pack, answer, repo=repo)
        _emit_json({"ok": ok, "description": desc})
        return 0 if ok else 1

    parser.error(f"unknown command {args.command!r}")
    return 2


__all__ = [
    "ANSWER_SCHEMA",
    "CHALLENGE_MODE",
    "PRODUCER_SCHEMA",
    "REGISTRY_SCHEMA",
    "SCHEMA",
    "audit_registry_discovery",
    "build_answer_template",
    "build_challenge_pack",
    "build_challenge_pack_from_producer_spec",
    "diagnose_challenge_workspace",
    "discover_challenge_registry",
    "grade_challenge_answer",
    "list_challenge_registry",
    "main",
    "repro_challenge_gate",
    "render_challenge_registry_report",
    "run_challenge_registry",
    "validate_challenge_producer_spec",
    "validate_challenge_producer_spec_file",
    "validate_challenge_pack",
    "validate_challenge_pack_file",
    "validate_challenge_registry",
    "validate_challenge_registry_file",
    "write_challenge_pack",
]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
