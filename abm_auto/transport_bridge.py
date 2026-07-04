"""Transport bridge manifest validation helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA = "abm-auto/transport-bridge-manifest/v1"
ALLOWED_ENGINES = frozenset({"MATSim", "SUMO", "external"})


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_relative_path(value: Any) -> bool:
    return _is_nonempty_string(value) and not Path(value).is_absolute()


def _sorted_values(values: frozenset[str]) -> str:
    return ", ".join(sorted(values))


def _validate_keyed_artifacts(
    artifacts: Any,
    *,
    label: str,
    require_reduction_metric: bool = False,
) -> list[str]:
    issues: list[str] = []
    if not isinstance(artifacts, list):
        return [f"{label} must be a list"]

    seen: set[str] = set()
    for idx, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            issues.append(f"{label}[{idx}] must be an object")
            continue

        key = artifact.get("key")
        if not _is_nonempty_string(key):
            issues.append(f"{label}[{idx}].key must be a non-empty string")
        elif key in seen:
            issues.append(f"duplicate {label[:-1]} key {key}")
        else:
            seen.add(key)

        if not _is_relative_path(artifact.get("path")):
            issues.append(f"{label}[{idx}].path must be relative")

        if require_reduction_metric and not _is_nonempty_string(artifact.get("reduction_metric")):
            issues.append(f"{label}[{idx}].reduction_metric must be a non-empty string")

    return issues


def validate_transport_bridge_manifest(manifest: dict) -> dict:
    """Validate a transport bridge manifest without executing the bridge."""
    if not isinstance(manifest, dict):
        return {"ok": False, "issues": ["manifest must be a JSON object"]}

    issues: list[str] = []
    if manifest.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA}")

    if not _is_nonempty_string(manifest.get("bridge_id")):
        issues.append("bridge_id must be a non-empty string")

    engine = manifest.get("engine")
    if not isinstance(engine, dict):
        issues.append("engine must be an object")
        engine = {}

    if engine.get("name") not in ALLOWED_ENGINES:
        issues.append(f"engine.name must be one of {_sorted_values(ALLOWED_ENGINES)}")
    if not _is_nonempty_string(engine.get("version")):
        issues.append("engine.version must be a non-empty string")
    command = engine.get("command")
    if not isinstance(command, list) or not command or not all(_is_nonempty_string(part) for part in command):
        issues.append("engine.command must be a non-empty list of strings")

    scenario = manifest.get("scenario")
    if not isinstance(scenario, dict):
        issues.append("scenario must be an object")
        scenario = {}
    if not _is_nonempty_string(scenario.get("time_unit")):
        issues.append("scenario.time_unit must be a non-empty string")

    issues.extend(_validate_keyed_artifacts(manifest.get("inputs"), label="inputs"))
    issues.extend(
        _validate_keyed_artifacts(
            manifest.get("outputs"),
            label="outputs",
            require_reduction_metric=True,
        )
    )

    claims = manifest.get("claims")
    if not isinstance(claims, list):
        issues.append("claims must be a list")
        claims = []
    for idx, claim in enumerate(claims):
        if not isinstance(claim, dict):
            issues.append(f"claims[{idx}] must be an object")
            continue
        for field in ("id", "metric", "boundary_note"):
            if not _is_nonempty_string(claim.get(field)):
                issues.append(f"claims[{idx}].{field} must be a non-empty string")

    return {"ok": not issues, "issues": issues}


def load_transport_bridge_manifest(path: Path) -> dict:
    """Load a transport bridge manifest JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def summarize_transport_bridge_manifest(manifest: dict) -> dict:
    """Return a compact reader-facing manifest summary."""
    engine = manifest.get("engine", {}) if isinstance(manifest, dict) else {}
    return {
        "bridge_id": manifest.get("bridge_id") if isinstance(manifest, dict) else None,
        "engine": engine.get("name") if isinstance(engine, dict) else None,
        "inputs": len(manifest.get("inputs", [])) if isinstance(manifest.get("inputs"), list) else 0,
        "outputs": len(manifest.get("outputs", [])) if isinstance(manifest.get("outputs"), list) else 0,
        "claims": len(manifest.get("claims", [])) if isinstance(manifest.get("claims"), list) else 0,
    }


__all__ = [
    "ALLOWED_ENGINES",
    "SCHEMA",
    "load_transport_bridge_manifest",
    "summarize_transport_bridge_manifest",
    "validate_transport_bridge_manifest",
]
