from __future__ import annotations

from pathlib import Path

from abm_auto.synthetic_population import (
    load_synthetic_population_manifest,
    summarize_synthetic_population_manifest,
    validate_synthetic_population_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_MANIFEST = REPO_ROOT / "docs/reproduce/synthetic-population/example-panel/manifest.json"


def _manifest(**overrides):
    manifest = {
        "schema": "abm-auto/synthetic-population-manifest/v1",
        "population_id": "example-panel-v1",
        "frame": {
            "source": "synthetic fixture",
            "geography": "not applicable",
            "time_scope": "2026 design fixture",
            "unit": "aggregate persona group",
        },
        "construction": {
            "method": "hand-authored fixture for manifest validation",
            "variables": ["age_band", "region", "prior_experience"],
            "direct_person_identifiers": False,
        },
        "weighting": {
            "scheme": "uniform fixture weights",
        },
        "validation": {
            "target": "manifest schema only",
            "metrics": ["field completeness"],
        },
        "allowed_claims": [
            "provenance fields are present",
            "no direct person identifiers are stored",
        ],
        "boundary_note": "This manifest does not validate synthetic people as human substitutes.",
    }
    manifest.update(overrides)
    return manifest


def test_valid_synthetic_population_manifest_passes():
    result = validate_synthetic_population_manifest(_manifest())

    assert result == {"ok": True, "issues": []}


def test_wrong_schema_fails():
    result = validate_synthetic_population_manifest(_manifest(schema="wrong"))

    assert result["ok"] is False
    assert "schema must be abm-auto/synthetic-population-manifest/v1" in result["issues"]


def test_missing_nested_frame_field_fails():
    manifest = _manifest(frame={
        "source": "synthetic fixture",
        "geography": "",
        "time_scope": "2026 design fixture",
        "unit": "aggregate persona group",
    })

    result = validate_synthetic_population_manifest(manifest)

    assert result["ok"] is False
    assert "frame.geography must be a non-empty string" in result["issues"]


def test_direct_person_identifiers_are_rejected():
    manifest = _manifest(construction={
        "method": "hand-authored fixture",
        "variables": ["age_band"],
        "direct_person_identifiers": True,
    })

    result = validate_synthetic_population_manifest(manifest)

    assert result["ok"] is False
    assert "construction.direct_person_identifiers must not be true" in result["issues"]


def test_committed_seed_manifest_validates_and_loads():
    manifest = load_synthetic_population_manifest(SEED_MANIFEST)

    result = validate_synthetic_population_manifest(manifest)

    assert result["ok"] is True


def test_synthetic_population_summary_reports_scope():
    summary = summarize_synthetic_population_manifest(_manifest())

    assert summary == {
        "population_id": "example-panel-v1",
        "source": "synthetic fixture",
        "geography": "not applicable",
        "time_scope": "2026 design fixture",
        "allowed_claims": 2,
        "validation_metrics": 1,
    }
