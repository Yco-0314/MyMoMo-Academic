"""ADR-021 D2 — the Checkpoint seam (pipeline resumability).

Persist the pipeline *state machine* (which Phase finished, with which input ctx,
producing which artefacts) alongside the artefacts the workspace already holds, so
``Pipeline(resume_from=...)`` can skip completed phases whose outputs are still valid.

Anti-fabrication 命门 (ADR-013): a checkpoint is honoured ONLY when its declared
artefacts still exist on disk AND their content hash matches what was recorded. A
"finished" record whose artefact was deleted or edited is rejected — the generator's
word is never trusted. (The record therefore stores each artefact's sha256, a
faithful completion of the spec's record schema so ``validate`` has something to
compare against.)

ADR-002 compatible: flat JSON files under ``workspace/checkpoints/``, atomic writes,
human-``cat``-able, git-diffable. Stdlib only (``hashlib``, ``json``).

Zero changes to abm_auto/runtime, codegen, calibration. Lives in runner/; the only
pipeline edit is an additive success hook + an optional ``resume_from`` kwarg.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Resume-relevant PipelineContext fields (LOCKED — pinned by test). Construction-time
# inputs plus the phase-mutated scalars a downstream phase reads. Live handles
# (workspace, executor, memory) and unserialisable objects are excluded.
RESUME_FIELDS: Tuple[str, ...] = (
    "story_path",
    "iterations",
    "max_retries",
    "peer_review",
    "lang",
    "seed",
    "fetch_citations",
    "baseline_path",
    "auto_lit_review",
    "mode_override",
    "intent_override",
    "external_model_path",
    "observed_path",
    "sensitivity_method",
    "sensitivity_samples",
    "using_external_model",
    "iteration",
    "used_bayesian_calibration",
)


def _stable(value: Any) -> Any:
    """Best-effort stable, JSON-serialisable projection of a ctx field value."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return value.as_posix()
    return str(value)


def hash_ctx(ctx: Any) -> str:
    """Stable SHA-256 over the locked resume-relevant fields of a PipelineContext."""
    payload = {f: _stable(getattr(ctx, f, None)) for f in RESUME_FIELDS}
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def content_hash(path: Path) -> str:
    """SHA-256 of a file, or of a directory's sorted (relpath, filehash) manifest."""
    path = Path(path)
    if path.is_dir():
        h = hashlib.sha256()
        for f in sorted(p for p in path.rglob("*") if p.is_file()):
            h.update(f.relative_to(path).as_posix().encode("utf-8"))
            h.update(b"\0")
            h.update(content_hash(f).encode("utf-8"))
            h.update(b"\0")
        return h.hexdigest()
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class CheckpointRecord:
    phase_name: str
    input_ctx_hash: str
    output_artefact_paths: List[str]          # workspace-relative POSIX paths
    artefact_hashes: Dict[str, str]           # path -> content sha256 (anti-fabrication)
    finished_at: str                          # ISO-8601

    def to_json(self) -> str:
        return json.dumps(
            {
                "phase_name": self.phase_name,
                "input_ctx_hash": self.input_ctx_hash,
                "output_artefact_paths": list(self.output_artefact_paths),
                "artefact_hashes": dict(self.artefact_hashes),
                "finished_at": self.finished_at,
            },
            indent=2,
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, text: str) -> "CheckpointRecord":
        d = json.loads(text)
        return cls(
            phase_name=d["phase_name"],
            input_ctx_hash=d["input_ctx_hash"],
            output_artefact_paths=list(d["output_artefact_paths"]),
            artefact_hashes=dict(d.get("artefact_hashes", {})),
            finished_at=d["finished_at"],
        )


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "phase"


@dataclass
class ValidationResult:
    ok: bool
    reason: str = ""           # "" | "missing:<path>" | "hash-mismatch:<path>"


class CheckpointStore:
    """Owns ``<workspace>/checkpoints/``. One JSON file per phase, ordinal-prefixed."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = Path(workspace_path)
        self.dir = self.workspace_path / "checkpoints"

    def _next_ordinal(self) -> int:
        if not self.dir.exists():
            return 0
        existing = [p for p in self.dir.glob("*.json")]
        return len(existing)

    def append(self, record: CheckpointRecord) -> Path:
        self.dir.mkdir(parents=True, exist_ok=True)
        ordinal = self._next_ordinal()
        path = self.dir / f"{ordinal:04d}_{_slug(record.phase_name)}.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(record.to_json(), encoding="utf-8")
        tmp.replace(path)  # atomic — a crash mid-write leaves a .tmp, ignored by load_all
        return path

    def load_all(self) -> List[CheckpointRecord]:
        if not self.dir.exists():
            return []
        files = sorted(p for p in self.dir.glob("*.json") if p.suffix == ".json")
        return [CheckpointRecord.from_json(p.read_text(encoding="utf-8")) for p in files]

    def by_phase(self) -> Dict[str, CheckpointRecord]:
        """Latest record per phase name (last write wins)."""
        out: Dict[str, CheckpointRecord] = {}
        for rec in self.load_all():
            out[rec.phase_name] = rec
        return out

    def validate(self, record: CheckpointRecord) -> ValidationResult:
        """A checkpoint is valid iff every artefact still exists AND matches its hash."""
        for rel in record.output_artefact_paths:
            abs_path = self.workspace_path / rel
            if not abs_path.exists():
                return ValidationResult(False, f"missing:{rel}")
            if content_hash(abs_path) != record.artefact_hashes.get(rel):
                return ValidationResult(False, f"hash-mismatch:{rel}")
        return ValidationResult(True)


def phase_artefacts(phase: Any, ctx: Any) -> List[Path]:
    """Artefacts a phase declares for checkpointing; [] for un-migrated phases."""
    fn = getattr(phase, "checkpoint_artefacts", None)
    if fn is None:
        return []
    return [Path(p) for p in fn(ctx)]


def make_record(phase: Any, ctx: Any, entry_hash: str, workspace_path: Path) -> CheckpointRecord:
    workspace_path = Path(workspace_path)
    rels: List[str] = []
    hashes: Dict[str, str] = {}
    for art in phase_artefacts(phase, ctx):
        art = Path(art)
        if not art.exists():
            continue
        rel = art.relative_to(workspace_path).as_posix() if art.is_absolute() else art.as_posix()
        rels.append(rel)
        hashes[rel] = content_hash(art)
    return CheckpointRecord(
        phase_name=phase.name,
        input_ctx_hash=entry_hash,
        output_artefact_paths=rels,
        artefact_hashes=hashes,
        finished_at=datetime.now(timezone.utc).isoformat(),
    )


def plan_skips(phases: List[Any], store: CheckpointStore, resume_from: Optional[str]) -> set:
    """Phase names to skip on resume: the prefix up to ``resume_from`` (exclusive),
    stopping only at the first phase whose checkpoint is **present but INVALID**
    (tampered artefact / hash mismatch). A phase with NO checkpoint is one that did
    not run the first time (``should_run`` was False) — it is passed over, not a
    stop signal (per the ADR-021 D2 spec: "the first INVALID checkpoint", not the
    first absent one). This is what lets resume skip past legitimately-skipped phases
    (live-run finding: ``--no-lit-review`` etc. leave gaps in the checkpoint sequence).

    Limitation (deferred): ctx is not reconstructed from checkpoints, so a skipped
    phase's in-memory ctx mutations are not replayed; resume relies on resume_from
    asserting that everything before it genuinely finished, with validate() as the
    anti-fabrication guard on the declared artefacts."""
    if resume_from is None:
        return set()
    records = store.by_phase()
    skip: set = set()
    for phase in phases:
        if phase.name == resume_from:
            break
        rec = records.get(phase.name)
        if rec is not None and not store.validate(rec).ok:
            break  # a present-but-invalid (tampered) checkpoint ends the skippable prefix
        skip.add(phase.name)  # valid checkpoint, OR no checkpoint (phase did not run)
    return skip


def run_phases(
    phases: List[Any],
    ctx: Any,
    store: Optional[CheckpointStore] = None,
    skip: Optional[set] = None,
    on_phase=None,
    finalizers: Optional[List[Any]] = None,
) -> None:
    """The orchestrator's phase walk + checkpoint success hook (testable standalone).

    For each phase: honour the halt flag, the skip set (resume), and ``should_run``.
    After a phase completes WITHOUT halting, append a checkpoint capturing the ctx
    hash seen on entry and the artefacts the phase declared.

    ``finalizers`` are always-run trailing phases that execute AFTER the main loop
    regardless of whether it completed or broke on ``pipeline_halted`` — so an
    end-of-run reporter (e.g. the trust report) is present exactly when a run
    halted/FAILED. Finalizers are NOT checkpointed and are not subject to the skip
    set, but they still honour their own ``should_run``.
    """
    skip = skip or set()
    for phase in phases:
        if getattr(ctx, "pipeline_halted", False):
            break
        if phase.name in skip:
            continue
        if not phase.should_run(ctx):
            continue
        entry_hash = hash_ctx(ctx) if store is not None else ""
        if on_phase is not None:
            on_phase(phase)
        phase.run(ctx)
        if store is not None and not getattr(ctx, "pipeline_halted", False):
            store.append(make_record(phase, ctx, entry_hash, store.workspace_path))

    for fin in (finalizers or []):
        if fin.should_run(ctx):
            if on_phase is not None:
                on_phase(fin)
            fin.run(ctx)
