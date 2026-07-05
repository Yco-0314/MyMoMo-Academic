from __future__ import annotations

import json
import subprocess
from pathlib import Path

from abm_auto.repro_bundle import build_bundle, validate_repro_bundle
from abm_auto.verification.gate import Verdict


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


def _write_required_artifacts(repo: Path) -> None:
    for name in ("predictions_locked.md", "findings.md", "design_spec.md"):
        (repo / name).write_text(f"# {name}\n", encoding="utf-8")
    (repo / "results.json").write_text("{}\n", encoding="utf-8")


def _write_lock_review(
    path: Path,
    *,
    timing: str = "prospective",
    result_visibility: str = "no_results_seen",
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "abm-auto/lock-review/v1",
                "study_id": "lock-provenance-smoke",
                "timing": timing,
                "result_visibility": result_visibility,
                "items": [
                    {
                        "clause_id": "P1",
                        "paper_claim": "The locked metric is a poor proxy.",
                        "locked_metric": "fragile proxy >= 0.90",
                        "validity": "mis_specified",
                        "issue_kind": "wrong_proxy",
                        "review_rationale": "The proxy does not measure the paper claim.",
                        "requires_relock": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _bundle(repo: Path, *, lock_provenance: dict | None = None) -> dict:
    return build_bundle(
        paper={"title": "Lock provenance smoke test", "authors": "x", "year": 2026},
        headline="MISS under a bad lock",
        verdicts=[
            Verdict(
                passed=False,
                tier="refutation",
                gate_name="P1",
                salient_number=(0.87, 0.90),
                construct_validity="mis_specified",
            )
        ],
        data_artifacts={"results": repo / "results.json"},
        doc_artifacts={
            "predictions_locked": repo / "predictions_locked.md",
            "findings": repo / "findings.md",
            "design_spec": repo / "design_spec.md",
        },
        repo=repo,
        lock_review=repo / "LOCK-REVIEW.json",
        lock_provenance=lock_provenance,
    )


def test_retrospective_lock_review_does_not_count_as_miss_lock(tmp_path: Path):
    _write_required_artifacts(tmp_path)
    _write_lock_review(
        tmp_path / "LOCK-REVIEW.json",
        timing="retrospective",
        result_visibility="results_seen",
    )

    result = validate_repro_bundle(_bundle(tmp_path), repo=tmp_path, check_data_hashes=True)

    assert result["ok"], result["issues"]
    assert result["miss_lock_count"] == 0
    assert result["unclassified_miss_count"] == 1
    assert result["construct_validity_classification_admissible"] is False
    assert any(
        "lock_review.timing must be 'prospective'" in issue
        for issue in result["classification_admissibility_issues"]
    )


def test_fake_lock_provenance_does_not_count_as_miss_lock(tmp_path: Path):
    _write_required_artifacts(tmp_path)
    _write_lock_review(tmp_path / "LOCK-REVIEW.json")
    fake_provenance = {
        "lock_commit": "a" * 40,
        "lock_review_commit": "b" * 40,
        "implementation_commit": "c" * 40,
        "first_run_commit": "d" * 40,
    }

    result = validate_repro_bundle(
        _bundle(tmp_path, lock_provenance=fake_provenance),
        repo=tmp_path,
        check_data_hashes=True,
    )

    assert result["ok"], result["issues"]
    assert result["miss_lock_count"] == 0
    assert result["unclassified_miss_count"] == 1
    assert result["construct_validity_classification_admissible"] is False
    assert any(
        "lock_provenance commits could not be verified" in issue
        for issue in result["classification_admissibility_issues"]
    )


def test_verified_prospective_lock_provenance_counts_as_miss_lock(tmp_path: Path):
    _run_git(tmp_path, "init")
    (tmp_path / "predictions_locked.md").write_text("# predictions\n", encoding="utf-8")
    lock_commit = _commit_all(tmp_path, "lock predictions")

    _write_lock_review(tmp_path / "LOCK-REVIEW.json")
    lock_review_commit = _commit_all(tmp_path, "review lock")

    (tmp_path / "implementation.py").write_text("# implementation\n", encoding="utf-8")
    (tmp_path / "findings.md").write_text("# findings\n", encoding="utf-8")
    (tmp_path / "design_spec.md").write_text("# design\n", encoding="utf-8")
    (tmp_path / "results.json").write_text("{}\n", encoding="utf-8")
    implementation_commit = _commit_all(tmp_path, "implement model")

    (tmp_path / "run.log").write_text("first run\n", encoding="utf-8")
    first_run_commit = _commit_all(tmp_path, "run model")

    result = validate_repro_bundle(
        _bundle(
            tmp_path,
            lock_provenance={
                "lock_commit": lock_commit,
                "lock_review_commit": lock_review_commit,
                "implementation_commit": implementation_commit,
                "first_run_commit": first_run_commit,
            },
        ),
        repo=tmp_path,
        check_data_hashes=True,
    )

    assert result["ok"], result["issues"]
    assert result["construct_validity_classification_admissible"] is True
    assert result["classification_admissibility_issues"] == []
    assert result["miss_lock_count"] == 1
    assert result["unclassified_miss_count"] == 0
