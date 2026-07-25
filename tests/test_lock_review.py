from __future__ import annotations

from abm_auto.lock_review import (
    SCHEMA,
    SCHEMA_V2,
    derive_construct_validity,
    derive_evidence_interpretation,
    validate_lock_review,
)


def _review(**overrides):
    review = {
        "schema": SCHEMA,
        "study_id": "wilson-entropy-gravity",
        "timing": "prospective",
        "result_visibility": "no_results_seen",
        "items": [
            {
                "clause_id": "P1",
                "paper_claim": "The model matches origin and destination margins.",
                "locked_metric": "max marginal residual <= 1e-9",
                "validity": "sound",
                "issue_kind": None,
                "review_rationale": "The locked metric directly measures the paper's constrained-flow claim.",
                "requires_relock": False,
            },
            {
                "clause_id": "P3",
                "paper_claim": "The entropy-maximizing model is the correct constrained allocation.",
                "locked_metric": "entropy >= distance-blind independent allocation",
                "validity": "mis_specified",
                "issue_kind": "direction_error",
                "review_rationale": "A distance-constrained optimum should not be compared against an unconstrained product allocation in that direction.",
                "requires_relock": True,
            },
        ],
    }
    review.update(overrides)
    return review


def test_validate_lock_review_accepts_clause_level_construct_validity():
    result = validate_lock_review(_review(), expected_clause_ids=["P1", "P3"])

    assert result["ok"] is True
    assert result["item_count"] == 2
    assert result["validity_counts"] == {
        "sound": 1,
        "mis_specified": 1,
        "uncertain": 0,
    }
    assert result["issue_kind_counts"] == {"direction_error": 1}


def test_validate_lock_review_rejects_missing_clause_coverage():
    result = validate_lock_review(_review(), expected_clause_ids=["P1", "P2", "P3"])

    assert result["ok"] is False
    assert "missing review item for clause P2" in result["issues"]


def test_validate_lock_review_rejects_prospective_reviews_that_saw_results():
    review = _review(result_visibility="results_seen")

    result = validate_lock_review(review)

    assert result["ok"] is False
    assert "prospective lock reviews must declare result_visibility='no_results_seen'" in result["issues"]


def test_validate_lock_review_rejects_mis_specified_item_without_issue_kind_or_relock():
    review = _review()
    review["items"][1]["issue_kind"] = None
    review["items"][1]["requires_relock"] = False

    result = validate_lock_review(review)

    assert result["ok"] is False
    assert "items[1].issue_kind is required when validity is 'mis_specified'" in result["issues"]
    assert "items[1].requires_relock must be true when validity is 'mis_specified'" in result["issues"]


def _construct_dimensions(**overrides):
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


def _v2_item(clause_id="P1", **overrides):
    item = {
        "clause_id": clause_id,
        "paper_claim": "The paper claim is measured by this clause.",
        "locked_metric": "locked metric",
        "validity": "sound",
        "construct_dimensions": _construct_dimensions(),
        "issue_kinds": [],
        "review_rationale": "The locked metric is a direct construct proxy.",
        "requires_relock": False,
    }
    item.update(overrides)
    return item


def _bar_profile(**overrides):
    profile = {
        "threshold_origin": "finite_system_proxy",
        "estimator_family": "activity_band",
        "finite_system_risks": ["finite_size", "seed_sampling"],
        "bar_fragility": "medium",
        "secondary_signature": "activity rises before the chaotic regime",
    }
    profile.update(overrides)
    return profile


def _v2_review(*items):
    return {
        "schema": SCHEMA_V2,
        "study_id": "wave-21-v2-fixture",
        "timing": "prospective",
        "result_visibility": "no_results_seen",
        "items": list(items),
    }


def test_validate_lock_review_accepts_v2_construct_dimensions():
    item = _v2_item()
    review = _v2_review(item)

    result = validate_lock_review(review, expected_clause_ids=["P1"])

    assert result["ok"] is True
    assert result["schema"] == SCHEMA_V2
    assert result["validity_counts"]["sound"] == 1


def test_validate_lock_review_v2_rejects_missing_dimension():
    dimensions = _construct_dimensions()
    del dimensions["regime_fit"]
    review = _v2_review(_v2_item(construct_dimensions=dimensions))

    result = validate_lock_review(review)

    assert result["ok"] is False
    assert "items[0].construct_dimensions.regime_fit is required" in result["issues"]


def test_validate_lock_review_v2_rejects_invalid_dimension_enum():
    review = _v2_review(
        _v2_item(construct_dimensions=_construct_dimensions(metric_robustness="hand_wavy"))
    )

    result = validate_lock_review(review)

    assert result["ok"] is False
    assert "items[0].construct_dimensions.metric_robustness is invalid" in result["issues"]


def test_validate_lock_review_v2_rejects_explicit_validity_mismatch():
    review = _v2_review(
        _v2_item(
            validity="sound",
            construct_dimensions=_construct_dimensions(metric_robustness="threshold_fragile"),
        )
    )

    result = validate_lock_review(review)

    assert result["ok"] is False
    assert "items[0].validity must equal derived construct validity 'uncertain'" in result["issues"]


def test_validate_lock_review_v2_rejects_mis_specified_without_relock():
    review = _v2_review(
        _v2_item(
            validity="mis_specified",
            construct_dimensions=_construct_dimensions(operationalization="wrong_proxy"),
            issue_kinds=["wrong_proxy"],
            requires_relock=False,
        )
    )

    result = validate_lock_review(review)

    assert result["ok"] is False
    assert "items[0].requires_relock must be true when validity is 'mis_specified'" in result["issues"]


def test_validate_lock_review_v2_accepts_finite_system_bar_profile():
    review = _v2_review(_v2_item(bar_profile=_bar_profile()))

    result = validate_lock_review(review)

    assert result["ok"] is True


def test_validate_lock_review_v2_rejects_high_fragility_without_secondary_signature():
    profile = _bar_profile(bar_fragility="high")
    del profile["secondary_signature"]
    review = _v2_review(_v2_item(bar_profile=profile))

    result = validate_lock_review(review)

    assert result["ok"] is False
    assert "items[0].bar_profile.secondary_signature is required when bar_fragility is 'high'" in result["issues"]


def test_derive_construct_validity_is_conservative_for_weak_dimensions():
    assert derive_construct_validity(_construct_dimensions()) == "sound"
    assert (
        derive_construct_validity(
            _construct_dimensions(mechanism_specificity="trivial_by_construction")
        )
        == "uncertain"
    )
    assert derive_construct_validity(_construct_dimensions(directionality="reversed")) == "mis_specified"


def test_derive_evidence_interpretation_marks_trivial_pass_as_weak():
    item = _v2_item(
        validity="uncertain",
        construct_dimensions=_construct_dimensions(
            control_quality="weak_control",
            mechanism_specificity="trivial_by_construction",
            load_bearing_role="sanity_check",
            emergence_level="accounting_identity",
            counterfactual_discrimination="non_discriminating",
        ),
    )

    interpretation = derive_evidence_interpretation({"passed": True}, item)

    assert interpretation["ok"] is True
    assert interpretation["evidence_strength"] == "weak"
    assert interpretation["failure_kind"] == "none"
    assert interpretation["finding_role"] == "sanity_check"


def test_derive_evidence_interpretation_separates_uncertain_lock_from_model_miss():
    uncertain_item = _v2_item(
        validity="uncertain",
        construct_dimensions=_construct_dimensions(regime_fit="risky_regime"),
    )
    sound_item = _v2_item()

    uncertain = derive_evidence_interpretation({"passed": False}, uncertain_item)
    sound = derive_evidence_interpretation({"passed": False}, sound_item)

    assert uncertain["failure_kind"] == "uncertain_lock"
    assert uncertain["evidence_strength"] == "weak"
    assert sound["failure_kind"] == "model_miss"
    assert sound["evidence_strength"] == "strong"


def test_derive_evidence_interpretation_marks_not_run_as_coverage_gap():
    item = _v2_item(validity="sound")

    interpretation = derive_evidence_interpretation(
        {"passed": False},
        item,
        {
            "test_execution_status": "not_run",
            "mechanism_fidelity": "missing_load_bearing_terms",
        },
    )

    assert interpretation["failure_kind"] == "not_run"
    assert interpretation["evidence_strength"] == "weak"


def test_derive_evidence_interpretation_rejects_invalid_realization_dimension():
    item = _v2_item(validity="sound")

    interpretation = derive_evidence_interpretation(
        {"passed": False},
        item,
        {"test_execution_status": "sort_of_ran"},
    )

    assert interpretation["ok"] is False
    assert "realization.test_execution_status is invalid" in interpretation["issues"]


def test_derive_evidence_interpretation_marks_threshold_endpoint_miss():
    item = _v2_item(
        validity="uncertain",
        construct_dimensions=_construct_dimensions(
            metric_robustness="threshold_fragile",
            control_quality="no_control_needed",
            mechanism_specificity="generic",
            load_bearing_role="supporting",
            counterfactual_discrimination="weakly_discriminating",
        ),
    )

    interpretation = derive_evidence_interpretation(
        {"passed": False},
        item,
        {
            "test_execution_status": "executed",
            "scale_fidelity": "right_sized_proxy",
            "mechanism_fidelity": "complete",
            "numerical_fidelity": "stable",
            "censoring_status": "uncensored",
            "qualitative_core_status": "qualitative_core_present",
        },
    )

    assert interpretation["failure_kind"] == "threshold_endpoint_miss"
    assert interpretation["evidence_strength"] == "moderate"


def test_derive_evidence_interpretation_marks_strict_bar_miss():
    item = _v2_item(
        validity="uncertain",
        construct_dimensions=_construct_dimensions(metric_robustness="threshold_fragile"),
        bar_profile=_bar_profile(
            bar_fragility="high",
            secondary_signature="late-time linear highway with stable displacement",
        ),
    )

    interpretation = derive_evidence_interpretation(
        {"passed": False},
        item,
        {
            "test_execution_status": "executed",
            "scale_fidelity": "faithful_scale",
            "mechanism_fidelity": "complete",
            "numerical_fidelity": "stable",
            "censoring_status": "uncensored",
            "qualitative_core_status": "qualitative_core_present",
            "bar_outcome": "missed",
            "estimator_status": "faithful",
            "secondary_signature_status": "present",
        },
    )

    assert interpretation["failure_kind"] == "strict_bar_miss"
    assert interpretation["evidence_strength"] == "moderate"
    assert interpretation["qualitative_core_status"] == "qualitative_core_present"


def test_derive_evidence_interpretation_marks_finite_system_measurement_miss():
    item = _v2_item(
        validity="uncertain",
        construct_dimensions=_construct_dimensions(metric_robustness="sample_size_sensitive"),
        bar_profile=_bar_profile(
            estimator_family="box_count",
            finite_system_risks=["finite_size", "boundary_condition"],
            bar_fragility="high",
            secondary_signature="mass-radius dimension remains in the expected band",
        ),
    )

    interpretation = derive_evidence_interpretation(
        {"passed": False},
        item,
        {
            "test_execution_status": "executed",
            "scale_fidelity": "right_sized_proxy",
            "mechanism_fidelity": "complete",
            "numerical_fidelity": "stable",
            "censoring_status": "uncensored",
            "qualitative_core_status": "qualitative_core_present",
            "bar_outcome": "missed",
            "estimator_status": "finite_size_biased",
            "secondary_signature_status": "present",
        },
    )

    assert interpretation["failure_kind"] == "finite_system_measurement_miss"
    assert interpretation["evidence_strength"] == "moderate"
    assert interpretation["qualitative_core_status"] == "qualitative_core_present"


def test_derive_evidence_interpretation_does_not_mark_measurement_miss_when_bar_met():
    item = _v2_item(
        validity="uncertain",
        construct_dimensions=_construct_dimensions(metric_robustness="sample_size_sensitive"),
        bar_profile=_bar_profile(
            estimator_family="box_count",
            finite_system_risks=["finite_size"],
            bar_fragility="high",
            secondary_signature="mass-radius dimension remains in the expected band",
        ),
    )

    interpretation = derive_evidence_interpretation(
        {"passed": False},
        item,
        {
            "test_execution_status": "executed",
            "scale_fidelity": "faithful_scale",
            "mechanism_fidelity": "complete",
            "numerical_fidelity": "stable",
            "censoring_status": "uncensored",
            "qualitative_core_status": "qualitative_core_present",
            "bar_outcome": "met",
            "estimator_status": "finite_size_biased",
            "secondary_signature_status": "present",
        },
    )

    assert interpretation["failure_kind"] == "uncertain_lock"
