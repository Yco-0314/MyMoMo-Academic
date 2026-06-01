"""Provenance — replayable credentials for a HarnessReport (ADR-013 candidate 3).

What this is
------------
A structured, content-addressed record emitted from a HarnessReport so a
third party can VERIFY a result without trusting whoever (LLM / search /
human) generated it. For each Gate verdict it records {gate, tier,
passed, salient_number, reasons}; for each artifact it records a
deterministic fingerprint (hash). Replay = re-run the Gates on the same
artifacts, recompute the hashes, and check both against the credential.

What it is NOT (the honest ceiling)
-----------------------------------
This is an AUDITABILITY certificate, not a TRUTH certificate. It proves
"these Gates produced these verdicts on artifacts with these hashes, and
you can replay to confirm." It does NOT prove the finding is correct or
meaningful — a credential whose refutation Gates all passed still only
means "survived these challenges", never "verified true". The tier field
carries that distinction; provenance never upgrades it.

Why it catches fabrication
--------------------------
A fabricated result points to no artifact. In a credential, its
artifact-hash entry is absent or, on replay, fails to match — the
fabrication is structurally visible. This is the ADR-012 "artifact
before conclusion" rule made machine-checkable: trust moves from the
generator's word to a hash a third party can recompute.

Replayability scope (stated, not hidden)
----------------------------------------
- FILE artifacts (Path): sha256 of file bytes → reproducible across
  machines. Strong replay.
- IN-MEMORY artifacts (dict / ndarray / dataclass): sha256 of a canonical
  serialization → reproducible only where the artifact is retained (and,
  for floats, subject to the same platform). Weak replay: meaningful only
  if the artifact itself is archived alongside the credential.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def fingerprint(artifact: Any) -> dict:
    """Deterministic content fingerprint of one artifact.

    Returns {"kind": ..., "sha256": ..., "replay": "strong"|"weak"}.
    A single helper with a bounded set of artifact kinds — not a
    grab-bag accessor on a god-object. Unknown kinds get a best-effort
    repr hash tagged replay="weak" so nothing silently lacks a
    fingerprint.
    """
    # File path → hash the bytes (strong, cross-machine).
    if isinstance(artifact, Path):
        try:
            data = artifact.read_bytes()
            return {"kind": "file", "path": str(artifact),
                    "sha256": hashlib.sha256(data).hexdigest(), "replay": "strong"}
        except Exception:
            return {"kind": "file-missing", "path": str(artifact),
                    "sha256": None, "replay": "weak"}

    # Source-code dict {path: contents} → hash the sorted canonical form.
    if isinstance(artifact, dict) and all(isinstance(v, str) for v in artifact.values()):
        canon = json.dumps({k: artifact[k] for k in sorted(artifact)}, ensure_ascii=False)
        return {"kind": "code_files", "n_files": len(artifact),
                "sha256": hashlib.sha256(canon.encode("utf-8")).hexdigest(),
                "replay": "weak"}

    # Signal / mapping dict → canonical JSON (sorted keys), then hash.
    if isinstance(artifact, dict):
        try:
            canon = json.dumps(artifact, sort_keys=True, default=str, ensure_ascii=False)
            return {"kind": "mapping",
                    "sha256": hashlib.sha256(canon.encode("utf-8")).hexdigest(),
                    "replay": "weak"}
        except Exception:
            pass

    # numpy array → hash raw bytes + shape/dtype (weak: platform float repr).
    try:
        import numpy as np
        if isinstance(artifact, np.ndarray):
            h = hashlib.sha256()
            h.update(str(artifact.dtype).encode())
            h.update(str(artifact.shape).encode())
            h.update(artifact.tobytes())
            return {"kind": "ndarray", "shape": list(artifact.shape),
                    "dtype": str(artifact.dtype), "sha256": h.hexdigest(),
                    "replay": "weak"}
    except ImportError:
        pass

    # Fallback: repr hash, explicitly weak so it's never mistaken for strong.
    return {"kind": type(artifact).__name__,
            "sha256": hashlib.sha256(repr(artifact).encode("utf-8")).hexdigest(),
            "replay": "weak"}


@dataclass
class Provenance:
    """A replayable credential built from a HarnessReport + its artifacts."""

    verification_clear: bool
    gates: list[dict]              # per-verdict {gate, tier, passed, salient_number, reasons}
    artifacts: dict[str, dict]     # {family: fingerprint(...)}
    skipped: list[str]

    def to_dict(self) -> dict:
        return {
            "schema": "abm-auto/provenance/v1",
            "verification_clear": self.verification_clear,
            "gates": self.gates,
            "artifacts": self.artifacts,
            "skipped": self.skipped,
        }

    def write(self, path: Path) -> Path:
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str),
                        encoding="utf-8")
        return path


def build_provenance(report, artifacts: dict[str, Any]) -> Provenance:
    """Turn a HarnessReport + the artifacts it judged into a credential.

    `report` is a HarnessReport (verification_clear + verdicts + skipped);
    `artifacts` is the same {family: payload} dict passed to Harness.run.
    Each verdict records its tier-honest result; each artifact records a
    fingerprint. Replay: re-run gates on the artifacts, recompute
    fingerprints, compare.
    """
    gates = [
        {
            "gate": v.gate_name,
            "tier": v.tier,
            "passed": v.passed,
            "salient_number": list(v.salient_number) if v.salient_number else None,
            "reasons": v.reasons,
        }
        for v in report.verdicts
    ]
    fps = {family: fingerprint(payload) for family, payload in artifacts.items()}
    return Provenance(
        verification_clear=report.verification_clear,
        gates=gates,
        artifacts=fps,
        skipped=list(report.skipped),
    )
