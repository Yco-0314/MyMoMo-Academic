"""Tests for the Phase -1 intent detector (4-way taxonomy + shaping halt).

The detector classifies the user's intent — reproduce / originate / cross_domain
/ idea — and DERIVES the 2-way execution mode downstream agents consume. An
`idea` or a low-confidence guess halts the pipeline with clarifying questions
instead of feeding a vague task into codegen; a user-declared intent is taken at
face value (except `idea`, which always shapes — that's the point of declaring it).
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from abm_auto.agents.mode_detector import (
    ModeDetector,
    ResearchSpec,
    VALID_INTENTS,
    derive_mode,
    needs_shaping,
)
from abm_auto.runner.workspace import Workspace


# ── pure helpers ────────────────────────────────────────────────────────────

def test_derive_mode_maps_four_intents_to_two_modes() -> None:
    assert derive_mode("reproduce") == "reproduce"
    assert derive_mode("originate") == "originate"
    assert derive_mode("cross_domain") == "originate"   # novel application
    assert derive_mode("idea") == "originate"           # placeholder; shaped first
    assert derive_mode("nonsense") == "originate"        # safe default


def test_idea_always_shapes_even_when_declared() -> None:
    # The whole point of declaring `idea` is to trigger the shaping loop.
    assert needs_shaping("idea", 0.99, overridden=True) is True


def test_declared_non_idea_never_shapes() -> None:
    assert needs_shaping("reproduce", 0.10, overridden=True) is False
    assert needs_shaping("cross_domain", 0.10, overridden=True) is False


def test_low_confidence_auto_intent_shapes() -> None:
    assert needs_shaping("originate", 0.50, overridden=False) is True
    assert needs_shaping("originate", 0.95, overridden=False) is False


def test_confidence_threshold_boundary() -> None:
    # threshold is exclusive: exactly-at-threshold proceeds
    assert needs_shaping("reproduce", 0.70, threshold=0.70, overridden=False) is False
    assert needs_shaping("reproduce", 0.69, threshold=0.70, overridden=False) is True


# ── ResearchSpec back-compat ────────────────────────────────────────────────

def test_spec_backfills_intent_from_mode() -> None:
    # Specs written before the 4-way taxonomy carry only `mode`.
    s = ResearchSpec.from_dict({"mode": "reproduce"})
    assert s.intent == "reproduce"
    s2 = ResearchSpec.from_dict({"mode": "originate"})
    assert s2.intent == "originate"


def test_spec_roundtrip_preserves_intent() -> None:
    s = ResearchSpec(mode="originate", intent="cross_domain",
                     transfer_method="opinion dynamics",
                     source_domain="sociology", target_domain="traffic")
    back = ResearchSpec.from_dict(s.to_dict())
    assert back.intent == "cross_domain"
    assert back.mode == "originate"
    assert back.transfer_method == "opinion dynamics"


# ── run() behaviour (LLM stubbed) ───────────────────────────────────────────

def _detector(tmp_path, story: str | None = None) -> ModeDetector:
    ws = Workspace(tmp_path)
    if story is not None:
        ws.write_story(story)
    agent = ModeDetector(MagicMock(), ws, model="mock")
    # Never hit the network in these tests.
    agent._make_clarification = lambda story, spec: ["Who are the agents?"]
    return agent


def test_intent_override_skips_detection(tmp_path) -> None:
    agent = _detector(tmp_path)  # no story → no metadata call
    spec = agent.run(intent_override="reproduce")
    assert spec.intent == "reproduce" and spec.mode == "reproduce"
    assert spec.confidence == 1.0
    assert spec.needs_clarification is False


def test_mode_override_is_treated_as_intent(tmp_path) -> None:
    agent = _detector(tmp_path)
    spec = agent.run(mode_override="originate")
    assert spec.intent == "originate" and spec.mode == "originate"
    assert spec.needs_clarification is False


def test_declared_idea_halts_for_shaping(tmp_path) -> None:
    agent = _detector(tmp_path, story="something about cities maybe")
    spec = agent.run(intent_override="idea")
    assert spec.intent == "idea"
    assert spec.needs_clarification is True
    assert (tmp_path / "clarification.md").exists()


def test_invalid_intent_override_raises(tmp_path) -> None:
    agent = _detector(tmp_path)
    with pytest.raises(ValueError):
        agent.run(intent_override="teleport")


def test_high_confidence_reproduce_proceeds(tmp_path) -> None:
    agent = _detector(tmp_path, story="Reproduce Schelling 1971 segregation.")
    agent._detect = lambda story: agent._make_spec(
        "reproduce", confidence=0.92, paper_ref="Schelling 1971", intent_reason="cited paper")
    spec = agent.run()
    assert spec.intent == "reproduce" and spec.mode == "reproduce"
    assert spec.needs_clarification is False
    assert (tmp_path / "research_spec.json").exists()
    assert not (tmp_path / "clarification.md").exists()


def test_low_confidence_halts_and_writes_clarification(tmp_path) -> None:
    agent = _detector(tmp_path, story="I want to study some social thing.")
    agent._detect = lambda story: agent._make_spec(
        "originate", confidence=0.45, intent_reason="vague phenomenon")
    spec = agent.run()
    assert spec.needs_clarification is True
    assert spec.clarification_questions == ["Who are the agents?"]
    assert (tmp_path / "clarification.md").exists()


def test_detected_idea_halts(tmp_path) -> None:
    agent = _detector(tmp_path, story="what if cities segregate like birds flock?")
    agent._detect = lambda story: agent._make_spec(
        "idea", confidence=0.9, intent_reason="no mechanism named")
    spec = agent.run()
    assert spec.intent == "idea"
    assert spec.needs_clarification is True   # idea halts even at high confidence


def test_cross_domain_proceeds_as_originate(tmp_path) -> None:
    agent = _detector(tmp_path, story="Apply the opinion model to traffic merging.")
    agent._detect = lambda story: agent._make_spec(
        "cross_domain", confidence=0.85, transfer_method="bounded confidence",
        source_domain="opinion dynamics", target_domain="traffic")
    spec = agent.run()
    assert spec.intent == "cross_domain" and spec.mode == "originate"
    assert spec.needs_clarification is False
    assert spec.transfer_method == "bounded confidence"


def test_all_valid_intents_are_classifiable(tmp_path) -> None:
    # Every taxonomy member must produce a coherent spec via _make_spec.
    agent = _detector(tmp_path)
    for intent in VALID_INTENTS:
        spec = agent._make_spec(intent, confidence=0.9)
        assert spec.intent == intent
        assert spec.mode in ("reproduce", "originate")


# ── phase wiring: needs_clarification must actually halt the pipeline ─────────

class _Ctx:
    """Minimal stand-in for PipelineContext (the fields ModeDetectorPhase touches)."""
    mode_override = None
    intent_override = None
    pipeline_halted = False
    halt_reason = ""
    spec = None


def _phase_with_spec(spec: ResearchSpec):
    from abm_auto.pipeline.phases.setup import ModeDetectorPhase
    agent = MagicMock()
    agent.run.return_value = spec
    return ModeDetectorPhase(agent)


def test_phase_halts_on_needs_clarification() -> None:
    ctx = _Ctx()
    spec = ResearchSpec(mode="originate", intent="idea",
                        confidence=0.9, needs_clarification=True)
    _phase_with_spec(spec).run(ctx)
    assert ctx.pipeline_halted is True
    assert "idea" in ctx.halt_reason and "clarification.md" in ctx.halt_reason


def test_phase_does_not_halt_on_clean_spec() -> None:
    ctx = _Ctx()
    spec = ResearchSpec(mode="reproduce", intent="reproduce",
                        confidence=0.95, needs_clarification=False)
    _phase_with_spec(spec).run(ctx)
    assert ctx.pipeline_halted is False
