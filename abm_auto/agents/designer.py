from __future__ import annotations

import json
import re
from rich.console import Console

from abm_auto.agents.base import BaseAgent
from abm_auto.agents.hypothesis_agent import HypothesisAgent

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

        # Inject agent design patterns reference so LLM makes explicit pattern choices
        try:
            agent_design_ref = self.load_knowledge("abm-agent-design")
            agent_design_block = f"\n\n---\n\n## Agent Design Reference\n\n{agent_design_ref}"
        except FileNotFoundError:
            agent_design_block = ""

        # Inject hypothesis.md when present (originate mode).
        # Extracts the recommended hypothesis and instructs DesignAgent to build
        # the model around it, not to re-derive the theoretical framing from scratch.
        hypothesis_block = ""
        if hypothesis:
            recommended = self._extract_recommended_hypothesis(hypothesis)
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
            used_h = self._detect_hypothesis_used_in_design(design)
            recommended_h = (
                HypothesisAgent._extract_recommended_number(hypothesis) if hypothesis else None
            )
            drift = (
                used_h and recommended_h and used_h != recommended_h
            )
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
                    text=(
                        f"Hypothesis-design drift detected: hypothesis.md recommended "
                        f"H{recommended_h}, but DESIGN.md built around H{used_h}. "
                        f"The implementation tests a different theory than the one selected."
                    ),
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
        except Exception:
            pass

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

    @staticmethod
    def _detect_hypothesis_used_in_design(design_md: str) -> str | None:
        """Inspect DESIGN.md to find which H<N> it claims to implement.

        Looks for the standard "Selected hypothesis" / "选定假设" marker in the
        Theoretical Anchor section. Returns the H number as a string, or None
        if the design has no such marker (e.g., reproduce mode).
        """
        # Patterns: "Selected hypothesis ... H3", "选定假设 ... H3", "**H3**", etc.
        patterns = [
            r"Selected\s+hypothesis[^\n]*?H\s*(\d+)",
            r"选[定择]\s*假设[^\n]*?H\s*(\d+)",
            r"\*\*\s*H\s*(\d+)\s*[:：]",  # bold heading like **H3：**
            r"build(?:ing)?\s+(?:around\s+)?H\s*(\d+)",
            r"构建\s*H\s*(\d+)",
        ]
        for p in patterns:
            m = re.search(p, design_md[:3000], re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    def _extract_recommended_hypothesis(self, hypothesis_md: str) -> str:
        """Extract the Recommendation section + the recommended H block.

        Bilingual: recognises both English ("## Recommendation", "Build H<N>")
        and Chinese ("## 推荐", "构建 H<N>") headings and verbs. Critical for
        the dual-mode workflow — if extraction fails silently, DesignAgent will
        pick H1 by default and silently implement the wrong hypothesis.
        """
        import re

        lines = hypothesis_md.splitlines()
        rec_lines: list[str] = []
        h_number: str | None = None

        # 1. Scan for the Recommendation section (English OR Chinese heading)
        # Note: \b doesn't work on CJK chars, so use lookahead with optional
        # non-word boundary instead. The patterns match at start of heading.
        rec_heading_pattern = re.compile(
            r"^##\s*(Recommendation|推荐|推荐方案|建议)(?![A-Za-z])",
            re.IGNORECASE,
        )
        reject_heading_pattern = re.compile(
            r"^##\s*(Rejected|Reject|被否决|被驳回|已驳回)(?![A-Za-z])",
            re.IGNORECASE,
        )

        in_rec = False
        for line in lines:
            if rec_heading_pattern.match(line):
                in_rec = True
                continue
            if in_rec:
                # Stop at the next ## heading (any other section)
                if line.startswith("## "):
                    break
                rec_lines.append(line)

        recommendation = "\n".join(rec_lines).strip()

        # 2. Find the recommended H number — multiple patterns, in priority order
        # (a) explicit "Build H<N>" / "构建 H<N>" / "推荐 H<N>" in recommendation
        if recommendation:
            patterns = [
                r"(?:Build|构建|推荐|选择|采用)\s*H\s*[:：]?\s*(\d+)",
                r"\*\*\s*(?:Build|构建)\s*H\s*[:：]?\s*(\d+)",
                r"H\s*(\d+)\b",  # last resort: first H<N> in recommendation block
            ]
            for p in patterns:
                m = re.search(p, recommendation, re.IGNORECASE)
                if m:
                    h_number = m.group(1)
                    break

        # (b) if recommendation section didn't yield a number, scan the
        #     rejected-alternatives block in reverse: whichever H is NOT in it
        #     is likely the recommended one (3 hypotheses minus 2 rejected).
        if h_number is None:
            rejected_nums: set[str] = set()
            in_reject = False
            for line in lines:
                if reject_heading_pattern.match(line):
                    in_reject = True
                    continue
                if in_reject and line.startswith("## "):
                    break
                if in_reject:
                    for m in re.finditer(r"H\s*(\d+)", line):
                        rejected_nums.add(m.group(1))
            if len(rejected_nums) == 2:
                # Exactly 2 rejected → the missing one is the recommendation
                all_nums = {"1", "2", "3"}
                candidate = all_nums - rejected_nums
                if len(candidate) == 1:
                    h_number = candidate.pop()

        # 3. Extract the chosen H block
        recommended_h = ""
        if h_number:
            in_block = False
            block_lines = []
            block_heading_re = re.compile(rf"^##\s*H\s*{h_number}\s*[:：]")
            other_h_re = re.compile(rf"^##\s*H\s*\d+\s*[:：]")
            for line in lines:
                if block_heading_re.match(line):
                    in_block = True
                    block_lines.append(line)
                    continue
                if in_block:
                    # Stop at next H block or at Recommendation / Rejected
                    if other_h_re.match(line):
                        break
                    if rec_heading_pattern.match(line) or reject_heading_pattern.match(line):
                        break
                    block_lines.append(line)
            recommended_h = "\n".join(block_lines).strip()

        # 4. Compose final extract — with a clear marker for the LLM
        if recommended_h and recommendation:
            return (
                f"**RECOMMENDED HYPOTHESIS: H{h_number}** "
                f"(extracted from hypothesis.md — build the design around this one)\n\n"
                f"{recommended_h}\n\n"
                f"### Why this hypothesis was recommended\n\n{recommendation}"
            )
        if recommendation:
            return (
                f"**Recommendation block from hypothesis.md "
                f"(could not isolate single H block — read carefully):**\n\n"
                f"{recommendation}\n\n"
                f"---\n\n## Full hypothesis.md\n\n{hypothesis_md[:1500]}"
            )
        return hypothesis_md[:1500]
