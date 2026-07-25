from __future__ import annotations

import json
import subprocess
from pathlib import Path

from abm_auto.repro_bundle import build_bundle, validate_repro_bundle
from abm_auto.verification.gate import Verdict


def _write_required_artifacts(root: Path) -> None:
    for name in ("predictions_locked.md", "findings.md", "design_spec.md"):
        (root / name).write_text(f"# {name}\n", encoding="utf-8")
    (root / "results.json").write_text("{}\n", encoding="utf-8")


def _construct_dimensions(**overrides: str) -> dict[str, str]:
    dimensions = {
        "operationalization": "direct",
        "directionality": "correct",
        "regime_fit": "in_regime",
        "metric_robustness": "threshold_fragile",
        "control_quality": "no_control_needed",
        "mechanism_specificity": "generic",
        "load_bearing_role": "supporting",
        "emergence_level": "emergent",
        "counterfactual_discrimination": "weakly_discriminating",
    }
    dimensions.update(overrides)
    return dimensions


def _bar_profile(**overrides) -> dict:
    profile = {
        "threshold_origin": "finite_system_proxy",
        "estimator_family": "box_count",
        "finite_system_risks": ["finite_size", "boundary_condition"],
        "bar_fragility": "high",
        "secondary_signature": "mass-radius estimate remains in the expected band",
    }
    profile.update(overrides)
    return profile


def _write_lock_review(
    path: Path,
    *,
    timing: str = "prospective",
    result_visibility: str = "no_results_seen",
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "abm-auto/lock-review/v2",
                "study_id": "finite-system-bundle-demo",
                "timing": timing,
                "result_visibility": result_visibility,
                "items": [
                    {
                        "clause_id": "P1",
                        "paper_claim": "A finite-grid fractal structure appears.",
                        "locked_metric": "box-count dimension >= 1.4",
                        "validity": "uncertain",
                        "construct_dimensions": _construct_dimensions(
                            metric_robustness="sample_size_sensitive"
                        ),
                        "bar_profile": _bar_profile(),
                        "issue_kinds": [],
                        "review_rationale": "The strict box-count endpoint is finite-grid sensitive.",
                        "requires_relock": False,
                    },
                    {
                        "clause_id": "P2",
                        "paper_claim": "A fragile activity band is reached.",
                        "locked_metric": "activity between 0.02 and 0.30",
                        "validity": "uncertain",
                        "construct_dimensions": _construct_dimensions(),
                        "bar_profile": _bar_profile(
                            estimator_family="activity_band",
                            finite_system_risks=["seed_sampling"],
                            secondary_signature="ordered class ranking is preserved",
                        ),
                        "issue_kinds": [],
                        "review_rationale": "The strict activity band is fragile but the ranking is meaningful.",
                        "requires_relock": False,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _commit_all(repo: Path, message: str) -> str:
    _run_git(repo, "add", ".")
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            message,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return _run_git(repo, "rev-parse", "HEAD")


def _finite_system_bundle(
    root: Path,
    lock_review: Path,
    *,
    lock_provenance: dict[str, str] | None = None,
) -> dict:
    bundle = build_bundle(
        paper={"title": "Finite system bundle demo", "authors": "x", "year": 2026},
        headline="Strict bars missed with qualitative cores present",
        verdicts=[
            Verdict(
                passed=False,
                tier="refutation",
                gate_name="P1",
                salient_number=(1.37, 1.40),
                construct_validity="uncertain",
            ),
            Verdict(
                passed=False,
                tier="refutation",
                gate_name="P2",
                salient_number=(0.424, 0.30),
                construct_validity="uncertain",
            ),
        ],
        data_artifacts={"results": root / "results.json"},
        doc_artifacts={
            "predictions_locked": root / "predictions_locked.md",
            "findings": root / "findings.md",
            "design_spec": root / "design_spec.md",
        },
        repo=root,
        lock_review=lock_review,
        lock_provenance=lock_provenance,
    )
    bundle["verdicts"][0]["realization_dimensions"] = {
        "test_execution_status": "executed",
        "scale_fidelity": "right_sized_proxy",
        "mechanism_fidelity": "complete",
        "numerical_fidelity": "stable",
        "censoring_status": "uncensored",
        "qualitative_core_status": "qualitative_core_present",
        "bar_outcome": "missed",
        "estimator_status": "finite_size_biased",
        "secondary_signature_status": "present",
    }
    bundle["verdicts"][1]["realization_dimensions"] = {
        "test_execution_status": "executed",
        "scale_fidelity": "faithful_scale",
        "mechanism_fidelity": "complete",
        "numerical_fidelity": "stable",
        "censoring_status": "uncensored",
        "qualitative_core_status": "qualitative_core_present",
        "bar_outcome": "missed",
        "estimator_status": "faithful",
        "secondary_signature_status": "present",
    }
    return bundle


def test_bundle_counts_finite_system_bar_interpretations_with_verified_provenance(
    tmp_path: Path,
):
    _run_git(tmp_path, "init")
    for name in ("predictions_locked.md", "design_spec.md"):
        (tmp_path / name).write_text(f"# {name}\n", encoding="utf-8")
    lock_commit = _commit_all(tmp_path, "lock predictions")
    lock_review = tmp_path / "LOCK-REVIEW.json"
    _write_lock_review(lock_review)
    lock_review_commit = _commit_all(tmp_path, "review lock")
    (tmp_path / "implementation.txt").write_text("implemented\n", encoding="utf-8")
    implementation_commit = _commit_all(tmp_path, "implement model")
    (tmp_path / "findings.md").write_text("# findings\n", encoding="utf-8")
    (tmp_path / "results.json").write_text("{}\n", encoding="utf-8")
    first_run_commit = _commit_all(tmp_path, "run model")

    bundle = _finite_system_bundle(
        tmp_path,
        lock_review,
        lock_provenance={
            "lock_commit": lock_commit,
            "lock_review_commit": lock_review_commit,
            "implementation_commit": implementation_commit,
            "first_run_commit": first_run_commit,
        },
    )

    result = validate_repro_bundle(bundle, repo=tmp_path, check_data_hashes=True)

    assert result["ok"], result["issues"]
    assert result["construct_validity_classification_admissible"] is True
    assert result["finite_system_measurement_miss_count"] == 1
    assert result["strict_bar_miss_count"] == 1
    assert result["qualitative_core_present_count"] == 2
    assert result["evidence_interpretations"][0]["failure_kind"] == "finite_system_measurement_miss"
    assert result["evidence_interpretations"][1]["failure_kind"] == "strict_bar_miss"


def test_bundle_does_not_classify_retrospective_finite_system_explanations(
    tmp_path: Path,
):
    _write_required_artifacts(tmp_path)
    lock_review = tmp_path / "LOCK-REVIEW.json"
    _write_lock_review(
        lock_review,
        timing="retrospective",
        result_visibility="results_seen",
    )
    bundle = _finite_system_bundle(tmp_path, lock_review)

    result = validate_repro_bundle(bundle, repo=tmp_path, check_data_hashes=True)

    assert result["ok"], result["issues"]
    assert result["construct_validity_classification_admissible"] is False
    assert result["finite_system_measurement_miss_count"] == 0
    assert result["strict_bar_miss_count"] == 0
    assert result["unclassified_miss_count"] == 2
