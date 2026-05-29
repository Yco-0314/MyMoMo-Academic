"""Final output phases: report, figures, peer review, ARS packaging.

  ReportPhase      — Phase 7: ReporterAgent synthesises the manuscript
  VisualizerPhase  — Phase 7b: figures into figures/ + appended to report
  PeerReviewPhase  — Phase 8: optional ReviewerAgent + resolution-ledger routing
  PackageArsPhase  — Always: bundle outputs for ARS integration
"""
from __future__ import annotations

import json

from rich.console import Console

from abm_auto.agents.visualizer import VisualizerAgent
from abm_auto.pipeline.phase import PipelineContext

console = Console()


class ReportPhase:
    """Phase 7: Final manuscript synthesis."""

    name = "Phase 7 (Report)"

    def __init__(self, reporter):
        self.reporter = reporter

    def should_run(self, ctx: PipelineContext) -> bool:
        return bool(ctx.all_insights)

    def run(self, ctx: PipelineContext) -> None:
        self.reporter.run(
            ctx.all_insights,
            citations=ctx.citations_text,
            baseline_comparison=ctx.comparison_text,
            spec=ctx.spec,
        )


class VisualizerPhase:
    """Phase 7b: Generate figures + append references to the report."""

    name = "Phase 7b (Visualization)"

    def should_run(self, ctx: PipelineContext) -> bool:
        return True   # always

    def run(self, ctx: PipelineContext) -> None:
        console.print("[bold cyan]Phase 7b: Generating figures...[/bold cyan]")
        viz = VisualizerAgent(ctx.workspace.path, lang=ctx.lang)
        figures = viz.run()
        if not figures:
            return
        report_path = ctx.workspace.report_path
        if not report_path.exists():
            return
        fig_section = "\n\n## Figures\n\n"
        for fig in figures:
            fig_section += f"![{fig.stem}](figures/{fig.name})\n\n"
        report_path.write_text(
            report_path.read_text(encoding="utf-8") + fig_section,
            encoding="utf-8",
        )


class PeerReviewPhase:
    """Phase 8: ReviewerAgent + resolution-ledger routing."""

    name = "Phase 8 (Peer Review)"

    def __init__(self, reviewer):
        self.reviewer = reviewer

    def should_run(self, ctx: PipelineContext) -> bool:
        return ctx.peer_review

    def run(self, ctx: PipelineContext) -> None:
        self.reviewer.run(spec=ctx.spec)
        _process_resolution_ledger(ctx, self.reviewer)


class PackageArsPhase:
    """Always-run: package workspace outputs for ARS academic-paper integration."""

    name = "Final (ARS package)"

    def should_run(self, ctx: PipelineContext) -> bool:
        return True

    def run(self, ctx: PipelineContext) -> None:
        ars_out = ctx.workspace.package_for_ars()
        console.print(
            f"  [dim]ARS package: {ars_out.relative_to(ctx.workspace.path.parent)}[/dim]"
        )


def _process_resolution_ledger(ctx: PipelineContext, reviewer) -> None:
    """Surface the Resolution Ledger action buckets from peer_review.md."""
    peer_review_path = ctx.workspace.path / "peer_review.md"
    if not peer_review_path.exists():
        return
    review_text = peer_review_path.read_text(encoding="utf-8")
    if "Resolution Ledger" not in review_text:
        return
    actions = reviewer.parse_ledger(review_text)
    ledger_summary_path = ctx.workspace.path / "resolution_ledger.json"
    ledger_summary_path.write_text(
        json.dumps(actions, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    total = sum(len(v) for v in actions.values())
    if total == 0:
        return
    console.print("\n[bold magenta]Resolution Ledger summary:[/bold magenta]")
    colors = {"FIX": "red", "NEW_ANALYSIS": "yellow", "DOWNGRADE": "cyan", "DROP": "dim"}
    for action, issues in actions.items():
        if issues:
            color = colors.get(action, "white")
            console.print(
                f"  [{color}]{action}[/{color}] ({len(issues)}): "
                + "; ".join(i[:60] for i in issues[:3])
                + ("…" if len(issues) > 3 else "")
            )
    console.print(f"  [dim]Full ledger: {ledger_summary_path.name}[/dim]")
