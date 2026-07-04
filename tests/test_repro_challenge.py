from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from abm_auto.repro_challenge import (
    ANSWER_SCHEMA,
    PRODUCER_SCHEMA,
    REGISTRY_SCHEMA,
    SCHEMA,
    build_challenge_pack,
    build_challenge_pack_from_producer_spec,
    audit_registry_discovery,
    build_answer_template,
    diagnose_challenge_workspace,
    discover_challenge_registry,
    grade_challenge_answer,
    list_challenge_registry,
    repro_challenge_gate,
    render_challenge_registry_report,
    run_challenge_registry,
    validate_challenge_producer_spec,
    validate_challenge_producer_spec_file,
    validate_challenge_pack,
    validate_challenge_pack_file,
    validate_challenge_registry,
    validate_challenge_registry_file,
    write_challenge_pack,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MIR_DOGFOOD_DIR = REPO_ROOT / "docs/reproduce/autodata-challenges/mir-v0-half-a"
MIR_DOGFOOD_PACK = MIR_DOGFOOD_DIR / "challenge-pack.json"
MIR_DOGFOOD_ANSWER = MIR_DOGFOOD_DIR / "answer-codex.json"
MIR_DOGFOOD_PRODUCER = MIR_DOGFOOD_DIR / "producer-spec.json"
FAILURE_PACK_CHALLENGE_DIR = REPO_ROOT / "docs/reproduce/autodata-challenges/failure-pack-example"
FAILURE_PACK_CHALLENGE_PACK = FAILURE_PACK_CHALLENGE_DIR / "challenge-pack.json"
FAILURE_PACK_CHALLENGE_ANSWER = FAILURE_PACK_CHALLENGE_DIR / "answer-codex.json"
FAILURE_PACK_CHALLENGE_PRODUCER = FAILURE_PACK_CHALLENGE_DIR / "producer-spec.json"
CHALLENGE_REGISTRY = REPO_ROOT / "docs/reproduce/autodata-challenges/registry.json"


def _artifacts(tmp_path: Path) -> dict[str, Path]:
    pred = tmp_path / "PREDICTIONS-locked.md"
    findings = tmp_path / "FINDINGS.md"
    results = tmp_path / "results.json"
    pred.write_text("P1 locked: should pass\nP2 locked: should miss\n", encoding="utf-8")
    findings.write_text("P1: PASS\nP2: MISS\n", encoding="utf-8")
    results.write_text('{"p1": true, "p2": false}\n', encoding="utf-8")
    return {
        "predictions_locked": pred,
        "findings": findings,
        "results": results,
    }


def _tasks() -> list[dict]:
    return [
        {
            "id": "verdict-summary",
            "prompt": "Report the locked P1/P2 verdicts using the evidence.",
            "required_artifacts": ["predictions_locked", "findings"],
            "expected_claims": [
                {"id": "P1", "verdict": "PASS"},
                {"id": "P2", "verdict": "MISS"},
            ],
        }
    ]


def _pack(tmp_path: Path) -> dict:
    return build_challenge_pack(
        challenge_id="synthetic-verdicts-v1",
        title="Synthetic Verdict Challenge",
        source={"kind": "synthetic-study", "reference": "local fixture"},
        artifacts=_artifacts(tmp_path),
        tasks=_tasks(),
        repo=tmp_path,
    )


def _answer(**overrides) -> dict:
    answer = {
        "schema": ANSWER_SCHEMA,
        "task_id": "verdict-summary",
        "claims": [
            {"id": "P1", "verdict": "PASS"},
            {"id": "P2", "verdict": "MISS"},
        ],
        "citations": {
            "P1": ["findings"],
            "P2": ["findings", "predictions_locked"],
        },
    }
    answer.update(overrides)
    return answer


def test_build_challenge_pack_hashes_artifacts_with_portable_paths(tmp_path):
    pack = _pack(tmp_path)

    assert pack["schema"] == SCHEMA
    assert pack["challenge_mode"] == "evidence_answering"
    assert pack["challenge_id"] == "synthetic-verdicts-v1"
    assert pack["artifacts"]["findings"]["path"] == "FINDINGS.md"
    assert pack["artifacts"]["findings"]["kind"] == "file"
    assert pack["artifacts"]["findings"]["replay"] == "strong"
    assert len(pack["artifacts"]["findings"]["sha256"]) == 64

    result = validate_challenge_pack(pack, repo=tmp_path)

    assert result["ok"], result["issues"]
    assert result["artifact_hashes_checked"] == 3
    assert result["task_count"] == 1
    assert result["expected_claim_count"] == 2


def test_write_challenge_pack_roundtrips_json(tmp_path):
    pack = _pack(tmp_path)

    path = write_challenge_pack(pack, tmp_path / "challenge-pack.json")

    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["schema"] == SCHEMA
    assert loaded["tasks"][0]["expected_claims"][1]["verdict"] == "MISS"


def test_validate_challenge_pack_rejects_absolute_paths_and_stale_hashes(tmp_path):
    absolute = _pack(tmp_path)
    absolute["artifacts"]["findings"]["path"] = str(tmp_path / "FINDINGS.md")

    absolute_result = validate_challenge_pack(absolute, repo=tmp_path)

    assert not absolute_result["ok"]
    assert any("absolute local path" in issue for issue in absolute_result["issues"])

    stale = _pack(tmp_path)
    stale["artifacts"]["findings"]["sha256"] = "0" * 64

    stale_result = validate_challenge_pack(stale, repo=tmp_path)

    assert not stale_result["ok"]
    assert any("sha256 mismatch" in issue for issue in stale_result["issues"])


def test_validate_challenge_pack_rejects_unknown_artifacts_and_bad_verdicts(tmp_path):
    pack = _pack(tmp_path)
    pack["tasks"][0]["required_artifacts"].append("missing-artifact")
    pack["tasks"][0]["expected_claims"].append({"id": "P3", "verdict": "TRUE"})

    result = validate_challenge_pack(pack, repo=tmp_path)

    assert not result["ok"]
    assert any("unknown artifact" in issue for issue in result["issues"])
    assert any("invalid verdict" in issue for issue in result["issues"])


def test_grade_challenge_answer_passes_when_claims_and_citations_match(tmp_path):
    result = grade_challenge_answer(_pack(tmp_path), _answer())

    assert result == {
        "ok": True,
        "issues": [],
        "task_id": "verdict-summary",
        "matched_claims": 2,
        "required_claims": 2,
        "salient_number": [2.0, 2.0],
    }


def test_grade_challenge_answer_rejects_fabricated_or_uncited_answers(tmp_path):
    fabricated = _answer(
        claims=[
            {"id": "P1", "verdict": "PASS"},
            {"id": "P2", "verdict": "PASS"},
            {"id": "P9", "verdict": "PASS"},
        ],
        citations={"P1": ["findings"]},
    )

    result = grade_challenge_answer(_pack(tmp_path), fabricated)

    assert not result["ok"]
    assert any("P2 expected MISS, got PASS" in issue for issue in result["issues"])
    assert any("P2 lacks citation" in issue for issue in result["issues"])
    assert any("unexpected claim P9" in issue for issue in result["issues"])


def test_repro_challenge_gate_reports_scope_ceiling(tmp_path):
    ok, desc = repro_challenge_gate(_pack(tmp_path), _answer(), repo=tmp_path)

    assert ok, desc
    assert "challenge gate passed" in desc
    assert "not a reproduction rerun" in desc
    assert "not a scientific truth certificate" in desc


def test_committed_mir_v0_dogfood_pack_validates_and_grades():
    pack = json.loads(MIR_DOGFOOD_PACK.read_text(encoding="utf-8"))
    answer = json.loads(MIR_DOGFOOD_ANSWER.read_text(encoding="utf-8"))

    validation = validate_challenge_pack_file(MIR_DOGFOOD_PACK, repo=REPO_ROOT)
    grade = grade_challenge_answer(pack, answer)
    ok, desc = repro_challenge_gate(pack, answer, repo=REPO_ROOT)

    assert validation["ok"], validation["issues"]
    assert validation["artifact_hashes_checked"] == 3
    assert validation["expected_claim_count"] == 4
    assert grade["ok"], grade["issues"]
    assert grade["matched_claims"] == 4
    assert ok, desc
    assert "not a reproduction rerun" in desc


def test_committed_mir_v0_dogfood_pack_uses_evidence_foundry_identity():
    producer = json.loads(MIR_DOGFOOD_PRODUCER.read_text(encoding="utf-8"))
    pack = json.loads(MIR_DOGFOOD_PACK.read_text(encoding="utf-8"))

    assert producer["extra"]["phase"] == "MyMoMo Evidence Foundry Challenge Harness Phase 1.1"
    assert pack["extra"]["phase"] == "MyMoMo Evidence Foundry Challenge Harness Phase 1.1"
    assert "AutoData" not in json.dumps(producer, sort_keys=True)
    assert "AutoData" not in json.dumps(pack, sort_keys=True)


def test_repro_challenge_module_cli_validates_and_grades_dogfood_pack():
    validate = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.repro_challenge",
            "validate",
            str(MIR_DOGFOOD_PACK),
            "--repo",
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert validate.returncode == 0, validate.stderr
    assert json.loads(validate.stdout)["ok"] is True

    grade = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.repro_challenge",
            "grade",
            str(MIR_DOGFOOD_PACK),
            str(MIR_DOGFOOD_ANSWER),
            "--repo",
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert grade.returncode == 0, grade.stderr
    assert json.loads(grade.stdout)["matched_claims"] == 4

    gate = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.repro_challenge",
            "gate",
            str(MIR_DOGFOOD_PACK),
            str(MIR_DOGFOOD_ANSWER),
            "--repo",
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert gate.returncode == 0, gate.stderr
    gate_output = json.loads(gate.stdout)
    assert gate_output["ok"] is True
    assert "not a reproduction rerun" in gate_output["description"]


def test_committed_challenge_registry_validates_and_lists_curriculum():
    registry = json.loads(CHALLENGE_REGISTRY.read_text(encoding="utf-8"))

    result = validate_challenge_registry_file(
        CHALLENGE_REGISTRY,
        repo=REPO_ROOT,
        grade_answers=True,
    )
    listed = list_challenge_registry(registry, domain="architecture", tag="mir")

    assert registry["schema"] == REGISTRY_SCHEMA
    assert result["ok"], result["issues"]
    assert result["entry_count"] == 2
    assert result["pack_validated_count"] == 2
    assert result["answer_graded_count"] == 2
    assert [entry["id"] for entry in listed] == ["mir-v0-half-a-evidence-answering-v1"]
    assert listed[0]["difficulty"] == "intro"


def test_validate_challenge_registry_rejects_duplicate_and_pack_mismatch():
    registry = {
        "schema": REGISTRY_SCHEMA,
        "title": "Broken Registry",
        "entries": [
            {
                "id": "wrong-id",
                "pack": "docs/reproduce/autodata-challenges/mir-v0-half-a/challenge-pack.json",
                "answer": "docs/reproduce/autodata-challenges/mir-v0-half-a/answer-codex.json",
                "domain": "architecture",
                "difficulty": "intro",
                "tags": ["mir"],
            },
            {
                "id": "wrong-id",
                "pack": "/absolute/challenge-pack.json",
                "domain": "architecture",
                "difficulty": "impossible",
                "tags": ["mir"],
            },
        ],
    }

    result = validate_challenge_registry(registry, repo=REPO_ROOT)

    assert not result["ok"]
    assert any("does not match pack challenge_id" in issue for issue in result["issues"])
    assert any("duplicate id" in issue for issue in result["issues"])
    assert any("uses absolute local path" in issue for issue in result["issues"])
    assert any("invalid difficulty" in issue for issue in result["issues"])


def test_repro_challenge_module_cli_validates_and_lists_registry():
    validate = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.repro_challenge",
            "registry-validate",
            str(CHALLENGE_REGISTRY),
            "--repo",
            str(REPO_ROOT),
            "--grade-answers",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert validate.returncode == 0, validate.stderr
    assert json.loads(validate.stdout)["entry_count"] == 2

    listing = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.repro_challenge",
            "registry-list",
            str(CHALLENGE_REGISTRY),
            "--domain",
            "architecture",
            "--tag",
            "mir",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert listing.returncode == 0, listing.stderr
    entries = json.loads(listing.stdout)["entries"]
    assert entries[0]["id"] == "mir-v0-half-a-evidence-answering-v1"


def test_committed_producer_spec_rebuilds_mir_dogfood_pack():
    producer = json.loads(MIR_DOGFOOD_PRODUCER.read_text(encoding="utf-8"))
    committed = json.loads(MIR_DOGFOOD_PACK.read_text(encoding="utf-8"))

    producer_validation = validate_challenge_producer_spec_file(
        MIR_DOGFOOD_PRODUCER,
        repo=REPO_ROOT,
    )
    produced = build_challenge_pack_from_producer_spec(producer, repo=REPO_ROOT)
    pack_validation = validate_challenge_pack(produced, repo=REPO_ROOT)

    assert producer["schema"] == PRODUCER_SCHEMA
    assert producer_validation["ok"], producer_validation["issues"]
    assert producer_validation["artifact_count"] == 3
    assert producer_validation["expected_claim_count"] == 4
    assert produced == committed
    assert pack_validation["ok"], pack_validation["issues"]


def test_validate_challenge_producer_spec_rejects_bad_paths_and_claims():
    producer = {
        "schema": PRODUCER_SCHEMA,
        "challenge_id": "bad-producer",
        "title": "Bad Producer",
        "source": {"kind": "fixture"},
        "artifacts": {
            "findings": "/absolute/FINDINGS.md",
        },
        "tasks": [
            {
                "id": "bad-task",
                "prompt": "Bad task",
                "required_artifacts": ["missing"],
                "expected_claims": [{"id": "P1", "verdict": "TRUE"}],
            }
        ],
    }

    result = validate_challenge_producer_spec(producer, repo=REPO_ROOT)

    assert not result["ok"]
    assert any("absolute local path" in issue for issue in result["issues"])
    assert any("unknown artifact" in issue for issue in result["issues"])
    assert any("invalid verdict" in issue for issue in result["issues"])


def test_repro_challenge_module_cli_produces_pack_from_spec(tmp_path):
    out_path = tmp_path / "challenge-pack.json"
    produce = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.repro_challenge",
            "produce",
            str(MIR_DOGFOOD_PRODUCER),
            "--repo",
            str(REPO_ROOT),
            "--out",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert produce.returncode == 0, produce.stderr
    result = json.loads(produce.stdout)
    assert result["ok"] is True
    assert result["path"] == str(out_path)
    assert json.loads(out_path.read_text(encoding="utf-8")) == json.loads(
        MIR_DOGFOOD_PACK.read_text(encoding="utf-8")
    )


def test_committed_failure_pack_challenge_validates_and_grades():
    producer = json.loads(FAILURE_PACK_CHALLENGE_PRODUCER.read_text(encoding="utf-8"))
    committed = json.loads(FAILURE_PACK_CHALLENGE_PACK.read_text(encoding="utf-8"))
    answer = json.loads(FAILURE_PACK_CHALLENGE_ANSWER.read_text(encoding="utf-8"))

    producer_validation = validate_challenge_producer_spec_file(
        FAILURE_PACK_CHALLENGE_PRODUCER,
        repo=REPO_ROOT,
    )
    produced = build_challenge_pack_from_producer_spec(producer, repo=REPO_ROOT)
    pack_validation = validate_challenge_pack(committed, repo=REPO_ROOT)
    grade = grade_challenge_answer(committed, answer)

    assert producer["schema"] == PRODUCER_SCHEMA
    assert producer_validation["ok"], producer_validation["issues"]
    assert producer_validation["artifact_count"] == 2
    assert producer_validation["expected_claim_count"] == 3
    assert produced == committed
    assert pack_validation["ok"], pack_validation["issues"]
    assert grade["ok"], grade["issues"]


def test_discover_challenge_registry_matches_committed_registry():
    committed = json.loads(CHALLENGE_REGISTRY.read_text(encoding="utf-8"))

    discovered = discover_challenge_registry(
        REPO_ROOT / "docs/reproduce/autodata-challenges",
        repo=REPO_ROOT,
        title=committed["title"],
    )
    audit = audit_registry_discovery(
        committed,
        REPO_ROOT / "docs/reproduce/autodata-challenges",
        repo=REPO_ROOT,
    )

    assert discovered == committed
    assert audit == {
        "ok": True,
        "issues": [],
        "discovered_count": 2,
        "registered_count": 2,
        "missing_ids": [],
        "extra_ids": [],
    }


def test_audit_registry_discovery_reports_missing_and_extra_entries():
    registry = {
        "schema": REGISTRY_SCHEMA,
        "title": "Broken",
        "entries": [
            {
                "id": "extra",
                "pack": "docs/reproduce/autodata-challenges/extra/challenge-pack.json",
                "domain": "architecture",
                "difficulty": "intro",
                "tags": ["extra"],
            }
        ],
    }

    audit = audit_registry_discovery(
        registry,
        REPO_ROOT / "docs/reproduce/autodata-challenges",
        repo=REPO_ROOT,
    )

    assert not audit["ok"]
    assert audit["missing_ids"] == [
        "failure-pack-evidence-answering-v1",
        "mir-v0-half-a-evidence-answering-v1",
    ]
    assert audit["extra_ids"] == ["extra"]
    assert any("missing registered challenge" in issue for issue in audit["issues"])
    assert any("extra registered challenge" in issue for issue in audit["issues"])


def test_repro_challenge_module_cli_discovers_and_audits_registry():
    discover = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.repro_challenge",
            "registry-discover",
            "docs/reproduce/autodata-challenges",
            "--repo",
            str(REPO_ROOT),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert discover.returncode == 0, discover.stderr
    assert [entry["id"] for entry in json.loads(discover.stdout)["entries"]] == [
        "failure-pack-evidence-answering-v1",
        "mir-v0-half-a-evidence-answering-v1",
    ]

    audit = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.repro_challenge",
            "registry-audit",
            str(CHALLENGE_REGISTRY),
            "docs/reproduce/autodata-challenges",
            "--repo",
            str(REPO_ROOT),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert audit.returncode == 0, audit.stderr
    assert json.loads(audit.stdout)["ok"] is True


def test_run_challenge_registry_gates_all_registered_answers():
    registry = json.loads(CHALLENGE_REGISTRY.read_text(encoding="utf-8"))

    result = run_challenge_registry(registry, repo=REPO_ROOT)

    assert result["ok"], result["results"]
    assert result["entry_count"] == 2
    assert result["gated_count"] == 2
    assert result["failed_count"] == 0
    results_by_id = {entry["id"]: entry for entry in result["results"]}
    assert results_by_id["mir-v0-half-a-evidence-answering-v1"]["ok"] is True
    assert results_by_id["failure-pack-evidence-answering-v1"]["ok"] is True
    assert "not a reproduction rerun" in results_by_id["mir-v0-half-a-evidence-answering-v1"]["description"]


def test_run_challenge_registry_fails_bad_answer(tmp_path):
    bad_answer = json.loads(MIR_DOGFOOD_ANSWER.read_text(encoding="utf-8"))
    bad_answer["claims"][0]["verdict"] = "MISS"
    answer_path = tmp_path / "bad-answer.json"
    answer_path.write_text(json.dumps(bad_answer), encoding="utf-8")
    registry = {
        "schema": REGISTRY_SCHEMA,
        "title": "Bad Answer Registry",
        "entries": [
            {
                "id": "mir-v0-half-a-evidence-answering-v1",
                "pack": str(MIR_DOGFOOD_PACK),
                "answer": str(answer_path),
                "domain": "architecture",
                "difficulty": "intro",
                "tags": ["mir"],
            }
        ],
    }

    result = run_challenge_registry(registry, repo=REPO_ROOT)

    assert not result["ok"]
    assert result["failed_count"] == 1
    assert "expected PASS, got MISS" in result["results"][0]["description"]


def test_repro_challenge_module_cli_gates_registry():
    gate = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.repro_challenge",
            "registry-gate",
            str(CHALLENGE_REGISTRY),
            "--repo",
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert gate.returncode == 0, gate.stderr
    result = json.loads(gate.stdout)
    assert result["ok"] is True
    assert result["gated_count"] == 2


def test_build_answer_template_from_challenge_pack():
    pack = json.loads(MIR_DOGFOOD_PACK.read_text(encoding="utf-8"))

    template = build_answer_template(pack)

    assert template["schema"] == ANSWER_SCHEMA
    assert template["task_id"] == "mir-half-a-verdict-summary"
    assert [claim["id"] for claim in template["claims"]] == [
        "P1-field-identity",
        "P3-byte-identical-render",
        "P5-extensions-seam",
        "P7-zero-change",
    ]
    assert {claim["verdict"] for claim in template["claims"]} == {"INCONCLUSIVE"}
    assert template["citations"] == {
        "P1-field-identity": [],
        "P3-byte-identical-render": [],
        "P5-extensions-seam": [],
        "P7-zero-change": [],
    }


def test_repro_challenge_module_cli_writes_answer_template(tmp_path):
    out_path = tmp_path / "answer-template.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.repro_challenge",
            "answer-template",
            str(MIR_DOGFOOD_PACK),
            "--out",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["path"] == str(out_path)
    template = json.loads(out_path.read_text(encoding="utf-8"))
    assert template["claims"][0] == {"id": "P1-field-identity", "verdict": "INCONCLUSIVE"}


def test_render_challenge_registry_report_contains_gate_summary():
    registry = json.loads(CHALLENGE_REGISTRY.read_text(encoding="utf-8"))

    report = render_challenge_registry_report(registry, repo=REPO_ROOT)

    assert report.startswith("# MyMoMo Evidence Foundry Registry Report\n")
    assert "- Registry: MyMoMo Evidence Foundry Curriculum" in report
    assert "- Overall gate: PASS" in report
    assert "| mir-v0-half-a-evidence-answering-v1 | architecture | intro | PASS |" in report
    assert "not a reproduction rerun" in report


def test_discover_challenge_registry_uses_evidence_foundry_default_title():
    discovered = discover_challenge_registry(
        REPO_ROOT / "docs/reproduce/autodata-challenges",
        repo=REPO_ROOT,
    )

    assert discovered["title"] == "MyMoMo Evidence Foundry Curriculum"


def test_repro_challenge_gate_uses_evidence_foundry_language(tmp_path):
    ok, desc = repro_challenge_gate(_pack(tmp_path), _answer(), repo=tmp_path)

    assert ok is True
    assert desc.startswith("Evidence Foundry challenge gate passed")
    assert "answer/evidence alignment" in desc


def test_repro_challenge_module_cli_writes_registry_report(tmp_path):
    out_path = tmp_path / "registry-report.md"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.repro_challenge",
            "registry-report",
            str(CHALLENGE_REGISTRY),
            "--repo",
            str(REPO_ROOT),
            "--out",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["path"] == str(out_path)
    assert "Overall gate: PASS" in out_path.read_text(encoding="utf-8")


def test_diagnose_challenge_workspace_runs_all_evidence_foundry_checks():
    result = diagnose_challenge_workspace(
        CHALLENGE_REGISTRY,
        REPO_ROOT / "docs/reproduce/autodata-challenges",
        repo=REPO_ROOT,
    )

    assert result["ok"] is True
    assert result["registry_validation"]["ok"] is True
    assert result["discovery_audit"]["ok"] is True
    assert result["registry_gate"]["ok"] is True
    assert result["summary"] == {
        "entries": 2,
        "gated": 2,
        "failed": 0,
        "missing": 0,
        "extra": 0,
    }


def test_repro_challenge_module_cli_runs_doctor():
    doctor = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm_auto.repro_challenge",
            "doctor",
            str(CHALLENGE_REGISTRY),
            "docs/reproduce/autodata-challenges",
            "--repo",
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert doctor.returncode == 0, doctor.stderr
    result = json.loads(doctor.stdout)
    assert result["ok"] is True
    assert result["summary"]["gated"] == 2
