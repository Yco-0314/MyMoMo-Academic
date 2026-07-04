"""Evidence Foundry failure-pack helpers."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "abm-auto/failure-pack/v1"
ALLOWED_VERDICTS = frozenset({"BLOCKED", "INCONCLUSIVE", "MISS", "PARTIAL"})


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_is_nonempty_string(item) for item in value)


def _is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def _sorted_values(values: frozenset[str]) -> str:
    return ", ".join(sorted(values))


def build_failure_pack(
    *,
    source_id: str,
    claims: list[dict],
    scope_ceilings: list[str],
    residuals: list[dict],
    boundary_note: str,
) -> dict:
    """Build a failure pack object."""
    return {
        "schema": SCHEMA,
        "source_id": source_id,
        "claims": claims,
        "scope_ceilings": scope_ceilings,
        "residuals": residuals,
        "boundary_note": boundary_note,
    }


def validate_failure_pack(pack: dict) -> dict:
    """Validate an Evidence Foundry failure pack."""
    if not isinstance(pack, dict):
        return {"ok": False, "issues": ["pack must be a JSON object"], "claim_count": 0}

    issues: list[str] = []
    if pack.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA}")
    if not _is_nonempty_string(pack.get("source_id")):
        issues.append("source_id must be a non-empty string")
    if not _is_nonempty_string(pack.get("boundary_note")):
        issues.append("boundary_note must be a non-empty string")
    if not _is_string_list(pack.get("scope_ceilings")):
        issues.append("scope_ceilings must be a non-empty list of strings")

    claims = pack.get("claims")
    if not isinstance(claims, list) or not claims:
        issues.append("claims must be a non-empty list")
        claims = []
    for idx, claim in enumerate(claims):
        if not isinstance(claim, dict):
            issues.append(f"claims[{idx}] must be an object")
            continue
        if not _is_nonempty_string(claim.get("id")):
            issues.append(f"claims[{idx}].id must be a non-empty string")
        if claim.get("verdict") not in ALLOWED_VERDICTS:
            issues.append(
                f"claims[{idx}].verdict must be one of {_sorted_values(ALLOWED_VERDICTS)}"
            )
        if not _is_nonempty_string(claim.get("reason")):
            issues.append(f"claims[{idx}].reason must be a non-empty string")
        if not _is_string_list(claim.get("evidence_refs")):
            issues.append(f"claims[{idx}].evidence_refs must be a non-empty list of strings")

    residuals = pack.get("residuals")
    if not isinstance(residuals, list) or not residuals:
        issues.append("residuals must be a non-empty list")
        residuals = []
    for idx, residual in enumerate(residuals):
        if not isinstance(residual, dict):
            issues.append(f"residuals[{idx}] must be an object")
            continue
        if not _is_nonempty_string(residual.get("metric")):
            issues.append(f"residuals[{idx}].metric must be a non-empty string")
        for field in ("observed", "predicted", "error"):
            if not _is_number(residual.get(field)):
                issues.append(f"residuals[{idx}].{field} must be numeric")

    return {
        "ok": not issues,
        "issues": issues,
        "claim_count": len(claims),
    }


def load_failure_pack(path: Path) -> dict:
    """Load a failure pack JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def summarize_failure_pack(pack: dict) -> dict:
    """Return a compact failure pack summary."""
    claims = pack.get("claims", []) if isinstance(pack, dict) else []
    residuals = pack.get("residuals", []) if isinstance(pack, dict) else []
    scope_ceilings = pack.get("scope_ceilings", []) if isinstance(pack, dict) else []
    verdicts = Counter(
        claim.get("verdict")
        for claim in claims
        if isinstance(claim, dict) and _is_nonempty_string(claim.get("verdict"))
    )
    return {
        "source_id": pack.get("source_id") if isinstance(pack, dict) else None,
        "claims": len(claims) if isinstance(claims, list) else 0,
        "residuals": len(residuals) if isinstance(residuals, list) else 0,
        "scope_ceilings": len(scope_ceilings) if isinstance(scope_ceilings, list) else 0,
        "verdicts": dict(sorted(verdicts.items())),
    }


__all__ = [
    "ALLOWED_VERDICTS",
    "SCHEMA",
    "build_failure_pack",
    "load_failure_pack",
    "summarize_failure_pack",
    "validate_failure_pack",
]
