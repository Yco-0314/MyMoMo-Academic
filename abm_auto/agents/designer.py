from __future__ import annotations

import json
from rich.console import Console

from abm_auto.agents import _hypothesis
from abm_auto.agents.base import BaseAgent

console = Console()


class DesignAgent(BaseAgent):
    """Converts STORY.md (+ optional lit_notes.md + hypothesis.md) → DESIGN.md.

    Loads a mode-specific prompt:
      reproduce → phase1_design_reproduce.md  (strict, extraction-focused)
      originate → phase1_design_originate.md  (hypothesis-anchored, design choices expected)
      no spec   → phase1_design.md            (legacy single-prompt fallback)
    """

    def run(self, extra_feedback: str | None = None) -> str:
        """Generate DESIGN.md from STORY.md (+ optional context).

        Args:
            extra_feedback: Optional free-text feedback from a previous
                            failed attempt. Used by the GVR loop in pipeline
                            (Designer + Viability adapter) to nudge the LLM
                            on a second/third try.
        """
        console.print("[bold cyan]Phase 1: Designing ABM...[/bold cyan]")

        story = self.workspace.read_story()
        if not story:
            raise ValueError("STORY.md is empty or missing.")

        lit_notes = self.workspace.read_lit_notes()
        hypothesis = self.workspace.read_hypothesis()

        # Pick prompt based on detected mode (research_spec.json)
        prompt_name, mode_label = self._select_prompt()
        console.print(f"  [dim]Using prompt: {prompt_name}.md (mode={mode_label})[/dim]")
        prompt_template = self.load_prompt(prompt_name)

        # Replace the {% if lit_notes %} block manually
        if lit_notes:
            prompt = prompt_template.replace(
                "{% if lit_notes %}\n## 0. Literature Context\n\nThe following methodology notes were extracted from relevant ABM literature. Use these to inform your design decisions, parameter ranges, and model structure:\n\n{{ lit_notes }}\n\n---\n{% endif %}",
                f"## 0. Literature Context\n\n{lit_notes}\n\n---",
            )
        else:
            import re
            prompt = re.sub(
                r"\{%\s*if lit_notes\s*%\}.*?\{%\s*endif\s*%\}",
                "",
                prompt_template,
                flags=re.DOTALL,
            )

        # Inject the topology-choice guide so the LLM commits to Grid / Network /
        # Plain explicitly in DESIGN.md. The MyMoMo Knowledge Base file is
        # decision-tree-shaped — directly maps DESIGN.md cues to a module choice.
        try:
            agent_design_ref = self.load_knowledge("03-modules")
            agent_design_block = f"\n\n---\n\n## Topology Module Reference\n\n{agent_design_ref}"
        except FileNotFoundError:
            agent_design_block = ""

        # Inject hypothesis.md when present (originate mode).
        # Extracts the recommended hypothesis and instructs DesignAgent to build
        # the model around it, not to re-derive the theoretical framing from scratch.
        hypothesis_block = ""
        if hypothesis:
            recommended = _hypothesis.recommended_hypothesis(hypothesis).text
            hypothesis_block = (
                "\n\n---\n\n"
                "## Theoretical Framework (from hypothesis.md)\n\n"
                "A competing-hypothesis analysis has been run. "
                "**Build your design around the recommended hypothesis below.** "
                "Do not invent a different mechanism — ground all agent behaviour rules "
                "and parameters in this framework.\n\n"
                f"{recommended}\n\n"
                "The full hypothesis.md (with rejected alternatives) is available for context."
            )
            console.print("  [dim]Using hypothesis.md as theoretical anchor[/dim]")

        # GVR feedback block — only present on retry attempts. Placed AT THE
        # TOP of the user prompt so the LLM reads "fix these issues" before
        # the original brief. Empirically more effective than appending.
        feedback_block = ""
        if extra_feedback:
            feedback_block = (
                "## ⚠ Refinement Feedback (from previous attempt)\n\n"
                "Your previous design was rejected. Address ALL of these issues "
                "in this revision:\n\n"
                f"{extra_feedback}\n\n"
                "---\n\n"
            )
            console.print("  [yellow]Using GVR feedback from previous attempt[/yellow]")

        system = "You are an expert ABM Architect. Produce a complete DESIGN.md document."
        user = (
            f"{feedback_block}"
            f"{prompt}\n\n---\n\n"
            f"## STORY.md\n\n{story}"
            f"{hypothesis_block}"
            f"{agent_design_block}"
        )

        # 6144 (up from 4096) accommodates the mode-specific prompts that now
        # include extra sections (Source Paper Reference / Source Trace for
        # reproduce; Theoretical Anchor / Hypothesis-to-Design Trace for
        # originate). El Farol regression showed reasoner truncating DESIGN.md
        # at 4096 when the prompt itself ate into the budget.
        design = self.call_llm(system, user, max_tokens=6144)
        self.workspace.write_design(design)
        console.print("  [green]✓ DESIGN.md generated[/green]")

        # Audit: which mode + which hypothesis (if any). Paired with
        # HypothesisAgent's audit log this exposes hypothesis-design drift
        # (the H1/H3 silent-bug class).
        try:
            used_h = _hypothesis.used_hypothesis(design)
            recommended_h = (
                _hypothesis.recommended_hypothesis(hypothesis).number if hypothesis else None
            )
            drift = _hypothesis.drift_reason(recommended_h, used_h)
            text = (
                f"DESIGN.md generated (prompt={prompt_name}, mode={mode_label}, "
                f"length={len(design)} chars"
            )
            if hypothesis:
                text += f", recommended_h=H{recommended_h or '?'}, used_h=H{used_h or '?'}"
            text += ")"

            if drift:
                # Raise a real issue — design diverged from hypothesis recommendation
                self.workspace.audit.raise_issue(
                    phase="Phase 1",
                    severity="HIGH",
                    text=f"Hypothesis-design drift detected: {drift}",
                    actor="DesignAgent",
                    structured={
                        "recommended_h": recommended_h,
                        "used_h": used_h,
                        "mode": mode_label,
                    },
                )
            else:
                self.workspace.audit.info(
                    phase="Phase 1",
                    text=text,
                    actor="DesignAgent",
                    structured={
                        "mode": mode_label,
                        "prompt": prompt_name,
                        "design_length": len(design),
                        "recommended_h": recommended_h,
                        "used_h": used_h,
                    },
                )
        except Exception as exc:
            console.print(f"  [yellow]⚠ audit logging failed: {exc}[/yellow]")

        return design

    def _select_prompt(self) -> tuple[str, str]:
        """Pick prompt filename based on detected research mode.

        Reads research_spec.json directly (lighter than importing ResearchSpec
        and risking circular deps). Falls back to the legacy single-file prompt
        when no spec is present — preserves backwards compatibility.

        Returns (prompt_name_without_extension, human_readable_mode_label).
        """
        spec_path = self.workspace.path / "research_spec.json"
        if not spec_path.exists():
            return "phase1_design", "no-spec (legacy)"
        try:
            mode = json.loads(spec_path.read_text(encoding="utf-8")).get("mode", "")
        except Exception:
            return "phase1_design", "spec-parse-failed (legacy)"

        if mode == "reproduce":
            return "phase1_design_reproduce", "reproduce"
        if mode == "originate":
            return "phase1_design_originate", "originate"
        return "phase1_design", f"unknown:{mode} (legacy)"
