"""Per-run trust report — an honest, ledger-centric summary of how much to trust a
run's result and what was / wasn't checked.

Ledger-centric by design: it reads what the run already recorded (the audit
ledger, whether REPORT.md exists, research_spec.json) and never re-runs or
re-architects gates. It states only what the ledger supports — flagged / open /
resolved / silent — and never claims "verified" (absence of an issue is not proof
of verification). This replaces the "100% success" framing with an honest picture.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from abm_auto.audit.ledger import AuditLedger, EventType, Severity

# Canonical pipeline phase labels (used to flag phases that produced NO audit
# events as "silent"). Align with the `phase=` strings used in raise_issue/info
# across abm_auto/pipeline/phases/ if they drift.
_PIPELINE_PHASES = [
    "Phase -1", "Phase 0", "Phase 0.5", "Phase 1", "Phase 1c", "Phase 1d",
    "Phase 2", "Phase 3", "Phase 4", "Phase 5", "Phase 6", "Phase 7", "Phase 8",
]


@dataclass
class PhaseTrust:
    phase: str
    open_issues: int
    resolved_issues: int


@dataclass
class TrustReport:
    cleanliness: str                       # CLEAN | CAVEATED | FAILED
    completed: bool
    open_high: int
    open_total: int
    resolved_total: int
    phases: list[PhaseTrust] = field(default_factory=list)
    silent_phases: list[str] = field(default_factory=list)
    fidelity: str | None = None            # REPRO | PARTIAL | MISS | None
    fidelity_detail: tuple[float, float] | None = None
    note: str = ""


def build_trust_report(workspace_path, repro_score: tuple[float, float] | None = None) -> TrustReport:
    """Aggregate a finished workspace into a TrustReport. ``repro_score`` is an
    optional (score, threshold) for the reproduction-fidelity verdict; pass None
    to omit fidelity."""
    workspace_path = Path(workspace_path)
    completed = (workspace_path / "REPORT.md").exists()

    ledger = AuditLedger(workspace_path)
    events = ledger.all_events()
    note = "" if (workspace_path / "audit_ledger.jsonl").exists() else "no audit ledger (run may be incomplete)"

    open_evs = ledger.open_issues()
    open_total = len(open_evs)
    open_high = sum(1 for e in open_evs if e.severity == Severity.HIGH)
    state = ledger.current_state()
    resolved_total = sum(1 for et in state.values() if et == EventType.RESOLVE)

    if not completed:
        cleanliness = "FAILED"
    elif open_total > 0:
        cleanliness = "CAVEATED"
    else:
        cleanliness = "CLEAN"

    return TrustReport(
        cleanliness=cleanliness, completed=completed,
        open_high=open_high, open_total=open_total, resolved_total=resolved_total,
        note=note,
    )
