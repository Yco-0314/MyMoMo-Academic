"""Platform capability disposition registry helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA = "abm-auto/platform-capability-registry/v1"
ALLOWED_DOMAINS = frozenset({
    "closed_extension",
    "evidence",
    "gama",
    "gis",
    "llm_society",
    "netlogo",
    "platform",
    "transport",
})
ALLOWED_DISPOSITIONS = frozenset({
    "audit_baseline",
    "bridge",
    "native",
    "out_of_scope",
})
ALLOWED_EVIDENCE_LEVELS = frozenset({f"E{i}" for i in range(7)})


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sorted_values(values: frozenset[str]) -> str:
    return ", ".join(sorted(values))


def validate_platform_capability_registry(registry: dict) -> dict:
    """Validate a platform capability disposition registry."""
    if not isinstance(registry, dict):
        return {
            "ok": False,
            "issues": ["registry must be a JSON object"],
            "entry_count": 0,
        }

    issues: list[str] = []
    if registry.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA}")

    entries = registry.get("entries")
    if not isinstance(entries, list):
        issues.append("entries must be a list")
        entries = []

    seen_keys: set[str] = set()
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            issues.append(f"entries[{idx}] must be an object")
            continue

        key = entry.get("key")
        if not _is_nonempty_string(key):
            issues.append(f"entries[{idx}].key must be a non-empty string")
        elif key in seen_keys:
            issues.append(f"duplicate capability key {key}")
        else:
            seen_keys.add(key)

        domain = entry.get("domain")
        if domain not in ALLOWED_DOMAINS:
            issues.append(
                f"entries[{idx}].domain must be one of {_sorted_values(ALLOWED_DOMAINS)}"
            )

        disposition = entry.get("disposition")
        if disposition not in ALLOWED_DISPOSITIONS:
            issues.append(
                "entries[{idx}].disposition must be one of {values}".format(
                    idx=idx,
                    values=_sorted_values(ALLOWED_DISPOSITIONS),
                )
            )

        if entry.get("evidence_level") not in ALLOWED_EVIDENCE_LEVELS:
            issues.append(f"entries[{idx}].evidence_level must be E0-E6")

        for field in ("concept", "source", "next_action", "boundary_note"):
            if not _is_nonempty_string(entry.get(field)):
                issues.append(f"entries[{idx}].{field} must be a non-empty string")

    return {
        "ok": not issues,
        "issues": issues,
        "entry_count": len(entries),
    }


def load_platform_capability_registry(path: Path) -> dict:
    """Load a platform capability registry JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def list_platform_capabilities(
    registry: dict,
    *,
    domain: str | None = None,
    disposition: str | None = None,
    evidence_level: str | None = None,
) -> list[dict]:
    """Return registry entries matching optional filters, preserving order."""
    entries = registry.get("entries", []) if isinstance(registry, dict) else []
    if not isinstance(entries, list):
        return []

    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if domain is not None and entry.get("domain") != domain:
            continue
        if disposition is not None and entry.get("disposition") != disposition:
            continue
        if evidence_level is not None and entry.get("evidence_level") != evidence_level:
            continue
        result.append(entry)
    return result


__all__ = [
    "ALLOWED_DISPOSITIONS",
    "ALLOWED_DOMAINS",
    "ALLOWED_EVIDENCE_LEVELS",
    "SCHEMA",
    "list_platform_capabilities",
    "load_platform_capability_registry",
    "validate_platform_capability_registry",
]
