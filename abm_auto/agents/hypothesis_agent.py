"""
Phase 0.5: Hypothesis Generation Agent (originate mode only).

Runs after LitReviewer, before DesignAgent — exclusively in originate mode.
In reproduce mode this agent is a no-op: the hypothesis is already the paper's.

Purpose:
  When a researcher describes a phenomenon rather than a paper to reproduce,
  the DesignAgent has no theoretical anchor. Without one it guesses mechanisms
  and produces vague designs. This agent:

    1. Reads story.md (what the researcher wants to model)
    2. Reads lit_notes.md (what the literature says, if available)
    3. Generates 3 competing hypotheses — different mechanistic explanations
       for the same phenomenon
    4. Scores each on testability, novelty, and ABM suitability
    5. Recommends one, with justification
    6. Writes hypothesis.md

  DesignAgent then reads hypothesis.md and builds the model around the
  recommended hypothesis — giving it a precise theoretical frame.

Output format (hypothesis.md):
  - Three structured hypothesis blocks (H1/H2/H3)
  - Each contains: mechanism, assumptions, predicted dynamics,
    key parameters, testability score, novelty note
  - A recommendation section: which hypothesis to build and why
  - A "rejected alternatives" brief: why H1/H2 weren't chosen
    (useful for the Review panel's R1 理论贡献质询师)
"""
from __future__ import annotations

from rich.console import Console

from abm_auto.agents import _hypothesis
from abm_auto.agents.base import BaseAgent

console = Console()

_HYPOTHESIS_SYSTEM = """You are a computational social science theorist.
Your job is to generate competing mechanistic hypotheses for agent-based modelling.
Each hypothesis must be:
  - Specific enough to implement as code (not "agents interact somehow")
  - Falsifiable: it predicts observable dynamics that can confirm or refute it
  - Distinct: the three hypotheses should differ in their core mechanism, not just parameters
Write in the same language as the story.md."""


class HypothesisAgent(BaseAgent):
    """
    Phase 0.5: generates competing hypotheses for originate-mode research.

    Called by Pipeline only when spec.mode == "originate".
    Skipped automatically if hypothesis.md already exists (re-run safety).
    """

    def run(self) -> str:
        """Generate hypothesis.md. Returns the text (empty string if skipped)."""

        # Skip if already generated
        existing = self.workspace.read_hypothesis()
        if existing and len(existing.strip()) > 100:
            console.print(
                "  [dim]Phase 0.5: hypothesis.md already present — skipping.[/dim]"
            )
            return existing

        console.print("[bold cyan]Phase 0.5: Generating competing hypotheses...[/bold cyan]")

        story = self.workspace.read_story()
        if not story:
            console.print("  [yellow]⚠ No story.md — skipping hypothesis generation[/yellow]")
            return ""

        lit_notes = self.workspace.read_lit_notes()

        hypothesis_md = self._generate(story, lit_notes)
        self.workspace.write_hypothesis(hypothesis_md)

        # Count and report
        h_count = hypothesis_md.count("## H")
        console.print(
            f"  [green]✓ hypothesis.md written "
            f"({h_count} hypotheses, {len(hypothesis_md)} chars)[/green]"
        )

        # Audit: record which hypothesis was recommended (paired with
        # DesignAgent's audit log, makes hypothesis-design drift visible).
        try:
            recommended_h = _hypothesis.recommended_hypothesis(hypothesis_md).number
            self.workspace.audit.info(
                phase="Phase 0.5",
                text=(
                    f"Generated {h_count} competing hypotheses; "
                    f"recommended H{recommended_h or '?'}"
                ),
                actor="HypothesisAgent",
                structured={
                    "h_count": h_count,
                    "recommended_h": recommended_h,
                    "length_chars": len(hypothesis_md),
                },
            )
        except Exception:
            pass

        return hypothesis_md

    # ── LLM ─────────────────────────────────────────────────────────────────

    def _generate(self, story: str, lit_notes: str) -> str:
        lit_block = f"\n\n## Literature Context\n\n{lit_notes[:1500]}" if lit_notes else ""

        prompt = (
            "## Research Scenario\n\n"
            f"{story[:1500]}"
            f"{lit_block}\n\n"
            "---\n\n"
            "Generate **exactly 3 competing hypotheses** (H1, H2, H3) that could explain\n"
            "the phenomenon above. Each hypothesis should propose a *different core mechanism*.\n\n"
            "For each hypothesis, provide:\n"
            "```\n"
            "## H<N>: <Short memorable name>\n\n"
            "**Core mechanism** (1–2 sentences): How does this mechanism produce the phenomenon?\n\n"
            "**Key assumptions**:\n"
            "- <assumption 1>\n"
            "- <assumption 2>\n\n"
            "**Predicted dynamics**: What should we observe in the simulation if this is correct?\n"
            "(Be specific: equilibria, phase transitions, timescales, distributions)\n\n"
            "**Key parameters to sweep**: <list 3–5 parameters with rough ranges>\n\n"
            "**Testability score**: <N>/10 — <one sentence why>\n\n"
            "**Novelty vs. literature**: <one sentence on what's new or different>\n"
            "```\n\n"
            "After H1/H2/H3, add:\n\n"
            "## Recommendation\n\n"
            "**Build H<N>** because <2–3 sentence justification covering: "
            "theoretical clarity, ABM implementability, and scientific value>.\n\n"
            "## Rejected alternatives (brief)\n\n"
            "- **H<X>**: <one sentence why not chosen>\n"
            "- **H<Y>**: <one sentence why not chosen>\n"
        )

        return self.call_llm(_HYPOTHESIS_SYSTEM, prompt, max_tokens=3000)
