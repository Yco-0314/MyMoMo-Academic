"""Tests for ADR-021 D4 — the inline Critic seam (no LLM: stub generators)."""
from __future__ import annotations

from types import SimpleNamespace

from abm_auto.agents.critic import (
    Critic,
    CriticReport,
    DesignCritic,
    MechanismCritic,
    Violation,
)


# --- 1. Violation / CriticReport / to_verdict ----------------------------

def test_empty_report_passes_and_verdict_is_refutation():
    rep = CriticReport(violations=[], gate_name="g")
    assert rep.passed is True
    v = rep.to_verdict()
    assert v.passed is True and v.tier == "refutation" and v.gate_name == "g"
    assert v.reasons == []


def test_report_with_violations_to_verdict_carries_messages():
    rep = CriticReport(
        violations=[Violation("C1", "bad thing", {"quote": "x"})], gate_name="g"
    )
    assert rep.passed is False
    v = rep.to_verdict()
    assert v.passed is False and v.tier == "refutation"
    assert v.reasons == ["bad thing"]


# --- 2. deterministic _verify (anti-fabrication) -------------------------

class _FixtureCritic(Critic):
    gate_name = "fixture"

    def __init__(self, text, generator):
        super().__init__(generator=generator)
        self._text = text

    def _artefact_text(self, ctx):
        return self._text


def test_verify_drops_unconfirmed_keeps_confirmed():
    text = "the model assumes beta=0.3 with no justification"
    candidates = [
        {"code": "REAL", "message": "unjustified beta", "evidence": {"quote": "no justification"}},
        {"code": "FAKE", "message": "hallucinated", "evidence": {"quote": "this string is not present"}},
    ]
    rep = _FixtureCritic(text, generator=lambda ctx: candidates).run(ctx=None)
    codes = [v.code for v in rep.violations]
    assert codes == ["REAL"]  # the fabricated (unmatched quote) candidate is dropped
    assert rep.violations[0].evidence["verified"] is True


def test_verify_drops_empty_quote():
    rep = _FixtureCritic("anything", generator=lambda ctx: [
        {"code": "X", "message": "m", "evidence": {}},
    ]).run(ctx=None)
    assert rep.passed is True


# --- 3. DesignCritic over a DESIGN.md fixture ----------------------------

def _ctx_with_design(tmp_path, text):
    p = tmp_path / "DESIGN.md"
    p.write_text(text, encoding="utf-8")
    return SimpleNamespace(workspace=SimpleNamespace(design_path=p, path=tmp_path))


def test_design_critic_flags_planted_passage(tmp_path):
    design = "## Parameters\nbeta = 0.3  # AI-ASSUMPTION: chosen arbitrarily, no source\n"
    ctx = _ctx_with_design(tmp_path, design)
    gen = lambda c: [{"code": "UNJUST_PARAM", "message": "beta unjustified",
                      "evidence": {"quote": "chosen arbitrarily, no source"}}]
    rep = DesignCritic(generator=gen).run(ctx)
    assert not rep.passed and len(rep.violations) == 1
    assert rep.violations[0].evidence["quote"] in design


def test_design_critic_clean_design_passes(tmp_path):
    ctx = _ctx_with_design(tmp_path, "## Parameters\nbeta = 0.3 (calibrated to Smith 2020)\n")
    # generator hallucinates a quote that is not in the artefact → dropped
    gen = lambda c: [{"code": "X", "message": "m", "evidence": {"quote": "arbitrary unsourced guess"}}]
    assert DesignCritic(generator=gen).run(ctx).passed is True


# --- 4. MechanismCritic over a mechanism_spec fixture --------------------

def test_mechanism_critic_flags_planted_ambiguity(tmp_path):
    spec = "update: agents adjust belief (order unspecified)\n"
    p = tmp_path / "mechanism_spec.md"
    p.write_text(spec, encoding="utf-8")
    ctx = SimpleNamespace(workspace=SimpleNamespace(mechanism_spec_path=p, path=tmp_path))
    gen = lambda c: [{"code": "AMBIG_ORDER", "message": "update order undefined",
                      "evidence": {"quote": "order unspecified"}}]
    rep = MechanismCritic(generator=gen).run(ctx)
    assert not rep.passed and rep.violations[0].code == "AMBIG_ORDER"
