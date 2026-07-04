"""ADR-023 L3 — replayable reproduction bundle (the trust-layer distribution primitive).

A single machine-readable artifact a reviewer can re-run and diff: the paper, the
per-finding Verdicts (ADR-013 gate.py — tier-honest, with each hypothesis's
(value, threshold)), content-addressed fingerprints of the input DATA + the
locked-predictions + findings DOCS, the code commit, and the environment.

Reusable across reproductions — candidate #10 (the real Ba-DEM Anshuka run) is the
first instance. This is the L3 "a reviewer re-runs the gate" primitive: re-running the
reproduction regenerates the bundle; a reviewer diffs the regenerated bundle against the
committed one (fingerprints prove the inputs were the same; verdicts prove the gate agreed).

Reuses abm_auto/verification: Verdict (the uniform gate output) + fingerprint (strong
file hashing). Additive GIS module; zero change to runtime/codegen/calibration.
"""
from __future__ import annotations

import json
import math
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from abm_auto.verification.gate import Verdict
from abm_auto.verification.provenance import fingerprint

SCHEMA = "abm-auto/repro-bundle/v1"


def _repo_root(repo: Optional[Path]) -> Path:
    return Path.cwd().resolve() if repo is None else Path(repo).resolve()


def _portable_path(path: Path, repo: Optional[Path]) -> str:
    if repo is None:
        return str(path)
    try:
        return path.resolve().relative_to(_repo_root(repo)).as_posix()
    except ValueError:
        return str(path)


def _fingerprint_with_portable_path(path: Path, repo: Optional[Path]) -> dict:
    full_path = (
        _repo_root(repo) / path
        if repo is not None and not path.is_absolute()
        else path
    )
    fp = fingerprint(full_path)
    fp["path"] = (
        path.as_posix()
        if repo is not None and not path.is_absolute()
        else _portable_path(path, repo)
    )
    return fp


def _artifact_path(path_value: Any, repo: Path) -> Path:
    path = Path(str(path_value))
    return path if path.is_absolute() else repo / path


def _is_two_number_tuple(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 2:
        return False
    return all(
        isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))
        for v in value
    )


def verdict_to_dict(v: Verdict) -> dict:
    return {
        "gate": v.gate_name,
        "tier": v.tier,
        "passed": v.passed,
        "salient_number": list(v.salient_number) if v.salient_number else None,
        "reasons": list(v.reasons),
        "evidence": v.evidence,
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
    for idx, verdict in enumerate(verdicts):
        prefix = f"verdicts[{idx}]"
        if not isinstance(verdict, dict):
            issues.append(f"{prefix} must be an object")
            continue
        if not verdict.get("gate"):
            issues.append(f"{prefix}.gate is required")
        if not verdict.get("tier"):
            issues.append(f"{prefix}.tier is required")
        if not isinstance(verdict.get("passed"), bool):
            issues.append(f"{prefix}.passed must be bool")
        if not _is_two_number_tuple(verdict.get("salient_number")):
            issues.append(f"{prefix}.salient_number must be [value, threshold]")

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
            path = Path(path_value)
            if path.is_absolute():
                issues.append(f"{prefix}.path uses absolute local path: {path_value}")
            if artifact.get("kind") != "file":
                issues.append(f"{prefix}.kind must be 'file'")
            sha = artifact.get("sha256")
            if not isinstance(sha, str) or len(sha) != 64:
                issues.append(f"{prefix}.sha256 must be a 64-char hex string")
            if artifact.get("replay") != "strong":
                issues.append(f"{prefix}.replay must be 'strong'")

            full_path = _artifact_path(path_value, repo_root)
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

    failed_verdict_count = sum(
        1 for verdict in verdicts
        if isinstance(verdict, dict) and verdict.get("passed") is False
    )
    return {
        "ok": not issues,
        "issues": issues,
        "schema": bundle.get("schema"),
        "headline": bundle.get("headline"),
        "verdict_count": len(verdicts),
        "failed_verdict_count": failed_verdict_count,
        "doc_hashes_checked": doc_hashes_checked,
        "data_hashes_checked": data_hashes_checked,
        "data_fingerprint_count": len(data),
        "missing_data_files": missing_data_files,
    }


def validate_repro_bundle_file(path, *, repo: Optional[Path] = None, **kwargs) -> dict:
    bundle_path = Path(path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if repo is None:
        repo = bundle_path.resolve().parents[3]
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
