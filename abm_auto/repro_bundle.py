"""ADR-023 L3 — replayable reproduction bundle (the trust-layer distribution primitive).

A single machine-readable artifact a reviewer can re-run and diff: the paper, the
per-finding Verdicts (ADR-013 gate.py — tier-honest, with each hypothesis's
(value, threshold)), content-addressed fingerprints of the input DATA + the
locked-predictions + findings DOCS, the code commit, and the environment.

Reusable across reproductions. This is the L3 "a reviewer re-runs the gate"
primitive: re-running the reproduction regenerates the bundle; a reviewer diffs
the regenerated bundle against the committed one (fingerprints prove the inputs
were the same; verdicts prove the gate agreed).

Reuses abm_auto/verification: Verdict (the uniform gate output) + fingerprint (strong
file hashing). Additive GIS module; zero change to runtime/codegen/calibration.
"""
from __future__ import annotations

import json
import hashlib
import math
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from abm_auto.lock_review import derive_evidence_interpretation, validate_lock_review
from abm_auto._repo_paths import (
    canonical_repo_relative_path,
    is_absolute_path,
    is_canonical_repo_relative_path,
    repo_root,
    resolve_repo_input_path,
    resolve_repo_read_path,
    resolve_repo_relative_path,
)
from abm_auto.verification.gate import Verdict
from abm_auto.verification.provenance import fingerprint

SCHEMA = "abm-auto/repro-bundle/v1"
LOCK_PROVENANCE_KEYS = (
    "lock_commit",
    "lock_review_commit",
    "implementation_commit",
    "first_run_commit",
)


def _repo_root(repo: Optional[Path]) -> Path:
    return repo_root(repo)


def _fingerprint_with_portable_path(path: Path, repo: Optional[Path]) -> dict:
    if repo is None:
        full_path = path
        portable_path = str(path)
    else:
        root = _repo_root(repo)
        full_path = resolve_repo_input_path(path, root)
        if full_path is None:
            raise ValueError("artifact path must be a canonical repository-relative path")
        portable_path = canonical_repo_relative_path(full_path, root)
        if portable_path is None or not is_canonical_repo_relative_path(portable_path):
            raise ValueError("artifact path must be a canonical repository-relative path")
    fp = fingerprint(full_path)
    fp["path"] = portable_path
    return fp


def _is_absolute_path(path_value: str) -> bool:
    return is_absolute_path(path_value)


def _is_canonical_repo_relative_path(path_value: Any) -> bool:
    return is_canonical_repo_relative_path(path_value)


def _artifact_path(path_value: Any, repo: Path) -> Optional[Path]:
    """Return a resolved in-repository artifact path, or ``None`` if unsafe."""
    return resolve_repo_relative_path(path_value, repo)


def _is_two_number_tuple(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 2:
        return False
    return all(
        isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))
        for v in value
    )


def _is_valid_construct_validity(value: Any) -> bool:
    return value in {"sound", "mis_specified", "uncertain"}


def _evidence_interpretation_counts(
    interpretations: list[dict],
    verdicts: list[dict],
    *,
    construct_classification_admissible: bool,
) -> dict:
    counts: dict[str, Any] = {
        "evidence_interpretation_count": len(interpretations),
        "weak_pass_count": 0,
        "moderate_pass_count": 0,
        "strong_pass_count": 0,
        "trivial_pass_count": 0,
        "core_clause_count": 0,
        "miss_lock_count": 0,
        "miss_model_count": 0,
        "uncertain_lock_count": 0,
        "scale_regime_miss_count": 0,
        "threshold_endpoint_miss_count": 0,
        "implementation_miss_count": 0,
        "censored_count": 0,
        "not_run_count": 0,
        "unclassified_miss_count": 0,
        "strict_bar_miss_count": 0,
        "finite_system_measurement_miss_count": 0,
        "qualitative_core_present_count": 0,
    }
    verdict_by_gate = {
        verdict.get("gate"): verdict
        for verdict in verdicts
        if isinstance(verdict, dict)
    }
    for interpretation in interpretations:
        gate = interpretation.get("gate")
        verdict = verdict_by_gate.get(gate, {})
        failure_kind = interpretation.get("failure_kind")
        strength = interpretation.get("evidence_strength")
        role = interpretation.get("finding_role")
        if interpretation.get("qualitative_core_status") == "qualitative_core_present":
            counts["qualitative_core_present_count"] += 1
        if role == "core":
            counts["core_clause_count"] += 1
        if verdict.get("passed") is True:
            if strength == "weak":
                counts["weak_pass_count"] += 1
            elif strength == "moderate":
                counts["moderate_pass_count"] += 1
            elif strength == "strong":
                counts["strong_pass_count"] += 1
            if strength == "weak" and role == "sanity_check":
                counts["trivial_pass_count"] += 1
        elif failure_kind == "lock_miss":
            if construct_classification_admissible:
                counts["miss_lock_count"] += 1
            else:
                counts["unclassified_miss_count"] += 1
        elif failure_kind == "model_miss":
            counts["miss_model_count"] += 1
        elif failure_kind == "uncertain_lock":
            if construct_classification_admissible:
                counts["uncertain_lock_count"] += 1
            else:
                counts["unclassified_miss_count"] += 1
        elif failure_kind == "scale_regime_miss":
            counts["scale_regime_miss_count"] += 1
        elif failure_kind == "threshold_endpoint_miss":
            counts["threshold_endpoint_miss_count"] += 1
        elif failure_kind == "implementation_miss":
            counts["implementation_miss_count"] += 1
        elif failure_kind == "censored":
            counts["censored_count"] += 1
        elif failure_kind == "not_run":
            counts["not_run_count"] += 1
        elif failure_kind == "strict_bar_miss":
            if construct_classification_admissible:
                counts["strict_bar_miss_count"] += 1
            else:
                counts["unclassified_miss_count"] += 1
        elif failure_kind == "finite_system_measurement_miss":
            if construct_classification_admissible:
                counts["finite_system_measurement_miss_count"] += 1
            else:
                counts["unclassified_miss_count"] += 1
    return counts


def verdict_to_dict(v: Verdict) -> dict:
    return {
        "gate": v.gate_name,
        "tier": v.tier,
        "passed": v.passed,
        "salient_number": list(v.salient_number) if v.salient_number else None,
        "reasons": list(v.reasons),
        "evidence": v.evidence,
        "construct_validity": v.construct_validity,
    }


def git_commit(repo: Optional[Path] = None) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(repo) if repo else None,
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _git_commit_id(repo: Path, commit: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"{commit}^{{commit}}"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _git_commit_exists(repo: Path, commit: str) -> bool:
    return _git_commit_id(repo, commit) is not None


def _git_is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode == 0


def _git_is_strict_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    ancestor_id = _git_commit_id(repo, ancestor)
    descendant_id = _git_commit_id(repo, descendant)
    return (
        ancestor_id is not None
        and descendant_id is not None
        and ancestor_id != descendant_id
        and _git_is_ancestor(repo, ancestor, descendant)
    )


def _git_file_sha256(repo: Path, commit: str, path: str) -> Optional[str]:
    """Return a committed file's byte hash, without reading the working tree."""
    try:
        result = subprocess.run(
            ["git", "show", f"{commit}:{path}"],
            cwd=repo,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return hashlib.sha256(result.stdout).hexdigest()


def _lock_provenance_shape_issues(lock_provenance: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(lock_provenance, dict):
        return ["lock_provenance must be an object"]
    for key in LOCK_PROVENANCE_KEYS:
        if key in lock_provenance:
            value = lock_provenance[key]
            if not isinstance(value, str) or not value.strip():
                issues.append(f"lock_provenance.{key} must be a non-empty string")
    return issues


def _lock_provenance_admissibility_issues(
    lock_provenance: Any,
    repo: Path,
    lock_review_artifact: Any,
) -> list[str]:
    issues: list[str] = []
    if not isinstance(lock_provenance, dict):
        return [
            "lock_provenance is required for non-sound construct-validity classification"
        ]

    missing_keys = [key for key in LOCK_PROVENANCE_KEYS if key not in lock_provenance]
    for key in missing_keys:
        issues.append(
            f"lock_provenance.{key} is required for non-sound construct-validity classification"
        )
    if missing_keys:
        return issues

    commits = {key: str(lock_provenance[key]).strip() for key in LOCK_PROVENANCE_KEYS}
    unverifiable = [
        key for key, value in commits.items()
        if not _git_commit_exists(repo, value)
    ]
    if unverifiable:
        issues.append(
            "lock_provenance commits could not be verified: "
            + ", ".join(sorted(unverifiable))
        )
        return issues

    ancestry_checks = (
        ("lock_commit", "lock_review_commit", False),
        ("lock_review_commit", "implementation_commit", True),
        ("lock_review_commit", "first_run_commit", True),
        ("implementation_commit", "first_run_commit", False),
    )
    for ancestor_key, descendant_key, strict in ancestry_checks:
        is_valid = (
            _git_is_strict_ancestor if strict else _git_is_ancestor
        )
        if not is_valid(repo, commits[ancestor_key], commits[descendant_key]):
            relation = "strictly precede" if strict else "be an ancestor of"
            issues.append(
                f"lock_provenance.{ancestor_key} must {relation} "
                f"lock_provenance.{descendant_key}"
            )

    if not isinstance(lock_review_artifact, dict):
        return issues
    path_value = lock_review_artifact.get("path")
    lock_review_path = _artifact_path(path_value, repo)
    sha = lock_review_artifact.get("sha256")
    if lock_review_path is None or not isinstance(sha, str):
        return issues

    committed_sha = _git_file_sha256(
        repo,
        commits["lock_review_commit"],
        Path(path_value).as_posix(),
    )
    if committed_sha is None:
        issues.append(
            "docs.lock_review must exist at lock_provenance.lock_review_commit"
        )
    elif committed_sha != sha:
        issues.append(
            "docs.lock_review.sha256 must match lock_provenance.lock_review_commit"
        )
    return issues


def _lock_review_worktree_admissibility_issues(
    lock_review_artifact: Any,
    repo: Path,
) -> list[str]:
    """Require the reviewed working-tree bytes to match the bundle fingerprint."""
    if not isinstance(lock_review_artifact, dict):
        return []
    path_value = lock_review_artifact.get("path")
    sha = lock_review_artifact.get("sha256")
    lock_review_path = _artifact_path(path_value, repo)
    if lock_review_path is None or not isinstance(sha, str):
        return []
    if not lock_review_path.exists():
        return ["docs.lock_review.path does not exist for construct-validity classification"]
    if fingerprint(lock_review_path).get("sha256") != sha:
        return [
            "docs.lock_review.sha256 must match working-tree bytes "
            "for construct-validity classification"
        ]
    return []


def _construct_validity_miss_counts(
    verdicts: list[dict],
    *,
    construct_classification_admissible: bool,
) -> dict[str, int]:
    counts = {
        "miss_lock_count": 0,
        "miss_model_count": 0,
        "uncertain_lock_count": 0,
        "unclassified_miss_count": 0,
    }
    for verdict in verdicts:
        if not isinstance(verdict, dict) or verdict.get("passed") is not False:
            continue
        validity = verdict.get("construct_validity", "sound")
        if validity == "sound":
            counts["miss_model_count"] += 1
        elif construct_classification_admissible:
            if validity == "mis_specified":
                counts["miss_lock_count"] += 1
            elif validity == "uncertain":
                counts["uncertain_lock_count"] += 1
        else:
            counts["unclassified_miss_count"] += 1
    return counts


def env_versions(packages=("numpy", "scipy", "rasterio", "pyproj")) -> dict:
    env = {"python": platform.python_version(), "platform": platform.platform()}
    for p in packages:
        try:
            env[p] = __import__(p).__version__
        except Exception:
            env[p] = None
    return env


def build_bundle(
    *,
    paper: dict,
    headline: str,
    verdicts: List[Verdict],
    data_artifacts: Dict[str, Path],
    doc_artifacts: Dict[str, Path],
    repo: Optional[Path] = None,
    extra: Optional[dict] = None,
    odd: Optional[Path] = None,
    citations: Optional[list] = None,
    benchmark: Optional[dict] = None,
    lock_review: Optional[Path] = None,
    lock_provenance: Optional[dict] = None,
) -> dict:
    """Assemble a replayable reproduction bundle. ``data_artifacts``/``doc_artifacts`` are
    {name: path}; each is fingerprinted (files → strong sha256). ``verdicts`` are the
    per-finding gate Verdicts. ``headline`` is the human summary (e.g. 'EARNED').

    Optional journal-grade L3 carriers (ADR-023 L3; all default-off, backward-compatible):
    ``odd`` is an ODD-protocol doc fingerprinted into ``docs`` alongside findings/design_spec
    (so the integrity gate hashes it too); ``citations`` is a list of citation strings/DOIs
    stored verbatim; ``benchmark`` is a free-form cross-tool baseline dict (ADR-021 D5)
    stored verbatim (no real cross-tool run is performed here)."""
    docs = {
        name: _fingerprint_with_portable_path(Path(p), repo)
        for name, p in doc_artifacts.items()
    }
    if odd is not None:
        docs["odd"] = _fingerprint_with_portable_path(Path(odd), repo)
    if lock_review is not None:
        docs["lock_review"] = _fingerprint_with_portable_path(Path(lock_review), repo)
    bundle = {
        "schema": SCHEMA,
        "paper": paper,
        "headline": headline,
        "code_commit": git_commit(repo),
        "env": env_versions(),
        "verdicts": [verdict_to_dict(v) for v in verdicts],
        "data": {
            name: _fingerprint_with_portable_path(Path(p), repo)
            for name, p in data_artifacts.items()
        },
        "docs": docs,
    }
    if extra:
        bundle["extra"] = extra
    if citations is not None:
        bundle["citations"] = citations
    if benchmark is not None:
        bundle["benchmark"] = benchmark
    if lock_provenance is not None:
        bundle["lock_provenance"] = lock_provenance
    return bundle


def write_bundle(bundle: dict, path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    return path


def validate_repro_bundle(
    bundle: dict,
    *,
    repo: Optional[Path] = None,
    check_doc_hashes: bool = True,
    check_data_hashes: bool = False,
) -> dict:
    """Validate a replayable reproduction bundle's structure and fingerprints.

    Data files may be gitignored and absent in CI, so data hashes are checked only
    when ``check_data_hashes=True``. Document hashes are checked by default because
    they are committed with the bundle.
    """
    repo_root = _repo_root(repo)
    issues: list[str] = []
    doc_hashes_checked = 0
    data_hashes_checked = 0
    missing_data_files: list[str] = []
    evidence_interpretations: list[dict] = []
    classification_admissibility_issues: list[str] = []
    lock_review_timing: str | None = None
    lock_review_is_valid = False

    if not isinstance(bundle, dict):
        return {"ok": False, "issues": ["bundle must be a JSON object"]}

    if bundle.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA!r}")
    if not isinstance(bundle.get("paper"), dict) or not bundle["paper"].get("title"):
        issues.append("paper.title is required")
    if not isinstance(bundle.get("headline"), str) or not bundle["headline"].strip():
        issues.append("headline is required")

    verdicts = bundle.get("verdicts")
    if not isinstance(verdicts, list) or not verdicts:
        issues.append("verdicts must be a non-empty list")
        verdicts = []
    verdict_clause_ids: list[str] = []
    non_sound_construct_validity = False
    for idx, verdict in enumerate(verdicts):
        prefix = f"verdicts[{idx}]"
        if not isinstance(verdict, dict):
            issues.append(f"{prefix} must be an object")
            continue
        if not verdict.get("gate"):
            issues.append(f"{prefix}.gate is required")
        elif isinstance(verdict.get("gate"), str):
            verdict_clause_ids.append(verdict["gate"])
        if not verdict.get("tier"):
            issues.append(f"{prefix}.tier is required")
        if not isinstance(verdict.get("passed"), bool):
            issues.append(f"{prefix}.passed must be bool")
        if not _is_two_number_tuple(verdict.get("salient_number")):
            issues.append(f"{prefix}.salient_number must be [value, threshold]")
        if "construct_validity" in verdict:
            construct_validity = verdict.get("construct_validity")
            if not _is_valid_construct_validity(construct_validity):
                issues.append(f"{prefix}.construct_validity is invalid")
            elif construct_validity != "sound":
                non_sound_construct_validity = True
            if construct_validity == "mis_specified" and verdict.get("passed") is True:
                issues.append(f"{prefix}.construct_validity='mis_specified' cannot be paired with passed=true")

    docs = bundle.get("docs")
    if not isinstance(docs, dict):
        issues.append("docs must be an object")
        docs = {}
    for required in ("predictions_locked", "findings", "design_spec"):
        if required not in docs:
            issues.append(f"docs.{required} is required")

    data = bundle.get("data")
    if not isinstance(data, dict) or not data:
        issues.append("data must be a non-empty object")
        data = {}

    for section_name, artifacts in (("docs", docs), ("data", data)):
        for name, artifact in artifacts.items():
            prefix = f"{section_name}.{name}"
            if not isinstance(artifact, dict):
                issues.append(f"{prefix} must be an object")
                continue
            path_value = artifact.get("path")
            if not isinstance(path_value, str) or not path_value:
                issues.append(f"{prefix}.path is required")
                continue
            if _is_absolute_path(path_value):
                issues.append(f"{prefix}.path uses absolute local path: {path_value}")
            if artifact.get("kind") != "file":
                issues.append(f"{prefix}.kind must be 'file'")
            sha = artifact.get("sha256")
            if not isinstance(sha, str) or len(sha) != 64:
                issues.append(f"{prefix}.sha256 must be a 64-char hex string")
            if artifact.get("replay") != "strong":
                issues.append(f"{prefix}.replay must be 'strong'")

            full_path = _artifact_path(path_value, repo_root)
            if full_path is None:
                if not _is_absolute_path(path_value):
                    issues.append(
                        f"{prefix}.path must be a canonical repository-relative path"
                    )
                continue
            if section_name == "docs" and check_doc_hashes:
                if not full_path.exists():
                    issues.append(f"{prefix}.path does not exist: {path_value}")
                else:
                    actual = fingerprint(full_path).get("sha256")
                    doc_hashes_checked += 1
                    if sha != actual:
                        issues.append(f"{prefix}.sha256 mismatch")
            if section_name == "data":
                if full_path.exists() and check_data_hashes:
                    actual = fingerprint(full_path).get("sha256")
                    data_hashes_checked += 1
                    if sha != actual:
                        issues.append(f"{prefix}.sha256 mismatch")
                elif not full_path.exists():
                    missing_data_files.append(path_value)

    # Optional journal-grade L3 carriers — present only when authored; light shape
    # checks so a bundle WITHOUT them still validates (backward compatibility).
    if "citations" in bundle:
        citations = bundle["citations"]
        if not isinstance(citations, list):
            issues.append("citations must be a list of non-empty strings")
        elif not all(isinstance(c, str) and c.strip() for c in citations):
            issues.append("citations must be a list of non-empty strings")
    if "benchmark" in bundle:
        if not isinstance(bundle["benchmark"], dict):
            issues.append("benchmark must be an object")
    lock_review_artifact = docs.get("lock_review") if isinstance(docs, dict) else None
    construct_validity_verdict_count = len(verdicts) if isinstance(lock_review_artifact, dict) else 0
    if non_sound_construct_validity and not isinstance(lock_review_artifact, dict):
        issues.append("docs.lock_review is required when any verdict construct_validity is not 'sound'")
    if isinstance(lock_review_artifact, dict):
        path_value = lock_review_artifact.get("path")
        if isinstance(path_value, str) and path_value:
            lock_review_path = _artifact_path(path_value, repo_root)
            if lock_review_path is not None and lock_review_path.exists():
                try:
                    lock_review = json.loads(lock_review_path.read_text(encoding="utf-8"))
                except Exception as exc:
                    issues.append(f"lock_review could not be parsed as JSON: {exc}")
                    lock_review = None
                if isinstance(lock_review, dict):
                    review_result = validate_lock_review(
                        lock_review,
                        expected_clause_ids=verdict_clause_ids,
                    )
                    if not review_result["ok"]:
                        issues.extend(f"lock_review: {issue}" for issue in review_result["issues"])
                    else:
                        lock_review_is_valid = True
                        lock_review_timing = review_result.get("timing")
                        review_by_clause = {
                            item.get("clause_id"): item
                            for item in lock_review.get("items", [])
                            if isinstance(item, dict)
                        }
                        for idx, verdict in enumerate(verdicts):
                            if not isinstance(verdict, dict):
                                continue
                            clause_id = verdict.get("gate")
                            review_item = review_by_clause.get(clause_id)
                            if not isinstance(review_item, dict):
                                continue
                            if verdict.get("construct_validity", "sound") != review_item.get("validity"):
                                issues.append(
                                    f"verdicts[{idx}].construct_validity must match "
                                    f"lock_review item {clause_id!r}"
                                )
                            if isinstance(review_item.get("construct_dimensions"), dict):
                                realization = verdict.get("realization_dimensions")
                                if realization is not None and not isinstance(realization, dict):
                                    issues.append(f"verdicts[{idx}].realization_dimensions must be an object")
                                    realization = None
                                interpretation = derive_evidence_interpretation(
                                    verdict,
                                    review_item,
                                    realization,
                                )
                                if not interpretation["ok"]:
                                    issues.extend(
                                        f"verdicts[{idx}].evidence_interpretation: {issue}"
                                        for issue in interpretation["issues"]
                                    )
                                evidence_interpretation = {
                                    "gate": clause_id,
                                    "validity": interpretation["validity"],
                                    "evidence_strength": interpretation["evidence_strength"],
                                    "failure_kind": interpretation["failure_kind"],
                                    "finding_role": interpretation["finding_role"],
                                }
                                qualitative_core_status = interpretation.get("qualitative_core_status")
                                if qualitative_core_status is not None:
                                    evidence_interpretation["qualitative_core_status"] = qualitative_core_status
                                evidence_interpretations.append(evidence_interpretation)
        elif non_sound_construct_validity:
            issues.append("docs.lock_review.path is required when any verdict construct_validity is not 'sound'")
    if "lock_provenance" in bundle:
        issues.extend(_lock_provenance_shape_issues(bundle["lock_provenance"]))

    construct_validity_classification_admissible = False
    if non_sound_construct_validity:
        if not lock_review_is_valid:
            classification_admissibility_issues.append(
                "valid lock_review is required for non-sound construct-validity classification"
            )
        if lock_review_timing != "prospective":
            classification_admissibility_issues.append(
                "lock_review.timing must be 'prospective' for non-sound construct-validity classification"
            )
        classification_admissibility_issues.extend(
            _lock_review_worktree_admissibility_issues(
                lock_review_artifact,
                repo_root,
            )
        )
        classification_admissibility_issues.extend(
            _lock_provenance_admissibility_issues(
                bundle.get("lock_provenance"),
                repo_root,
                lock_review_artifact,
            )
        )
        construct_validity_classification_admissible = not classification_admissibility_issues

    failed_verdict_count = sum(
        1 for verdict in verdicts
        if isinstance(verdict, dict) and verdict.get("passed") is False
    )
    construct_counts = _construct_validity_miss_counts(
        verdicts,
        construct_classification_admissible=construct_validity_classification_admissible,
    )
    interpretation_counts = (
        _evidence_interpretation_counts(
            evidence_interpretations,
            verdicts,
            construct_classification_admissible=construct_validity_classification_admissible,
        )
        if evidence_interpretations
        else {}
    )
    result = {
        "ok": not issues,
        "issues": issues,
        "schema": bundle.get("schema"),
        "headline": bundle.get("headline"),
        "verdict_count": len(verdicts),
        "failed_verdict_count": failed_verdict_count,
        "construct_validity_verdict_count": construct_validity_verdict_count,
        "miss_lock_count": construct_counts["miss_lock_count"],
        "miss_model_count": construct_counts["miss_model_count"],
        "uncertain_lock_count": construct_counts["uncertain_lock_count"],
        "unclassified_miss_count": construct_counts["unclassified_miss_count"],
        "construct_validity_classification_admissible": (
            construct_validity_classification_admissible
        ),
        "classification_admissibility_issues": classification_admissibility_issues,
        "doc_hashes_checked": doc_hashes_checked,
        "data_hashes_checked": data_hashes_checked,
        "data_fingerprint_count": len(data),
        "missing_data_files": missing_data_files,
    }
    if evidence_interpretations:
        result.update(interpretation_counts)
        result["evidence_interpretations"] = evidence_interpretations
    return result


def validate_repro_bundle_file(path, *, repo: Optional[Path] = None, **kwargs) -> dict:
    requested_path = Path(path)
    if repo is None:
        try:
            repo = requested_path.absolute().parents[3]
        except IndexError:
            return {
                "ok": False,
                "issues": ["bundle path must resolve inside repository"],
            }
    repo = _repo_root(repo)
    bundle_path = resolve_repo_read_path(requested_path, repo)
    if bundle_path is None:
        return {
            "ok": False,
            "issues": ["bundle path must resolve inside repository"],
        }
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    return validate_repro_bundle(bundle, repo=repo, **kwargs)


def repro_bundle_integrity_gate(path, *, repo: Optional[Path] = None) -> tuple[bool, str]:
    result = validate_repro_bundle_file(path, repo=repo)
    if not result["ok"]:
        first = "; ".join(result["issues"][:3])
        return False, f"L3 bundle integrity gate failed: {first}"
    return (
        True,
        "L3 bundle integrity gate passed "
        f"(verdicts={result['verdict_count']}, "
        f"failed_verdicts={result['failed_verdict_count']}, "
        f"doc_hashes_checked={result['doc_hashes_checked']}, "
        f"data_fingerprints={result['data_fingerprint_count']}); "
        "this verifies schema, portable paths, and committed document hashes, "
        "not a rerun of the reproduction and not a truth certificate",
    )
