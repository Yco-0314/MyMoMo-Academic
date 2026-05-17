from __future__ import annotations
import json

from rich.console import Console

from abm_auto.agents.base import BaseAgent
from abm_auto.agents.coder import CoderAgent

console = Console()


class OptimizerAgent(BaseAgent):
    """Suggests new parameters for the next simulation run."""

    def run(self, current_run: int, previous_insights: str, coder: CoderAgent,
            memory_context: str = "") -> dict:
        console.print(f"[bold cyan]Phase 6: Optimizing parameters for run #{current_run + 1}...[/bold cyan]")

        story = self.workspace.read_story()
        params_history = self.workspace.read_params_history()

        # Build a summary of all previous runs
        all_results_summary = self._build_results_summary()

        current_params = next(
            (h["params"] for h in params_history if h["run"] == current_run), {}
        )

        system = (
            "You are an expert ABM researcher. "
            "Respond ONLY with valid JSON as specified. No other text."
        )
        extra = f"\n\n## 实验记忆（跨轮次积累的知识）\n{memory_context}" if memory_context else ""
        raw = self.call_llm_with_prompt(
            "optimize",
            system,
            max_tokens=1024,
            story_summary=story[:600],
            run_number=str(current_run),
            current_params=json.dumps(current_params, ensure_ascii=False),
            previous_analysis=previous_insights[:1500] + extra,
            all_results_summary=all_results_summary[:1000],
        )

        # Extract JSON
        try:
            # Strip markdown fences if present
            raw_clean = raw.strip()
            if raw_clean.startswith("```"):
                raw_clean = raw_clean.split("\n", 1)[-1].rsplit("```", 1)[0]
            suggestion = json.loads(raw_clean)
        except json.JSONDecodeError:
            console.print("  [yellow]⚠ Could not parse optimizer JSON, keeping current params[/yellow]")
            return current_params

        new_params = suggestion.get("parameters", {})
        hypothesis = suggestion.get("hypothesis", "")

        console.print(f"  [dim]Hypothesis: {hypothesis}[/dim]")
        console.print(f"  [dim]New params: {new_params}[/dim]")

        # Apply to SimulatorScenarios.csv
        coder.apply_params(new_params)

        # Record history
        self.workspace.append_params_history(
            run=current_run + 1,
            params={**current_params, **new_params},
            hypothesis=hypothesis,
        )

        return new_params

    def _build_results_summary(self) -> str:
        history = self.workspace.read_params_history()
        if not history:
            return "No previous runs."
        lines = []
        for entry in history:
            lines.append(f"Run {entry['run']}: {entry.get('hypothesis', '')} | Params: {entry['params']}")
        return "\n".join(lines)
