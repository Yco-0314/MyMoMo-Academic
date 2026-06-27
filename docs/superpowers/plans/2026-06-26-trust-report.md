# Per-run Trust Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A ledger-centric per-run trust report that aggregates the audit ledger + completion state (+ optional reproduction score) into one honest summary — surfaced at run end, written to the workspace, and viewable via `abm-auto trust <workspace>`.

**Architecture:** A deep module `abm_auto/trust.py` reads existing recorded signals (the `AuditLedger`, whether `REPORT.md` exists, `research_spec.json`) and produces a `TrustReport`. A small `TrustReportPhase` writes/prints it at run end; a `trust` CLI command views it. No pipeline phase or gate is changed to emit new data.

**Tech Stack:** Python, the existing `abm_auto.audit.ledger.AuditLedger`, typer/rich CLI, pytest.

**Spec:** `docs/superpowers/specs/2026-06-26-trust-report-design.md`
**Branch:** `feat/trust-report` (public repo). Tests: `.venv/bin/python -m pytest tests/test_trust.py -v`.

---

## File Structure

- **Create `abm_auto/trust.py`** — `PhaseTrust`, `TrustReport`, `build_trust_report`, renderers. One responsibility: turn a finished workspace into a trust summary.
- **Create `tests/test_trust.py`** — synthetic-workspace tests (hand-written `audit_ledger.jsonl` + `REPORT.md`), no live LLM.
- **Modify `abm_auto/pipeline/phases/output.py`** — add `TrustReportPhase`.
- **Modify `abm_auto/pipeline/pipeline.py`** — register `TrustReportPhase` last in `_build_phases()`.
- **Modify `abm_auto/cli.py`** — add the `trust` command.

Relevant existing API (read before coding):
- `abm_auto.audit.ledger.AuditLedger(workspace_path)` → `all_events() -> list[AuditEvent]`, `open_issues() -> list[AuditEvent]` (latest raise/reopen per open issue), `current_state() -> dict[issue_id, event_type]`.
- `AuditEvent` fields: `event_id, timestamp, event_type, issue_id, phase, severity, text, structured, actor`.
- `abm_auto.audit.ledger.EventType` (`RAISE/REOPEN/RESOLVE/INFO/...`), `Severity` (`HIGH/MEDIUM/...`).
- The ledger file is `audit_ledger.jsonl` in the workspace; `AuditLedger` constructs even if absent (no events).

---

## Task 1: `TrustReport`/`PhaseTrust` + `build_trust_report` cleanliness verdict

**Files:**
- Create: `abm_auto/trust.py`
- Test: `tests/test_trust.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_trust.py`:

```python
"""Tests for the per-run trust report (abm_auto.trust)."""
from __future__ import annotations

import json

from abm_auto.trust import build_trust_report


def _event(issue_id, event_type, phase, severity="medium", text="x"):
    return {
        "event_id": issue_id, "timestamp": "2026-06-26T00:00:00Z",
        "event_type": event_type, "issue_id": issue_id, "phase": phase,
        "severity": severity, "text": text, "structured": {}, "actor": "Gate",
    }


def _workspace(tmp_path, events, report=True):
    if report:
        (tmp_path / "REPORT.md").write_text("# report", encoding="utf-8")
    lines = "\n".join(json.dumps(e) for e in events)
    (tmp_path / "audit_ledger.jsonl").write_text(lines + ("\n" if lines else ""), encoding="utf-8")
    return tmp_path


def test_clean_when_completed_and_no_open_issues(tmp_path):
    _workspace(tmp_path, [_event("i1", "raise", "Phase 4"), _event("i1", "resolve", "Phase 4")])
    r = build_trust_report(tmp_path)
    assert r.cleanliness == "CLEAN"
    assert r.completed is True
    assert r.open_total == 0
    assert r.resolved_total == 1


def test_caveated_when_open_issue_remains(tmp_path):
    _workspace(tmp_path, [_event("i1", "raise", "Phase 4", severity="high")])
    r = build_trust_report(tmp_path)
    assert r.cleanliness == "CAVEATED"
    assert r.open_total == 1
    assert r.open_high == 1


def test_failed_when_no_report(tmp_path):
    _workspace(tmp_path, [], report=False)
    r = build_trust_report(tmp_path)
    assert r.cleanliness == "FAILED"
    assert r.completed is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_trust.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'abm_auto.trust'`.

- [ ] **Step 3: Write `abm_auto/trust.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_trust.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add abm_auto/trust.py tests/test_trust.py
git commit -m "feat(trust): build_trust_report cleanliness verdict (ledger-centric)"
```

---

## Task 2: Per-phase breakdown + silent-phase detection

> **Amendment (post-review):** the `_PIPELINE_PHASES` / `silent_phases` exact-match
> approach below was IMPLEMENTED then REVERTED during review. Real ledger `phase=`
> strings are decorated/variant (`"Phase 5 (run 3)"`, `"Phase 6 (calibration)"`,
> `"Phase 3 pre-run"`, …) with no reliable normalization to a canonical list, so
> enumerating "silent" phases would emit false "ungated" claims — the opposite of
> this report's honesty goal. Final design: keep the per-phase open/resolved
> breakdown (phases that recorded events), DROP `_PIPELINE_PHASES` and the
> `silent_phases` field, and let the renderers' blanket caveat cover the
> complement ("phases not shown recorded no audit signal — not proof they were
> checked"). See the `fix(trust): drop brittle silent-phase claims…` commit.

**Files:**
- Modify: `abm_auto/trust.py`
- Test: `tests/test_trust.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_trust.py`:

```python
def test_per_phase_breakdown_and_silent(tmp_path):
    _workspace(tmp_path, [
        _event("a", "raise", "Phase 4", severity="high"),
        _event("b", "raise", "Phase 5"), _event("b", "resolve", "Phase 5"),
    ])
    r = build_trust_report(tmp_path)
    by_phase = {p.phase: p for p in r.phases}
    assert by_phase["Phase 4"].open_issues == 1 and by_phase["Phase 4"].resolved_issues == 0
    assert by_phase["Phase 5"].open_issues == 0 and by_phase["Phase 5"].resolved_issues == 1
    # A canonical phase that produced no events is reported as silent.
    assert "Phase 2" in r.silent_phases
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_trust.py::test_per_phase_breakdown_and_silent -v`
Expected: FAIL — `r.phases` is empty and `silent_phases` is empty.

- [ ] **Step 3: Implement the breakdown in `build_trust_report`**

In `abm_auto/trust.py`, before the `return`, compute phases + silent, and pass them to `TrustReport(...)`:

```python
    open_ids = {e.issue_id for e in open_evs}
    phases_seen: dict[str, dict[str, int]] = {}
    for e in events:
        if e.event_type == EventType.INFO:
            phases_seen.setdefault(e.phase, {"open": 0, "resolved": 0})
            continue
        bucket = phases_seen.setdefault(e.phase, {"open": 0, "resolved": 0})
    # count open/resolved per phase from the issue's latest state
    latest: dict[str, object] = {}
    for e in events:
        if e.event_type != EventType.INFO:
            latest[e.issue_id] = e
    for e in latest.values():
        b = phases_seen.setdefault(e.phase, {"open": 0, "resolved": 0})
        if e.issue_id in open_ids:
            b["open"] += 1
        elif e.event_type == EventType.RESOLVE:
            b["resolved"] += 1
    phases = [PhaseTrust(p, c["open"], c["resolved"]) for p, c in sorted(phases_seen.items())]
    silent_phases = [p for p in _PIPELINE_PHASES if p not in phases_seen]
```

Then change the `return` to include them:

```python
    return TrustReport(
        cleanliness=cleanliness, completed=completed,
        open_high=open_high, open_total=open_total, resolved_total=resolved_total,
        phases=phases, silent_phases=silent_phases, note=note,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_trust.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add abm_auto/trust.py tests/test_trust.py
git commit -m "feat(trust): per-phase open/resolved breakdown + silent-phase detection"
```

---

## Task 3: Fidelity verdict + renderers

**Files:**
- Modify: `abm_auto/trust.py`
- Test: `tests/test_trust.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_trust.py`:

```python
import pytest


@pytest.mark.parametrize("score,thresh,expected", [
    (5.0, 10.0, "REPRO"), (10.0, 10.0, "REPRO"),
    (15.0, 10.0, "PARTIAL"), (20.0, 10.0, "PARTIAL"),
    (25.0, 10.0, "MISS"),
])
def test_fidelity_verdict(tmp_path, score, thresh, expected):
    _workspace(tmp_path, [])
    r = build_trust_report(tmp_path, repro_score=(score, thresh))
    assert r.fidelity == expected
    assert r.fidelity_detail == (score, thresh)


def test_fidelity_none_without_score(tmp_path):
    _workspace(tmp_path, [])
    assert build_trust_report(tmp_path).fidelity is None


def test_render_is_honest_no_verified(tmp_path):
    _workspace(tmp_path, [_event("a", "raise", "Phase 4", severity="high")])
    r = build_trust_report(tmp_path)
    md = r.render_markdown()
    assert "CAVEATED" in md
    assert "verified" not in md.lower()   # ledger-centric: never claims "verified"
    assert r.render_console()             # non-empty
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_trust.py -k "fidelity or render" -v`
Expected: FAIL — fidelity always None; `render_markdown`/`render_console` missing.

- [ ] **Step 3: Implement fidelity + renderers**

In `build_trust_report`, after computing `cleanliness`, derive fidelity from `repro_score`:

```python
    fidelity = None
    if repro_score is not None:
        score, t = repro_score
        fidelity = "REPRO" if score <= t else ("PARTIAL" if score <= 2 * t else "MISS")
```

Pass `fidelity=fidelity, fidelity_detail=repro_score` into the `TrustReport(...)` return.

Then add methods to `TrustReport`:

```python
    def render_console(self) -> str:
        lines = [f"Trust: {self.cleanliness}" + (f" | fidelity {self.fidelity}" if self.fidelity else "")]
        lines.append(
            f"  completed={self.completed}  open={self.open_total} (HIGH {self.open_high})"
            f"  resolved={self.resolved_total}"
        )
        if self.fidelity_detail:
            lines.append(f"  reproduction score={self.fidelity_detail[0]} (threshold {self.fidelity_detail[1]})")
        if self.silent_phases:
            lines.append(f"  ungated/silent phases: {', '.join(self.silent_phases)}")
        if self.note:
            lines.append(f"  note: {self.note}")
        lines.append("  (ledger-centric: 'no issues' is not proof of verification)")
        return "\n".join(lines)

    def render_markdown(self) -> str:
        out = ["# Trust report", "", f"**Cleanliness:** {self.cleanliness}  ", f"**Completed:** {self.completed}  "]
        if self.fidelity:
            out.append(f"**Reproduction fidelity:** {self.fidelity}  ")
            if self.fidelity_detail:
                out.append(f"(score {self.fidelity_detail[0]} vs threshold {self.fidelity_detail[1]})  ")
        out += ["", f"Open issues: {self.open_total} (HIGH {self.open_high}); resolved: {self.resolved_total}", ""]
        if self.phases:
            out.append("| phase | open | resolved |")
            out.append("|---|---|---|")
            for p in self.phases:
                out.append(f"| {p.phase} | {p.open_issues} | {p.resolved_issues} |")
            out.append("")
        if self.silent_phases:
            out.append(f"Ungated / silent phases (no audit signal): {', '.join(self.silent_phases)}")
            out.append("")
        if self.note:
            out.append(f"> {self.note}")
            out.append("")
        out.append("_Ledger-centric: this reflects recorded audit signals only; absence of an issue is not proof of verification._")
        return "\n".join(out)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_trust.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add abm_auto/trust.py tests/test_trust.py
git commit -m "feat(trust): fidelity verdict + honest console/markdown renderers"
```

---

## Task 4: `abm-auto trust <workspace>` CLI command

**Files:**
- Modify: `abm_auto/cli.py`
- Test: `tests/test_trust.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_trust.py`:

```python
from typer.testing import CliRunner

from abm_auto.cli import app

_runner = CliRunner()


def test_trust_cli_renders(tmp_path):
    _workspace(tmp_path, [_event("a", "raise", "Phase 4", severity="high")])
    result = _runner.invoke(app, ["trust", str(tmp_path)])
    assert result.exit_code == 0
    assert "CAVEATED" in result.stdout
    assert (tmp_path / "trust_report.md").exists()  # refreshes the file


def test_trust_cli_missing_path():
    result = _runner.invoke(app, ["trust", "/no/such/workspace"])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_trust.py -k trust_cli -v`
Expected: FAIL — no `trust` command (`exit_code != 0` for the first; usage error).

- [ ] **Step 3: Add the `trust` command to `abm_auto/cli.py`**

Add near the other workspace commands (e.g., after `memory`):

```python
@app.command()
def trust(
    workspace: Path = typer.Argument(..., help="Path to an existing workspace directory", exists=True),
):
    """Show the per-run trust report: cleanliness (CLEAN/CAVEATED/FAILED), optional
    reproduction fidelity, open/resolved issues per phase, and ungated phases."""
    from abm_auto.trust import build_trust_report

    report = build_trust_report(workspace)
    (workspace / "trust_report.md").write_text(report.render_markdown(), encoding="utf-8")
    console.print(report.render_console())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_trust.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add abm_auto/cli.py tests/test_trust.py
git commit -m "feat(cli): 'abm-auto trust <workspace>' command"
```

---

## Task 5: `TrustReportPhase` at run end

**Files:**
- Modify: `abm_auto/pipeline/phases/output.py`
- Modify: `abm_auto/pipeline/pipeline.py`
- Test: `tests/test_trust.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_trust.py`:

```python
def test_trust_report_phase_writes_file(tmp_path):
    _workspace(tmp_path, [_event("a", "raise", "Phase 4")])

    class _WS:
        path = tmp_path

    class _Ctx:
        workspace = _WS()

    from abm_auto.pipeline.phases.output import TrustReportPhase
    phase = TrustReportPhase()
    assert phase.should_run(_Ctx()) is True
    phase.run(_Ctx())
    assert (tmp_path / "trust_report.md").exists()
    assert "Trust report" in (tmp_path / "trust_report.md").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_trust.py::test_trust_report_phase_writes_file -v`
Expected: FAIL — `ImportError: cannot import name 'TrustReportPhase'`.

- [ ] **Step 3: Add `TrustReportPhase` to `abm_auto/pipeline/phases/output.py`**

```python
class TrustReportPhase:
    """Final: write the per-run trust report and print its summary."""

    name = "Final (Trust report)"

    def should_run(self, ctx) -> bool:
        return True

    def run(self, ctx) -> None:
        from abm_auto.trust import build_trust_report

        ws = ctx.workspace.path
        report = build_trust_report(ws)
        (ws / "trust_report.md").write_text(report.render_markdown(), encoding="utf-8")
        console.print("\n[bold]Trust report[/bold]")
        console.print(report.render_console())
```

(The module already imports `console = Console()`.)

- [ ] **Step 4: Register it last in `abm_auto/pipeline/pipeline.py`**

In `_build_phases()`, add `TrustReportPhase` to the import from `output` and append `TrustReportPhase()` as the LAST entry of the returned phases list (after `PackageArsPhase()`).

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_trust.py -v`
Expected: PASS (all trust tests).

- [ ] **Step 6: Commit**

```bash
git add abm_auto/pipeline/phases/output.py abm_auto/pipeline/pipeline.py tests/test_trust.py
git commit -m "feat(pipeline): TrustReportPhase writes/prints the trust report at run end"
```

---

## Task 6: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Full trust suite**

Run: `.venv/bin/python -m pytest tests/test_trust.py -v`
Expected: all PASS.

- [ ] **Step 2: No regression in the broader suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS / skipped only (the pipeline gained one trailing phase; existing tests unaffected).

- [ ] **Step 3: CLI smoke**

Run: `.venv/bin/python -m abm_auto.cli trust --help`
Expected: shows the trust command help, no error.

---

## Self-Review

**Spec coverage:**
- Ledger-centric, zero gate/phase re-architecture → Tasks read `AuditLedger`; only ADD a trailing phase + CLI. ✓
- Cleanliness CLEAN/CAVEATED/FAILED → Task 1. ✓
- Fidelity REPRO/PARTIAL/MISS (≤t/≤2t/else), None without signal → Task 3. ✓
- Per-phase open/resolved + silent-phase labelling → Task 2. ✓
- Never claims "verified" → Task 3 (`test_render_is_honest_no_verified`) + the renderers' caveat line. ✓
- Console + `trust_report.md` file + `trust` CLI command → Tasks 4–5. ✓
- Error handling: missing ledger → `note`; missing path → CLI `exists=True` errors (Task 4 test). ✓
- Tests synthetic, no live LLM → all tasks. ✓

**Placeholder scan:** none — every step has real code + exact commands.

**Type consistency:** `build_trust_report(workspace_path, repro_score=None) -> TrustReport`; `TrustReport(cleanliness, completed, open_high, open_total, resolved_total, phases, silent_phases, fidelity, fidelity_detail, note)`; `PhaseTrust(phase, open_issues, resolved_issues)`; `render_console()/render_markdown()`; `TrustReportPhase` with `name/should_run/run`. All defined in Task 1–3 before use in Task 4–5. The fidelity reproduction *source* is left as the caller's `repro_score` argument (None in the phase v1) — wiring a real reproduction score from the calibration result is a deliberate follow-up, not part of this plan; cleanliness ships regardless.
```
