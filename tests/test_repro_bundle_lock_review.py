from __future__ import annotations

import json
from pathlib import Path

from abm_auto.repro_bundle import build_bundle, validate_repro_bundle
from abm_auto.verification.gate import Verdict


def _write_required_artifacts(root: Path) -> None:
    for name in ("predictions_locked.md", "findings.md", "design_spec.md"):
        (root / name).write_text(f"# {name}\n", encoding="utf-8")
    (root / "results.json").write_text("{}\n", encoding="utf-8")


def _write_lock_review(path: Path, *, clauses: tuple[str, ...] = ("P1", "P2")) -> None:
    items = []
    for clause in clauses:
        items.append({
            "clause_id": clause,
            "paper_claim": f"{clause} paper claim",
            "locked_metric": f"{clause} locked metric",
            "validity": "mis_specified" if clause == "P1" else "sound",
            "issue_kind": "noise_sensitive_metric" if clause == "P1" else None,
            "review_rationale": f"{clause} construct-validity rationale",
            "requires_relock": clause == "P1",
        })
    path.write_text(
        json.dumps({
            "schema": "abm-auto/lock-review/v1",
            "study_id": "construct-validity-smoke-test",
            "timing": "prospective",
            "result_visibility": "no_results_seen",
            "items": items,
        }),
        encoding="utf-8",
    )


def _construct_dimensions(**overrides: str) -> dict[str, str]:
    dimensions = {
        "operationalization": "direct",
        "directionality": "correct",
        "regime_fit": "in_regime",
        "metric_robustness": "robust",
        "control_quality": "causal_control",
        "mechanism_specificity": "distinctive",
        "load_bearing_role": "core",
        "emergence_level": "emergent",
        "counterfactual_discrimination": "discriminating",
    }
    dimensions.update(overrides)
    return dimensions


def _write_v2_lock_review(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "abm-auto/lock-review/v2",
                "study_id": "v2-interpretation-smoke-test",
                "timing": "prospective",
                "result_visibility": "no_results_seen",
                "items": [
                    {
                        "clause_id": "P1",
                        "paper_claim": "Demand satisfaction is checked.",
                        "locked_metric": "residual <= 0.01",
                        "validity": "uncertain",
                        "construct_dimensions": _construct_dimensions(
                            control_quality="weak_control",
                            mechanism_specificity="trivial_by_construction",
                            load_bearing_role="sanity_check",
                            emergence_level="accounting_identity",
                            counterfactual_discrimination="non_discriminating",
                        ),
                        "issue_kinds": [],
                        "review_rationale": (
                            "The metric is true but weak because the allocator enforces it."
                        ),
                        "requires_relock": False,
                    },
                    {
                        "clause_id": "P2",
                        "paper_claim": "Doorway alternation appears.",
                        "locked_metric": "alternation index >= 0.6",
                        "validity": "sound",
                        "construct_dimensions": _construct_dimensions(),
                        "issue_kinds": [],
                        "review_rationale": (
                            "The metric directly measures the doorway alternation claim."
                        ),
                        "requires_relock": False,
                    },
                    {
                        "clause_id": "P3",
                        "paper_claim": "Speed falls at high density.",
                        "locked_metric": "v(rho=5) < 0.4",
                        "validity": "uncertain",
                        "construct_dimensions": _construct_dimensions(
                            metric_robustness="threshold_fragile",
                            control_quality="no_control_needed",
                            mechanism_specificity="generic",
                            load_bearing_role="supporting",
                            counterfactual_discrimination="weakly_discriminating",
                        ),
                        "issue_kinds": [],
                        "review_rationale": (
                            "The monotone relation is robust but the endpoint is fragile."
                        ),
                        "requires_relock": False,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _bundle(
    root: Path,
    *,
    verdicts: list[Verdict],
    lock_review: Path | None,
    lock_provenance: dict | None = None,
) -> dict:
    return build_bundle(
        paper={"title": "Construct validity smoke test", "authors": "x", "year": 2026},
        headline="Construct validity smoke",
        verdicts=verdicts,
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


def test_bundle_keeps_unverified_lock_review_miss_unclassified(tmp_path: Path):
    _write_required_artifacts(tmp_path)
    lock_review = tmp_path / "LOCK-REVIEW.json"
    _write_lock_review(lock_review)

    bundle = _bundle(
        tmp_path,
        verdicts=[
            Verdict(
                passed=False,
                tier="refutation",
                gate_name="P1",
                salient_number=(0.87, 0.90),
                construct_validity="mis_specified",
            ),
            Verdict(
                passed=False,
                tier="refutation",
                gate_name="P2",
                salient_number=(-3.1, -2.2),
                construct_validity="sound",
            ),
        ],
        lock_review=lock_review,
        lock_provenance={
            "lock_commit": "a" * 40,
            "lock_review_commit": "b" * 40,
            "implementation_commit": "c" * 40,
            "first_run_commit": "d" * 40,
        },
    )

    result = validate_repro_bundle(bundle, repo=tmp_path, check_data_hashes=True)

    assert result["ok"], result["issues"]
    assert bundle["docs"]["lock_review"]["path"] == "LOCK-REVIEW.json"
    assert result["failed_verdict_count"] == 2
    assert result["miss_lock_count"] == 0
    assert result["miss_model_count"] == 1
    assert result["unclassified_miss_count"] == 1


def test_bundle_derives_v2_evidence_interpretation_counts(tmp_path: Path):
    _write_required_artifacts(tmp_path)
    lock_review = tmp_path / "LOCK-REVIEW.json"
    _write_v2_lock_review(lock_review)

    bundle = _bundle(
        tmp_path,
        verdicts=[
            Verdict(
                passed=True,
                tier="refutation",
                gate_name="P1",
                salient_number=(0.0, 0.01),
                construct_validity="uncertain",
            ),
            Verdict(
                passed=False,
                tier="refutation",
                gate_name="P2",
                salient_number=(0.0, 0.6),
                construct_validity="sound",
            ),
            Verdict(
                passed=False,
                tier="refutation",
                gate_name="P3",
                salient_number=(0.461, 0.4),
                construct_validity="uncertain",
            ),
        ],
        lock_review=lock_review,
    )
    bundle["verdicts"][1]["realization_dimensions"] = {
        "test_execution_status": "not_run",
        "mechanism_fidelity": "missing_load_bearing_terms",
    }
    bundle["verdicts"][2]["realization_dimensions"] = {
        "test_execution_status": "executed",
        "scale_fidelity": "right_sized_proxy",
        "mechanism_fidelity": "complete",
        "numerical_fidelity": "stable",
        "censoring_status": "uncensored",
        "qualitative_core_status": "qualitative_core_present",
    }

    result = validate_repro_bundle(bundle, repo=tmp_path, check_data_hashes=True)

    assert result["ok"], result["issues"]
    assert result["evidence_interpretation_count"] == 3
    assert result["weak_pass_count"] == 1
    assert result["strong_pass_count"] == 0
    assert result["not_run_count"] == 1
    assert result["threshold_endpoint_miss_count"] == 1
    assert result["miss_model_count"] == 0
    assert result["uncertain_lock_count"] == 0
    assert result["evidence_interpretations"] == [
        {
            "gate": "P1",
            "validity": "uncertain",
            "evidence_strength": "weak",
            "failure_kind": "none",
            "finding_role": "sanity_check",
        },
        {
            "gate": "P2",
            "validity": "sound",
            "evidence_strength": "weak",
            "failure_kind": "not_run",
            "finding_role": "core",
        },
        {
            "gate": "P3",
            "validity": "uncertain",
            "evidence_strength": "moderate",
            "failure_kind": "threshold_endpoint_miss",
            "finding_role": "supporting",
        },
    ]


def test_bundle_rejects_miss_lock_without_valid_lock_review(tmp_path: Path):
    _write_required_artifacts(tmp_path)
    lock_review = tmp_path / "LOCK-REVIEW.json"
    lock_review.write_text('{"schema": "abm-auto/lock-review/v1"}\n', encoding="utf-8")

    bundle = _bundle(
        tmp_path,
        verdicts=[
            Verdict(
                passed=False,
                tier="refutation",
                gate_name="P1",
                salient_number=(0.87, 0.90),
                construct_validity="mis_specified",
            ),
        ],
        lock_review=lock_review,
    )

    result = validate_repro_bundle(bundle, repo=tmp_path, check_data_hashes=True)

    assert not result["ok"]
    assert any("lock_review" in issue for issue in result["issues"])


def test_bundle_rejects_lock_review_missing_verdict_clause(tmp_path: Path):
    _write_required_artifacts(tmp_path)
    lock_review = tmp_path / "LOCK-REVIEW.json"
    _write_lock_review(lock_review, clauses=("P1",))

    bundle = _bundle(
        tmp_path,
        verdicts=[
            Verdict(
                passed=False,
                tier="refutation",
                gate_name="P1",
                salient_number=(0.87, 0.90),
                construct_validity="mis_specified",
            ),
            Verdict(
                passed=False,
                tier="refutation",
                gate_name="P2",
                salient_number=(-3.1, -2.2),
                construct_validity="sound",
            ),
        ],
        lock_review=lock_review,
    )

    result = validate_repro_bundle(bundle, repo=tmp_path, check_data_hashes=True)

    assert not result["ok"]
    assert any("missing review item for clause P2" in issue for issue in result["issues"])


def test_bundle_rejects_mis_specified_passed_verdict(tmp_path: Path):
    _write_required_artifacts(tmp_path)
    lock_review = tmp_path / "LOCK-REVIEW.json"
    _write_lock_review(lock_review, clauses=("P1",))

    bundle = _bundle(
        tmp_path,
        verdicts=[
            Verdict(
                passed=True,
                tier="refutation",
                gate_name="P1",
                salient_number=(0.91, 0.90),
                construct_validity="mis_specified",
            ),
        ],
        lock_review=lock_review,
    )

    result = validate_repro_bundle(bundle, repo=tmp_path, check_data_hashes=True)

    assert not result["ok"]
    assert (
        "verdicts[0].construct_validity='mis_specified' cannot be paired "
        "with passed=true"
    ) in result["issues"]
