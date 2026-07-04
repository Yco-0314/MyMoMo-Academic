"""Synthetic population provenance manifest helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA = "abm-auto/synthetic-population-manifest/v1"


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_string(container: dict, field: str, label: str, issues: list[str]) -> None:
    if not _is_nonempty_string(container.get(field)):
        issues.append(f"{label}.{field} must be a non-empty string")


def _require_nonempty_string_list(value: Any, label: str, issues: list[str]) -> None:
    if not isinstance(value, list) or not value or not all(_is_nonempty_string(item) for item in value):
        issues.append(f"{label} must be a non-empty list of strings")


def validate_synthetic_population_manifest(manifest: dict) -> dict:
    """Validate a synthetic population provenance manifest."""
    if not isinstance(manifest, dict):
        return {"ok": False, "issues": ["manifest must be a JSON object"]}

    issues: list[str] = []
    if manifest.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA}")
    if not _is_nonempty_string(manifest.get("population_id")):
        issues.append("population_id must be a non-empty string")
    if not _is_nonempty_string(manifest.get("boundary_note")):
        issues.append("boundary_note must be a non-empty string")

    frame = manifest.get("frame")
    if not isinstance(frame, dict):
        issues.append("frame must be an object")
        frame = {}
    for field in ("source", "geography", "time_scope", "unit"):
        _require_string(frame, field, "frame", issues)

    construction = manifest.get("construction")
    if not isinstance(construction, dict):
        issues.append("construction must be an object")
        construction = {}
    _require_string(construction, "method", "construction", issues)
    _require_nonempty_string_list(
        construction.get("variables"),
        "construction.variables",
        issues,
    )
    if construction.get("direct_person_identifiers") is True:
        issues.append("construction.direct_person_identifiers must not be true")

    weighting = manifest.get("weighting")
    if not isinstance(weighting, dict):
        issues.append("weighting must be an object")
        weighting = {}
    _require_string(weighting, "scheme", "weighting", issues)

    validation = manifest.get("validation")
    if not isinstance(validation, dict):
        issues.append("validation must be an object")
        validation = {}
    _require_string(validation, "target", "validation", issues)
    _require_nonempty_string_list(validation.get("metrics"), "validation.metrics", issues)

    _require_nonempty_string_list(
        manifest.get("allowed_claims"),
        "allowed_claims",
        issues,
    )

    return {"ok": not issues, "issues": issues}


def load_synthetic_population_manifest(path: Path) -> dict:
    """Load a synthetic population manifest JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def summarize_synthetic_population_manifest(manifest: dict) -> dict:
    """Return a compact reader-facing synthetic population summary."""
    frame = manifest.get("frame", {}) if isinstance(manifest, dict) else {}
    validation = manifest.get("validation", {}) if isinstance(manifest, dict) else {}
    allowed_claims = manifest.get("allowed_claims", []) if isinstance(manifest, dict) else []
    metrics = validation.get("metrics", []) if isinstance(validation, dict) else []
    return {
        "population_id": manifest.get("population_id") if isinstance(manifest, dict) else None,
        "source": frame.get("source") if isinstance(frame, dict) else None,
        "geography": frame.get("geography") if isinstance(frame, dict) else None,
        "time_scope": frame.get("time_scope") if isinstance(frame, dict) else None,
        "allowed_claims": len(allowed_claims) if isinstance(allowed_claims, list) else 0,
        "validation_metrics": len(metrics) if isinstance(metrics, list) else 0,
    }


__all__ = [
    "SCHEMA",
    "load_synthetic_population_manifest",
    "summarize_synthetic_population_manifest",
    "validate_synthetic_population_manifest",
]
