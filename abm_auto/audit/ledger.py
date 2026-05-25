"""
Audit Ledger — append-only event stream tracking cross-phase issues.

Design (decided 2026-05-22, see CONTEXT.md "Audit Ledger"):
  - Schema:    hybrid free text + optional structured fields (decision 1 = C)
  - Lifecycle: append-only events, status derived from latest event (decision 2 = D)
  - Coexists:  with kill_memo.md / dropped_scenarios.md / Resolution Ledger (decision 3 = B)

Storage:
  audit_ledger.jsonl  — canonical event stream (one JSON event per line)
  audit_ledger.md     — human-readable rendered view (regenerated on each append)

Event types form a small state machine per issue_id:
  raise → (acknowledge | resolve | reopen)*
  info  → (no successor — informational, not an issue)

Issue identity:
  issue_id = "iss-" + sha1(phase + text[:80])[:10]  — content-addressed for dedup.
  A repeated raise of the same content from the same phase is a no-op (idempotent).
  A raise from a different phase with the same text creates a new issue.

Reading:
  current_state()  — dict[issue_id, latest_event_type] — used to count open/resolved
  open_issues()    — list of issues currently in `raise` state (no resolve/ack after)
  events_for(id)   — full timeline for a single issue
  render_markdown()— for Reviewer consumption and human reading
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ── Constants ───────────────────────────────────────────────────────────────


class Severity:
    BLOCKING = "BLOCKING"   # pipeline cannot continue
    HIGH = "HIGH"           # serious issue, reviewer must address
    MEDIUM = "MEDIUM"       # noteworthy, should be reviewed
    LOW = "LOW"             # minor, FYI
    INFO = "INFO"           # not an issue, just a notable event

    _ORDER = [BLOCKING, HIGH, MEDIUM, LOW, INFO]


class EventType:
    RAISE = "raise"
    ACKNOWLEDGE = "acknowledge"
    RESOLVE = "resolve"
    REOPEN = "reopen"
    INFO = "info"

    _TERMINAL = {RESOLVE, ACKNOWLEDGE}  # issue no longer "open" if last event is one of these


# ── Event dataclass ─────────────────────────────────────────────────────────


@dataclass
class AuditEvent:
    """A single append-only event in the audit stream."""

    event_id: str           # sequential "ev-NNNN"
    timestamp: str          # ISO 8601 UTC
    event_type: str         # one of EventType.*
    issue_id: str           # content-addressed issue id (or "info-<hash>" for info events)
    phase: str              # "Phase -1" / "Phase 1c" / "Phase 8" etc.
    severity: str           # one of Severity.* — set on raise, inherited otherwise
    text: str               # the human-readable message
    structured: dict[str, Any] = field(default_factory=dict)  # optional structured fields
    actor: str = ""         # which agent wrote this event

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "AuditEvent":
        return cls(**json.loads(raw))


# ── Main class ──────────────────────────────────────────────────────────────


class AuditLedger:
    """Append-only event log + derived state views.

    Thread/process safety: file appends are atomic (small JSON lines), but the
    rendered .md file may briefly desync if two writers race. Acceptable for
    pipeline use — only one agent writes at a time.
    """

    def __init__(self, workspace_path: Path):
        self.workspace_path = Path(workspace_path)
        self.jsonl_path = self.workspace_path / "audit_ledger.jsonl"
        self.md_path = self.workspace_path / "audit_ledger.md"

    # ── Write API ───────────────────────────────────────────────────────────

    def raise_issue(
        self,
        phase: str,
        severity: str,
        text: str,
        actor: str,
        structured: Optional[dict[str, Any]] = None,
    ) -> str:
        """Create or re-raise an issue. Returns issue_id (idempotent on same content)."""
        issue_id = self._make_issue_id(phase, text)

        # Idempotency: if the latest event for this issue_id is already a raise
        # with the same severity, do not append a duplicate.
        latest = self._latest_event(issue_id)
        if latest is not None and latest.event_type == EventType.RAISE and latest.severity == severity:
            return issue_id

        # If the latest event was resolve/acknowledge, this is a reopen
        event_type = EventType.RAISE
        if latest is not None and latest.event_type in EventType._TERMINAL:
            event_type = EventType.REOPEN

        self._append_event(AuditEvent(
            event_id=self._next_event_id(),
            timestamp=_now_iso(),
            event_type=event_type,
            issue_id=issue_id,
            phase=phase,
            severity=severity,
            text=text,
            structured=structured or {},
            actor=actor,
        ))
        return issue_id

    def acknowledge(self, issue_id: str, note: str, actor: str) -> None:
        """Mark an issue as acknowledged-but-not-fixed (deliberate non-action)."""
        latest = self._latest_event(issue_id)
        if latest is None:
            return  # don't acknowledge non-existent issues
        self._append_event(AuditEvent(
            event_id=self._next_event_id(),
            timestamp=_now_iso(),
            event_type=EventType.ACKNOWLEDGE,
            issue_id=issue_id,
            phase=latest.phase,
            severity=latest.severity,
            text=note,
            actor=actor,
        ))

    def resolve(self, issue_id: str, note: str, actor: str) -> None:
        """Mark an issue as resolved."""
        latest = self._latest_event(issue_id)
        if latest is None:
            return
        self._append_event(AuditEvent(
            event_id=self._next_event_id(),
            timestamp=_now_iso(),
            event_type=EventType.RESOLVE,
            issue_id=issue_id,
            phase=latest.phase,
            severity=latest.severity,
            text=note,
            actor=actor,
        ))

    def info(
        self,
        phase: str,
        text: str,
        actor: str,
        structured: Optional[dict[str, Any]] = None,
    ) -> str:
        """Record a non-issue informational event (e.g., mode detected)."""
        info_id = "info-" + hashlib.sha1(
            f"{phase}|{text[:80]}".encode("utf-8")
        ).hexdigest()[:10]
        self._append_event(AuditEvent(
            event_id=self._next_event_id(),
            timestamp=_now_iso(),
            event_type=EventType.INFO,
            issue_id=info_id,
            phase=phase,
            severity=Severity.INFO,
            text=text,
            structured=structured or {},
            actor=actor,
        ))
        return info_id

    # ── Read API ────────────────────────────────────────────────────────────

    def all_events(self) -> list[AuditEvent]:
        """Return every event in chronological order."""
        if not self.jsonl_path.exists():
            return []
        events: list[AuditEvent] = []
        for line in self.jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(AuditEvent.from_json(line))
            except Exception:
                continue  # tolerate corrupt lines
        return events

    def current_state(self) -> dict[str, str]:
        """Return dict[issue_id, latest event_type]."""
        state: dict[str, str] = {}
        for ev in self.all_events():
            state[ev.issue_id] = ev.event_type
        return state

    def open_issues(self) -> list[AuditEvent]:
        """Return the most recent raise/reopen event for each currently-open issue.

        An issue is open if its latest event is `raise` or `reopen` (i.e., not
        resolve/acknowledge). Info events are excluded.
        """
        latest_per_id: dict[str, AuditEvent] = {}
        for ev in self.all_events():
            if ev.event_type == EventType.INFO:
                continue
            latest_per_id[ev.issue_id] = ev
        return [
            ev for ev in latest_per_id.values()
            if ev.event_type in (EventType.RAISE, EventType.REOPEN)
        ]

    def events_for(self, issue_id: str) -> list[AuditEvent]:
        """Return the full timeline for one issue."""
        return [ev for ev in self.all_events() if ev.issue_id == issue_id]

    # ── Render ──────────────────────────────────────────────────────────────

    def render_markdown(self) -> str:
        """Build human-readable markdown view. Called automatically on every append."""
        events = self.all_events()
        if not events:
            return "# Audit Ledger\n\n_No events recorded._\n"

        open_issues = self.open_issues()

        # Group events by issue_id for the timeline section
        by_issue: dict[str, list[AuditEvent]] = {}
        for ev in events:
            by_issue.setdefault(ev.issue_id, []).append(ev)

        # ── Header + summary ──
        lines = [
            "# Audit Ledger",
            "",
            f"_Append-only event log. {len(events)} events, "
            f"{len(open_issues)} currently-open issues._",
            "",
        ]

        # ── Open issues table (sorted by severity) ──
        if open_issues:
            severity_rank = {s: i for i, s in enumerate(Severity._ORDER)}
            open_issues_sorted = sorted(
                open_issues, key=lambda e: severity_rank.get(e.severity, 99)
            )
            lines += [
                "## Open issues",
                "",
                "| Severity | Phase | Actor | Issue |",
                "|----------|-------|-------|-------|",
            ]
            for ev in open_issues_sorted:
                text_safe = ev.text.replace("\n", " ").replace("|", "\\|")[:120]
                lines.append(
                    f"| {ev.severity} | {ev.phase} | {ev.actor} | {text_safe} |"
                )
            lines.append("")

        # ── Resolved / acknowledged summary ──
        resolved_ids = [
            iid for iid, evs in by_issue.items()
            if evs[-1].event_type in EventType._TERMINAL
        ]
        if resolved_ids:
            lines += [
                f"## Closed issues ({len(resolved_ids)})",
                "",
            ]
            for iid in resolved_ids:
                last = by_issue[iid][-1]
                first = by_issue[iid][0]
                status_label = "✓ resolved" if last.event_type == EventType.RESOLVE else "≡ acknowledged"
                lines.append(
                    f"- {status_label} (was {first.severity}, raised by {first.actor} in {first.phase}): "
                    f"{first.text[:120]}"
                )
            lines.append("")

        # ── Full timeline ──
        lines += ["## Full event timeline", ""]
        for ev in events:
            badge = {
                EventType.RAISE: "🚩",
                EventType.REOPEN: "🔄",
                EventType.RESOLVE: "✓",
                EventType.ACKNOWLEDGE: "≡",
                EventType.INFO: "ℹ",
            }.get(ev.event_type, "•")
            lines.append(
                f"- `{ev.event_id}` {badge} **{ev.event_type}** "
                f"[{ev.severity}] {ev.phase} (by {ev.actor}): {ev.text[:160]}"
            )

        return "\n".join(lines) + "\n"

    def for_reviewer(self) -> str:
        """Compact view tuned for inclusion in reviewer prompts (token-budget aware)."""
        open_issues = self.open_issues()
        events = self.all_events()
        resolved = [e for e in events if e.event_type == EventType.RESOLVE]
        acknowledged = [e for e in events if e.event_type == EventType.ACKNOWLEDGE]

        if not events:
            return "（审计记录为空——pipeline 各阶段未提出任何 issue）"

        lines = [
            f"审计统计：共 {len(events)} 个事件，{len(open_issues)} 个当前 open，"
            f"{len(resolved)} 个已解决，{len(acknowledged)} 个已 acknowledged。",
            "",
        ]
        if open_issues:
            lines.append("**Open issues（请重点关注）：**")
            for ev in open_issues:
                lines.append(f"- [{ev.severity}] {ev.phase}（{ev.actor}）：{ev.text[:200]}")
            lines.append("")

        if resolved:
            lines.append(f"**已解决（{len(resolved)} 条）：**")
            for ev in resolved[-5:]:  # last 5 only to keep prompt small
                lines.append(f"- [{ev.severity}] {ev.phase}（{ev.actor}）：{ev.text[:120]}")
            lines.append("")
        return "\n".join(lines)

    # ── Internal ────────────────────────────────────────────────────────────

    @staticmethod
    def _make_issue_id(phase: str, text: str) -> str:
        h = hashlib.sha1(f"{phase}|{text[:80]}".encode("utf-8")).hexdigest()[:10]
        return f"iss-{h}"

    def _latest_event(self, issue_id: str) -> Optional[AuditEvent]:
        latest: Optional[AuditEvent] = None
        for ev in self.all_events():
            if ev.issue_id == issue_id:
                latest = ev
        return latest

    def _next_event_id(self) -> str:
        existing = self.all_events()
        return f"ev-{len(existing) + 1:04d}"

    def _append_event(self, ev: AuditEvent) -> None:
        # Append the JSON line
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(ev.to_json() + "\n")
        # Regenerate the markdown view
        self.md_path.write_text(self.render_markdown(), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
