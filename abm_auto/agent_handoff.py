"""Agent handoff note validation helpers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

REQUIRED_HEADINGS = (
    "# Agent Handoff Note",
    "## Status",
    "## Git",
    "## Changed Files",
    "## Commits",
    "## Commands Run",
    "## Verification",
    "## Evidence Foundry Challenge Handoff",
    "## Remaining Work",
    "## Resume Command",
    "## Risks / Assumptions",
)

REQUIRED_FIELDS = (
    "State",
    "Summary",
    "Branch",
    "Current commit",
    "Working tree",
    "Added",
    "Modified",
    "Deleted",
    "Created",
    "Pending",
    "Command",
    "Result",
    "Targeted tests",
    "Full GIS suite",
    "Engine oracle science",
    "Engine oracle byte check",
    "Base suite",
    "Forbidden base-engine diff",
    "Challenge pack",
    "Answer manifest",
    "Validate result",
    "Grade result",
    "Gate result",
    "Next task",
    "Files likely involved",
    "Next command",
    "Risks",
    "Assumptions",
)

PLACEHOLDER_VALUES = frozenset({
    "fill-me",
    "needs-decision",
    "tbd",
    "todo",
    "unresolved",
})

_FIELD_RE = re.compile(r"^\s*-\s+([^:\n]+):\s*(.*)$")


def load_agent_handoff_note(path: Path) -> str:
    """Load a handoff note or handoff template as UTF-8 text."""
    return Path(path).read_text(encoding="utf-8")


def _found_headings(text: str) -> set[str]:
    return {line.strip() for line in text.splitlines() if line.strip().startswith("#")}


def _field_values(text: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for line in text.splitlines():
        match = _FIELD_RE.match(line)
        if match is None:
            continue
        label = match.group(1).strip()
        value = match.group(2).strip()
        fields.setdefault(label, []).append(value)
    return fields


def validate_agent_handoff_template(text: str) -> dict:
    """Validate that a handoff template contains the required structure."""
    if not isinstance(text, str):
        return {
            "ok": False,
            "issues": ["handoff text must be a string"],
            "heading_count": 0,
            "field_count": 0,
        }

    issues: list[str] = []
    headings = _found_headings(text)
    fields = _field_values(text)

    for heading in REQUIRED_HEADINGS:
        if heading not in headings:
            issues.append(f"missing required heading {heading}")

    for field in REQUIRED_FIELDS:
        if field not in fields:
            issues.append(f"missing required field {field}")

    return {
        "ok": not issues,
        "issues": issues,
        "heading_count": sum(1 for heading in REQUIRED_HEADINGS if heading in headings),
        "field_count": sum(1 for field in REQUIRED_FIELDS if field in fields),
    }


def _is_nonplaceholder_value(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    return bool(normalized) and normalized not in PLACEHOLDER_VALUES


def validate_agent_handoff_note(text: str) -> dict:
    """Validate that a completed handoff note has required fields populated."""
    template_result = validate_agent_handoff_template(text)
    issues = list(template_result["issues"])
    if not isinstance(text, str):
        return template_result

    fields = _field_values(text)
    for field in REQUIRED_FIELDS:
        values = fields.get(field)
        if values is None:
            continue
        if not any(_is_nonplaceholder_value(value) for value in values):
            issues.append(f"field {field} must have a non-placeholder value")

    return {
        "ok": not issues,
        "issues": issues,
        "heading_count": template_result["heading_count"],
        "field_count": template_result["field_count"],
    }


def agent_handoff_gate(text: str) -> tuple[bool, str]:
    """Gate a completed handoff note for structural completeness."""
    result = validate_agent_handoff_note(text)
    ok = result["ok"]
    status = "passed" if ok else "failed"
    return (
        ok,
        f"Agent handoff gate {status} "
        f"(headings={result['heading_count']}/{len(REQUIRED_HEADINGS)}, "
        f"fields={result['field_count']}/{len(REQUIRED_FIELDS)}, "
        f"issues={len(result['issues'])}); checks handoff completeness, not factual truth",
    )


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    """Command-line entrypoint for handoff template and note validation."""
    parser = argparse.ArgumentParser(description="Validate agent handoff notes.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    template = subparsers.add_parser("template", help="Validate handoff template structure.")
    template.add_argument("path", type=Path)

    note = subparsers.add_parser("note", help="Validate a completed handoff note.")
    note.add_argument("path", type=Path)

    gate = subparsers.add_parser("gate", help="Gate a completed handoff note for automation.")
    gate.add_argument("path", type=Path)

    args = parser.parse_args(argv)
    text = load_agent_handoff_note(args.path)

    if args.command == "template":
        result = validate_agent_handoff_template(text)
        _print_json(result)
        return 0 if result["ok"] else 1

    if args.command == "note":
        result = validate_agent_handoff_note(text)
        _print_json(result)
        return 0 if result["ok"] else 1

    if args.command == "gate":
        ok, description = agent_handoff_gate(text)
        validation = validate_agent_handoff_note(text)
        _print_json({
            "ok": ok,
            "description": description,
            "validation": validation,
        })
        return 0 if ok else 1

    parser.error(f"unsupported command {args.command}")


__all__ = [
    "PLACEHOLDER_VALUES",
    "REQUIRED_FIELDS",
    "REQUIRED_HEADINGS",
    "agent_handoff_gate",
    "load_agent_handoff_note",
    "main",
    "validate_agent_handoff_note",
    "validate_agent_handoff_template",
]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
