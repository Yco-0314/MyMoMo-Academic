"""Batch gate for MyMoMo Evidence Foundry seed artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from abm_auto.agent_handoff import (
    agent_handoff_gate,
    load_agent_handoff_note,
    validate_agent_handoff_template,
)
from abm_auto.counterfactual_challenge import (
    counterfactual_challenge_gate,
    load_counterfactual_challenge,
)
from abm_auto.evidence_challenge_manifest import (
    evidence_challenge_manifest_gate,
    load_evidence_challenge_manifest,
)
from abm_auto.failure_pack import load_failure_pack, validate_failure_pack
from abm_auto.llm_replay import load_llm_replay_jsonl, validate_llm_replay_events
from abm_auto.mechanism_challenge import (
    load_mechanism_challenge,
    mechanism_challenge_gate,
)
from abm_auto.platform_capabilities import (
    load_platform_capability_registry,
    validate_platform_capability_registry,
)
from abm_auto.repro_challenge import diagnose_challenge_workspace, run_challenge_registry
from abm_auto.social_platform import (
    load_social_platform_scenario,
    social_platform_exposure_gate,
)
from abm_auto.synthetic_population import (
    load_synthetic_population_manifest,
    validate_synthetic_population_manifest,
)
from abm_auto.synthetic_survey_gate import (
    evaluate_synthetic_survey_gate,
    load_synthetic_survey_json,
)
from abm_auto.terrain_bridge import load_terrain_bridge_manifest, terrain_bridge_gate
from abm_auto.transport_bridge import (
    load_transport_bridge_manifest,
    validate_transport_bridge_manifest,
)
from abm_auto.unified_abm_bridge import (
    load_unified_abm_bridge_contract,
    unified_abm_bridge_gate,
)

SCHEMA = "abm-auto/evidence-foundry-batch/v1"
BOUNDARY_NOTE = (
    "Batch gate checks artifact health only; it is not a scientific truth certificate."
)
SUPPORTED_KINDS = frozenset({
    "agent_handoff_note",
    "counterfactual_challenge",
    "evidence_challenge_manifest",
    "failure_pack",
    "llm_agent_replay",
    "mechanism_challenge",
    "platform_capability_registry",
    "repro_challenge_registry",
    "social_platform_environment",
    "synthetic_population_manifest",
    "synthetic_survey_gate",
    "terrain_bridge_manifest",
    "transport_bridge_manifest",
    "unified_abm_bridge_contract",
})
EVIDENCE_FOUNDRY_BATCH_REPORT_TITLE = "# MyMoMo Evidence Foundry Batch Report"
EVIDENCE_FOUNDRY_CURRICULUM_TITLE = "MyMoMo Evidence Foundry Curriculum"
EVIDENCE_FOUNDRY_HANDOFF_HEADING = "## Evidence Foundry Challenge Handoff"
AGENT_HANDOFF_GATE_COMMAND = ".venv/bin/python -m abm_auto.agent_handoff gate"


def _repo_root(repo: Path | None) -> Path:
    return Path.cwd().resolve() if repo is None else Path(repo).resolve()


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sorted_kinds() -> str:
    return ", ".join(sorted(SUPPORTED_KINDS))


def _artifact_path(path_value: Any, repo: Path) -> Path:
    path = Path(str(path_value))
    return path if path.is_absolute() else repo / path


def _read_repo_text(repo: Path, rel_path: str) -> str | None:
    path = repo / rel_path
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _load_repo_json(repo: Path, rel_path: str) -> dict | None:
    path = repo / rel_path
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def _record_check(checks: dict[str, bool], issues: list[str], key: str, ok: bool, issue: str) -> None:
    checks[key] = ok
    if not ok:
        issues.append(issue)


def _uses_evidence_foundry_phase(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("MyMoMo Evidence Foundry")
        and "AutoData" not in value
    )


def _validate_relative_existing_path(
    entry: dict,
    *,
    field: str,
    prefix: str,
    repo: Path,
    issues: list[str],
) -> None:
    value = entry.get(field)
    if not _is_nonempty_string(value) or Path(str(value)).is_absolute():
        issues.append(f"{prefix}.{field} must be a repo-relative path string")
        return
    if not _artifact_path(value, repo).exists():
        issues.append(f"{prefix}.{field} does not exist")


def load_evidence_foundry_batch(path: Path) -> dict:
    """Load an Evidence Foundry batch registry JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_evidence_foundry_batch(batch: dict, *, repo: Path | None = None) -> dict:
    """Validate an Evidence Foundry batch registry and referenced paths."""
    repo_root = _repo_root(repo)
    if not isinstance(batch, dict):
        return {"ok": False, "issues": ["batch must be a JSON object"], "entry_count": 0}

    issues: list[str] = []
    if batch.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA}")
    if not _is_nonempty_string(batch.get("title")):
        issues.append("title must be a non-empty string")
    if not _is_nonempty_string(batch.get("boundary_note")):
        issues.append("boundary_note must be a non-empty string")

    entries = batch.get("entries")
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
            issues.append(f"{prefix}.id must be a non-empty string")
        elif entry_id in seen_ids:
            issues.append(f"duplicate entry id {entry_id}")
        else:
            seen_ids.add(entry_id)
        if not _is_nonempty_string(entry.get("boundary_note")):
            issues.append(f"{prefix}.boundary_note must be a non-empty string")

        kind = entry.get("kind")
        if kind not in SUPPORTED_KINDS:
            issues.append(f"{prefix}.kind must be one of {_sorted_kinds()}")
            continue

        if kind == "synthetic_survey_gate":
            _validate_relative_existing_path(entry, field="observed", prefix=prefix, repo=repo_root, issues=issues)
            _validate_relative_existing_path(entry, field="answer", prefix=prefix, repo=repo_root, issues=issues)
        else:
            _validate_relative_existing_path(entry, field="path", prefix=prefix, repo=repo_root, issues=issues)

    return {"ok": not issues, "issues": issues, "entry_count": len(entries)}


def _entry_path(entry: dict, repo: Path) -> Path:
    return _artifact_path(entry["path"], repo)


def _validation_result_description(kind: str, validation: dict) -> str:
    status = "passed" if validation["ok"] else "failed"
    issue_note = "" if validation["ok"] else f": {validation['issues'][:3]}"
    return f"{kind} validation {status}{issue_note}"


def _capability_classification_summary(registry: dict) -> dict:
    entries = registry.get("entries", []) if isinstance(registry, dict) else []
    groups: dict[tuple[str, str, str], int] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = (
            str(entry.get("domain", "")),
            str(entry.get("disposition", "")),
            str(entry.get("evidence_level", "")),
        )
        groups[key] = groups.get(key, 0) + 1

    return {
        "groups": [
            {
                "domain": domain,
                "disposition": disposition,
                "evidence_level": evidence_level,
                "count": count,
            }
            for (domain, disposition, evidence_level), count in sorted(groups.items())
        ],
    }


def _run_entry(entry: dict, repo: Path) -> dict:
    kind = entry["kind"]
    entry_id = entry["id"]

    if kind == "repro_challenge_registry":
        registry = json.loads(_entry_path(entry, repo).read_text(encoding="utf-8"))
        result = run_challenge_registry(registry, repo=repo)
        desc = (
            f"repro challenge registry gate {'passed' if result['ok'] else 'failed'} "
            f"(entries={result['entry_count']}, failed={result['failed_count']}); "
            "checks answer/evidence alignment only"
        )
        return {"id": entry_id, "kind": kind, "ok": result["ok"], "description": desc}

    if kind == "failure_pack":
        pack = load_failure_pack(_entry_path(entry, repo))
        validation = validate_failure_pack(pack)
        return {
            "id": entry_id,
            "kind": kind,
            "ok": validation["ok"],
            "description": _validation_result_description(kind, validation),
        }

    if kind == "counterfactual_challenge":
        ok, desc = counterfactual_challenge_gate(load_counterfactual_challenge(_entry_path(entry, repo)))
        return {"id": entry_id, "kind": kind, "ok": ok, "description": desc}

    if kind == "mechanism_challenge":
        ok, desc = mechanism_challenge_gate(load_mechanism_challenge(_entry_path(entry, repo)))
        return {"id": entry_id, "kind": kind, "ok": ok, "description": desc}

    if kind == "evidence_challenge_manifest":
        ok, desc = evidence_challenge_manifest_gate(
            load_evidence_challenge_manifest(_entry_path(entry, repo)),
            repo=repo,
        )
        return {"id": entry_id, "kind": kind, "ok": ok, "description": desc}

    if kind == "synthetic_population_manifest":
        manifest = load_synthetic_population_manifest(_entry_path(entry, repo))
        validation = validate_synthetic_population_manifest(manifest)
        return {
            "id": entry_id,
            "kind": kind,
            "ok": validation["ok"],
            "description": _validation_result_description(kind, validation),
        }

    if kind == "llm_agent_replay":
        events = load_llm_replay_jsonl(_entry_path(entry, repo))
        validation = validate_llm_replay_events(events)
        return {
            "id": entry_id,
            "kind": kind,
            "ok": validation["ok"],
            "description": _validation_result_description(kind, validation),
        }

    if kind == "synthetic_survey_gate":
        observed = load_synthetic_survey_json(_artifact_path(entry["observed"], repo))
        answer = load_synthetic_survey_json(_artifact_path(entry["answer"], repo))
        result = evaluate_synthetic_survey_gate(observed, answer)
        metrics = result["metrics"]
        desc = (
            f"synthetic survey gate {'passed' if result['ok'] else 'failed'} "
            f"(verdict={result['verdict']}, compared_rows={metrics['compared_rows']}); "
            "does not validate synthetic people as human substitutes"
        )
        return {"id": entry_id, "kind": kind, "ok": result["ok"], "description": desc}

    if kind == "social_platform_environment":
        ok, desc = social_platform_exposure_gate(load_social_platform_scenario(_entry_path(entry, repo)))
        return {"id": entry_id, "kind": kind, "ok": ok, "description": desc}

    if kind == "transport_bridge_manifest":
        manifest = load_transport_bridge_manifest(_entry_path(entry, repo))
        validation = validate_transport_bridge_manifest(manifest)
        return {
            "id": entry_id,
            "kind": kind,
            "ok": validation["ok"],
            "description": _validation_result_description(kind, validation),
        }

    if kind == "terrain_bridge_manifest":
        ok, desc = terrain_bridge_gate(
            load_terrain_bridge_manifest(_entry_path(entry, repo)),
            repo=repo,
        )
        return {"id": entry_id, "kind": kind, "ok": ok, "description": desc}

    if kind == "unified_abm_bridge_contract":
        ok, desc = unified_abm_bridge_gate(
            load_unified_abm_bridge_contract(_entry_path(entry, repo)),
            repo=repo,
        )
        return {"id": entry_id, "kind": kind, "ok": ok, "description": desc}

    if kind == "platform_capability_registry":
        registry = load_platform_capability_registry(_entry_path(entry, repo))
        validation = validate_platform_capability_registry(registry)
        return {
            "id": entry_id,
            "kind": kind,
            "ok": validation["ok"],
            "classification_summary": _capability_classification_summary(registry),
            "description": (
                f"platform capability registry validation "
                f"{'passed' if validation['ok'] else 'failed'} "
                f"(entries={validation['entry_count']}); "
                "classification health only, not runtime bridge execution"
            ),
        }

    if kind == "agent_handoff_note":
        ok, desc = agent_handoff_gate(load_agent_handoff_note(_entry_path(entry, repo)))
        return {"id": entry_id, "kind": kind, "ok": ok, "description": desc}

    return {"id": entry_id, "kind": kind, "ok": False, "description": f"unsupported kind {kind}"}


def run_evidence_foundry_batch(batch: dict, *, repo: Path | None = None) -> dict:
    """Run all entries in an Evidence Foundry batch registry."""
    repo_root = _repo_root(repo)
    validation = validate_evidence_foundry_batch(batch, repo=repo_root)
    if not validation["ok"]:
        return {
            "ok": False,
            "issues": validation["issues"],
            "entry_count": validation["entry_count"],
            "passed_count": 0,
            "failed_count": validation["entry_count"],
            "results": [],
            "boundary_note": batch.get("boundary_note") if isinstance(batch, dict) else BOUNDARY_NOTE,
        }

    results = [_run_entry(entry, repo_root) for entry in batch["entries"]]
    failed_count = sum(1 for result in results if not result["ok"])
    return {
        "ok": failed_count == 0,
        "issues": [] if failed_count == 0 else [result["description"] for result in results if not result["ok"]],
        "entry_count": len(results),
        "passed_count": len(results) - failed_count,
        "failed_count": failed_count,
        "results": results,
        "boundary_note": batch["boundary_note"],
    }


def evidence_foundry_batch_gate(batch: dict, *, repo: Path | None = None) -> tuple[bool, str]:
    """Return a compact gate tuple for the full Evidence Foundry batch."""
    result = run_evidence_foundry_batch(batch, repo=repo)
    status = "passed" if result["ok"] else "failed"
    desc = (
        f"Evidence Foundry batch gate {status} "
        f"(entries={result['entry_count']}, passed={result['passed_count']}, "
        f"failed={result['failed_count']}); "
        "artifact health only, not a scientific truth certificate"
    )
    return result["ok"], desc


def render_evidence_foundry_batch_report(batch: dict, *, repo: Path | None = None) -> str:
    """Render a Markdown report for an Evidence Foundry batch run."""
    result = run_evidence_foundry_batch(batch, repo=repo)
    title = batch.get("title", "Untitled") if isinstance(batch, dict) else "Untitled"
    lines = [
        "# MyMoMo Evidence Foundry Batch Report",
        "",
        f"- Registry: {title}",
        f"- Overall gate: {'PASS' if result['ok'] else 'FAIL'}",
        f"- Entries: {result['entry_count']}",
        f"- Failed: {result['failed_count']}",
        "",
        "| Entry | Kind | Gate |",
        "|---|---|---|",
    ]
    for entry in result["results"]:
        lines.append(
            f"| {entry['id']} | {entry['kind']} | {'PASS' if entry['ok'] else 'FAIL'} |"
        )

    classification_groups = [
        group
        for entry in result["results"]
        for group in entry.get("classification_summary", {}).get("groups", [])
    ]
    if classification_groups:
        lines.extend([
            "",
            "## Capability Classifications",
            "",
            "| Domain | Disposition | Evidence Level | Count |",
            "|---|---|---|---:|",
        ])
        for group in classification_groups:
            lines.append(
                "| {domain} | {disposition} | {evidence_level} | {count} |".format(
                    **group,
                )
            )

    lines.extend(["", "## Notes", ""])
    if result["results"]:
        for entry in result["results"]:
            lines.append(f"- `{entry['id']}`: {entry['description']}")
    else:
        for issue in result["issues"]:
            lines.append(f"- {issue}")

    lines.extend([
        "",
        "This report checks committed artifact health only; it is not a scientific truth certificate.",
        "",
    ])
    return "\n".join(lines)


def write_evidence_foundry_batch_report(
    batch: dict,
    out: Path,
    *,
    repo: Path | None = None,
) -> Path:
    """Write a Markdown Evidence Foundry batch report."""
    out_path = Path(out)
    out_path.write_text(render_evidence_foundry_batch_report(batch, repo=repo), encoding="utf-8")
    return out_path


def audit_evidence_foundry_batch_report(batch_path: Path, *, repo: Path | None = None) -> dict:
    """Check that the committed batch report exactly matches current rendering."""
    repo_root = _repo_root(repo)
    batch_full_path = _artifact_path(batch_path, repo_root)
    report_path = batch_full_path.with_name("BATCH-REPORT.md")
    if not batch_full_path.exists():
        return {
            "ok": False,
            "line_count": 0,
            "matches_committed": False,
            "issues": ["batch path does not exist"],
        }

    batch = load_evidence_foundry_batch(batch_full_path)
    report_text = render_evidence_foundry_batch_report(batch, repo=repo_root)
    issues: list[str] = []
    if not report_text.strip():
        issues.append("rendered batch report is empty")
    if not report_path.exists():
        issues.append("committed batch report does not exist")
        matches_committed = False
    else:
        matches_committed = report_path.read_text(encoding="utf-8") == report_text
        if not matches_committed:
            issues.append("committed batch report does not match rendered report")

    return {
        "ok": not issues,
        "line_count": len(report_text.splitlines()),
        "matches_committed": matches_committed,
        "issues": issues,
    }


def audit_evidence_foundry_naming(*, repo: Path | None = None) -> dict:
    """Check that user-facing Evidence Foundry seed artifacts use the durable name."""
    repo_root = _repo_root(repo)
    checks: dict[str, bool] = {}
    issues: list[str] = []

    batch_report_path = "docs/reproduce/evidence-foundry/BATCH-REPORT.md"
    batch_report = _read_repo_text(repo_root, batch_report_path)
    _record_check(
        checks,
        issues,
        "batch_report_title",
        bool(batch_report and batch_report.splitlines()[0] == EVIDENCE_FOUNDRY_BATCH_REPORT_TITLE),
        f"{batch_report_path} must start with {EVIDENCE_FOUNDRY_BATCH_REPORT_TITLE!r}",
    )

    registry_path = "docs/reproduce/autodata-challenges/registry.json"
    registry = _load_repo_json(repo_root, registry_path)
    _record_check(
        checks,
        issues,
        "challenge_registry_title",
        bool(registry and registry.get("title") == EVIDENCE_FOUNDRY_CURRICULUM_TITLE),
        f"{registry_path}.title must be {EVIDENCE_FOUNDRY_CURRICULUM_TITLE!r}",
    )

    handoff_protocol_path = "docs/agent-handoff-protocol.md"
    handoff_protocol = _read_repo_text(repo_root, handoff_protocol_path)
    _record_check(
        checks,
        issues,
        "handoff_protocol_heading",
        bool(handoff_protocol and EVIDENCE_FOUNDRY_HANDOFF_HEADING in handoff_protocol),
        f"{handoff_protocol_path} must contain {EVIDENCE_FOUNDRY_HANDOFF_HEADING!r}",
    )
    _record_check(
        checks,
        issues,
        "handoff_protocol_gate_command",
        bool(handoff_protocol and AGENT_HANDOFF_GATE_COMMAND in handoff_protocol),
        f"{handoff_protocol_path} must contain {AGENT_HANDOFF_GATE_COMMAND!r}",
    )

    handoff_template_path = "docs/agent-handoff-template.md"
    handoff_template = _read_repo_text(repo_root, handoff_template_path)
    _record_check(
        checks,
        issues,
        "handoff_template_heading",
        bool(handoff_template and EVIDENCE_FOUNDRY_HANDOFF_HEADING in handoff_template),
        f"{handoff_template_path} must contain {EVIDENCE_FOUNDRY_HANDOFF_HEADING!r}",
    )
    handoff_template_structure = (
        validate_agent_handoff_template(handoff_template)
        if handoff_template is not None
        else {"ok": False, "issues": ["handoff template does not exist"]}
    )
    _record_check(
        checks,
        issues,
        "handoff_template_structure",
        handoff_template_structure["ok"],
        f"{handoff_template_path} must contain every required handoff field",
    )

    claude_bridge_path = "CLAUDE.md"
    claude_bridge = _read_repo_text(repo_root, claude_bridge_path)
    _record_check(
        checks,
        issues,
        "claude_bridge_thin",
        bool(claude_bridge and "intentionally thin" in claude_bridge),
        f"{claude_bridge_path} must state that it is intentionally thin",
    )
    _record_check(
        checks,
        issues,
        "claude_bridge_points_to_agents",
        bool(claude_bridge and "AGENTS.md" in claude_bridge),
        f"{claude_bridge_path} must point Claude Code back to AGENTS.md",
    )
    _record_check(
        checks,
        issues,
        "claude_bridge_points_to_protocol",
        bool(claude_bridge and "docs/agent-handoff-protocol.md" in claude_bridge),
        f"{claude_bridge_path} must point Claude Code to docs/agent-handoff-protocol.md",
    )
    _record_check(
        checks,
        issues,
        "claude_bridge_no_private_cot",
        bool(claude_bridge and "does not require private chain-of-thought disclosure" in claude_bridge),
        f"{claude_bridge_path} must not require private chain-of-thought disclosure",
    )

    mir_challenge_path = "docs/reproduce/autodata-challenges/mir-v0-half-a/challenge-pack.json"
    mir_challenge = _load_repo_json(repo_root, mir_challenge_path)
    mir_challenge_phase = (mir_challenge or {}).get("extra", {}).get("phase")
    _record_check(
        checks,
        issues,
        "mir_challenge_phase",
        _uses_evidence_foundry_phase(mir_challenge_phase),
        f"{mir_challenge_path}.extra.phase must use MyMoMo Evidence Foundry and avoid AutoData",
    )

    mir_producer_path = "docs/reproduce/autodata-challenges/mir-v0-half-a/producer-spec.json"
    mir_producer = _load_repo_json(repo_root, mir_producer_path)
    mir_producer_phase = (mir_producer or {}).get("extra", {}).get("phase")
    _record_check(
        checks,
        issues,
        "mir_producer_phase",
        _uses_evidence_foundry_phase(mir_producer_phase),
        f"{mir_producer_path}.extra.phase must use MyMoMo Evidence Foundry and avoid AutoData",
    )

    return {"ok": not issues, "issues": issues, "checks": checks}


def diagnose_evidence_foundry_workspace(
    batch_path: Path,
    challenge_registry_path: Path,
    challenge_root: Path,
    *,
    repo: Path | None = None,
) -> dict:
    """Run the standard top-level Evidence Foundry workspace health checks."""
    repo_root = _repo_root(repo)
    batch_full_path = _artifact_path(batch_path, repo_root)
    challenge_workspace = diagnose_challenge_workspace(
        challenge_registry_path,
        challenge_root,
        repo=repo_root,
    )
    naming_audit = audit_evidence_foundry_naming(repo=repo_root)

    if not batch_full_path.exists():
        batch_gate = {
            "ok": False,
            "issues": ["batch path does not exist"],
            "entry_count": 0,
            "passed_count": 0,
            "failed_count": 0,
            "results": [],
            "boundary_note": BOUNDARY_NOTE,
        }
        report = {"ok": False, "line_count": 0, "issues": ["batch path does not exist"]}
    else:
        batch = load_evidence_foundry_batch(batch_full_path)
        batch_gate = run_evidence_foundry_batch(batch, repo=repo_root)
        report = audit_evidence_foundry_batch_report(batch_full_path, repo=repo_root)

    ok = challenge_workspace["ok"] and batch_gate["ok"] and report["ok"] and naming_audit["ok"]
    return {
        "ok": ok,
        "challenge_workspace": challenge_workspace,
        "batch_gate": batch_gate,
        "report": report,
        "naming_audit": naming_audit,
        "summary": {
            "batch_entries": batch_gate["entry_count"],
            "batch_failed": batch_gate["failed_count"],
            "challenge_entries": challenge_workspace["summary"]["entries"],
            "challenge_failed": challenge_workspace["summary"]["failed"],
            "report_lines": report["line_count"],
            "naming_issues": len(naming_audit["issues"]),
            "report_matches_committed": report.get("matches_committed", False),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run MyMoMo Evidence Foundry batch gates.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    gate = subparsers.add_parser("gate", help="Run a batch registry and print JSON.")
    gate.add_argument("batch", type=Path)
    gate.add_argument("--repo", type=Path, default=None)
    report = subparsers.add_parser("report", help="Render a batch registry Markdown report.")
    report.add_argument("batch", type=Path)
    report.add_argument("--repo", type=Path, default=None)
    report.add_argument("--out", type=Path, required=True)
    doctor = subparsers.add_parser("doctor", help="Run top-level Evidence Foundry workspace checks.")
    doctor.add_argument("batch", type=Path)
    doctor.add_argument("--challenge-registry", type=Path, required=True)
    doctor.add_argument("--challenge-root", type=Path, required=True)
    doctor.add_argument("--repo", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.command == "gate":
        batch = load_evidence_foundry_batch(args.batch)
        result = run_evidence_foundry_batch(batch, repo=args.repo)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    if args.command == "report":
        batch = load_evidence_foundry_batch(args.batch)
        out = write_evidence_foundry_batch_report(batch, args.out, repo=args.repo)
        print(str(out))
        return 0
    if args.command == "doctor":
        result = diagnose_evidence_foundry_workspace(
            args.batch,
            args.challenge_registry,
            args.challenge_root,
            repo=args.repo,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1

    parser.error(f"unsupported command {args.command}")
    return 2


__all__ = [
    "BOUNDARY_NOTE",
    "SCHEMA",
    "SUPPORTED_KINDS",
    "audit_evidence_foundry_batch_report",
    "audit_evidence_foundry_naming",
    "diagnose_evidence_foundry_workspace",
    "evidence_foundry_batch_gate",
    "load_evidence_foundry_batch",
    "render_evidence_foundry_batch_report",
    "run_evidence_foundry_batch",
    "validate_evidence_foundry_batch",
    "write_evidence_foundry_batch_report",
]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
