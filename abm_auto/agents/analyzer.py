from __future__ import annotations

from rich.console import Console

from abm_auto.agents.base import BaseAgent
from abm_auto.runner.executor import Executor

console = Console()


class AnalyzerAgent(BaseAgent):
    """Interprets CSV simulation results and produces insights."""

    def run(self, executor: Executor, run_number: int) -> str:
        console.print(f"[bold cyan]Phase 5: Analyzing results (run #{run_number})...[/bold cyan]")

        results_summary = executor.get_results_summary(run_number)
        story = self.workspace.read_story()
        design = self.workspace.read_design()

        # Summarise story and design briefly
        story_summary = story[:800] if story else "No story available."
        design_summary = self._extract_design_summary(design)

        params_history = self.workspace.read_params_history()
        current_params = next(
            (h["params"] for h in params_history if h["run"] == run_number), {}
        )

        system = "You are an expert computational social scientist. Provide concise, actionable analysis."
        insights = self.call_llm_with_prompt(
            "analyze",
            system,
            max_tokens=2048,
            story_summary=story_summary,
            design_summary=design_summary,
            run_number=str(run_number),
            current_params=str(current_params),
            results_summary=results_summary,
        )

        # Save to workspace
        insights_path = self.workspace.results_dir / f"run_{run_number:02d}" / "insights.md"
        insights_path.write_text(insights, encoding="utf-8")

        console.print(f"  [green]✓ Insights saved for run #{run_number}[/green]")
        return insights

    def _extract_design_summary(self, design: str) -> str:
        """Extract the Model Overview section from DESIGN.md."""
        if not design:
            return "No design available."
        lines = design.split("\n")
        summary_lines = []
        in_overview = False
        for line in lines:
            if "Model Overview" in line:
                in_overview = True
            if in_overview:
                summary_lines.append(line)
                if len(summary_lines) > 15:
                    break
        return "\n".join(summary_lines) if summary_lines else design[:500]
