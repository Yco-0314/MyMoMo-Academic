from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from abm_auto.study_corpus import (
    SCHEMA,
    build_study_registry,
    diagnose_study_corpus,
    discover_study_corpus,
    render_study_index_markdown,
    validate_study_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
STUDIES_ROOT = REPO_ROOT / "docs/studies"


def test_discovers_complete_bundles_and_prediction_only_pending_studies():
    corpus = discover_study_corpus(STUDIES_ROOT, repo=REPO_ROOT)

    complete_ids = {entry["id"] for entry in corpus["complete"]}
    pending_ids = {entry["id"] for entry in corpus["pending"]}

    assert corpus["complete_count"] >= 78
    assert "cont-bouchaud" in complete_ids
    assert "axtell-firms" in complete_ids
    assert "bouchaud-mezard" in complete_ids
    assert "bouchaud-mezard" not in pending_ids

    cont = next(entry for entry in corpus["complete"] if entry["id"] == "cont-bouchaud")
    assert cont["bundle"] == "docs/studies/cont-bouchaud/verdict-bundle.json"
    assert cont["predictions"] == "docs/studies/cont-bouchaud/PREDICTIONS-locked.md"
    assert not Path(cont["bundle"]).is_absolute()


def test_discovery_ignores_untracked_study_bundles_in_git_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    study_dir = repo / "docs/studies/in-progress-study"
    study_dir.mkdir(parents=True)
    predictions = study_dir / "PREDICTIONS-locked.md"
    predictions.write_text("# Locked\n", encoding="utf-8")
    (study_dir / "verdict-bundle.json").write_text('{"untracked": true}\n', encoding="utf-8")

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "docs/studies/in-progress-study/PREDICTIONS-locked.md"], cwd=repo, check=True)

    corpus = discover_study_corpus(repo / "docs/studies", repo=repo)
    registry = build_study_registry(repo / "docs/studies", repo=repo)

    assert corpus["complete"] == []
    assert corpus["pending"] == [
        {
            "id": "in-progress-study",
            "status": "pending_bundle",
            "study_dir": "docs/studies/in-progress-study",
            "predictions": "docs/studies/in-progress-study/PREDICTIONS-locked.md",
        }
    ]
    assert registry["summary"]["complete_count"] == 0
    assert registry["summary"]["pending_count"] == 1


def test_builds_deterministic_registry_with_verdict_summary():
    registry = build_study_registry(STUDIES_ROOT, repo=REPO_ROOT)

    assert registry["schema"] == SCHEMA
    assert registry["study_root"] == "docs/studies"
    assert registry["summary"]["complete_count"] >= 78
    assert registry["summary"]["status_counts"]["complete"] >= 78

    cont = next(entry for entry in registry["entries"] if entry["id"] == "cont-bouchaud")
    assert cont["status"] == "complete"
    assert cont["paper"]["title"] == "Herd behavior and aggregate fluctuations in financial markets"
    assert cont["verdict_count"] == 3
    assert cont["failed_verdict_count"] == 0
    assert cont["passed_verdict_count"] == 3

    bouchaud_mezard = next(entry for entry in registry["entries"] if entry["id"] == "bouchaud-mezard")
    assert bouchaud_mezard["status"] == "complete"
    assert bouchaud_mezard["bundle"] == "docs/studies/bouchaud-mezard/verdict-bundle.json"
    assert bouchaud_mezard["predictions"] == "docs/studies/bouchaud-mezard/PREDICTIONS-locked.md"


def test_registry_validator_rejects_duplicate_ids_and_absolute_paths():
    registry = build_study_registry(STUDIES_ROOT, repo=REPO_ROOT)
    validation = validate_study_registry(registry, repo=REPO_ROOT)
    assert validation["ok"] is True

    duplicate = json.loads(json.dumps(registry))
    duplicate["entries"].append(dict(duplicate["entries"][0]))
    duplicate_result = validate_study_registry(duplicate, repo=REPO_ROOT)
    assert duplicate_result["ok"] is False
    assert any("duplicate entry id" in issue for issue in duplicate_result["issues"])

    absolute_path = json.loads(json.dumps(registry))
    absolute_path["entries"][0]["study_dir"] = str(REPO_ROOT / "docs/studies/cont-bouchaud")
    absolute_result = validate_study_registry(absolute_path, repo=REPO_ROOT)
    assert absolute_result["ok"] is False
    assert any("study_dir must be a repo-relative path" in issue for issue in absolute_result["issues"])


def test_doctor_validates_bundles_but_does_not_fail_pending_prediction_locks():
    result = diagnose_study_corpus(
        STUDIES_ROOT,
        repo=REPO_ROOT,
        registry_path=STUDIES_ROOT / "REGISTRY.json",
        index_path=STUDIES_ROOT / "INDEX.md",
    )

    assert result["ok"] is True
    assert result["summary"]["complete_count"] >= 78
    assert result["summary"]["failed_bundle_count"] == 0
    assert result["summary"]["failed_registry_issue_count"] == 0
    assert result["summary"]["registry_matches_committed"] is True
    assert result["summary"]["index_matches_committed"] is True
    assert "bouchaud-mezard" not in result["pending_ids"]


def test_index_markdown_states_boundary_and_lists_pending_studies():
    registry = build_study_registry(STUDIES_ROOT, repo=REPO_ROOT)
    markdown = render_study_index_markdown(registry)

    assert markdown.startswith("# MyMoMo Study Corpus Index\n")
    assert "not a scientific truth certificate" in markdown
    assert "| Study | Status | Verdicts | Failed | Headline |" in markdown
    assert "`cont-bouchaud`" in markdown
    assert "`axtell-firms`" in markdown


def test_cli_build_writes_registry_and_index(tmp_path: Path):
    registry_path = tmp_path / "REGISTRY.json"
    index_path = tmp_path / "INDEX.md"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.study_corpus",
            "build",
            "docs/studies",
            "--repo",
            str(REPO_ROOT),
            "--registry",
            str(registry_path),
            "--index",
            str(index_path),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)
    assert result["ok"] is True
    assert result["summary"]["complete_count"] >= 78
    assert registry_path.exists()
    assert index_path.exists()


def test_cli_build_resolves_relative_output_paths_against_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    study_dir = repo / "docs/studies/pending-study"
    study_dir.mkdir(parents=True)
    (study_dir / "PREDICTIONS-locked.md").write_text("# Locked\n", encoding="utf-8")

    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir()

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.study_corpus",
            "build",
            "docs/studies",
            "--repo",
            str(repo),
            "--registry",
            "docs/studies/REGISTRY.json",
            "--index",
            "docs/studies/INDEX.md",
        ],
        cwd=outside_cwd,
        check=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        text=True,
    )

    result = json.loads(completed.stdout)
    assert result["ok"] is True
    assert (repo / "docs/studies/REGISTRY.json").exists()
    assert (repo / "docs/studies/INDEX.md").exists()
    assert not (outside_cwd / "docs/studies/REGISTRY.json").exists()
    assert not (outside_cwd / "docs/studies/INDEX.md").exists()


def test_cli_doctor_prints_json_result():
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.study_corpus",
            "doctor",
            "docs/studies",
            "--repo",
            str(REPO_ROOT),
            "--registry",
            "docs/studies/REGISTRY.json",
            "--index",
            "docs/studies/INDEX.md",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)

    assert result["ok"] is True
    assert result["summary"]["complete_count"] >= 78
    assert result["summary"]["registry_matches_committed"] is True
    assert result["summary"]["index_matches_committed"] is True


def test_doctor_rejects_stale_committed_index(tmp_path: Path):
    repo = tmp_path / "repo"
    study_dir = repo / "docs/studies/pending-study"
    study_dir.mkdir(parents=True)
    (study_dir / "PREDICTIONS-locked.md").write_text("# Locked\n", encoding="utf-8")

    registry = build_study_registry(repo / "docs/studies", repo=repo)
    registry_path = repo / "docs/studies/REGISTRY.json"
    index_path = repo / "docs/studies/INDEX.md"
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    index_path.write_text("# stale\n", encoding="utf-8")

    result = diagnose_study_corpus(
        repo / "docs/studies",
        repo=repo,
        registry_path=registry_path,
        index_path=index_path,
    )

    assert result["ok"] is False
    assert result["summary"]["registry_matches_committed"] is True
    assert result["summary"]["index_matches_committed"] is False
    assert "committed index does not match current study corpus" in result["registry_validation"]["issues"]


def test_committed_registry_and_index_match_current_corpus():
    registry_path = STUDIES_ROOT / "REGISTRY.json"
    index_path = STUDIES_ROOT / "INDEX.md"

    assert registry_path.exists()
    assert index_path.exists()

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    expected = build_study_registry(STUDIES_ROOT, repo=REPO_ROOT)

    assert registry == expected
    assert index_path.read_text(encoding="utf-8") == render_study_index_markdown(expected)


@pytest.mark.parametrize(
    "bad_root",
    [
        "docs/studies/missing",
        "docs/studies/cont-bouchaud/verdict-bundle.json",
    ],
)
def test_doctor_reports_missing_or_non_directory_study_root(bad_root: str):
    result = diagnose_study_corpus(REPO_ROOT / bad_root, repo=REPO_ROOT)

    assert result["ok"] is False
    assert any("studies root" in issue for issue in result["issues"])
