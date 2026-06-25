from __future__ import annotations

from rich.console import Console

from abm_auto.agents.base import BaseAgent

console = Console()


class ReporterAgent(BaseAgent):
    """Generates the final research report from all simulation runs."""

    def run(self, all_insights: list[str], citations: str | None = None, baseline_comparison: str | None = None, spec=None) -> str:
        console.print("[bold cyan]Phase 7: Generating final report...[/bold cyan]")

        story = self.workspace.read_story()
        design = self.workspace.read_design()
        params_history = self.workspace.read_params_history()
        total_runs = len(all_insights)

        # Build runs summary
        runs_summary_parts = []
        for i, insights in enumerate(all_insights, start=1):
            runs_summary_parts.append(f"### Run {i}\n{insights[:600]}")
        all_runs_summary = "\n\n".join(runs_summary_parts)

        params_str = "\n".join(
            f"Run {h['run']}: {h.get('hypothesis', '')} → {h['params']}"
            for h in params_history
        )

        # Anti-hallucination constraint — Reporter has been observed to
        # invent "Run 3" content when only 2 iterations ran. Spell it out.
        iteration_constraint = (
            f"This study ran EXACTLY {total_runs} iteration(s). "
            f"Do not invent additional runs. Reference only Run 1 through Run {total_runs}."
        )

        # Anti-unit-drift block — Reporter has been observed treating
        # virus_spread_chance=4.4 as a probability instead of percent,
        # mis-explaining "4.4>1 means certain transmission". Inject the
        # declared unit per param (mirrors CoderAgent's contract block).
        param_units_block = _format_param_units(spec)

        # Pick prompt based on language
        prompt_name = "report_en" if self.lang == "en" else "report"
        system = (
            "You are an expert computational social scientist writing an academic paper. "
            "Be precise and reference specific numbers from the results."
        )
        report = self.call_llm_with_prompt(
            prompt_name,
            system,
            max_tokens=4096,
            story_summary=story[:800],
            design_summary=design[:1200],
            total_runs=str(total_runs),
            iteration_constraint=iteration_constraint,
            param_units_block=param_units_block,
            all_runs_summary=all_runs_summary,
            params_history=params_str,
            citations=citations or "No citations fetched.",
            baseline_comparison=baseline_comparison or "No baseline comparison available.",
        )
        self.workspace.write_report(report)

        console.print(f"  [green]✓ Report saved to {self.workspace.report_path}[/green]")

        try:
            import re
            section_count = len(re.findall(r"^##\s", report, re.M))
            self.workspace.audit.info(
                phase="Phase 7",
                text=(
                    f"Final report generated ({len(report)} chars, "
                    f"{section_count} sections, from {total_runs} runs)"
                ),
                actor="ReporterAgent",
                structured={
                    "length": len(report),
                    "sections": section_count,
                    "runs_synthesised": total_runs,
                    "had_citations": bool(citations),
                    "had_baseline": bool(baseline_comparison),
                },
            )
        except Exception as exc:
            console.print(f"  [yellow]⚠ audit logging failed: {exc}[/yellow]")

        return report


def _format_param_units(spec) -> str:
    """Render calibration_param_specs as a markdown table of (name, unit, range).

    Returns "(no calibration parameters declared)" when spec is None or empty,
    so the template variable always has a sensible string.
    """
    if spec is None:
        return "(no calibration parameters declared)"
    specs = getattr(spec, "calibration_param_specs", None) or []
    if not specs:
        return "(no calibration parameters declared)"
    lines = ["| Parameter | Unit | Range |", "|---|---|---|"]
    for s in specs:
        name = s.get("name", "?")
        unit = s.get("unit", "?")
        lo = s.get("min", "?")
        hi = s.get("max", "?")
        lines.append(f"| `{name}` | {unit} | [{lo}, {hi}] |")
    return "\n".join(lines)
