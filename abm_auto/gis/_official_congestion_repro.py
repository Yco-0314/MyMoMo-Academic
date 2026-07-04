"""Manifest-backed repro pack for official dynamic congestion validation.

This module wraps the official dynamic congestion validation smoke in a small
manifest contract. It fixes run parameters, expected diagnostics, and boundary
text so reviewers can rerun the same bounded Seattle SDOT evidence without
trusting an ad hoc function call.
"""
from __future__ import annotations

from datetime import date
import json
import math
from numbers import Integral
from pathlib import Path
from typing import Any

from abm_auto.gis._official_congestion_validation import (
    official_dynamic_congestion_validation_report,
)


OFFICIAL_DYNAMIC_CONGESTION_REPRO_SCHEMA = (
    "abm-auto/official-dynamic-congestion-validation-repro/v1"
)
SEATTLE_SDOT_2023_DYNAMIC_CONGESTION_REPRO_MANIFEST = Path(
    "data/fixtures/official-traffic-counts/"
    "seattle-sdot-2023-dynamic-congestion-repro/manifest.json"
)


def _non_empty_string(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _schema(value: Any) -> str:
    if value != OFFICIAL_DYNAMIC_CONGESTION_REPRO_SCHEMA:
        raise ValueError(f"schema must be {OFFICIAL_DYNAMIC_CONGESTION_REPRO_SCHEMA}")
    return OFFICIAL_DYNAMIC_CONGESTION_REPRO_SCHEMA


def _iso_date(name: str, value: Any) -> str:
    value = _non_empty_string(name, value)
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise ValueError(f"{name} must be an ISO date")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO date") from exc
    return value


def _resolve_required_path(manifest_path: Path, field: str, value: Any) -> str:
    raw = Path(_non_empty_string(field, value))
    resolved = raw if raw.is_absolute() else manifest_path.parent / raw
    resolved = resolved.resolve()
    if not resolved.exists():
        raise ValueError(f"{field} does not exist: {resolved}")
    return str(resolved)


def _positive_integer(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be a finite number")
    return out


def _non_negative_finite_number(name: str, value: Any) -> float:
    out = _finite_number(name, value)
    if out < 0:
        raise ValueError(f"{name} must be a non-negative finite number")
    return out


def _positive_finite_number(name: str, value: Any) -> float:
    out = _finite_number(name, value)
    if out <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return out


def _coverage(name: str, value: Any) -> float:
    out = _finite_number(name, value)
    if out < 0 or out > 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return out


def _bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def _run(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("run must be an object")
    return {
        "agents_per_edge": _positive_integer(
            "agents_per_edge",
            raw.get("agents_per_edge"),
        ),
        "comparison_agents_per_edge": _positive_integer(
            "comparison_agents_per_edge",
            raw.get("comparison_agents_per_edge"),
        ),
        "n_steps": _positive_integer("n_steps", raw.get("n_steps")),
        "speed_m_per_tick": _positive_finite_number(
            "speed_m_per_tick",
            raw.get("speed_m_per_tick"),
        ),
        "congestion_alpha": _non_negative_finite_number(
            "congestion_alpha",
            raw.get("congestion_alpha"),
        ),
        "reroute": _bool("reroute", raw.get("reroute")),
    }


def _expected(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("expected must be an object")
    return {
        "expected_n_edges": _positive_integer(
            "expected_n_edges",
            raw.get("expected_n_edges"),
        ),
        "expected_min_coverage": _coverage(
            "expected_min_coverage",
            raw.get("expected_min_coverage"),
        ),
        "expected_low_simulated_total": _non_negative_finite_number(
            "expected_low_simulated_total",
            raw.get("expected_low_simulated_total"),
        ),
        "expected_high_simulated_total": _non_negative_finite_number(
            "expected_high_simulated_total",
            raw.get("expected_high_simulated_total"),
        ),
        "expected_worst_edge_street": _non_empty_string(
            "expected_worst_edge_street",
            raw.get("expected_worst_edge_street"),
        ),
        "expected_worst_edge_objectid": _positive_integer(
            "expected_worst_edge_objectid",
            raw.get("expected_worst_edge_objectid"),
        ),
        "expected_min_loss_delta": _positive_finite_number(
            "expected_min_loss_delta",
            raw.get("expected_min_loss_delta"),
        ),
    }


def load_official_dynamic_congestion_repro_manifest(path) -> dict:
    """Load and validate an official dynamic congestion repro manifest."""
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raise ValueError("manifest must be a JSON object")

    manifest = dict(raw)
    manifest.update(
        {
            "schema": _schema(raw.get("schema")),
            "dataset": _non_empty_string("dataset", raw.get("dataset")),
            "source_url": _non_empty_string("source_url", raw.get("source_url")),
            "source_agency": _non_empty_string(
                "source_agency",
                raw.get("source_agency"),
            ),
            "license": _non_empty_string("license", raw.get("license")),
            "downloaded_at": _iso_date("downloaded_at", raw.get("downloaded_at")),
            "centerline_match_manifest_path": _resolve_required_path(
                manifest_path,
                "centerline_match_manifest_path",
                raw.get("centerline_match_manifest_path"),
            ),
            "run": _run(raw.get("run")),
            "expected": _expected(raw.get("expected")),
            "boundary_note": _non_empty_string(
                "boundary_note",
                raw.get("boundary_note"),
            ),
        }
    )
    return manifest


def _run_validation(manifest: dict, agents_per_edge: int) -> dict:
    run = manifest["run"]
    return official_dynamic_congestion_validation_report(
        manifest["centerline_match_manifest_path"],
        agents_per_edge=agents_per_edge,
        n_steps=run["n_steps"],
        speed_m_per_tick=run["speed_m_per_tick"],
        congestion_alpha=run["congestion_alpha"],
        reroute=run["reroute"],
    )


def _close_enough(actual: float, expected: float) -> bool:
    return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-9)


def _summary(low_report: dict, high_report: dict) -> dict:
    return {
        "n_edges": low_report["observed_provenance"]["n_edges"],
        "low_simulated_total": low_report["simulated_total"],
        "high_simulated_total": high_report["simulated_total"],
        "low_loss": low_report["loss"],
        "high_loss": high_report["loss"],
        "loss_delta": abs(low_report["loss"] - high_report["loss"]),
        "coverage": low_report["metrics"]["coverage"],
        "comparison_coverage": high_report["metrics"]["coverage"],
        "worst_edge_street": low_report["worst_edge"]["street"],
        "worst_edge_objectid": low_report["worst_edge"]["objectid"],
        "max_absolute_error": low_report["worst_edge"]["absolute_error"],
    }


def _failure_report(manifest: dict, reason: str, low_report=None, high_report=None):
    return {
        "ok": False,
        "reason": reason,
        "manifest": manifest,
        "dataset": manifest["dataset"],
        "source_url": manifest["source_url"],
        "source_agency": manifest["source_agency"],
        "license": manifest["license"],
        "downloaded_at": manifest["downloaded_at"],
        "run": manifest["run"],
        "expected": manifest["expected"],
        "summary": None,
        "low_report": low_report,
        "high_report": high_report,
        "boundary_note": manifest["boundary_note"],
    }


def official_dynamic_congestion_repro_report(
    manifest_path=SEATTLE_SDOT_2023_DYNAMIC_CONGESTION_REPRO_MANIFEST,
) -> dict:
    """Run the manifest-backed official dynamic congestion repro pack."""
    manifest = load_official_dynamic_congestion_repro_manifest(manifest_path)
    run = manifest["run"]
    expected = manifest["expected"]
    low_report = _run_validation(manifest, run["agents_per_edge"])
    if not low_report["ok"]:
        return _failure_report(manifest, low_report["reason"], low_report)
    high_report = _run_validation(manifest, run["comparison_agents_per_edge"])
    if not high_report["ok"]:
        return _failure_report(manifest, high_report["reason"], low_report, high_report)

    summary = _summary(low_report, high_report)
    if summary["n_edges"] != expected["expected_n_edges"]:
        return _failure_report(
            manifest,
            "observed edge count did not match expected_n_edges",
            low_report,
            high_report,
        )
    if summary["coverage"] < expected["expected_min_coverage"]:
        return _failure_report(
            manifest,
            "coverage below expected_min_coverage",
            low_report,
            high_report,
        )
    if summary["comparison_coverage"] < expected["expected_min_coverage"]:
        return _failure_report(
            manifest,
            "comparison coverage below expected_min_coverage",
            low_report,
            high_report,
        )
    if not _close_enough(
        summary["low_simulated_total"],
        expected["expected_low_simulated_total"],
    ):
        return _failure_report(
            manifest,
            "low simulated total did not match expected_low_simulated_total",
            low_report,
            high_report,
        )
    if not _close_enough(
        summary["high_simulated_total"],
        expected["expected_high_simulated_total"],
    ):
        return _failure_report(
            manifest,
            "high simulated total did not match expected_high_simulated_total",
            low_report,
            high_report,
        )
    if summary["loss_delta"] < expected["expected_min_loss_delta"]:
        return _failure_report(
            manifest,
            "loss delta below expected_min_loss_delta",
            low_report,
            high_report,
        )
    if summary["worst_edge_street"] != expected["expected_worst_edge_street"]:
        return _failure_report(
            manifest,
            "worst edge street did not match expected_worst_edge_street",
            low_report,
            high_report,
        )
    if summary["worst_edge_objectid"] != expected["expected_worst_edge_objectid"]:
        return _failure_report(
            manifest,
            "worst edge objectid did not match expected_worst_edge_objectid",
            low_report,
            high_report,
        )

    return {
        "ok": True,
        "reason": "",
        "manifest": manifest,
        "dataset": manifest["dataset"],
        "source_url": manifest["source_url"],
        "source_agency": manifest["source_agency"],
        "license": manifest["license"],
        "downloaded_at": manifest["downloaded_at"],
        "run": run,
        "expected": expected,
        "summary": summary,
        "low_report": low_report,
        "high_report": high_report,
        "boundary_note": manifest["boundary_note"],
    }


def official_dynamic_congestion_repro_gate(
    manifest_path=SEATTLE_SDOT_2023_DYNAMIC_CONGESTION_REPRO_MANIFEST,
) -> tuple[bool, str]:
    """Gate for the manifest-backed official dynamic congestion repro pack."""
    report = official_dynamic_congestion_repro_report(manifest_path)
    if not report["ok"]:
        return False, report["reason"]

    summary = report["summary"]
    return (
        True,
        "official dynamic congestion repro pack passed "
        f"(dataset={report['dataset']}, "
        f"n_edges={summary['n_edges']}, "
        f"low_total={summary['low_simulated_total']:.1f}, "
        f"high_total={summary['high_simulated_total']:.1f}, "
        f"loss_delta={summary['loss_delta']:.6f}, "
        f"worst_edge={summary['worst_edge_street']}/"
        f"{summary['worst_edge_objectid']}); "
        f"{report['boundary_note']}",
    )


__all__ = [
    "OFFICIAL_DYNAMIC_CONGESTION_REPRO_SCHEMA",
    "SEATTLE_SDOT_2023_DYNAMIC_CONGESTION_REPRO_MANIFEST",
    "load_official_dynamic_congestion_repro_manifest",
    "official_dynamic_congestion_repro_gate",
    "official_dynamic_congestion_repro_report",
]
