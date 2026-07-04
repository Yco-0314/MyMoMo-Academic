"""Evidence Foundry counterfactual challenge helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA = "abm-auto/counterfactual-challenge/v1"


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def _candidate_by_id(challenge: dict) -> dict[str, dict]:
    return {
        candidate["id"]: candidate
        for candidate in challenge.get("candidates", [])
        if isinstance(candidate, dict) and _is_nonempty_string(candidate.get("id"))
    }


def validate_counterfactual_challenge(challenge: dict) -> dict:
    """Validate a recorded-output counterfactual challenge."""
    if not isinstance(challenge, dict):
        return {"ok": False, "issues": ["challenge must be a JSON object"]}

    issues: list[str] = []
    if challenge.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA}")
    for field in ("challenge_id", "claim", "primary_id", "alternative_id", "boundary_note"):
        if not _is_nonempty_string(challenge.get(field)):
            issues.append(f"{field} must be a non-empty string")

    observed = challenge.get("observed_metrics")
    if not isinstance(observed, dict) or not observed:
        issues.append("observed_metrics must be a non-empty object")
        observed = {}
    for metric, value in observed.items():
        if not _is_nonempty_string(metric) or not _is_number(value):
            issues.append(f"observed metric {metric!r} must be numeric")

    metrics = challenge.get("discriminating_metrics")
    if not isinstance(metrics, list) or not metrics or not all(_is_nonempty_string(item) for item in metrics):
        issues.append("discriminating_metrics must be a non-empty list of strings")
        metrics = []

    candidates = challenge.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        issues.append("candidates must be a non-empty list")
        candidates = []

    seen: set[str] = set()
    for idx, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            issues.append(f"candidates[{idx}] must be an object")
            continue
        candidate_id = candidate.get("id")
        if not _is_nonempty_string(candidate_id):
            issues.append(f"candidates[{idx}].id must be a non-empty string")
            continue
        if candidate_id in seen:
            issues.append(f"duplicate candidate id {candidate_id}")
        seen.add(candidate_id)
        if not _is_nonempty_string(candidate.get("mechanism")):
            issues.append(f"candidates[{idx}].mechanism must be a non-empty string")
        candidate_metrics = candidate.get("metrics")
        if not isinstance(candidate_metrics, dict):
            issues.append(f"candidates[{idx}].metrics must be an object")
            candidate_metrics = {}
        for metric in metrics:
            if metric not in candidate_metrics:
                issues.append(f"candidate {candidate_id} missing metric {metric}")
            elif not _is_number(candidate_metrics[metric]):
                issues.append(f"candidate {candidate_id} metric {metric} must be numeric")

    candidate_ids = _candidate_by_id({"candidates": candidates})
    for field in ("primary_id", "alternative_id"):
        value = challenge.get(field)
        if _is_nonempty_string(value) and value not in candidate_ids:
            issues.append(f"{field} references unknown candidate {value}")

    for metric in metrics:
        if metric not in observed:
            issues.append(f"observed_metrics missing discriminating metric {metric}")

    return {"ok": not issues, "issues": issues}


def load_counterfactual_challenge(path: Path) -> dict:
    """Load a counterfactual challenge JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _total_error(observed: dict, candidate: dict, metrics: list[str]) -> float:
    return round(
        sum(abs(float(observed[metric]) - float(candidate["metrics"][metric])) for metric in metrics),
        10,
    )


def evaluate_counterfactual_challenge(
    challenge: dict,
    *,
    margin: float = 0.05,
) -> dict:
    """Evaluate whether the primary candidate discriminates against alternative."""
    validation = validate_counterfactual_challenge(challenge)
    if not validation["ok"]:
        return {
            "ok": False,
            "verdict": "MISS",
            "issues": validation["issues"],
            "primary_error": None,
            "alternative_error": None,
            "boundary_note": challenge.get("boundary_note") if isinstance(challenge, dict) else "",
        }

    candidates = _candidate_by_id(challenge)
    primary = candidates[challenge["primary_id"]]
    alternative = candidates[challenge["alternative_id"]]
    metrics = challenge["discriminating_metrics"]
    primary_error = _total_error(challenge["observed_metrics"], primary, metrics)
    alternative_error = _total_error(challenge["observed_metrics"], alternative, metrics)
    improvement = round(alternative_error - primary_error, 10)

    if improvement > margin:
        verdict = "PASS"
    elif abs(improvement) <= margin:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "MISS"

    return {
        "ok": verdict == "PASS",
        "verdict": verdict,
        "issues": [] if verdict == "PASS" else [f"primary improvement {improvement} did not exceed margin {margin}"],
        "primary_error": primary_error,
        "alternative_error": alternative_error,
        "improvement": improvement,
        "boundary_note": challenge["boundary_note"],
    }


def counterfactual_challenge_gate(
    challenge: dict,
    *,
    margin: float = 0.05,
) -> tuple[bool, str]:
    """Return a compact gate tuple for counterfactual challenge evaluation."""
    result = evaluate_counterfactual_challenge(challenge, margin=margin)
    status = "passed" if result["ok"] else "failed"
    desc = (
        f"Counterfactual challenge gate {status} "
        f"(verdict={result['verdict']}, primary_error={result['primary_error']}, "
        f"alternative_error={result['alternative_error']}); "
        "compares recorded candidate metrics, not causal proof"
    )
    return result["ok"], desc


__all__ = [
    "SCHEMA",
    "counterfactual_challenge_gate",
    "evaluate_counterfactual_challenge",
    "load_counterfactual_challenge",
    "validate_counterfactual_challenge",
]
