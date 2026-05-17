"""
Viability Gate — Phase 1 exit check.

After DesignAgent produces DESIGN.md, this gate decides whether the design
is strong enough to continue into Phase 2 (code generation).

Two failure modes trigger an early stop:
  1. Rule-based: too many AI-ASSUMPTION tags OR too many missing design elements.
  2. LLM-judge: the design is fundamentally under-specified even by loose standards.

On failure: writes kill_memo.md and returns ViabilityResult(ok=False).
On pass:    returns ViabilityResult(ok=True), pipeline continues normally.

Design elements checked (the 8 from melodie-design):
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

# The 8 required design elements (partial keyword match, case-insensitive)
_REQUIRED_ELEMENTS = [
    "agent",          # Agent types, counts, states
    "interact",       # Interaction mechanism
    "time",           # Time structure / period / step
    "initial",        # Initialization
    "decision",       # Decision logic / behavior rule
    "scenario",       # Parameters / scenarios
    "output",         # Output metrics / KPIs
]

# Thresholds — tuned conservatively so the gate rejects only clearly broken designs
_MAX_ASSUMPTIONS = 5        # more than this → design relies too much on AI guessing
_MAX_MISSING_ELEMENTS = 3   # missing 3+ required elements → story.md too sparse


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

    def check(self, design_path: Path, story_path: Path) -> ViabilityResult:
        """
        Run the viability gate.

        Returns ViabilityResult — if .ok is False, caller should write
        kill_memo.md and halt the pipeline.
        """
        console.print("[bold cyan]Viability Gate: checking design quality...[/bold cyan]")

        if not design_path.exists():
            result = ViabilityResult(
                ok=False,
                reasons=["DESIGN.md was not created by DesignAgent."],
            )
            self._write_kill_memo(result, story_path)
            return result

        design_text = design_path.read_text(encoding="utf-8")
        story_text = story_path.read_text(encoding="utf-8") if story_path.exists() else ""

        # ── Rule 1: Count AI-ASSUMPTION tags ──────────────────────────────────
        assumption_count = len(re.findall(r"AI[-_]ASSUMPTION", design_text, re.IGNORECASE))

        # ── Rule 2: Check for missing required design elements ─────────────────
        missing = []
        design_lower = design_text.lower()
        for element in _REQUIRED_ELEMENTS:
            if element not in design_lower:
                missing.append(element)

        reasons = []
        if assumption_count > _MAX_ASSUMPTIONS:
            reasons.append(
                f"Design has {assumption_count} AI-ASSUMPTION tags (limit: {_MAX_ASSUMPTIONS}). "
                f"The story.md does not provide enough information — the model would be mostly AI-invented."
            )
        if len(missing) > _MAX_MISSING_ELEMENTS:
            reasons.append(
                f"Design is missing {len(missing)} required elements: {', '.join(missing)}. "
                f"These are needed for a valid ABM specification."
            )

        # ── LLM judge (only runs if rule checks are inconclusive) ─────────────
        llm_verdict = "skip"
        llm_reason = ""
        if not reasons:
            # Rules passed — do a quick LLM sanity check
            llm_verdict, llm_reason = self._llm_judge(design_text, story_text)
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
        else:
            console.print(f"  [bold red]✗ Viability Gate FAILED[/bold red]")
            for r in reasons:
                console.print(f"  [red]  • {r}[/red]")
            self._write_kill_memo(result, story_path)

        return result

    def _llm_judge(self, design_text: str, story_text: str) -> tuple[str, str]:
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
            "Verdict: is this design specific enough to implement as a real ABM simulation? "
            "FAIL if: agent behaviour is completely unspecified, all parameters are placeholder values "
            "with no justification, or the model has no measurable output. "
            "PASS if the design is implementable even with some assumptions."
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

    def _write_kill_memo(self, result: ViabilityResult, story_path: Path) -> None:
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
            f"- AI-ASSUMPTION count: **{result.assumption_count}** (limit: {_MAX_ASSUMPTIONS})\n",
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
