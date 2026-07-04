"""Tests for the L3 reproduction-bundle primitive (ADR-023 L3 / ladder #6)."""
from __future__ import annotations

import json
from pathlib import Path

import abm_auto.gis._repro_bundle as repro_bundle
from abm_auto.verification.gate import Verdict
from abm_auto.gis._repro_bundle import SCHEMA, build_bundle, verdict_to_dict, write_bundle

REPO_ROOT = Path(__file__).resolve().parents[2]
ANSHUKA_BUNDLE = REPO_ROOT / "docs/reproduce/anshuka-2026-real-dem/verdict-bundle.json"


def test_verdict_to_dict_carries_value_and_threshold():
    v = Verdict(passed=True, tier="refutation", gate_name="H1",
                reasons=[], salient_number=(15.2, 35.0))
    d = verdict_to_dict(v)
    assert d == {"gate": "H1", "tier": "refutation", "passed": True,
                 "salient_number": [15.2, 35.0], "reasons": [], "evidence": None}


def test_build_bundle_fingerprints_files_strong(tmp_path):
    dem = tmp_path / "dem.tif"; dem.write_bytes(b"\x00\x01\x02 fake dem bytes")
    pred = tmp_path / "PREDICTIONS-locked.md"; pred.write_text("H1: ...", encoding="utf-8")
    verdicts = [
        Verdict(passed=True, tier="refutation", gate_name="H1 (P1 converge)",
                salient_number=(15.2, 35.0)),
        Verdict(passed=False, tier="refutation", gate_name="H3 (P3 widen)",
                reasons=["Δ 18 < 20"], salient_number=(18.0, 20.0)),
    ]
    b = build_bundle(
        paper={"title": "Anshuka 2026", "doi": "10.1007/s13753-026-00729-7"},
        headline="EARNED",
        verdicts=verdicts,
        data_artifacts={"ba_dem": dem},
        doc_artifacts={"predictions": pred},
        repo=tmp_path,
    )
    assert b["schema"] == SCHEMA
    assert b["headline"] == "EARNED"
    assert b["paper"]["doi"].startswith("10.1007")
    # data file → strong sha256 fingerprint
    assert b["data"]["ba_dem"]["replay"] == "strong"
    assert b["data"]["ba_dem"]["kind"] == "file"
    assert len(b["data"]["ba_dem"]["sha256"]) == 64
    assert b["docs"]["predictions"]["replay"] == "strong"
    # verdicts serialized with (value, threshold)
    assert [v["gate"] for v in b["verdicts"]] == ["H1 (P1 converge)", "H3 (P3 widen)"]
    assert b["verdicts"][0]["passed"] is True
    assert b["verdicts"][1]["salient_number"] == [18.0, 20.0]
    # env present
    assert "python" in b["env"]


def test_build_bundle_detects_data_tamper(tmp_path):
    dem = tmp_path / "dem.tif"; dem.write_bytes(b"original")
    common = dict(paper={"title": "x"}, headline="EARNED", verdicts=[],
                  doc_artifacts={}, repo=tmp_path)
    h1 = build_bundle(data_artifacts={"dem": dem}, **common)["data"]["dem"]["sha256"]
    dem.write_bytes(b"tampered")                       # a reviewer re-fetches different bytes
    h2 = build_bundle(data_artifacts={"dem": dem}, **common)["data"]["dem"]["sha256"]
    assert h1 != h2                                    # the fingerprint catches it


def test_write_bundle_roundtrips(tmp_path):
    b = build_bundle(paper={"t": "x"}, headline="NOT YET", verdicts=[],
                     data_artifacts={}, doc_artifacts={}, repo=tmp_path)
    p = write_bundle(b, tmp_path / "verdict-bundle.json")
    assert json.loads(p.read_text(encoding="utf-8"))["schema"] == SCHEMA


def test_committed_anshuka_l3_bundle_passes_integrity_gate():
    result = repro_bundle.validate_repro_bundle_file(ANSHUKA_BUNDLE, repo=REPO_ROOT)

    assert result["ok"], result["issues"]
    assert result["verdict_count"] == 5
    assert result["failed_verdict_count"] == 2
    assert result["doc_hashes_checked"] >= 3
    assert result["data_fingerprint_count"] >= 1

    ok, desc = repro_bundle.repro_bundle_integrity_gate(ANSHUKA_BUNDLE, repo=REPO_ROOT)
    assert ok, desc
    assert "L3 bundle integrity gate passed" in desc
    assert "not a rerun of the reproduction" in desc


def test_validate_repro_bundle_rejects_absolute_local_paths():
    bundle = json.loads(ANSHUKA_BUNDLE.read_text(encoding="utf-8"))
    bundle["docs"]["predictions_locked"]["path"] = str(
        REPO_ROOT / "docs/reproduce/anshuka-2026-real-dem/PREDICTIONS-locked.md"
    )

    result = repro_bundle.validate_repro_bundle(bundle, repo=REPO_ROOT)

    assert not result["ok"]
    assert any("absolute local path" in issue for issue in result["issues"])


def test_validate_repro_bundle_detects_stale_doc_hash():
    bundle = json.loads(ANSHUKA_BUNDLE.read_text(encoding="utf-8"))
    bundle["docs"]["findings"]["sha256"] = "0" * 64

    result = repro_bundle.validate_repro_bundle(bundle, repo=REPO_ROOT)

    assert not result["ok"]
    assert any("sha256 mismatch" in issue for issue in result["issues"])


def _minimal_l3_bundle(tmp_path, **extra_kwargs):
    """A schema-valid synthetic bundle (predictions_locked/findings/design_spec docs +
    one data file) usable as a base for the optional-carrier tests."""
    dem = tmp_path / "dem.tif"; dem.write_bytes(b"\x00\x01 fake dem")
    docs = {}
    for name in ("predictions_locked", "findings", "design_spec"):
        p = tmp_path / f"{name}.md"; p.write_text(f"{name}: ...", encoding="utf-8")
        docs[name] = p
    verdicts = [
        Verdict(passed=True, tier="refutation", gate_name="H1",
                salient_number=(15.2, 35.0)),
    ]
    return build_bundle(
        paper={"title": "Anshuka 2026", "doi": "10.1007/s13753-026-00729-7"},
        headline="EARNED",
        verdicts=verdicts,
        data_artifacts={"ba_dem": dem},
        doc_artifacts=docs,
        repo=tmp_path,
        **extra_kwargs,
    )


def test_build_bundle_with_odd_citations_benchmark_validates(tmp_path):
    odd = tmp_path / "ODD-protocol.md"; odd.write_text("ODD: ...", encoding="utf-8")
    citations = ["10.1007/s13753-026-00729-7", "Grimm et al. 2020 ODD"]
    benchmark = {"tool": "mesa", "archetype": "diffusion",
                 "metric": "adoption_rate", "value": 0.42}

    # baseline (no optional carriers) for the doc-hash delta comparison
    base = _minimal_l3_bundle(tmp_path)
    base_path = write_bundle(base, tmp_path / "base.json")
    base_result = repro_bundle.validate_repro_bundle_file(base_path, repo=tmp_path)
    assert base_result["ok"], base_result["issues"]

    b = _minimal_l3_bundle(tmp_path, odd=odd, citations=citations, benchmark=benchmark)
    # odd fingerprinted into docs exactly like the other docs
    assert b["docs"]["odd"]["replay"] == "strong"
    assert b["docs"]["odd"]["kind"] == "file"
    assert len(b["docs"]["odd"]["sha256"]) == 64
    # citations / benchmark round-trip verbatim
    assert b["citations"] == citations
    assert b["benchmark"] == benchmark

    path = write_bundle(b, tmp_path / "verdict-bundle.json")
    result = repro_bundle.validate_repro_bundle_file(path, repo=tmp_path)
    assert result["ok"], result["issues"]
    # odd was hashed → exactly one more doc hash than the baseline bundle
    assert result["doc_hashes_checked"] == base_result["doc_hashes_checked"] + 1

    ok, desc = repro_bundle.repro_bundle_integrity_gate(path, repo=tmp_path)
    assert ok, desc

    # round-trip through JSON preserves citations/benchmark verbatim
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["citations"] == citations
    assert loaded["benchmark"] == benchmark


def test_build_bundle_without_optional_carriers_still_validates(tmp_path):
    b = _minimal_l3_bundle(tmp_path)
    assert "odd" not in b["docs"]
    assert "citations" not in b
    assert "benchmark" not in b

    path = write_bundle(b, tmp_path / "verdict-bundle.json")
    result = repro_bundle.validate_repro_bundle_file(path, repo=tmp_path)
    assert result["ok"], result["issues"]
    ok, desc = repro_bundle.repro_bundle_integrity_gate(path, repo=tmp_path)
    assert ok, desc


def test_validate_repro_bundle_flags_malformed_citations(tmp_path):
    b = _minimal_l3_bundle(tmp_path)
    b["citations"] = ["", 5]

    result = repro_bundle.validate_repro_bundle(b, repo=tmp_path)

    assert not result["ok"]
    assert any("citations" in issue for issue in result["issues"])


def test_validate_repro_bundle_flags_malformed_benchmark(tmp_path):
    b = _minimal_l3_bundle(tmp_path)
    b["benchmark"] = ["not", "a", "dict"]

    result = repro_bundle.validate_repro_bundle(b, repo=tmp_path)

    assert not result["ok"]
    assert any("benchmark" in issue for issue in result["issues"])
