from __future__ import annotations
import re

from rich.console import Console

from abm_auto.agents.base import BaseAgent

console = Console()


class OddWriter(BaseAgent):
    """Generates an ODD Protocol document from DESIGN.md."""

    def run(self) -> str:
        console.print("[bold cyan]Phase 1b: Writing ODD Protocol...[/bold cyan]")

        design = self.workspace.read_design()
        if not design:
            raise ValueError("DESIGN.md is missing — run DesignAgent first.")

        project_name = self._extract_project_name(design)
        prompt_template = self.load_prompt("odd")
        prompt = (
            prompt_template
            .replace("{{ design }}", design)
            .replace("{{ project_name }}", project_name)
        )

        system = (
            "You are an expert ABM modeler writing a peer-review-ready ODD Protocol. "
            "Be precise and complete. Use the exact 7-section structure specified."
        )
        odd = self.call_llm(system, prompt, max_tokens=4096)

        odd_path = self.workspace.path / "ODD.md"
        odd_path.write_text(odd, encoding="utf-8")
        console.print(f"  [green]✓ ODD.md generated[/green]")
        return odd

    def _extract_project_name(self, design: str) -> str:
        match = re.search(r"\*\*Project Name\*\*:\s*(.+)", design)
        if match:
            return match.group(1).strip()
        return "ABM Model"
