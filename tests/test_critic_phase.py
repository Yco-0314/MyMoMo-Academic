"""Tests for ADR-021 D4 — CriticPhase soft-gate policy + insert_critics wiring."""
from __future__ import annotations

from types import SimpleNamespace

from abm_auto.agents.critic import CriticReport, Violation
from abm_auto.pipeline.phases.critic_phase import CriticPhase, insert_critics


class _FakeAudit:
    def __init__(self):
        self.issues = []

    def raise_issue(self, phase, severity, text, actor, structured=None):
        self.issues.append(
            {"phase": phase, "severity": severity, "text": text, "structured": structured}
        )
        return "issue-1"


class _FakeCritic:
    def __init__(self, after_phase, report, gate_name="fake"):
        self.after_phase = after_phase
        self.gate_name = gate_name
        self._report = report

    def run(self, ctx):
        return self._report


def _ctx():
    return SimpleNamespace(
        workspace=SimpleNamespace(audit=_FakeAudit()),
        pipeline_halted=False,
        halt_reason="",
    )


# --- 5. soft-gate policy --------------------------------------------------

def test_default_policy_blocks_and_halts():
    report = CriticReport([Violation("C", "boom", {"quote": "q"})], gate_name="g")
    phase = CriticPhase(_FakeCritic("P", report), allow_soft=False)
    ctx = _ctx()
    phase.run(ctx)
    assert ctx.pipeline_halted is True
    assert ctx.workspace.audit.issues[0]["severity"] == "BLOCKING"
    assert ctx.workspace.audit.issues[0]["structured"] == {"quote": "q"}


def test_soft_policy_continues_with_high_issue():
    report = CriticReport([Violation("C", "boom", {"quote": "q"})], gate_name="g")
    phase = CriticPhase(_FakeCritic("P", report), allow_soft=True)
    ctx = _ctx()
    phase.run(ctx)
    assert ctx.pipeline_halted is False  # continues
    assert ctx.workspace.audit.issues[0]["severity"] == "HIGH"


def test_passing_report_raises_nothing():
    phase = CriticPhase(_FakeCritic("P", CriticReport([], gate_name="g")))
    ctx = _ctx()
    phase.run(ctx)
    assert ctx.pipeline_halted is False
    assert ctx.workspace.audit.issues == []


# --- 6. insert_critics wiring / off-by-default ---------------------------

class _Phase:
    def __init__(self, name):
        self.name = name


def test_insert_critics_off_is_identity():
    phases = [_Phase("A"), _Phase("B")]
    assert insert_critics(phases, critics=[]) == phases


def test_insert_critics_places_after_named_phase():
    phases = [_Phase("A"), _Phase("Design"), _Phase("B"), _Phase("Mechanism")]
    critics = [
        _FakeCritic("Design", CriticReport([]), gate_name="design"),
        _FakeCritic("Mechanism", CriticReport([]), gate_name="mechanism"),
    ]
    out = insert_critics(phases, critics)
    names = [getattr(p, "name", None) for p in out]
    assert names == [
        "A",
        "Design",
        "Critic (design) after Design",
        "B",
        "Mechanism",
        "Critic (mechanism) after Mechanism",
    ]
