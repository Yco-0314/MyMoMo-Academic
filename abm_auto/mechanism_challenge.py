"""Evidence Foundry mechanism-signature challenge helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA = "abm-auto/mechanism-challenge/v1"


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_string_list(
    value: Any,
    *,
    field: str,
    item_label: str,
    require_nonempty: bool = True,
    check_duplicates: bool = False,
) -> list[str]:
    issues: list[str] = []
    if not isinstance(value, list) or (require_nonempty and not value):
        issues.append(f"{field} must be a non-empty list of strings")
        return issues

    seen: set[str] = set()
    for item in value:
        if not _is_nonempty_string(item):
            issues.append(f"{field} must be a non-empty list of strings")
            break
        if check_duplicates:
            if item in seen:
                issues.append(f"duplicate {item_label} {item}")
            seen.add(item)
    return issues


def load_mechanism_challenge(path: Path) -> dict:
    """Load a mechanism challenge JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_mechanism_challenge(challenge: dict) -> dict:
    """Validate a declared-signature mechanism challenge."""
    if not isinstance(challenge, dict):
        return {"ok": False, "issues": ["challenge must be a JSON object"]}

    issues: list[str] = []
    if challenge.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA}")
    for field in ("challenge_id", "mechanism_family", "boundary_note"):
        if not _is_nonempty_string(challenge.get(field)):
            issues.append(f"{field} must be a non-empty string")

    issues.extend(
        _validate_string_list(
            challenge.get("required_signatures"),
            field="required_signatures",
            item_label="required signature",
            check_duplicates=True,
        )
    )

    candidate = challenge.get("candidate")
    if not isinstance(candidate, dict):
        issues.append("candidate must be an object")
        candidate = {}
    if not _is_nonempty_string(candidate.get("id")):
        issues.append("candidate.id must be a non-empty string")
    issues.extend(
        _validate_string_list(
            candidate.get("present_signatures"),
            field="candidate.present_signatures",
            item_label="candidate present signature",
            check_duplicates=True,
        )
    )
    issues.extend(
        _validate_string_list(
            candidate.get("evidence_refs"),
            field="candidate.evidence_refs",
            item_label="candidate evidence ref",
        )
    )

    return {"ok": not issues, "issues": issues}


def evaluate_mechanism_challenge(challenge: dict) -> dict:
    """Evaluate whether a candidate declares all required mechanism signatures."""
    validation = validate_mechanism_challenge(challenge)
    if not validation["ok"]:
        return {
            "ok": False,
            "verdict": "MISS",
            "issues": validation["issues"],
            "missing_signatures": [],
            "matched_signatures": [],
            "required_count": 0,
            "present_count": 0,
            "boundary_note": challenge.get("boundary_note") if isinstance(challenge, dict) else "",
        }

    required = challenge["required_signatures"]
    present = challenge["candidate"]["present_signatures"]
    present_set = set(present)
    missing = [signature for signature in required if signature not in present_set]
    matched = [signature for signature in required if signature in present_set]
    verdict = "PASS" if not missing else "MISS"

    return {
        "ok": verdict == "PASS",
        "verdict": verdict,
        "issues": [] if verdict == "PASS" else [f"missing required signature {item}" for item in missing],
        "missing_signatures": missing,
        "matched_signatures": matched,
        "required_count": len(required),
        "present_count": len(present),
        "boundary_note": challenge["boundary_note"],
    }


def mechanism_challenge_gate(challenge: dict) -> tuple[bool, str]:
    """Return a compact gate tuple for mechanism-signature challenge evaluation."""
    result = evaluate_mechanism_challenge(challenge)
    status = "passed" if result["ok"] else "failed"
    desc = (
        f"Mechanism challenge gate {status} "
        f"(verdict={result['verdict']}, matched={len(result['matched_signatures'])}/"
        f"{result['required_count']}); "
        "signature presence is mechanism evidence only, not scientific truth"
    )
    return result["ok"], desc


__all__ = [
    "SCHEMA",
    "evaluate_mechanism_challenge",
    "load_mechanism_challenge",
    "mechanism_challenge_gate",
    "validate_mechanism_challenge",
]
