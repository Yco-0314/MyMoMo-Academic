from __future__ import annotations

from rich.console import Console

from abm_auto.agents.base import BaseAgent

console = Console()


class DesignAgent(BaseAgent):
    """Converts STORY.md (+ optional lit_notes.md) → DESIGN.md."""

    def run(self) -> str:
        console.print("[bold cyan]Phase 1: Designing ABM...[/bold cyan]")

        story = self.workspace.read_story()
        if not story:
            raise ValueError("STORY.md is empty or missing.")

        lit_notes = self.workspace.read_lit_notes()

        prompt_template = self.load_prompt("phase1_design")

        # Build the jinja-like render for lit_notes block
        if lit_notes:
            lit_block = f"## Literature Context\n\n{lit_notes}\n\n---\n"
        else:
            lit_block = ""

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

        system = "You are an expert ABM Architect. Produce a complete DESIGN.md document."
        user = f"{prompt}\n\n---\n\n## STORY.md\n\n{story}{agent_design_block}"

        design = self.call_llm(system, user, max_tokens=4096)
        self.workspace.write_design(design)
        console.print("  [green]✓ DESIGN.md generated[/green]")
        return design
