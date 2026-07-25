from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

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


def _bundle(
    repo: Path,
    *,
    lock_provenance: dict | None = None,
    lock_review: Path | None = None,
) -> dict:
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
        lock_review=lock_review or repo / "LOCK-REVIEW.json",
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


def test_malformed_lock_provenance_does_not_crash_or_count_as_miss_lock(
    tmp_path: Path,
):
    _write_required_artifacts(tmp_path)
    _write_lock_review(tmp_path / "LOCK-REVIEW.json")
    malformed_provenance = {
        "lock_commit": "a\x00b",
        "lock_review_commit": "b" * 40,
        "implementation_commit": "c" * 40,
        "first_run_commit": "d" * 40,
    }

    result = validate_repro_bundle(
        _bundle(tmp_path, lock_provenance=malformed_provenance),
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


@pytest.mark.parametrize("same_head", [False, True])
def test_post_run_or_same_head_lock_review_does_not_count_as_miss_lock(
    tmp_path: Path,
    same_head: bool,
):
    _run_git(tmp_path, "init")
    (tmp_path / "predictions_locked.md").write_text("# predictions\n", encoding="utf-8")
    lock_commit = _commit_all(tmp_path, "lock predictions")

    (tmp_path / "implementation.py").write_text("# implementation\n", encoding="utf-8")
    (tmp_path / "findings.md").write_text("# findings\n", encoding="utf-8")
    (tmp_path / "design_spec.md").write_text("# design\n", encoding="utf-8")
    (tmp_path / "results.json").write_text("{}\n", encoding="utf-8")
    implementation_commit = _commit_all(tmp_path, "implement model")

    (tmp_path / "run.log").write_text("first run\n", encoding="utf-8")
    first_run_commit = _commit_all(tmp_path, "run model")

    lock_review = tmp_path / "LOCK-REVIEW.json"
    _write_lock_review(lock_review)
    late_review_commit = _commit_all(tmp_path, "review lock after run")
    if same_head:
        implementation_commit = late_review_commit
        first_run_commit = late_review_commit

    result = validate_repro_bundle(
        _bundle(
            tmp_path,
            lock_provenance={
                "lock_commit": lock_commit,
                "lock_review_commit": late_review_commit,
                "implementation_commit": implementation_commit,
                "first_run_commit": first_run_commit,
            },
        ),
        repo=tmp_path,
        check_data_hashes=True,
    )

    assert result["ok"], result["issues"]
    assert result["construct_validity_classification_admissible"] is False
    assert result["miss_lock_count"] == 0
    assert result["unclassified_miss_count"] == 1
    assert any(
        "lock_provenance.lock_review_commit must strictly precede" in issue
        for issue in result["classification_admissibility_issues"]
    )


def test_lock_review_content_must_match_the_recorded_review_commit(tmp_path: Path):
    _run_git(tmp_path, "init")
    (tmp_path / "predictions_locked.md").write_text("# predictions\n", encoding="utf-8")
    lock_commit = _commit_all(tmp_path, "lock predictions")

    lock_review = tmp_path / "LOCK-REVIEW.json"
    _write_lock_review(lock_review)
    lock_review_commit = _commit_all(tmp_path, "review lock")

    (tmp_path / "implementation.py").write_text("# implementation\n", encoding="utf-8")
    (tmp_path / "findings.md").write_text("# findings\n", encoding="utf-8")
    (tmp_path / "design_spec.md").write_text("# design\n", encoding="utf-8")
    (tmp_path / "results.json").write_text("{}\n", encoding="utf-8")
    implementation_commit = _commit_all(tmp_path, "implement model")

    (tmp_path / "run.log").write_text("first run\n", encoding="utf-8")
    first_run_commit = _commit_all(tmp_path, "run model")

    lock_review.write_text(
        lock_review.read_text(encoding="utf-8").replace(
            "The proxy does not measure the paper claim.",
            "The replacement proxy does not measure the paper claim.",
        ),
        encoding="utf-8",
    )
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
    assert result["construct_validity_classification_admissible"] is False
    assert result["miss_lock_count"] == 0
    assert result["unclassified_miss_count"] == 1
    assert any(
        "docs.lock_review.sha256 must match lock_provenance.lock_review_commit" in issue
        for issue in result["classification_admissibility_issues"]
    )


def test_bundle_rejects_escaping_artifact_paths_and_accepts_canonical_paths(
    tmp_path: Path,
):
    _write_required_artifacts(tmp_path)
    _write_lock_review(tmp_path / "LOCK-REVIEW.json")

    canonical_bundle = _bundle(tmp_path)
    canonical_result = validate_repro_bundle(
        canonical_bundle,
        repo=tmp_path,
        check_data_hashes=True,
    )

    assert canonical_result["ok"], canonical_result["issues"]
    assert canonical_bundle["docs"]["lock_review"]["path"] == "LOCK-REVIEW.json"

    for section, name in (
        ("docs", "lock_review"),
        ("docs", "findings"),
        ("data", "results"),
    ):
        bundle = _bundle(tmp_path)
        bundle[section][name]["path"] = "../outside-repo-artifact"

        result = validate_repro_bundle(bundle, repo=tmp_path, check_data_hashes=True)

        assert result["ok"] is False
        assert (
            f"{section}.{name}.path must be a canonical repository-relative path"
            in result["issues"]
        )


def test_bundle_requires_canonical_posix_artifact_paths(tmp_path: Path):
    _write_required_artifacts(tmp_path)
    canonical_lock_review = tmp_path / "docs/reproduce/foo.json"
    canonical_lock_review.parent.mkdir(parents=True)
    _write_lock_review(canonical_lock_review)

    canonical_bundle = _bundle(tmp_path, lock_review=canonical_lock_review)
    canonical_result = validate_repro_bundle(
        canonical_bundle,
        repo=tmp_path,
        check_data_hashes=True,
    )

    assert canonical_result["ok"], canonical_result["issues"]
    assert canonical_bundle["docs"]["lock_review"]["path"] == "docs/reproduce/foo.json"

    for path_value in (
        "./docs/reproduce/foo.json",
        "docs//reproduce/foo.json",
        r"docs\reproduce\foo.json",
        "C:docs/reproduce/foo.json",
    ):
        bundle = _bundle(tmp_path, lock_review=canonical_lock_review)
        bundle["docs"]["lock_review"]["path"] = path_value

        result = validate_repro_bundle(bundle, repo=tmp_path, check_data_hashes=True)

        assert result["ok"] is False
        assert "docs.lock_review.path must be a canonical repository-relative path" in result["issues"]


def test_bundle_rejects_lock_review_symlink_escape(tmp_path: Path):
    _write_required_artifacts(tmp_path)
    _write_lock_review(tmp_path / "LOCK-REVIEW.json")
    bundle = _bundle(tmp_path)
    outside = tmp_path.parent / "outside-lock-review.json"
    _write_lock_review(outside)
    (tmp_path / "LOCK-REVIEW.json").unlink()
    (tmp_path / "LOCK-REVIEW.json").symlink_to(outside)

    bundle["docs"]["lock_review"]["path"] = "LOCK-REVIEW.json"
    result = validate_repro_bundle(bundle, repo=tmp_path, check_data_hashes=True)

    assert result["ok"] is False
    assert "docs.lock_review.path must be a canonical repository-relative path" in result["issues"]


def test_build_bundle_rejects_escaping_symlink_before_fingerprinting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _write_required_artifacts(tmp_path)
    escaped_target = tmp_path.parent / "outside-artifact.json"
    escaped_target.write_text("{\"outside\": true}\n", encoding="utf-8")
    escaped_link = tmp_path / "escaped-artifact.json"
    escaped_link.symlink_to(escaped_target)
    fingerprint_calls: list[Path] = []

    def unexpected_fingerprint(path: Path) -> dict:
        fingerprint_calls.append(path)
        raise AssertionError("an escaping artifact must be rejected before fingerprinting")

    monkeypatch.setattr("abm_auto.repro_bundle.fingerprint", unexpected_fingerprint)

    with pytest.raises(ValueError, match="repository-relative path"):
        build_bundle(
            paper={"title": "Symlink hardening", "authors": "x", "year": 2026},
            headline="reject escaped artifacts",
            verdicts=[Verdict(passed=True, tier="support", gate_name="P1")],
            data_artifacts={"results": tmp_path / "results.json"},
            doc_artifacts={"escaped": escaped_link},
            repo=tmp_path,
        )

    assert fingerprint_calls == []


def test_build_bundle_fingerprints_in_repo_symlink_target_with_canonical_path(
    tmp_path: Path,
):
    _write_required_artifacts(tmp_path)
    target = tmp_path / "artifacts/results.json"
    target.parent.mkdir()
    target.write_text("{\"inside\": true}\n", encoding="utf-8")
    link = tmp_path / "results-link.json"
    link.symlink_to(target)

    bundle = build_bundle(
        paper={"title": "Symlink hardening", "authors": "x", "year": 2026},
        headline="allow in-repo artifacts",
        verdicts=[Verdict(passed=True, tier="support", gate_name="P1")],
        data_artifacts={"results": Path("results-link.json")},
        doc_artifacts={"findings": tmp_path / "findings.md"},
        repo=tmp_path,
    )

    assert bundle["data"]["results"]["path"] == "artifacts/results.json"
