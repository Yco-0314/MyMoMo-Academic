"""Manifest-backed repro pack for official dynamic incident validation.

This module wraps the official dynamic incident event-effect smoke in a small
manifest contract. It fixes run parameters, expected diagnostics, and boundary
text so reviewers can rerun the same bounded event-effect evidence without
trusting an ad hoc function call.
"""
from __future__ import annotations

from datetime import date
import json
import math
from numbers import Integral
from pathlib import Path
from typing import Any

from abm_auto.gis._official_incident_validation import (
    official_dynamic_incident_event_effect_report,
)


OFFICIAL_DYNAMIC_INCIDENT_REPRO_SCHEMA = (
    "abm-auto/official-dynamic-incident-event-effect-repro/v1"
)
OFFICIAL_DYNAMIC_INCIDENT_REPRO_MANIFEST = Path(
    "data/fixtures/official-incident-events/"
    "official-dynamic-incident-repro/manifest.json"
)


def _non_empty_string(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _schema(value: Any) -> str:
    if value != OFFICIAL_DYNAMIC_INCIDENT_REPRO_SCHEMA:
        raise ValueError(f"schema must be {OFFICIAL_DYNAMIC_INCIDENT_REPRO_SCHEMA}")
    return OFFICIAL_DYNAMIC_INCIDENT_REPRO_SCHEMA


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


def _positive_finite_number(name: str, value: Any) -> float:
    out = _finite_number(name, value)
    if out <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return out


def _bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def _closed_steps(value: Any) -> list[int]:
    if not isinstance(value, list) or not value:
        raise ValueError(
            "expected_incident_steps_with_closed_edges must be a non-empty "
            "list of non-negative integers"
        )
    out = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, Integral) or item < 0:
            raise ValueError(
                "expected_incident_steps_with_closed_edges must be a non-empty "
                "list of non-negative integers"
            )
        out.append(int(item))
    return out


def _run(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("run must be an object")
    return {
        "n_steps": _positive_integer("n_steps", raw.get("n_steps")),
        "speed_m_per_tick": _positive_finite_number(
            "speed_m_per_tick",
            raw.get("speed_m_per_tick"),
        ),
        "reroute": _bool("reroute", raw.get("reroute")),
    }


def _expected(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("expected must be an object")
    return {
        "expected_n_matched_incidents": _positive_integer(
            "expected_n_matched_incidents",
            raw.get("expected_n_matched_incidents"),
        ),
        "expected_arrival_delay": _finite_number(
            "expected_arrival_delay",
            raw.get("expected_arrival_delay"),
        ),
        "expected_waiting_delta": _finite_number(
            "expected_waiting_delta",
            raw.get("expected_waiting_delta"),
        ),
        "expected_incident_steps_with_closed_edges": _closed_steps(
            raw.get("expected_incident_steps_with_closed_edges")
        ),
        "expected_max_closed_edges": _positive_integer(
            "expected_max_closed_edges",
            raw.get("expected_max_closed_edges"),
        ),
        "expected_changed": _bool("expected_changed", raw.get("expected_changed")),
    }


def load_official_dynamic_incident_repro_manifest(path) -> dict:
    """Load and validate an official dynamic incident repro manifest."""
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
            "incident_manifest_path": _resolve_required_path(
                manifest_path,
                "incident_manifest_path",
                raw.get("incident_manifest_path"),
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


def _run_smoke(manifest: dict) -> dict:
    run = manifest["run"]
    return official_dynamic_incident_event_effect_report(
        manifest["incident_manifest_path"],
        n_steps=run["n_steps"],
        speed_m_per_tick=run["speed_m_per_tick"],
        reroute=run["reroute"],
    )


def _summary(smoke_report: dict) -> dict:
    effect = smoke_report["effect"]
    return {
        "n_matched_incidents": smoke_report["n_matched_incidents"],
        "arrival_delay": effect["arrival_delay"],
        "waiting_delta": effect["waiting_delta"],
        "incident_steps_with_closed_edges": effect[
            "incident_steps_with_closed_edges"
        ],
        "max_closed_edges": effect["max_closed_edges"],
        "changed": effect["changed"],
        "baseline_mean_arrival_t": effect["baseline_mean_arrival_t"],
        "incident_mean_arrival_t": effect["incident_mean_arrival_t"],
        "baseline_total_waiting": effect["baseline_total_waiting"],
        "incident_total_waiting": effect["incident_total_waiting"],
    }


def _close_enough(actual: float, expected: float) -> bool:
    return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-9)


def _failure_report(manifest: dict, reason: str, smoke_report=None):
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
        "smoke_report": smoke_report,
        "boundary_note": manifest["boundary_note"],
    }


def official_dynamic_incident_repro_report(
    manifest_path=OFFICIAL_DYNAMIC_INCIDENT_REPRO_MANIFEST,
) -> dict:
    """Run the manifest-backed official dynamic incident repro pack."""
    manifest = load_official_dynamic_incident_repro_manifest(manifest_path)
    expected = manifest["expected"]
    smoke_report = _run_smoke(manifest)
    if not smoke_report["ok"]:
        return _failure_report(manifest, smoke_report["reason"], smoke_report)

    summary = _summary(smoke_report)
    if summary["n_matched_incidents"] != expected["expected_n_matched_incidents"]:
        return _failure_report(
            manifest,
            "matched incident count did not match expected_n_matched_incidents",
            smoke_report,
        )
    if not _close_enough(
        summary["arrival_delay"],
        expected["expected_arrival_delay"],
    ):
        return _failure_report(
            manifest,
            "arrival delay did not match expected_arrival_delay",
            smoke_report,
        )
    if not _close_enough(
        summary["waiting_delta"],
        expected["expected_waiting_delta"],
    ):
        return _failure_report(
            manifest,
            "waiting delta did not match expected_waiting_delta",
            smoke_report,
        )
    if (
        summary["incident_steps_with_closed_edges"]
        != expected["expected_incident_steps_with_closed_edges"]
    ):
        return _failure_report(
            manifest,
            "closed-edge steps did not match "
            "expected_incident_steps_with_closed_edges",
            smoke_report,
        )
    if summary["max_closed_edges"] != expected["expected_max_closed_edges"]:
        return _failure_report(
            manifest,
            "max closed edges did not match expected_max_closed_edges",
            smoke_report,
        )
    if summary["changed"] != expected["expected_changed"]:
        return _failure_report(
            manifest,
            "changed flag did not match expected_changed",
            smoke_report,
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
        "run": manifest["run"],
        "expected": expected,
        "summary": summary,
        "smoke_report": smoke_report,
        "boundary_note": manifest["boundary_note"],
    }


def official_dynamic_incident_repro_gate(
    manifest_path=OFFICIAL_DYNAMIC_INCIDENT_REPRO_MANIFEST,
) -> tuple[bool, str]:
    """Gate for the manifest-backed official dynamic incident repro pack."""
    report = official_dynamic_incident_repro_report(manifest_path)
    if not report["ok"]:
        return False, report["reason"]

    summary = report["summary"]
    return (
        True,
        "official dynamic incident repro pack passed "
        f"(dataset={report['dataset']}, "
        f"matched_incidents={summary['n_matched_incidents']}, "
        f"arrival_delay={summary['arrival_delay']}, "
        f"waiting_delta={summary['waiting_delta']}, "
        f"closed_edge_steps={summary['incident_steps_with_closed_edges']}, "
        f"max_closed_edges={summary['max_closed_edges']}); "
        f"{report['boundary_note']}",
    )


__all__ = [
    "OFFICIAL_DYNAMIC_INCIDENT_REPRO_MANIFEST",
    "OFFICIAL_DYNAMIC_INCIDENT_REPRO_SCHEMA",
    "load_official_dynamic_incident_repro_manifest",
    "official_dynamic_incident_repro_gate",
    "official_dynamic_incident_repro_report",
]
