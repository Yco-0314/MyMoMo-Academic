"""Synthetic survey distribution gate helpers."""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

OBSERVED_SCHEMA = "abm-auto/synthetic-survey-observed/v1"
ANSWER_SCHEMA = "abm-auto/synthetic-survey-answer/v1"
BOUNDARY_NOTE = (
    "This gate compares fixed survey distributions; it does not validate "
    "synthetic people as human substitutes."
)


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _row_key(row: dict) -> str:
    return f"{row.get('question_id')}|{row.get('group')}|{row.get('option')}"


def _validate_rows(rows: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(rows, list) or not rows:
        return ["rows must be a non-empty list"]

    seen: set[str] = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            issues.append(f"rows[{idx}] must be an object")
            continue
        for field in ("question_id", "group", "option"):
            if not _is_nonempty_string(row.get(field)):
                issues.append(f"rows[{idx}].{field} must be a non-empty string")
        share = row.get("share")
        if isinstance(share, bool) or not isinstance(share, (int, float)) or share < 0 or share > 1:
            issues.append(f"rows[{idx}].share must be between 0 and 1")
        key = _row_key(row)
        if key in seen:
            issues.append(f"duplicate row key {key}")
        else:
            seen.add(key)
    return issues


def _validate_common(payload: dict, *, schema: str) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "issues": ["payload must be a JSON object"]}

    issues: list[str] = []
    if payload.get("schema") != schema:
        issues.append(f"schema must be {schema}")
    if not _is_nonempty_string(payload.get("survey_id")):
        issues.append("survey_id must be a non-empty string")
    if not _is_nonempty_string(payload.get("population_id")):
        issues.append("population_id must be a non-empty string")
    issues.extend(_validate_rows(payload.get("rows")))
    return {"ok": not issues, "issues": issues}


def validate_synthetic_survey_observed(observed: dict) -> dict:
    """Validate an observed held-out survey fixture."""
    result = _validate_common(observed, schema=OBSERVED_SCHEMA)
    if isinstance(observed, dict):
        questions = observed.get("questions")
        if not isinstance(questions, list) or not questions:
            result["issues"].append("questions must be a non-empty list")
            result["ok"] = False
    return result


def validate_synthetic_survey_answer(answer: dict) -> dict:
    """Validate a synthetic survey answer fixture."""
    return _validate_common(answer, schema=ANSWER_SCHEMA)


def load_synthetic_survey_json(path: Path) -> dict:
    """Load a synthetic survey JSON fixture."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _row_map(rows: list[dict]) -> dict[str, dict]:
    return {_row_key(row): row for row in rows}


def evaluate_synthetic_survey_gate(
    observed: dict,
    answer: dict,
    *,
    max_distribution_error: float = 0.10,
    max_subgroup_error: float = 0.20,
) -> dict:
    """Compare observed and synthetic survey answer distributions."""
    issues: list[str] = []
    observed_validation = validate_synthetic_survey_observed(observed)
    answer_validation = validate_synthetic_survey_answer(answer)
    if not observed_validation["ok"]:
        issues.extend(f"observed: {issue}" for issue in observed_validation["issues"])
    if not answer_validation["ok"]:
        issues.extend(f"answer: {issue}" for issue in answer_validation["issues"])

    if issues:
        return {
            "ok": False,
            "verdict": "MISS",
            "metrics": {
                "compared_rows": 0,
                "max_distribution_error": None,
                "mean_distribution_error": None,
                "max_subgroup_error": None,
            },
            "issues": issues,
            "boundary_note": BOUNDARY_NOTE,
        }

    if observed["survey_id"] != answer["survey_id"]:
        issues.append("survey_id mismatch")
    if observed["population_id"] != answer["population_id"]:
        issues.append("population_id mismatch")

    observed_rows = observed["rows"]
    answer_by_key = _row_map(answer["rows"])
    distribution_errors: list[float] = []
    subgroup_errors: list[float] = []
    all_errors: list[float] = []

    for row in observed_rows:
        key = _row_key(row)
        answer_row = answer_by_key.get(key)
        if answer_row is None:
            issues.append(f"missing synthetic row {key}")
            continue
        error = round(abs(float(row["share"]) - float(answer_row["share"])), 10)
        all_errors.append(error)
        if row["group"] == "all":
            distribution_errors.append(error)
        else:
            subgroup_errors.append(error)

    max_distribution = round(max(distribution_errors), 10) if distribution_errors else 0.0
    mean_distribution = round(mean(distribution_errors), 10) if distribution_errors else 0.0
    max_subgroup = round(max(subgroup_errors), 10) if subgroup_errors else 0.0

    if "survey_id mismatch" in issues or "population_id mismatch" in issues:
        verdict = "MISS"
    elif any(issue.startswith("missing synthetic row") for issue in issues):
        verdict = "MISS"
    elif max_distribution > max_distribution_error:
        issues.append("aggregate distribution error exceeds threshold")
        verdict = "MISS"
    elif max_subgroup > max_subgroup_error:
        issues.append("subgroup error exceeds threshold")
        verdict = "PARTIAL"
    else:
        verdict = "PASS"

    ok = verdict == "PASS"
    return {
        "ok": ok,
        "verdict": verdict,
        "metrics": {
            "compared_rows": len(all_errors),
            "max_distribution_error": max_distribution,
            "mean_distribution_error": mean_distribution,
            "max_subgroup_error": max_subgroup,
        },
        "issues": issues,
        "boundary_note": BOUNDARY_NOTE,
    }


def synthetic_survey_gate(
    observed: dict,
    answer: dict,
    *,
    max_distribution_error: float = 0.10,
    max_subgroup_error: float = 0.20,
) -> tuple[bool, str]:
    """Return a compact gate tuple for synthetic survey evaluation."""
    result = evaluate_synthetic_survey_gate(
        observed,
        answer,
        max_distribution_error=max_distribution_error,
        max_subgroup_error=max_subgroup_error,
    )
    status = "passed" if result["ok"] else "failed"
    metrics = result["metrics"]
    desc = (
        f"Synthetic survey gate {status} "
        f"(verdict={result['verdict']}, compared_rows={metrics['compared_rows']}, "
        f"max_distribution_error={metrics['max_distribution_error']}, "
        f"max_subgroup_error={metrics['max_subgroup_error']}); "
        "does not validate synthetic people as human substitutes"
    )
    return result["ok"], desc


__all__ = [
    "ANSWER_SCHEMA",
    "BOUNDARY_NOTE",
    "OBSERVED_SCHEMA",
    "evaluate_synthetic_survey_gate",
    "load_synthetic_survey_json",
    "synthetic_survey_gate",
    "validate_synthetic_survey_answer",
    "validate_synthetic_survey_observed",
]
