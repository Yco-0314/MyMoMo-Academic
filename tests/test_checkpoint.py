"""Tests for ADR-021 D2 — the Checkpoint seam (resumability).

No LLM / no Pipeline construction: the run-loop hook and resume planning are
exercised through the testable `run_phases` / `plan_skips` helpers with fake
phases and a fake ctx.
"""
from __future__ import annotations

from types import SimpleNamespace

from abm_auto.runner.checkpoint import (
    RESUME_FIELDS,
    CheckpointRecord,
    CheckpointStore,
    content_hash,
    hash_ctx,
    make_record,
    plan_skips,
    run_phases,
)


def _ctx(**over):
    base = dict(
        story_path="s.md", iterations=3, max_retries=3, peer_review=False, lang="zh",
        seed=0, fetch_citations=False, baseline_path=None, auto_lit_review=True,
        mode_override=None, intent_override=None, external_model_path=None,
        observed_path=None, sensitivity_method=None, sensitivity_samples=10,
        using_external_model=False, iteration=0, used_bayesian_calibration=False,
        pipeline_halted=False, halt_reason="",
    )
    base.update(over)
    return SimpleNamespace(**base)


class FakePhase:
    def __init__(self, name, artefacts=(), halt=False):
        self.name = name
        self._artefacts = list(artefacts)
        self._halt = halt
        self.ran = False

    def should_run(self, ctx):
        return True

    def checkpoint_artefacts(self, ctx):
        return self._artefacts

    def run(self, ctx):
        self.ran = True
        if self._halt:
            ctx.pipeline_halted = True


# --- 1. CheckpointStore round-trip ---------------------------------------

def test_store_append_load_roundtrip_in_order(tmp_path):
    store = CheckpointStore(tmp_path)
    for i in range(3):
        store.append(CheckpointRecord(f"Phase {i}", f"h{i}", [], {}, "2026-06-24T00:00:00Z"))
    recs = store.load_all()
    assert [r.phase_name for r in recs] == ["Phase 0", "Phase 1", "Phase 2"]
    assert (tmp_path / "checkpoints").is_dir()


def test_store_ignores_stray_tmp(tmp_path):
    store = CheckpointStore(tmp_path)
    store.append(CheckpointRecord("Phase 0", "h", [], {}, "t"))
    # simulate a crash mid-write
    (tmp_path / "checkpoints" / "0001_phase-1.json.tmp").write_text("{partial", encoding="utf-8")
    assert [r.phase_name for r in store.load_all()] == ["Phase 0"]


# --- 2. hash_ctx ----------------------------------------------------------

def test_resume_fields_are_locked():
    # Pin the field set (changing it is a deliberate, reviewed decision).
    assert RESUME_FIELDS == (
        "story_path", "iterations", "max_retries", "peer_review", "lang", "seed",
        "fetch_citations", "baseline_path", "auto_lit_review", "mode_override",
        "intent_override", "external_model_path", "observed_path",
        "sensitivity_method", "sensitivity_samples", "using_external_model",
        "iteration", "used_bayesian_calibration",
    )


def test_hash_ctx_sensitive_to_resume_scalar_blind_to_live_handle():
    a = _ctx()
    b = _ctx()
    assert hash_ctx(a) == hash_ctx(b)
    assert hash_ctx(_ctx(iteration=1)) != hash_ctx(a)  # resume-relevant scalar
    # a live handle is not in RESUME_FIELDS → no effect
    a.workspace = object()
    assert hash_ctx(a) == hash_ctx(b)


# --- 3. validate (anti-fabrication) --------------------------------------

def test_validate_clean_missing_and_tampered(tmp_path):
    store = CheckpointStore(tmp_path)
    art = tmp_path / "DESIGN.md"
    art.write_text("design v1", encoding="utf-8")
    rec = CheckpointRecord("P", "h", ["DESIGN.md"], {"DESIGN.md": content_hash(art)}, "t")

    assert store.validate(rec).ok  # clean

    art.write_text("design v2 (edited)", encoding="utf-8")
    res = store.validate(rec)
    assert not res.ok and res.reason.startswith("hash-mismatch")  # tamper detected

    art.unlink()
    res = store.validate(rec)
    assert not res.ok and res.reason.startswith("missing")


# --- 4. run_phases success hook ------------------------------------------

def test_run_phases_writes_one_checkpoint_per_success(tmp_path):
    store = CheckpointStore(tmp_path)
    phases = [FakePhase("A"), FakePhase("B"), FakePhase("C")]
    run_phases(phases, _ctx(), store=store)
    assert [r.phase_name for r in store.load_all()] == ["A", "B", "C"]
    assert all(p.ran for p in phases)


def test_run_phases_halted_phase_writes_no_checkpoint(tmp_path):
    store = CheckpointStore(tmp_path)
    phases = [FakePhase("A"), FakePhase("B", halt=True), FakePhase("C")]
    ctx = _ctx()
    run_phases(phases, ctx, store=store)
    # A checkpoints; B halts (no checkpoint); C never runs
    assert [r.phase_name for r in store.load_all()] == ["A"]
    assert phases[2].ran is False


def test_finalizers_run_even_after_halt(tmp_path):
    # A finalizer is an always-run trailing phase: it must execute whether the
    # main loop completed OR broke on pipeline_halted (the trust report's whole
    # value is being present exactly when a run halted/FAILED).
    store = CheckpointStore(tmp_path)
    phases = [FakePhase("A"), FakePhase("B", halt=True), FakePhase("C")]
    fin = FakePhase("Final")
    run_phases(phases, _ctx(), store=store, finalizers=[fin])
    assert phases[2].ran is False   # C still skipped by the halt
    assert fin.ran is True          # but the finalizer ran anyway
    # finalizers are NOT checkpointed
    assert [r.phase_name for r in store.load_all()] == ["A"]


def test_finalizers_run_on_clean_completion(tmp_path):
    store = CheckpointStore(tmp_path)
    phases = [FakePhase("A"), FakePhase("B")]
    fin = FakePhase("Final")
    run_phases(phases, _ctx(), store=store, finalizers=[fin])
    assert all(p.ran for p in phases)
    assert fin.ran is True
    assert [r.phase_name for r in store.load_all()] == ["A", "B"]


def test_finalizer_should_run_false_is_skipped(tmp_path):
    class _SkipPhase(FakePhase):
        def should_run(self, ctx):
            return False

    fin = _SkipPhase("Final")
    run_phases([FakePhase("A")], _ctx(), finalizers=[fin])
    assert fin.ran is False


# --- 5. plan_skips / resume ----------------------------------------------

def test_resume_skips_valid_prefix(tmp_path):
    store = CheckpointStore(tmp_path)
    a_art = tmp_path / "a.txt"; a_art.write_text("A", encoding="utf-8")
    b_art = tmp_path / "b.txt"; b_art.write_text("B", encoding="utf-8")
    phases = [
        FakePhase("A", artefacts=[a_art]),
        FakePhase("B", artefacts=[b_art]),
        FakePhase("C"),
    ]
    # first run: all three checkpoint
    run_phases(phases, _ctx(), store=store)

    # resume from C: A and B have valid checkpoints → skipped
    fresh = [FakePhase("A", artefacts=[a_art]), FakePhase("B", artefacts=[b_art]), FakePhase("C")]
    skip = plan_skips(fresh, store, resume_from="C")
    assert skip == {"A", "B"}


def test_resume_tamper_breaks_skip_prefix(tmp_path):
    store = CheckpointStore(tmp_path)
    a_art = tmp_path / "a.txt"; a_art.write_text("A", encoding="utf-8")
    b_art = tmp_path / "b.txt"; b_art.write_text("B", encoding="utf-8")
    phases = [FakePhase("A", artefacts=[a_art]), FakePhase("B", artefacts=[b_art]), FakePhase("C")]
    run_phases(phases, _ctx(), store=store)

    # tamper with A's artefact → A no longer skippable → nothing before C skips
    a_art.write_text("A edited", encoding="utf-8")
    skip = plan_skips(phases, store, resume_from="C")
    assert skip == set()  # the invalid checkpoint halts the skip prefix at A


def test_resume_none_skips_nothing(tmp_path):
    store = CheckpointStore(tmp_path)
    phases = [FakePhase("A"), FakePhase("B")]
    run_phases(phases, _ctx(), store=store)
    assert plan_skips(phases, store, resume_from=None) == set()


def test_resume_passes_over_absent_checkpoint(tmp_path):
    # Live-run finding: a phase that did NOT run (should_run False, e.g. --no-lit-review)
    # leaves no checkpoint. An ABSENT checkpoint must be passed over, not stop the prefix.
    store = CheckpointStore(tmp_path)
    # only A and C ran (B was skipped via should_run, so it has no checkpoint)
    run_phases([FakePhase("A"), FakePhase("C")], _ctx(), store=store)
    full = [FakePhase("A"), FakePhase("B"), FakePhase("C")]  # B reappears in the real list
    skip = plan_skips(full, store, resume_from="C")
    assert skip == {"A", "B"}  # B (no checkpoint) is skipped, not a stop signal


def test_make_record_captures_relative_paths_and_hashes(tmp_path):
    store = CheckpointStore(tmp_path)
    art = tmp_path / "DESIGN.md"; art.write_text("d", encoding="utf-8")
    phase = FakePhase("Phase 1", artefacts=[art])
    rec = make_record(phase, _ctx(), entry_hash="h", workspace_path=tmp_path)
    assert rec.output_artefact_paths == ["DESIGN.md"]
    assert rec.artefact_hashes["DESIGN.md"] == content_hash(art)
