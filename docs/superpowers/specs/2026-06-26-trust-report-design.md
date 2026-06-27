# Per-run trust report — design

**Date:** 2026-06-26
**Status:** Approved (brainstorming) — ready for implementation plan
**Area:** new `abm_auto/trust.py` + a final pipeline phase + a `trust` CLI command (public repo, off `v3-substantial`)

## Problem

mymomo's distinctive value is being a *harness* — making generated research
trustworthy via deterministic gates (ADR-013). But that trust is currently
**invisible and partial**: gate outcomes and issues are scattered (the audit
ledger, per-phase gates, the report), and the headline framing ("50 models,
100% success") over-sells. There is no single, honest, per-run answer to "how
much should I trust this result, and what was/wasn't checked?"

Goal: one per-run **trust report** that aggregates what the run already recorded
into an honest summary — surfaced at run end, written to the workspace, and
viewable via a CLI command (and later by the chat agent).

## Scope

**Ledger-centric, zero re-architecture.** The report READS existing recorded
signals; it does not change any pipeline phase or gate to emit new data.

**Non-goals:** making every phase emit a `Verdict` to a central collector;
a web/HTML view; changing gate logic. (Those are explicitly out — the report
surfaces what exists.)

## Design

### Deep module: `abm_auto/trust.py`

`build_trust_report(workspace_path: Path) -> TrustReport` reads:
- **Audit ledger** via the existing `AuditLedger(workspace_path)`:
  `open_issues()`, `current_state()`, and the event stream (severity + phase +
  actor + type). This is the central record of what gates/agents flagged.
- **Run completion:** whether `REPORT.md` exists in the workspace (the pipeline
  reached its end) and whether `research_spec.json` records a halt.
- **Reproduction signal (optional):** if `research_spec.json` shows
  intent=`reproduce` AND a machine-readable comparison exists (a calibration
  result / baseline comparison carrying a numeric score vs threshold), read it
  for the fidelity verdict. If no such signal is cleanly available, fidelity is
  `None` — the report never invents one.

It computes two verdicts:

- **Cleanliness** (always): `FAILED` if the run halted or did not produce
  `REPORT.md`; `CAVEATED` if it completed but has open HIGH/MEDIUM issues;
  `CLEAN` if it completed with no open issues.
- **Fidelity** (only when the reproduction signal above is present), against the
  comparison's own threshold `t`: `REPRO` (score ≤ t) / `PARTIAL` (t < score ≤ 2t)
  / `MISS` (score > 2t); else `None`.

And a **per-phase breakdown** from the ledger: for each phase, the count of open
vs resolved issues by severity; and phases that produced **no audit events at
all** are labelled **"ungated / silent"**.

### Anti-fabrication honesty (the 命门)

Because it is ledger-centric, the report states only what the ledger can honestly
support — `flagged` / `open` / `resolved` / `no issues recorded` / `ungated
(silent)`. It **must not** claim `verified`, because absence of an issue is not
proof of verification (a phase may simply be ungated). This is the point: it
replaces "100% success" with "completed; 0 open HIGH issues; these phases were
gated; these were silent."

### `TrustReport` dataclass

Fields: `cleanliness: str`, `fidelity: str | None`, `completed: bool`,
`open_high: int`, `open_total: int`, `resolved_total: int`,
`phases: list[PhaseTrust]` (name, open/resolved counts, gated|silent), and
`fidelity_detail: tuple[float, float] | None` (score, threshold). Methods:
`render_console() -> str` (rich summary) and `render_markdown() -> str`
(`trust_report.md` body).

### Integration (three thin touch-points)

1. **`TrustReportPhase`** — a small phase appended last in
   `Pipeline._build_phases()` (one new file in `pipeline/phases/`, one line to
   register it, matching the existing Phase pattern). On `run()` it calls
   `build_trust_report(ctx.workspace.path)`, writes `trust_report.md`, and prints
   `render_console()`.
2. **`abm-auto trust <workspace>`** — a CLI command mirroring
   `memory`/`trajectories`/`review`: `build_trust_report` → print `render_console()`
   (and refresh `trust_report.md`).
3. **Future (out of this spec, enables #3):** the chat agent surfaces trust by
   calling `abm-auto trust <ws>` through its existing `abm_auto` tool.

## Error handling

- No `audit_ledger.jsonl` → the report notes "no audit ledger (run may be
  incomplete)" and still renders cleanliness from completion state.
- Non-existent / non-workspace path → clear error from the CLI command.
- Malformed ledger lines → skipped with the count noted (don't crash the report).

## Testing (no live LLM, no real run)

- `build_trust_report` on a synthetic workspace (hand-written `audit_ledger.jsonl`
  with mixed open/resolved issues + a `REPORT.md`) → asserts the cleanliness
  verdict, open/resolved counts, and per-phase breakdown incl. an "ungated/silent"
  phase.
- Completion: workspace with no `REPORT.md` → `FAILED`/incomplete.
- Honesty: a phase with no events is reported "ungated", never "verified".
- Fidelity: with a reproduction signal present → REPRO/PARTIAL/MISS by threshold;
  absent → `None`.
- `abm-auto trust <ws>` via `CliRunner` renders the summary; missing path errors.

## Where it lives

- `abm_auto/trust.py` (the module + `TrustReport`/`PhaseTrust` + builder + renderers)
- `abm_auto/pipeline/phases/` — one new `TrustReportPhase` file + one registration line
- `abm_auto/cli.py` — the `trust` command
- Tests in `tests/test_trust.py`
- Branch `feat/trust-report`, off `v3-substantial`.
