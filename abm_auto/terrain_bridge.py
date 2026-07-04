"""Terrain bridge manifest helpers.

The terrain bridge records a public DEM/heightfield exchange contract for later
3D and physical-space work. The gate validates metadata, checksum, and boundary
rules only. It does not render scenes, build meshes, run terrain solvers, or
certify real-world terrain accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "abm-auto/terrain-bridge-manifest/v1"
ALLOWED_SOURCE_KINDS = frozenset({"ascii_heightfield", "dem_raster"})
ALLOWED_CONSUMER_DOMAINS = frozenset({
    "evidence",
    "future_3d_renderer",
    "gisabm",
    "physical_process",
    "platform",
})
REQUIRED_BOUNDARY_RULES = frozenset({
    "no_3d_renderer_claim",
    "no_physical_solver_claim",
    "no_real_world_accuracy_claim",
    "vertical_units_declared",
})


def _repo_root(repo: Path | None) -> Path:
    return Path.cwd().resolve() if repo is None else Path(repo).resolve()


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sorted_values(values: frozenset[str]) -> str:
    return ", ".join(sorted(values))


def _artifact_path(path_value: Any, repo: Path) -> Path:
    path = Path(str(path_value))
    return path if path.is_absolute() else repo / path


def _validate_source_path(value: Any, *, repo: Path, issues: list[str]) -> Path | None:
    if not _is_nonempty_string(value):
        issues.append("terrain_source.path must be a repo-relative path string")
        return None
    path = Path(str(value))
    if path.is_absolute():
        issues.append("terrain_source.path must be repo-relative")
        return None
    full_path = _artifact_path(path, repo)
    if not full_path.exists():
        issues.append("terrain_source.path does not exist")
        return None
    return full_path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_boundary_note(note: Any, issues: list[str]) -> None:
    if not _is_nonempty_string(note):
        issues.append("boundary_note must be a non-empty string")
        return
    lower = str(note).lower()
    if "not a 3d renderer" not in lower:
        issues.append("boundary_note must say this is not a 3D renderer")
    if "not a physical simulation certificate" not in lower:
        issues.append("boundary_note must say this is not a physical simulation certificate")


def _grid_shape(value: Any, issues: list[str]) -> tuple[int, int] | None:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
        or value[0] <= 0
        or value[1] <= 0
    ):
        issues.append("coordinate_frame.grid_shape must be [rows, cols] positive integers")
        return None
    return int(value[0]), int(value[1])


def _read_ascii_heightfield(path: Path, issues: list[str]) -> list[list[float]] | None:
    rows: list[list[float]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = [float(value) for value in stripped.split()]
        except ValueError:
            issues.append(f"terrain_source ASCII row {line_no} contains a non-numeric value")
            return None
        if not row:
            issues.append(f"terrain_source ASCII row {line_no} is empty")
            return None
        rows.append(row)

    if not rows:
        issues.append("terrain_source ASCII heightfield is empty")
        return None
    width = len(rows[0])
    for idx, row in enumerate(rows, start=1):
        if len(row) != width:
            issues.append(f"terrain_source ASCII row {idx} has inconsistent column count")
            return None
    return rows


def _ascii_heightfield_shape(path: Path, issues: list[str]) -> tuple[int, int] | None:
    rows = _read_ascii_heightfield(path, issues)
    if rows is None:
        return None
    return len(rows), len(rows[0])


def _read_dem_raster(path: Path, issues: list[str]):
    try:
        import numpy as np
        import rasterio
    except ImportError:
        issues.append("terrain metrics for dem_raster require rasterio")
        return None

    try:
        with rasterio.open(path) as src:
            band = src.read(1, masked=True)
    except Exception as exc:
        issues.append(f"terrain_source DEM raster could not be read: {exc}")
        return None

    array = np.ma.asarray(band, dtype=float)
    if array.ndim != 2:
        issues.append("terrain_source DEM raster band 1 must be two-dimensional")
        return None
    values = np.ma.compressed(array)
    values = values[np.isfinite(values)]
    if values.size == 0:
        issues.append("terrain_source DEM raster has no valid cells")
        return None
    return array


def _masked_values(array):
    import numpy as np

    values = np.ma.compressed(array)
    return values[np.isfinite(values)]


def _max_neighbor_delta_masked(array) -> float:
    import numpy as np

    data = np.ma.filled(np.ma.asarray(array, dtype=float), np.nan)
    deltas: list[float] = []
    if data.shape[1] > 1:
        horizontal = np.abs(data[:, :-1] - data[:, 1:])
        deltas.extend(horizontal[np.isfinite(horizontal)].tolist())
    if data.shape[0] > 1:
        vertical = np.abs(data[:-1, :] - data[1:, :])
        deltas.extend(vertical[np.isfinite(vertical)].tolist())
    return max(deltas) if deltas else 0.0


def load_terrain_bridge_manifest(path: Path) -> dict:
    """Load a terrain bridge manifest JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_terrain_bridge_manifest(
    manifest: dict,
    *,
    repo: Path | None = None,
) -> dict:
    """Validate a terrain bridge manifest without rendering or running solvers."""
    repo_root = _repo_root(repo)
    if not isinstance(manifest, dict):
        return {
            "ok": False,
            "issues": ["manifest must be a JSON object"],
            "manifest_id": None,
            "consumer_count": 0,
        }

    issues: list[str] = []
    if manifest.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA!r}")
    if not _is_nonempty_string(manifest.get("manifest_id")):
        issues.append("manifest_id must be a non-empty string")
    if not _is_nonempty_string(manifest.get("title")):
        issues.append("title must be a non-empty string")
    _validate_boundary_note(manifest.get("boundary_note"), issues)

    source = manifest.get("terrain_source")
    if not isinstance(source, dict):
        issues.append("terrain_source must be an object")
        source = {}
    source_kind = source.get("kind")
    if source_kind not in ALLOWED_SOURCE_KINDS:
        issues.append(
            f"terrain_source.kind must be one of {_sorted_values(ALLOWED_SOURCE_KINDS)}"
        )
    if not _is_nonempty_string(source.get("provenance")):
        issues.append("terrain_source.provenance must be a non-empty string")
    if not isinstance(source.get("synthetic"), bool):
        issues.append("terrain_source.synthetic must be boolean")
    if not _is_nonempty_string(source.get("sha256")):
        issues.append("terrain_source.sha256 must be a non-empty string")

    source_path = _validate_source_path(source.get("path"), repo=repo_root, issues=issues)
    if source_path is not None and _is_nonempty_string(source.get("sha256")):
        actual = _sha256(source_path)
        if actual != source["sha256"]:
            issues.append("terrain_source.sha256 does not match file")

    frame = manifest.get("coordinate_frame")
    if not isinstance(frame, dict):
        issues.append("coordinate_frame must be an object")
        frame = {}
    for field in ("crs", "horizontal_units", "vertical_units", "vertical_datum"):
        if not _is_nonempty_string(frame.get(field)):
            issues.append(f"coordinate_frame.{field} must be a non-empty string")
    declared_shape = _grid_shape(frame.get("grid_shape"), issues)

    if source_kind == "ascii_heightfield" and source_path is not None and declared_shape is not None:
        actual_shape = _ascii_heightfield_shape(source_path, issues)
        if actual_shape is not None and actual_shape != declared_shape:
            issues.append(
                "terrain_source ASCII shape "
                f"{actual_shape[0]}x{actual_shape[1]} does not match declared "
                f"{declared_shape[0]}x{declared_shape[1]}"
            )

    _validate_consumers(manifest.get("consumers"), issues)
    _validate_boundary_rules(manifest.get("boundary_rules"), issues)
    _validate_verification(manifest.get("verification"), issues)

    consumers = manifest.get("consumers") if isinstance(manifest.get("consumers"), list) else []
    return {
        "ok": not issues,
        "issues": issues,
        "manifest_id": manifest.get("manifest_id"),
        "consumer_count": len(consumers),
    }


def _validate_consumers(value: Any, issues: list[str]) -> None:
    if not isinstance(value, list) or not value:
        issues.append("consumers must be a non-empty list")
        return

    seen_ids: set[str] = set()
    for idx, consumer in enumerate(value):
        prefix = f"consumers[{idx}]"
        if not isinstance(consumer, dict):
            issues.append(f"{prefix} must be an object")
            continue
        consumer_id = consumer.get("id")
        if not _is_nonempty_string(consumer_id):
            issues.append(f"{prefix}.id must be a non-empty string")
        elif consumer_id in seen_ids:
            issues.append(f"duplicate consumer id {consumer_id}")
        else:
            seen_ids.add(str(consumer_id))
        domain = consumer.get("domain")
        if domain not in ALLOWED_CONSUMER_DOMAINS:
            issues.append(
                f"{prefix}.domain must be one of {_sorted_values(ALLOWED_CONSUMER_DOMAINS)}"
            )
        if not _is_nonempty_string(consumer.get("role")):
            issues.append(f"{prefix}.role must be a non-empty string")
        if not _is_nonempty_string(consumer.get("boundary_note")):
            issues.append(f"{prefix}.boundary_note must be a non-empty string")


def _validate_boundary_rules(value: Any, issues: list[str]) -> None:
    if not isinstance(value, dict):
        issues.append("boundary_rules must be an object")
        value = {}
    for rule in sorted(REQUIRED_BOUNDARY_RULES):
        if rule not in value:
            issues.append(f"boundary_rules.{rule} is required")
            continue
        if not _is_nonempty_string(value.get(rule)):
            issues.append(f"boundary_rules.{rule} must be a non-empty string")


def _validate_string_list(value: Any, *, prefix: str, issues: list[str]) -> None:
    if not isinstance(value, list) or not value:
        issues.append(f"{prefix} must be a non-empty string list")
        return
    for idx, item in enumerate(value):
        if not _is_nonempty_string(item):
            issues.append(f"{prefix}[{idx}] must be a non-empty string")


def _validate_verification(value: Any, issues: list[str]) -> None:
    if not isinstance(value, dict):
        issues.append("verification must be an object")
        return
    if not _is_nonempty_string(value.get("gate_command")):
        issues.append("verification.gate_command must be a non-empty string")
    if not _is_nonempty_string(value.get("expected_result")):
        issues.append("verification.expected_result must be a non-empty string")
    _validate_string_list(
        value.get("non_claims"),
        prefix="verification.non_claims",
        issues=issues,
    )


def terrain_bridge_gate(
    manifest: dict,
    *,
    repo: Path | None = None,
) -> tuple[bool, str]:
    """Return a compact gate tuple for a terrain bridge manifest."""
    validation = validate_terrain_bridge_manifest(manifest, repo=repo)
    status = "passed" if validation["ok"] else "failed"
    detail = f"consumers={validation['consumer_count']}"
    if not validation["ok"]:
        detail = f"{detail}, issues={validation['issues'][:3]}"
    return (
        validation["ok"],
        f"Terrain bridge manifest gate {status} ({detail}); "
        "not a 3D renderer; not a physical simulation certificate",
    )


def summarize_terrain_bridge_manifest(
    manifest: dict,
    *,
    repo: Path | None = None,
) -> dict:
    """Return deterministic terrain metrics for an ASCII heightfield manifest."""
    repo_root = _repo_root(repo)
    validation = validate_terrain_bridge_manifest(manifest, repo=repo_root)
    source = manifest.get("terrain_source", {}) if isinstance(manifest, dict) else {}
    source_kind = source.get("kind") if isinstance(source, dict) else None

    empty = {
        "ok": False,
        "issues": list(validation["issues"]),
        "manifest_id": validation.get("manifest_id"),
        "source_kind": source_kind,
        "rows": 0,
        "cols": 0,
        "min_elevation": None,
        "max_elevation": None,
        "mean_elevation": None,
        "relief": None,
        "max_neighbor_delta": None,
        "boundary_note": manifest.get("boundary_note") if isinstance(manifest, dict) else "",
    }
    if not validation["ok"]:
        return empty
    source_path = _artifact_path(source["path"], repo_root)
    if source_kind == "ascii_heightfield":
        issues: list[str] = []
        rows = _read_ascii_heightfield(source_path, issues)
        if rows is None:
            empty["issues"].extend(issues)
            return empty

        values = [value for row in rows for value in row]
        min_elevation = min(values)
        max_elevation = max(values)
        return {
            "ok": True,
            "issues": [],
            "manifest_id": manifest.get("manifest_id"),
            "source_kind": source_kind,
            "rows": len(rows),
            "cols": len(rows[0]),
            "min_elevation": min_elevation,
            "max_elevation": max_elevation,
            "mean_elevation": sum(values) / len(values),
            "relief": max_elevation - min_elevation,
            "max_neighbor_delta": _max_neighbor_delta(rows),
            "boundary_note": manifest.get("boundary_note", ""),
        }

    if source_kind == "dem_raster":
        issues = []
        array = _read_dem_raster(source_path, issues)
        if array is None:
            empty["issues"].extend(issues)
            return empty
        declared_rows, declared_cols = manifest["coordinate_frame"]["grid_shape"]
        rows, cols = int(array.shape[0]), int(array.shape[1])
        if (rows, cols) != (declared_rows, declared_cols):
            empty["issues"].append(
                "terrain_source DEM raster shape "
                f"{rows}x{cols} does not match declared {declared_rows}x{declared_cols}"
            )
            return empty
        values = _masked_values(array)
        min_elevation = float(values.min())
        max_elevation = float(values.max())
        return {
            "ok": True,
            "issues": [],
            "manifest_id": manifest.get("manifest_id"),
            "source_kind": source_kind,
            "rows": rows,
            "cols": cols,
            "min_elevation": min_elevation,
            "max_elevation": max_elevation,
            "mean_elevation": float(values.mean()),
            "relief": max_elevation - min_elevation,
            "max_neighbor_delta": _max_neighbor_delta_masked(array),
            "boundary_note": manifest.get("boundary_note", ""),
        }

    empty["issues"].append("terrain metrics supports ascii_heightfield or dem_raster only")
    return empty


def _max_neighbor_delta(rows: list[list[float]]) -> float:
    deltas: list[float] = []
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            if c + 1 < len(row):
                deltas.append(abs(value - row[c + 1]))
            if r + 1 < len(rows):
                deltas.append(abs(value - rows[r + 1][c]))
    return max(deltas) if deltas else 0.0


def terrain_metrics_gate(
    manifest: dict,
    *,
    repo: Path | None = None,
) -> tuple[bool, str]:
    """Gate that proves a terrain bridge manifest can be consumed as metrics."""
    summary = summarize_terrain_bridge_manifest(manifest, repo=repo)
    issues = list(summary["issues"])
    if summary["ok"]:
        if float(summary["relief"]) <= 0.0:
            issues.append("terrain relief must be positive")
        if float(summary["max_neighbor_delta"]) <= 0.0:
            issues.append("terrain max_neighbor_delta must be positive")

    ok = summary["ok"] and not issues
    status = "passed" if ok else "failed"
    detail = (
        f"rows={summary['rows']}, cols={summary['cols']}, "
        f"relief={summary['relief']}, max_neighbor_delta={summary['max_neighbor_delta']}"
    )
    if not ok:
        detail = f"{detail}, issues={issues[:3]}"
    return (
        ok,
        f"Terrain metrics gate {status} ({detail}); "
        "not a 3D renderer; not a physical simulation certificate",
    )


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    gate_parser = subparsers.add_parser("gate", help="validate a terrain bridge manifest")
    gate_parser.add_argument("path")
    gate_parser.add_argument("--repo", default=None)
    args = parser.parse_args(argv)

    if args.command == "gate":
        manifest = load_terrain_bridge_manifest(Path(args.path))
        repo = Path(args.repo) if args.repo is not None else None
        validation = validate_terrain_bridge_manifest(manifest, repo=repo)
        ok, message = terrain_bridge_gate(manifest, repo=repo)
        payload = dict(validation)
        payload["message"] = message
        print(json.dumps(payload, sort_keys=True))
        return 0 if ok else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))


__all__ = [
    "ALLOWED_CONSUMER_DOMAINS",
    "ALLOWED_SOURCE_KINDS",
    "REQUIRED_BOUNDARY_RULES",
    "SCHEMA",
    "load_terrain_bridge_manifest",
    "terrain_bridge_gate",
    "terrain_metrics_gate",
    "summarize_terrain_bridge_manifest",
    "validate_terrain_bridge_manifest",
]
