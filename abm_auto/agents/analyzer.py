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

        # Audit: log run + raise issue if results look degenerate
        try:
            degenerate_signal = self._check_degenerate(results_summary)
            if degenerate_signal:
                self.workspace.audit.raise_issue(
                    phase=f"Phase 5 (run {run_number})",
                    severity="HIGH",
                    text=(
                        f"Degenerate simulation output detected: {degenerate_signal}. "
                        f"Insights may not be meaningful for this run."
                    ),
                    actor="AnalyzerAgent",
                    structured={"run": run_number, "signal": degenerate_signal},
                )
            else:
                self.workspace.audit.info(
                    phase=f"Phase 5 (run {run_number})",
                    text=f"Analysed run {run_number}, insights {len(insights)} chars",
                    actor="AnalyzerAgent",
                    structured={
                        "run": run_number,
                        "insights_length": len(insights),
                        "params": current_params,
                    },
                )
        except Exception:
            pass

        return insights

    @staticmethod
    def _check_degenerate(results_summary: str) -> str | None:
        """Detect obvious degeneracy signals in the results summary string.

        Returns a short description if degenerate, else None. Cheap heuristic —
        the real check is in SanityChecker; this just surfaces the symptom in
        the audit log so reviewers see it without trawling raw CSVs.
        """
        if not results_summary:
            return "results_summary is empty"
        low = results_summary.lower()
        signals = []
        if "all zero" in low or "all-zero" in low or "全部为零" in low:
            signals.append("all-zero metrics")
        if "nan" in low or "缺失" in low:
            signals.append("NaN / missing values")
        if "constant" in low or "no variation" in low or "无变化" in low:
            signals.append("constant metric (no variation)")
        return "; ".join(signals) if signals else None

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
