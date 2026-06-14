"""
Viability Gate — Phase 1 exit check.

After DesignAgent produces DESIGN.md, this gate decides whether the design
is strong enough to continue into Phase 2 (code generation).

Two failure modes trigger an early stop:
  1. Rule-based: too many AI-ASSUMPTION tags OR too many missing design elements.
  2. LLM-judge: the design is fundamentally under-specified even by loose standards.

On failure: writes kill_memo.md and returns ViabilityResult(ok=False).
On pass:    returns ViabilityResult(ok=True), pipeline continues normally.

Thresholds are mode-aware (passed via ResearchSpec from ModeDetector):
  reproduce mode — strict: max 5 assumptions, max 3 missing elements
  originate mode — relaxed: max 15 assumptions, max 6 missing elements
  (originate research naturally has more unknowns — that's expected)

Design elements checked (the 8 core ABM design dimensions):
  Agents / Interaction / Time / Initialization / Decision / Scenario / Validation / Output
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import anthropic
from rich.console import Console

from abm_auto.agents.base import BaseAgent

console = Console()

# The 8 required design elements — each is a list of alternative keyword
# strings; if ANY appears in DESIGN.md (case-insensitive substring match),
# the element counts as present. Bilingual coverage so Chinese-language designs
# aren't falsely flagged as incomplete.
_REQUIRED_ELEMENTS: list[tuple[str, list[str]]] = [
    ("agent",       ["agent", "代理", "智能体"]),
    ("interact",    ["interact", "交互", "互动", "邻居"]),
    ("time",        ["time", "step", "period", "时间", "时期", "时步", "每周", "每步"]),
    ("initial",     ["initial", "setup", "初始", "初值", "初始化"]),
    ("decision",    ["decision", "behavior", "behaviour", "决策", "行为", "动作"]),
    ("scenario",    ["scenario", "parameter", "场景", "参数"]),
    ("output",      ["output", "metric", "result", "输出", "指标", "结果", "测度"]),
]

# Default thresholds (reproduce mode) — overridden by ResearchSpec when available
_MAX_ASSUMPTIONS = 5
_MAX_MISSING_ELEMENTS = 3
_DEFAULT_LLM_QUESTION = (
    "Is this design specific enough to implement as a real ABM simulation? "
    "FAIL if: agent behaviour is completely unspecified, all parameters are placeholder values "
    "with no justification, or the model has no measurable output. "
    "PASS if the design is implementable even with some assumptions."
)

# ── Assumption counting (hardened: ADR-013 W4 dogfood) ──────────────────────
# A real tag is either BRACKETED (`[AI-ASSUMPTION]` / `[AI-ASSUMPTION: …]`,
# incl. an inline bare marker) or COLON-form (`**AI-ASSUMPTION**:` in the
# §Assumptions section; the colon may be separated from the token by markdown
# emphasis / whitespace). A bare PROSE mention without a bracket or a colon —
# the rule-explanation heading, e.g. "Assumptions (AI-ASSUMPTION only — last
# resort)" / "（AI-ASSUMPTION——最后手段）" — is NOT a tag.
_TAG_RE = re.compile(
    r"\[\s*AI[-_]ASSUMPTION|AI[-_]ASSUMPTION[\s*_]*[:：]", re.IGNORECASE
)

# Identifiers the TEMPLATE generator OWNS — tagging them is a category error
# (boilerplate, not a research assumption). Excluded from the count.
_TEMPLATE_BOILERPLATE_SUBJECTS = {
    "id", "id_scenario", "id_run", "scenario_id", "run_id", "run_num",
    "agent_id", "period", "id_agent",
}

# Phrases that echo the token "AI-ASSUMPTION" as RULE TEXT / section headings,
# not as an actual assertion. Lines containing these are scaffolding.
_SCAFFOLD_MARKERS = (
    "ai-assumption only", "仅ai-assumption", "ai-assumption rule",
    "ai-assumption tag", "ai-assumption item", "ai-assumption count",
    "list any ai-assumption", "list all ai-assumption",
)


def _subject_key(line: str) -> "str | None":
    """Best-effort subject of an assumption line, for de-duplication: a
    backticked `name`, or the LHS of a `name = value`. Returns a normalised
    identifier, or None when the line names no code subject."""
    m = re.search(r"`([A-Za-z_][A-Za-z0-9_]*)`", line)
    if m:
        return m.group(1).lower()
    tail = _TAG_RE.split(line, maxsplit=1)[-1]
    m = re.search(r"([A-Za-z_][A-Za-z0-9_]{2,})\s*[=＝]", tail)
    if m:
        return m.group(1).lower()
    return None


def count_assumptions(design_text: str) -> int:
    """Count DISTINCT, real AI-ASSUMPTION tags in DESIGN.md.

    Hardened (ADR-013 W4 dogfood) against three artifacts that inflated the
    raw ``findall`` count and pushed complex-but-standard models past the
    gate: (1) the gate's own rule-explanation headings; (2) the same
    assumption restated inline AND in the §Assumptions section (double
    count); (3) template-owned boilerplate (``id``, ``scenario_id``, …)
    tagged in error. Counting expressiveness, not string occurrences.
    """
    seen: set[str] = set()
    count = 0
    for line in design_text.splitlines():
        if not _TAG_RE.search(line):
            continue                                    # not a real `AI-ASSUMPTION:` tag
        if any(marker in line.lower() for marker in _SCAFFOLD_MARKERS):
            continue                                    # rule text / section heading
        subject = _subject_key(line)
        if subject in _TEMPLATE_BOILERPLATE_SUBJECTS:
            continue                                    # generator boilerplate, not research
        if subject is not None:
            if subject in seen:
                continue                                # inline + §Assumptions → count once
            seen.add(subject)
        count += 1
    return count


@dataclass
class ViabilityResult:
    ok: bool
    assumption_count: int = 0
    missing_elements: list[str] = field(default_factory=list)
    llm_verdict: str = ""      # "pass" | "fail" | "skip" (if LLM check not run)
    llm_reason: str = ""
    reasons: list[str] = field(default_factory=list)


class ViabilityChecker(BaseAgent):
    """Checks DESIGN.md quality before committing to Phase 2."""

    def check(
        self,
        design_path: Path,
        story_path: Path,
        spec=None,   # ResearchSpec | None — avoids circular import
    ) -> ViabilityResult:
        """
        Run the viability gate.

        Args:
            design_path: Path to DESIGN.md
            story_path:  Path to story.md
            spec:        ResearchSpec from ModeDetector (optional).
                         If provided, thresholds and LLM question are mode-aware.
                         If None, falls back to reproduce-mode defaults.

        Returns ViabilityResult — if .ok is False, writes kill_memo.md.
        """
        # Resolve thresholds from spec (mode-aware) or defaults
        if spec is not None:
            max_assumptions = spec.viability_max_assumptions
            max_missing = spec.viability_max_missing_elements
            llm_question = spec.viability_llm_question or _DEFAULT_LLM_QUESTION
            mode_label = spec.mode
        else:
            max_assumptions = _MAX_ASSUMPTIONS
            max_missing = _MAX_MISSING_ELEMENTS
            llm_question = _DEFAULT_LLM_QUESTION
            mode_label = "reproduce"  # conservative default

        console.print(
            f"[bold cyan]Viability Gate[/bold cyan] "
            f"[dim](mode={mode_label}, max_assumptions={max_assumptions}, "
            f"max_missing={max_missing})[/dim]"
        )

        if not design_path.exists():
            result = ViabilityResult(
                ok=False,
                reasons=["DESIGN.md was not created by DesignAgent."],
            )
            self._write_kill_memo(result, story_path, max_assumptions)
            return result

        design_text = design_path.read_text(encoding="utf-8")
        story_text = story_path.read_text(encoding="utf-8") if story_path.exists() else ""

        # ── Rule 1: Count AI-ASSUMPTION tags (hardened — ADR-013 W4 dogfood) ──
        assumption_count = count_assumptions(design_text)

        # ── Rule 2: Check for missing required design elements ─────────────────
        # An element counts as present if ANY of its keyword aliases (across
        # English and Chinese) is found in design_text.
        missing = []
        design_lower = design_text.lower()
        for element_name, aliases in _REQUIRED_ELEMENTS:
            if not any(alias.lower() in design_lower for alias in aliases):
                missing.append(element_name)

        reasons = []
        if assumption_count > max_assumptions:
            reasons.append(
                f"Design has {assumption_count} AI-ASSUMPTION tags (limit: {max_assumptions}). "
                f"The story.md does not provide enough information — the model would be mostly AI-invented."
            )
        if len(missing) > max_missing:
            reasons.append(
                f"Design is missing {len(missing)} required elements: {', '.join(missing)}. "
                f"These are needed for a valid ABM specification."
            )

        # ── LLM judge (only runs if rule checks are inconclusive) ─────────────
        llm_verdict = "skip"
        llm_reason = ""
        if not reasons:
            llm_verdict, llm_reason = self._llm_judge(design_text, story_text, llm_question)
            if llm_verdict == "fail":
                reasons.append(f"LLM viability judge: {llm_reason}")

        ok = len(reasons) == 0

        result = ViabilityResult(
            ok=ok,
            assumption_count=assumption_count,
            missing_elements=missing,
            llm_verdict=llm_verdict,
            llm_reason=llm_reason,
            reasons=reasons,
        )

        if ok:
            console.print(
                f"  [green]✓ Viability Gate passed[/green] "
                f"[dim](assumptions={assumption_count}, "
                f"missing elements={len(missing)})[/dim]"
            )
            # Record as info — but if assumption count is non-trivial, also raise
            # a MEDIUM-severity issue so the reviewer can see it later
            self.workspace.audit.info(
                phase="Phase 1c",
                text=f"Viability Gate passed (assumptions={assumption_count}, missing={len(missing)})",
                actor="ViabilityChecker",
                structured={
                    "assumption_count": assumption_count,
                    "missing_elements": missing,
                    "mode": mode_label,
                },
            )
            if assumption_count >= max(1, max_assumptions // 2):
                self.workspace.audit.raise_issue(
                    phase="Phase 1c",
                    severity="MEDIUM",
                    text=(
                        f"Design relies on {assumption_count} AI-ASSUMPTION tags "
                        f"(below the {max_assumptions} limit but above half). "
                        f"Reviewer should check whether these assumptions are well-justified."
                    ),
                    actor="ViabilityChecker",
                    structured={
                        "assumption_count": assumption_count,
                        "missing_elements": missing,
                    },
                )
        else:
            console.print(f"  [bold red]✗ Viability Gate FAILED[/bold red]")
            for r in reasons:
                console.print(f"  [red]  • {r}[/red]")
            self._write_kill_memo(result, story_path, max_assumptions)
            # Audit: a BLOCKING issue per reason — these halt the pipeline
            for r in reasons:
                self.workspace.audit.raise_issue(
                    phase="Phase 1c",
                    severity="BLOCKING",
                    text=r,
                    actor="ViabilityChecker",
                    structured={
                        "assumption_count": assumption_count,
                        "missing_elements": missing,
                        "llm_verdict": llm_verdict,
                    },
                )

        return result

    def _llm_judge(
        self, design_text: str, story_text: str, llm_question: str
    ) -> tuple[str, str]:
        """Ask LLM whether the design is viable. Returns (verdict, reason)."""
        system = (
            "You are a strict ABM research quality gatekeeper. "
            "You only answer with JSON: {\"verdict\": \"pass\" or \"fail\", \"reason\": \"<one sentence>\"}. "
            "No other text."
        )
        prompt = (
            "## Story (source material)\n"
            f"{story_text[:1200]}\n\n"
            "## Design Document (DESIGN.md)\n"
            f"{design_text[:2500]}\n\n"
            f"Verdict: {llm_question}"
        )
        try:
            import json
            raw = self.call_llm(system, prompt, max_tokens=256)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
            parsed = json.loads(raw)
            verdict = parsed.get("verdict", "pass").lower()
            reason = parsed.get("reason", "")
            return verdict, reason
        except Exception:
            return "skip", ""  # LLM check failed — don't block the pipeline

    def _write_kill_memo(
        self, result: ViabilityResult, story_path: Path, max_assumptions: int = _MAX_ASSUMPTIONS
    ) -> None:
        """Write kill_memo.md to the workspace."""
        lines = [
            "# Kill Memo — Viability Gate Failed\n",
            "This pipeline run was halted after Phase 1 because the design is not viable.\n",
            "## Reasons\n",
        ]
        for r in result.reasons:
            lines.append(f"- {r}\n")

        lines += [
            "\n## Diagnostics\n",
            f"- AI-ASSUMPTION count: **{result.assumption_count}** (limit: {max_assumptions})\n",
            f"- Missing design elements: **{result.missing_elements or 'none'}**\n",
        ]
        if result.llm_verdict == "fail":
            lines += [
                f"- LLM judge verdict: **fail**\n",
                f"- LLM judge reason: {result.llm_reason}\n",
            ]

        lines += [
            "\n## What to do next\n",
            "1. **Enrich `story.md`** — add more detail on agent behaviour, "
            "interaction mechanism, and measurable outputs.\n",
            "2. Or run `/ars-lit-review` first to gather background knowledge "
            "before attempting the design again.\n",
            "3. Then re-run the pipeline.\n",
            f"\n*Source story: `{story_path.name}`*\n",
        ]

        kill_memo_path = self.workspace.path / "kill_memo.md"
        kill_memo_path.write_text("".join(lines), encoding="utf-8")
        console.print(f"  [dim]kill_memo.md written: {kill_memo_path}[/dim]")
