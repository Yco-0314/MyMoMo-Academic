"""Tests for provenance — replayable credentials (ADR-013 candidate 3).

Core guarantees under test:
  - fingerprint is DETERMINISTIC (same artifact → same hash) and SENSITIVE
    (any change → different hash) — the property that makes a credential
    checkable and makes fabrication (hash mismatch) visible.
  - build_provenance preserves tier-honesty (refutation stays refutation)
    and the tier-separated verification_clear.
  - file artifacts get strong replay; in-memory get weak (stated, not hidden).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from abm_auto.analysis.critical_slowing_down import critical_slowing_down
from abm_auto.analysis.null_gate import NullGate
from abm_auto.codegen.anti_pattern_gate import AntiPatternGate
from abm_auto.verification.harness import Harness
from abm_auto.verification.provenance import (
    Provenance,
    build_provenance,
    fingerprint,
)


# ── fingerprint: determinism + sensitivity ──────────────────────────────


def test_fingerprint_file_deterministic_and_strong(tmp_path: Path) -> None:
    f = tmp_path / "a.csv"
    f.write_text("tick,x\n0,1\n1,2\n")
    fp1 = fingerprint(f)
    fp2 = fingerprint(f)
    assert fp1 == fp2                      # deterministic
    assert fp1["kind"] == "file"
    assert fp1["replay"] == "strong"       # file → cross-machine
    assert len(fp1["sha256"]) == 64


def test_fingerprint_file_detects_change(tmp_path: Path) -> None:
    f = tmp_path / "a.csv"
    f.write_text("tick,x\n0,1\n")
    h1 = fingerprint(f)["sha256"]
    f.write_text("tick,x\n0,999\n")        # tamper
    h2 = fingerprint(f)["sha256"]
    assert h1 != h2                        # any change → different hash


def test_fingerprint_code_files() -> None:
    fp = fingerprint({"core/model.py": "class M: pass\n"})
    assert fp["kind"] == "code_files"
    assert fp["replay"] == "weak"
    # order-independent: same files in different dict order → same hash
    a = fingerprint({"x.py": "1", "y.py": "2"})
    b = fingerprint({"y.py": "2", "x.py": "1"})
    assert a["sha256"] == b["sha256"]


def test_fingerprint_mapping_and_ndarray() -> None:
    m = fingerprint({"n_params": 3, "n_flat_params": 0})
    assert m["kind"] == "mapping"
    arr = fingerprint(np.array([1.0, 2.0, 3.0]))
    assert arr["kind"] == "ndarray"
    assert arr["shape"] == [3]
    # sensitivity: a changed element changes the hash
    assert fingerprint(np.array([1.0, 2.0, 3.0]))["sha256"] != \
        fingerprint(np.array([1.0, 2.0, 4.0]))["sha256"]


def test_fingerprint_missing_file_is_weak(tmp_path: Path) -> None:
    fp = fingerprint(tmp_path / "nope.csv")
    assert fp["sha256"] is None
    assert fp["replay"] == "weak"


# ── build_provenance from a real HarnessReport ──────────────────────────


def _stat(s: np.ndarray) -> float:
    return critical_slowing_down(s).ews_strength


def _rising(n: int = 200) -> np.ndarray:
    rng = np.random.default_rng(0)
    x = np.zeros(n)
    a = np.linspace(0.1, 0.95, n)
    for t in range(1, n):
        x[t] = a[t] * x[t - 1] + rng.normal(0, 0.1)
    return x


def test_build_provenance_tier_honest() -> None:
    artifacts = {
        "source_code": {"core/model.py": "class M: pass\n"},
        "scalar_trajectory": _rising(),
    }
    report = Harness().run([AntiPatternGate(), NullGate(_stat, seed=1)], artifacts)
    prov = build_provenance(report, artifacts)
    assert isinstance(prov, Provenance)

    by_gate = {g["gate"]: g for g in prov.gates}
    # anti_pattern is verification; surrogate_null is refutation — tiers preserved
    assert by_gate["anti_pattern"]["tier"] == "verification"
    assert by_gate["surrogate_null"]["tier"] == "refutation"
    # every artifact fingerprinted
    assert set(prov.artifacts) == {"source_code", "scalar_trajectory"}
    assert prov.verification_clear is True


def test_provenance_writes_and_roundtrips(tmp_path: Path) -> None:
    import json

    artifacts = {"source_code": {"core/model.py": "class M: pass\n"}}
    report = Harness().run([AntiPatternGate()], artifacts)
    prov = build_provenance(report, artifacts)
    out = prov.write(tmp_path / "provenance.json")
    loaded = json.loads(out.read_text())
    assert loaded["schema"] == "abm-auto/provenance/v1"
    assert loaded["gates"][0]["gate"] == "anti_pattern"
    assert "sha256" in loaded["artifacts"]["source_code"]


def test_fabrication_visible_via_hash_mismatch(tmp_path: Path) -> None:
    """The anti-fabrication property: a credential's artifact hash, on
    replay against a tampered artifact, no longer matches."""
    f = tmp_path / "sim.csv"
    f.write_text("tick,x\n0,1\n")
    artifacts = {"source_code": {"core/model.py": "class M: pass\n"}}
    report = Harness().run([AntiPatternGate()], artifacts)
    prov = build_provenance(report, artifacts)
    recorded = prov.artifacts["source_code"]["sha256"]
    # tamper the artifact, re-fingerprint → mismatch exposes the change
    tampered = fingerprint({"core/model.py": "class M: pass  # changed\n"})["sha256"]
    assert recorded != tampered
