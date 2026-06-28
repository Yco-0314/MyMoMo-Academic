"""Manifest-backed observed raster reproducibility helpers.

This module loads local observed-raster manifests and delegates raster I/O,
validation, and calibration to the existing GIS observed-raster bridge. It does
not download remote data, reproject, resample, or import base calibration code.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from abm_auto.gis._observed_raster_bridge import (
    calibrate_observed_raster,
    load_observed_raster,
)

DEFAULT_OBSERVED_RASTER_MANIFEST = Path(
    "data/fixtures/observed-raster/test_manifest.json"
)


def _non_empty_string(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be a finite number")
    return out


def _numeric_mapping(name: str, value: Any) -> dict[str, float]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{name} must be a non-empty dict")
    out: dict[str, float] = {}
    for key, number in value.items():
        clean_key = _non_empty_string(f"{name} keys", key)
        out[clean_key] = _finite_number(clean_key, number)
    return out


def _numeric_grid(value: Any) -> dict[str, list[float]]:
    if not isinstance(value, dict) or not value:
        raise ValueError("param_grid must be a non-empty dict")
    out: dict[str, list[float]] = {}
    for key, values in value.items():
        clean_key = _non_empty_string("param_grid keys", key)
        if not isinstance(values, list) or not values:
            raise ValueError(f"parameter grid for {clean_key} must be non-empty")
        out[clean_key] = [_finite_number(clean_key, number) for number in values]
    return out


def _resolve_raster_path(manifest_path: Path, raster_path: str) -> str:
    raw = Path(raster_path)
    resolved = raw if raw.is_absolute() else manifest_path.parent / raw
    resolved = resolved.resolve()
    if not resolved.exists():
        raise ValueError(f"raster_path does not exist: {resolved}")
    return str(resolved)


def load_observed_raster_manifest(path) -> dict:
    """Load and validate a local observed-raster manifest."""
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raise ValueError("manifest must be a JSON object")

    raster_path = _resolve_raster_path(
        manifest_path,
        _non_empty_string("raster_path", raw.get("raster_path")),
    )
    dataset = _non_empty_string("dataset", raw.get("dataset"))
    source_url = _non_empty_string("source_url", raw.get("source_url"))
    license_text = _non_empty_string("license", raw.get("license"))

    manifest = dict(raw)
    manifest.update(
        {
            "raster_path": raster_path,
            "dataset": dataset,
            "source_url": source_url,
            "license": license_text,
            "threshold": _finite_number("threshold", raw.get("threshold")),
            "param_grid": _numeric_grid(raw.get("param_grid")),
            "expected_best_params": _numeric_mapping(
                "expected_best_params",
                raw.get("expected_best_params"),
            ),
        }
    )
    return manifest


def load_observed_raster_from_manifest(path):
    """Load an ObservedRasterTarget from a validated local manifest."""
    manifest = load_observed_raster_manifest(path)
    source = f"{manifest['dataset']}: {manifest['source_url']}"
    return load_observed_raster(
        manifest["raster_path"],
        source=source,
        dataset=manifest["dataset"],
    )


def _manifest_metadata(manifest: dict) -> dict:
    return {
        "manifest_dataset": manifest["dataset"],
        "manifest_source_url": manifest["source_url"],
        "manifest_license": manifest["license"],
        "manifest_raster_path": manifest["raster_path"],
    }


def calibrate_observed_raster_from_manifest(
    simulator,
    manifest_path,
) -> dict:
    """Run deterministic observed-raster calibration from manifest settings."""
    manifest = load_observed_raster_manifest(manifest_path)
    observed = load_observed_raster(
        manifest["raster_path"],
        source=f"{manifest['dataset']}: {manifest['source_url']}",
        dataset=manifest["dataset"],
    )
    result = calibrate_observed_raster(
        simulator,
        observed,
        manifest["param_grid"],
        threshold=manifest["threshold"],
    )
    result.update(_manifest_metadata(manifest))
    result["manifest_expected_best_params"] = dict(manifest["expected_best_params"])
    return result


def _cluster(top: int, left: int, size: int = 2, shape=(6, 6)):
    import numpy as np

    raster = np.zeros(shape, dtype=float)
    raster[top:top + size, left:left + size] = 1.0
    return raster


def observed_raster_repro_gate(
    manifest_path=DEFAULT_OBSERVED_RASTER_MANIFEST,
) -> tuple[bool, str]:
    """Gate for local manifest-backed observed-raster calibration."""

    def simulator(params: dict[str, float]):
        return _cluster(int(params["row"]), int(params["col"]))

    result = calibrate_observed_raster_from_manifest(simulator, manifest_path)
    expected = result["manifest_expected_best_params"]
    losses = [evaluation["loss"] for evaluation in result["evaluations"]]
    has_improvement = any(loss > result["best_loss"] for loss in losses)

    if result["best_params"] != expected:
        return False, (
            "observed-raster repro pack chose "
            f"{result['best_params']} instead of {expected}"
        )
    if not has_improvement:
        return False, "observed-raster repro pack produced no lower-loss improvement"
    if not result["manifest_source_url"]:
        return False, "observed-raster repro pack lost source provenance"

    return (
        True,
        "observed-raster repro pack selected expected parameters "
        f"(dataset={result['manifest_dataset']}, "
        f"best_loss={result['best_loss']:.6f}); "
        "this is local manifest-backed observed-raster plumbing, "
        "not remote data download, not official GHSL or WorldPop pixels, "
        "and not Bayesian posterior inference",
    )
