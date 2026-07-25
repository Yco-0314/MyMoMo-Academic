"""Construct-validity review for locked reproduction clauses.

This module validates the pre-run review artifact for a prediction lock. It is
intentionally separate from ``verification.gate``: gates judge run artifacts,
while lock reviews judge whether a locked metric is a sound proxy for the
paper claim before the run is interpreted.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

SCHEMA_V1 = "abm-auto/lock-review/v1"
SCHEMA_V2 = "abm-auto/lock-review/v2"
SCHEMA = SCHEMA_V1

VALID_TIMINGS = {"prospective", "retrospective"}
VALID_RESULT_VISIBILITIES = {"no_results_seen", "results_seen", "unknown"}
VALID_CONSTRUCT_VALIDITIES = {"sound", "mis_specified", "uncertain"}
BASE_VALID_ISSUE_KINDS = {
    "direction_error",
    "wrong_proxy",
    "regime_mismatch",
    "noise_sensitive_metric",
    "threshold_fragile",
    "implementation_risk",
}
VALID_CONSTRUCT_DIMENSIONS = {
    "operationalization": {"direct", "proxy", "wrong_proxy", "ambiguous"},
    "directionality": {"correct", "reversed", "ambiguous", "not_directional"},
    "regime_fit": {
        "in_regime",
        "risky_regime",
        "extrapolated",
        "wrong_regime",
        "unknown",
    },
    "metric_robustness": {
        "robust",
        "threshold_fragile",
        "noise_sensitive",
        "censored",
        "sample_size_sensitive",
        "unknown",
    },
    "control_quality": {
        "causal_control",
        "weak_control",
        "confounded",
        "no_control_needed",
        "unknown",
    },
    "mechanism_specificity": {"distinctive", "generic", "trivial_by_construction", "unknown"},
    "load_bearing_role": {"core", "supporting", "sanity_check"},
    "emergence_level": {
        "emergent",
        "parameter_implied",
        "accounting_identity",
        "diagnostic_only",
        "unknown",
    },
    "counterfactual_discrimination": {
        "discriminating",
        "weakly_discriminating",
        "non_discriminating",
        "unknown",
    },
}
VALID_THRESHOLD_ORIGINS = {
    "analytical_exact",
    "analytical_asymptotic",
    "literature_exact",
    "literature_band",
    "finite_system_proxy",
    "empirical_band",
}
VALID_ESTIMATOR_FAMILIES = {
    "activity_band",
    "box_count",
    "correlation",
    "damage_spread",
    "direct_measure",
    "mass_radius",
    "onset_detection",
    "period_detection",
    "qualitative_signature",
    "slope_fit",
}
VALID_FINITE_SYSTEM_RISKS = {
    "boundary_condition",
    "coarse_grid",
    "estimator_bias",
    "finite_size",
    "insufficient_horizon",
    "none",
    "seed_sampling",
    "stochastic_noise",
}
VALID_BAR_FRAGILITIES = {"low", "medium", "high"}
HARD_MIS_SPECIFIED_DIMENSION_VALUES = {"wrong_proxy", "reversed", "wrong_regime", "confounded"}
UNCERTAIN_DIMENSION_VALUES = {
    "ambiguous",
    "unknown",
    "threshold_fragile",
    "noise_sensitive",
    "censored",
    "sample_size_sensitive",
    "weak_control",
    "risky_regime",
    "extrapolated",
    "generic",
    "trivial_by_construction",
    "parameter_implied",
    "accounting_identity",
    "diagnostic_only",
    "weakly_discriminating",
    "non_discriminating",
}
VALID_ISSUE_KINDS = (
    BASE_VALID_ISSUE_KINDS
    | HARD_MIS_SPECIFIED_DIMENSION_VALUES
    | UNCERTAIN_DIMENSION_VALUES
)

VALID_REALIZATION_DIMENSIONS = {
    "test_execution_status": {"executed", "partial_run", "not_run", "failed_to_run", "unknown"},
    "scale_fidelity": {
        "faithful_scale",
        "right_sized_proxy",
        "underpowered",
        "not_scale_sensitive",
        "unknown",
    },
    "mechanism_fidelity": {"complete", "approximate", "missing_load_bearing_terms", "unknown"},
    "numerical_fidelity": {"stable", "integration_limited", "unstable", "unknown"},
    "censoring_status": {"uncensored", "right_censored", "left_censored", "cap_hit", "unknown"},
    "qualitative_core_status": {
        "qualitative_core_present",
        "qualitative_core_absent",
        "not_applicable",
        "unknown",
    },
    "bar_outcome": {"met", "missed", "not_applicable", "unknown"},
    "estimator_status": {
        "faithful",
        "finite_size_biased",
        "boundary_condition_biased",
        "underresolved",
        "noisy",
        "unknown",
    },
    "secondary_signature_status": {"present", "absent", "not_declared", "unknown"},
}


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_nonempty_string(item: dict, key: str, prefix: str, issues: list[str]) -> None:
    if not _is_nonempty_string(item.get(key)):
        issues.append(f"{prefix}.{key} must be a non-empty string")


def derive_construct_validity(dimensions: dict) -> str:
    """Derive the v1-compatible construct-validity rollup from v2 dimensions."""
    values = set(dimensions.values())
    if values & HARD_MIS_SPECIFIED_DIMENSION_VALUES:
        return "mis_specified"
    if values & UNCERTAIN_DIMENSION_VALUES:
        return "uncertain"
    return "sound"


def _validate_construct_dimensions(dimensions: Any, prefix: str, issues: list[str]) -> bool:
    local_issues: list[str] = []
    if not isinstance(dimensions, dict):
        issues.append(f"{prefix}.construct_dimensions must be an object")
        return False

    for key, allowed_values in VALID_CONSTRUCT_DIMENSIONS.items():
        if key not in dimensions:
            local_issues.append(f"{prefix}.construct_dimensions.{key} is required")
            continue
        if dimensions[key] not in allowed_values:
            local_issues.append(f"{prefix}.construct_dimensions.{key} is invalid")

    for key in sorted(set(dimensions) - set(VALID_CONSTRUCT_DIMENSIONS)):
        local_issues.append(f"{prefix}.construct_dimensions.{key} is unexpected")

    issues.extend(local_issues)
    return not local_issues


def _validate_bar_profile(profile: Any, prefix: str, issues: list[str]) -> None:
    if profile is None:
        return
    if not isinstance(profile, dict):
        issues.append(f"{prefix}.bar_profile must be an object")
        return

    threshold_origin = profile.get("threshold_origin")
    if threshold_origin not in VALID_THRESHOLD_ORIGINS:
        issues.append(f"{prefix}.bar_profile.threshold_origin is invalid")

    estimator_family = profile.get("estimator_family")
    if estimator_family not in VALID_ESTIMATOR_FAMILIES:
        issues.append(f"{prefix}.bar_profile.estimator_family is invalid")

    finite_system_risks = profile.get("finite_system_risks")
    if not isinstance(finite_system_risks, list) or not finite_system_risks:
        issues.append(f"{prefix}.bar_profile.finite_system_risks must be a non-empty list")
    else:
        for risk_idx, risk in enumerate(finite_system_risks):
            if risk not in VALID_FINITE_SYSTEM_RISKS:
                issues.append(f"{prefix}.bar_profile.finite_system_risks[{risk_idx}] is invalid")
        if "none" in finite_system_risks and len(finite_system_risks) > 1:
            issues.append(f"{prefix}.bar_profile.finite_system_risks cannot mix 'none' with other risks")

    bar_fragility = profile.get("bar_fragility")
    if bar_fragility not in VALID_BAR_FRAGILITIES:
        issues.append(f"{prefix}.bar_profile.bar_fragility is invalid")
    elif bar_fragility == "high" and not _is_nonempty_string(profile.get("secondary_signature")):
        issues.append(
            f"{prefix}.bar_profile.secondary_signature is required when bar_fragility is 'high'"
        )

    if "secondary_signature" in profile and not _is_nonempty_string(profile.get("secondary_signature")):
        issues.append(f"{prefix}.bar_profile.secondary_signature must be a non-empty string")

    allowed = {
        "bar_fragility",
        "estimator_family",
        "finite_system_risks",
        "secondary_signature",
        "threshold_origin",
    }
    for key in sorted(set(profile) - allowed):
        issues.append(f"{prefix}.bar_profile.{key} is unexpected")


def _item_issue_kinds(item: dict, prefix: str, issues: list[str]) -> list[str]:
    issue_kinds: list[str] = []
    issue_kind = item.get("issue_kind")
    if issue_kind is not None:
        if issue_kind not in VALID_ISSUE_KINDS:
            issues.append(f"{prefix}.issue_kind is invalid")
        else:
            issue_kinds.append(issue_kind)

    raw_issue_kinds = item.get("issue_kinds")
    if raw_issue_kinds is None:
        return issue_kinds
    if not isinstance(raw_issue_kinds, list):
        issues.append(f"{prefix}.issue_kinds must be a list")
        return issue_kinds
    for idx, value in enumerate(raw_issue_kinds):
        if value not in VALID_ISSUE_KINDS:
            issues.append(f"{prefix}.issue_kinds[{idx}] is invalid")
        else:
            issue_kinds.append(value)
    return issue_kinds


def _resolve_review_item_validity(item: dict, prefix: str, issues: list[str]) -> str | None:
    validity = item.get("validity")
    dimensions = item.get("construct_dimensions")
    if isinstance(dimensions, dict):
        derived = derive_construct_validity(dimensions)
        if validity is None:
            return derived
        if validity in VALID_CONSTRUCT_VALIDITIES and validity != derived:
            issues.append(f"{prefix}.validity must equal derived construct validity {derived!r}")
        return validity
    return validity


def _validate_realization_dimensions(realization: dict, issues: list[str]) -> None:
    for key, value in realization.items():
        allowed_values = VALID_REALIZATION_DIMENSIONS.get(key)
        if allowed_values is None:
            issues.append(f"realization.{key} is unexpected")
        elif value not in allowed_values:
            issues.append(f"realization.{key} is invalid")


def derive_evidence_interpretation(
    verdict: dict,
    review_item: dict,
    realization: dict | None = None,
) -> dict:
    """Interpret a run verdict using v2 construct and realization dimensions.

    This helper classifies what a PASS/MISS means. It does not change the
    underlying verdict and does not certify scientific truth.
    """
    issues: list[str] = []
    realization = realization or {}
    _validate_realization_dimensions(realization, issues)
    dimensions = review_item.get("construct_dimensions")
    if not isinstance(dimensions, dict):
        dimensions = {}

    validity = review_item.get("validity")
    if dimensions:
        derived_validity = derive_construct_validity(dimensions)
        if validity is None:
            validity = derived_validity
        elif validity != derived_validity:
            issues.append(
                f"review_item.validity must equal derived construct validity {derived_validity!r}"
            )
    if validity not in VALID_CONSTRUCT_VALIDITIES:
        issues.append("review_item.validity is invalid")
        validity = "uncertain"

    passed = verdict.get("passed")
    if not isinstance(passed, bool):
        issues.append("verdict.passed must be bool")
        passed = False

    finding_role = dimensions.get("load_bearing_role", "supporting")
    mechanism_specificity = dimensions.get("mechanism_specificity")
    emergence_level = dimensions.get("emergence_level")
    counterfactual_discrimination = dimensions.get("counterfactual_discrimination")
    metric_robustness = dimensions.get("metric_robustness")
    bar_profile = review_item.get("bar_profile")
    if not isinstance(bar_profile, dict):
        bar_profile = {}
    finite_system_risks = set(bar_profile.get("finite_system_risks", [])) - {"none"}
    bar_fragility = bar_profile.get("bar_fragility")

    execution_status = realization.get("test_execution_status")
    scale_fidelity = realization.get("scale_fidelity")
    mechanism_fidelity = realization.get("mechanism_fidelity")
    numerical_fidelity = realization.get("numerical_fidelity")
    censoring_status = realization.get("censoring_status")
    qualitative_core_status = realization.get("qualitative_core_status")
    bar_outcome = realization.get("bar_outcome")
    estimator_status = realization.get("estimator_status")
    secondary_signature_status = realization.get("secondary_signature_status")

    qualitative_core_present = qualitative_core_status == "qualitative_core_present"
    estimator_limited = estimator_status in {
        "boundary_condition_biased",
        "finite_size_biased",
        "noisy",
        "underresolved",
    }

    failure_kind = "none"
    if passed:
        if validity == "mis_specified":
            issues.append("passed mis_specified verdict is invalid")
            evidence_strength = "weak"
        elif (
            mechanism_specificity == "trivial_by_construction"
            or emergence_level == "accounting_identity"
            or counterfactual_discrimination == "non_discriminating"
        ):
            evidence_strength = "weak"
        elif validity == "uncertain":
            evidence_strength = "moderate"
        else:
            evidence_strength = "strong"
    elif execution_status in {"not_run", "failed_to_run"}:
        failure_kind = "not_run"
        evidence_strength = "weak"
    elif (
        qualitative_core_present
        and finite_system_risks
        and bar_outcome == "missed"
        and estimator_limited
    ):
        failure_kind = "finite_system_measurement_miss"
        evidence_strength = "moderate"
    elif (
        qualitative_core_present
        and bar_fragility == "high"
        and bar_outcome == "missed"
        and secondary_signature_status == "present"
    ):
        failure_kind = "strict_bar_miss"
        evidence_strength = "moderate"
    elif (
        qualitative_core_present
        and metric_robustness == "threshold_fragile"
        and numerical_fidelity != "unstable"
    ):
        failure_kind = "threshold_endpoint_miss"
        evidence_strength = "moderate"
    elif scale_fidelity in {"underpowered", "right_sized_proxy"}:
        failure_kind = "scale_regime_miss"
        evidence_strength = (
            "moderate" if qualitative_core_status == "qualitative_core_present" else "weak"
        )
    elif mechanism_fidelity == "missing_load_bearing_terms" or numerical_fidelity in {
        "integration_limited",
        "unstable",
    }:
        failure_kind = "implementation_miss"
        evidence_strength = "weak"
    elif censoring_status in {"right_censored", "left_censored", "cap_hit"}:
        failure_kind = "censored"
        evidence_strength = "weak"
    elif validity == "mis_specified":
        failure_kind = "lock_miss"
        evidence_strength = "weak"
    elif validity == "uncertain":
        failure_kind = "uncertain_lock"
        evidence_strength = "weak"
    else:
        failure_kind = "model_miss"
        evidence_strength = "strong" if finding_role == "core" else "moderate"

    return {
        "ok": not issues,
        "issues": issues,
        "validity": validity,
        "evidence_strength": evidence_strength,
        "failure_kind": failure_kind,
        "finding_role": finding_role,
        "qualitative_core_status": qualitative_core_status,
    }


def validate_lock_review(
    review: dict,
    *,
    expected_clause_ids: list[str] | tuple[str, ...] | set[str] | None = None,
) -> dict:
    """Validate a machine-readable ``LOCK-REVIEW.json`` artifact.

    The validator checks structure and anti-escape invariants only. It does not
    certify that the scientific judgment is correct.
    """
    if not isinstance(review, dict):
        return {"ok": False, "issues": ["lock review must be a JSON object"]}

    issues: list[str] = []
    schema = review.get("schema")
    if schema not in {SCHEMA_V1, SCHEMA_V2}:
        issues.append(f"schema must be {SCHEMA_V1!r} or {SCHEMA_V2!r}")
    _require_nonempty_string(review, "study_id", "review", issues)

    timing = review.get("timing")
    if timing not in VALID_TIMINGS:
        issues.append("review.timing must be 'prospective' or 'retrospective'")

    result_visibility = review.get("result_visibility")
    if result_visibility not in VALID_RESULT_VISIBILITIES:
        issues.append("review.result_visibility is invalid")
    if timing == "prospective" and result_visibility != "no_results_seen":
        issues.append("prospective lock reviews must declare result_visibility='no_results_seen'")

    items = review.get("items")
    if not isinstance(items, list) or not items:
        issues.append("items must be a non-empty list")
        items = []

    seen_clause_ids: set[str] = set()
    validity_counts = Counter({validity: 0 for validity in VALID_CONSTRUCT_VALIDITIES})
    issue_kind_counts: Counter[str] = Counter()

    for idx, item in enumerate(items):
        prefix = f"items[{idx}]"
        if not isinstance(item, dict):
            issues.append(f"{prefix} must be an object")
            continue

        for key in ("clause_id", "paper_claim", "locked_metric", "review_rationale"):
            _require_nonempty_string(item, key, prefix, issues)

        clause_id = item.get("clause_id")
        if _is_nonempty_string(clause_id):
            if clause_id in seen_clause_ids:
                issues.append(f"duplicate clause_id {clause_id}")
            seen_clause_ids.add(clause_id)

        dimensions_are_valid = True
        if schema == SCHEMA_V2:
            dimensions_are_valid = _validate_construct_dimensions(
                item.get("construct_dimensions"),
                prefix,
                issues,
            )
            _validate_bar_profile(item.get("bar_profile"), prefix, issues)

        validity = (
            _resolve_review_item_validity(item, prefix, issues)
            if schema == SCHEMA_V2 and dimensions_are_valid
            else item.get("validity")
        )
        if validity not in VALID_CONSTRUCT_VALIDITIES:
            issues.append(f"{prefix}.validity is invalid")
        else:
            validity_counts[validity] += 1

        item_issue_kinds = _item_issue_kinds(item, prefix, issues)
        for issue_kind in item_issue_kinds:
            issue_kind_counts[issue_kind] += 1

        requires_relock = item.get("requires_relock")
        if not isinstance(requires_relock, bool):
            issues.append(f"{prefix}.requires_relock must be bool")

        if validity == "mis_specified":
            if schema == SCHEMA_V1 and item.get("issue_kind") is None:
                issues.append(
                    f"{prefix}.issue_kind is required when validity is 'mis_specified'"
                )
            if schema == SCHEMA_V2:
                dimensions = item.get("construct_dimensions")
                dimension_values = set(dimensions.values()) if isinstance(dimensions, dict) else set()
                hard_issues = (
                    dimension_values | set(item_issue_kinds)
                ) & HARD_MIS_SPECIFIED_DIMENSION_VALUES
                if not hard_issues:
                    issues.append(f"{prefix}.mis_specified validity requires a hard issue")
            if requires_relock is not True:
                issues.append(
                    f"{prefix}.requires_relock must be true when validity is 'mis_specified'"
                )

    if expected_clause_ids is not None:
        expected = {str(clause_id) for clause_id in expected_clause_ids}
        for clause_id in sorted(expected - seen_clause_ids):
            issues.append(f"missing review item for clause {clause_id}")
        for clause_id in sorted(seen_clause_ids - expected):
            issues.append(f"unexpected review item for clause {clause_id}")

    return {
        "ok": not issues,
        "issues": issues,
        "schema": schema,
        "study_id": review.get("study_id"),
        "timing": timing,
        "result_visibility": result_visibility,
        "item_count": len(items),
        "validity_counts": dict(sorted(validity_counts.items())),
        "issue_kind_counts": dict(sorted(issue_kind_counts.items())),
    }


__all__ = [
    "SCHEMA",
    "SCHEMA_V1",
    "SCHEMA_V2",
    "VALID_CONSTRUCT_DIMENSIONS",
    "VALID_CONSTRUCT_VALIDITIES",
    "VALID_BAR_FRAGILITIES",
    "VALID_ISSUE_KINDS",
    "VALID_ESTIMATOR_FAMILIES",
    "VALID_FINITE_SYSTEM_RISKS",
    "VALID_REALIZATION_DIMENSIONS",
    "VALID_THRESHOLD_ORIGINS",
    "derive_construct_validity",
    "derive_evidence_interpretation",
    "validate_lock_review",
]
