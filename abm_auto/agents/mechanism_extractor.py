"""
Phase 1d — Mechanism Spec Extraction.

Reads DESIGN.md (+ hypothesis.md if originate mode) and produces a
pseudocode `mechanism_spec.md` that pins down every behavioural
decision the design left ambiguous. The downstream CoderAgent reads
this spec as a HARD CONTRACT — implements it literally.

This phase is the "raise the ceiling" half of the fidelity-improvement
strategy: instead of asking CoderAgent to translate English-prose design
into Python (lossy, high variance), give it an unambiguous pseudocode
target that has ONE valid implementation.

Pipeline placement:
    DesignAgent → ViabilityChecker (Phase 1+1c)
      ↓
    MechanismExtractor (Phase 1d)  ← this agent
      ↓
    OddWriter (Phase 1b)
      ↓
    CoderAgent (Phase 2) — reads mechanism_spec.md at TOP of user prompt

Output file: <workspace>/mechanism_spec.md
"""
from __future__ import annotations

from rich.console import Console

from abm_auto.agents.base import BaseAgent

console = Console()

_SYSTEM = (
    "You are a simulation algorithm specifier. Your job is to read an ABM "
    "design document and produce unambiguous pseudocode that pins down "
    "every behavioural decision left ambiguous. The pseudocode you write "
    "will be translated LITERALLY into Python by the downstream coder; "
    "any ambiguity becomes mechanism drift. Write in the same language as "
    "the design document (Chinese if Chinese, English if English)."
)

# Soft minimum for a meaningful spec; below this we treat output as failed.
_MIN_OUTPUT_CHARS = 400


class MechanismExtractor(BaseAgent):
    """Phase 1d: produce mechanism_spec.md.

    Idempotent: if mechanism_spec.md already exists with substantive content,
    skip (lets re-runs of partial pipelines preserve work).
    """

    def run(self) -> str:
        existing = self.workspace.read_mechanism_spec()
        if existing and len(existing.strip()) > _MIN_OUTPUT_CHARS:
            console.print(
                "  [dim]Phase 1d: mechanism_spec.md already present — skipping.[/dim]"
            )
            return existing

        console.print("[bold cyan]Phase 1d: Extracting mechanism spec...[/bold cyan]")

        design = self.workspace.read_design()
        if not design:
            console.print(
                "  [yellow]⚠ No DESIGN.md — skipping mechanism spec[/yellow]"
            )
            return ""

        hypothesis = self.workspace.read_hypothesis()

        template = self.load_prompt("mechanism_spec")
        prompt = self.render_prompt(
            template,
            design=design,
            hypothesis=hypothesis or "",
        )
        # Strip the unfilled {% if hypothesis %} ... {% endif %} block when no hypothesis
        if not hypothesis:
            import re
            prompt = re.sub(
                r"\{%\s*if hypothesis\s*%\}.*?\{%\s*endif\s*%\}",
                "",
                prompt,
                flags=re.DOTALL,
            )

        spec = self.call_llm(_SYSTEM, prompt, max_tokens=2048)
        if not spec or len(spec.strip()) < _MIN_OUTPUT_CHARS:
            console.print(
                f"  [yellow]⚠ Mechanism spec is too short ({len(spec or '')} chars) — "
                f"keeping it but quality may be low[/yellow]"
            )

        self.workspace.write_mechanism_spec(spec)
        console.print(
            f"  [green]✓ mechanism_spec.md written ({len(spec)} chars)[/green]"
        )

        # Audit
        try:
            section_count = spec.count("\n## ")
            self.workspace.audit.info(
                phase="Phase 1d",
                text=f"Mechanism spec generated ({len(spec)} chars, {section_count} sections)",
                actor="MechanismExtractor",
                structured={
                    "length": len(spec),
                    "sections": section_count,
                    "had_hypothesis": bool(hypothesis),
                },
            )
        except Exception:
            pass

        return spec
