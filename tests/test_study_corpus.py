from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from abm_auto.repro_bundle import build_bundle, write_bundle
from abm_auto.study_corpus import (
    SCHEMA,
    build_study_registry,
    diagnose_study_corpus,
    discover_study_corpus,
    render_study_index_markdown,
    validate_study_registry,
)
from abm_auto.verification.gate import Verdict

REPO_ROOT = Path(__file__).resolve().parents[1]
STUDIES_ROOT = REPO_ROOT / "docs/studies"


def _lock_review_json(*, clauses=("P1", "P2")) -> str:
    items = []
    for clause in clauses:
        items.append({
            "clause_id": clause,
            "paper_claim": f"{clause} paper claim",
            "locked_metric": f"{clause} locked metric",
            "validity": "mis_specified" if clause == "P1" else "sound",
            "issue_kind": "direction_error" if clause == "P1" else None,
            "review_rationale": f"{clause} rationale",
            "requires_relock": clause == "P1",
        })
    return json.dumps({
        "schema": "abm-auto/lock-review/v1",
        "study_id": "construct-validity-demo",
        "timing": "prospective",
        "result_visibility": "no_results_seen",
        "items": items,
    })


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


def _v2_lock_review_json() -> str:
    return json.dumps({
        "schema": "abm-auto/lock-review/v2",
        "study_id": "v2-interpretation-demo",
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
                "review_rationale": "The metric is true but weak by construction.",
                "requires_relock": False,
            },
            {
                "clause_id": "P2",
                "paper_claim": "Doorway alternation appears.",
                "locked_metric": "alternation index >= 0.6",
                "validity": "sound",
                "construct_dimensions": _construct_dimensions(),
                "issue_kinds": [],
                "review_rationale": "The metric directly measures alternation.",
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
                "review_rationale": "The relation is present but the endpoint is fragile.",
                "requires_relock": False,
            },
        ],
    })


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


def test_registry_counts_miss_lock_separately_from_model_miss(tmp_path: Path):
    _run_git(tmp_path, "init")
    study_dir = tmp_path / "docs/studies/construct-validity-demo"
    study_dir.mkdir(parents=True)
    docs = {}
    for name in ("predictions_locked", "findings", "design_spec"):
        path = study_dir / f"{name}.md"
        path.write_text(f"# {name}\n", encoding="utf-8")
        docs[name] = path
    lock_commit = _commit_all(tmp_path, "lock predictions")
    lock_review = study_dir / "LOCK-REVIEW.json"
    lock_review.write_text(_lock_review_json(), encoding="utf-8")
    lock_review_commit = _commit_all(tmp_path, "review lock")
    data = study_dir / "results.json"
    data.write_text("{}\n", encoding="utf-8")
    implementation_commit = _commit_all(tmp_path, "implement model")
    (study_dir / "run.log").write_text("first run\n", encoding="utf-8")
    first_run_commit = _commit_all(tmp_path, "run model")

    bundle = build_bundle(
        paper={"title": "Construct validity demo", "authors": "x", "year": 2026},
        headline="Two misses with different meanings",
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
        data_artifacts={"results": data},
        doc_artifacts=docs,
        repo=tmp_path,
        lock_review=lock_review,
        lock_provenance={
            "lock_commit": lock_commit,
            "lock_review_commit": lock_review_commit,
            "implementation_commit": implementation_commit,
            "first_run_commit": first_run_commit,
        },
    )
    write_bundle(bundle, study_dir / "verdict-bundle.json")
    _commit_all(tmp_path, "commit bundle")

    registry = build_study_registry(tmp_path / "docs/studies", repo=tmp_path)

    entry = registry["entries"][0]
    assert entry["failed_verdict_count"] == 2
    assert entry["miss_lock_count"] == 1
    assert entry["miss_model_count"] == 1
    assert entry["uncertain_lock_count"] == 0
    assert entry["unclassified_miss_count"] == 0
    assert registry["summary"]["miss_lock_count"] == 1
    assert registry["summary"]["miss_model_count"] == 1
    assert registry["summary"]["unclassified_miss_count"] == 0


def test_registry_summarizes_v2_evidence_interpretation_counts(tmp_path: Path):
    study_dir = tmp_path / "docs/studies/v2-interpretation-demo"
    study_dir.mkdir(parents=True)
    docs = {}
    for name in ("predictions_locked", "findings", "design_spec"):
        path = study_dir / f"{name}.md"
        path.write_text(f"# {name}\n", encoding="utf-8")
        docs[name] = path
    lock_review = study_dir / "LOCK-REVIEW.json"
    lock_review.write_text(_v2_lock_review_json(), encoding="utf-8")
    data = study_dir / "results.json"
    data.write_text("{}\n", encoding="utf-8")

    bundle = build_bundle(
        paper={"title": "V2 interpretation demo", "authors": "x", "year": 2026},
        headline="V2 interpretation counts",
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
        data_artifacts={"results": data},
        doc_artifacts=docs,
        repo=tmp_path,
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
    write_bundle(bundle, study_dir / "verdict-bundle.json")

    registry = build_study_registry(tmp_path / "docs/studies", repo=tmp_path)
    validation = validate_study_registry(registry, repo=tmp_path)

    entry = registry["entries"][0]
    assert validation["ok"], validation["issues"]
    assert entry["evidence_interpretation_count"] == 3
    assert entry["weak_pass_count"] == 1
    assert entry["strong_pass_count"] == 0
    assert entry["not_run_count"] == 1
    assert entry["threshold_endpoint_miss_count"] == 1
    assert entry["miss_model_count"] == 0
    assert registry["summary"]["weak_pass_count"] == 1
    assert registry["summary"]["not_run_count"] == 1
    assert registry["summary"]["threshold_endpoint_miss_count"] == 1


def test_registry_does_not_emit_construct_validity_summary_without_lock_review(tmp_path: Path):
    study_dir = tmp_path / "docs/studies/unreviewed-default-sound-demo"
    study_dir.mkdir(parents=True)
    docs = {}
    for name in ("predictions_locked", "findings", "design_spec"):
        path = study_dir / f"{name}.md"
        path.write_text(f"# {name}\n", encoding="utf-8")
        docs[name] = path
    data = study_dir / "results.json"
    data.write_text("{}\n", encoding="utf-8")

    bundle = build_bundle(
        paper={"title": "Unreviewed default sound demo", "authors": "x", "year": 2026},
        headline="Default sound metadata without lock review is not a reviewed classification",
        verdicts=[
            Verdict(
                passed=False,
                tier="refutation",
                gate_name="P1",
                salient_number=(0.87, 0.90),
            ),
        ],
        data_artifacts={"results": data},
        doc_artifacts=docs,
        repo=tmp_path,
    )
    write_bundle(bundle, study_dir / "verdict-bundle.json")

    registry = build_study_registry(tmp_path / "docs/studies", repo=tmp_path)

    entry = registry["entries"][0]
    assert entry["failed_verdict_count"] == 1
    assert "construct_validity_verdict_count" not in entry
    assert "miss_lock_count" not in entry
    assert "miss_model_count" not in entry
    assert "construct_validity_verdict_count" not in registry["summary"]


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
