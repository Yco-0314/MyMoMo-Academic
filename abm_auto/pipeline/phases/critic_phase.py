"""ADR-021 D4 — CriticPhase: the soft-gate plug-in for an inline Critic.

Runs a Critic after its named Phase and applies soft-gate policy:
  - default: any violation → a BLOCKING audit issue + halt the pipeline.
  - allow_soft=True (`--allow-critic-soft`): downgrade to a HIGH audit issue + continue.

The evidence dict travels into the audit ledger's `structured` field so the halt is
backed by verifiable structural pointers, not prose (ADR-013 命门).

Additive, opt-in: CriticPhases are inserted into the phase list only when critics are
enabled; default off ⇒ the phase list is byte-identical to today.
"""
from __future__ import annotations

from typing import List


class CriticPhase:
    """Wraps a Critic as a Phase that runs after `critic.after_phase`."""

    def __init__(self, critic, allow_soft: bool = False):
        self.critic = critic
        self.allow_soft = allow_soft
        self.name = f"Critic ({critic.gate_name}) after {critic.after_phase}"
        self.contract = None  # opaque to D3 contract validation

    def should_run(self, ctx) -> bool:
        return True

    def run(self, ctx) -> None:
        report = self.critic.run(ctx)
        if report.passed:
            return
        severity = "HIGH" if self.allow_soft else "BLOCKING"
        for v in report.violations:
            ctx.workspace.audit.raise_issue(
                phase=self.name,
                severity=severity,
                text=v.message,
                actor="Critic",
                structured=v.evidence,
            )
        if not self.allow_soft:
            ctx.pipeline_halted = True
            ctx.halt_reason = (
                f"{self.name}: {len(report.violations)} unresolved violation(s) "
                f"(re-run with --allow-critic-soft to continue past Critic findings)"
            )


def insert_critics(phases: List, critics: List, allow_soft: bool = False) -> List:
    """Return a new phase list with a CriticPhase inserted right after each phase whose
    name matches a critic's `after_phase`. Pure (no side effects) — testable standalone.
    With no critics, returns the list unchanged (additivity)."""
    by_after = {c.after_phase: c for c in critics}
    out: List = []
    for phase in phases:
        out.append(phase)
        crit = by_after.get(getattr(phase, "name", None))
        if crit is not None:
            out.append(CriticPhase(crit, allow_soft=allow_soft))
    return out
