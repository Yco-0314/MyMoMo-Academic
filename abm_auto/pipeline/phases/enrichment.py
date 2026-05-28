"""Phase 6.5 / 6e / 6f: optional enrichment phases.

  WhatIfPhase    — Phase 6.5: counterfactual scenarios (originate mode only)
  CitationsPhase — Phase 6e: Semantic Scholar lookup, if --fetch-citations
  BaselinePhase  — Phase 6f: compare against an external baseline CSV
"""
from __future__ import annotations

from rich.console import Console

from abm_auto.pipeline.phase import PipelineContext

console = Console()


class WhatIfPhase:
    """Phase 6.5: WhatIfOracle in originate mode only.

    Maps the model's behavioural envelope — 6 counterfactual scenarios
    (best/likely/worst/wildcard/contrarian/second-order). Skipped in
    reproduce mode because fidelity, not exploration, is the goal.
    """

    name = "Phase 6.5 (What-If)"

    def __init__(self, oracle):
        self.oracle = oracle

    def should_run(self, ctx: PipelineContext) -> bool:
        return bool(
            ctx.spec and ctx.spec.mode == "originate" and ctx.all_insights
        )

    def run(self, ctx: PipelineContext) -> None:
        what_if_text = self.oracle.run(ctx.all_insights, spec=ctx.spec)
        if what_if_text:
            ctx.all_insights.append(what_if_text)


class CitationsPhase:
    """Phase 6e: Fetch supporting citations via Semantic Scholar."""

    name = "Phase 6e (Citations)"

    def should_run(self, ctx: PipelineContext) -> bool:
        return ctx.fetch_citations

    def run(self, ctx: PipelineContext) -> None:
        console.print("[bold cyan]Phase 6e: Fetching citations...[/bold cyan]")
        try:
            from abm_auto.agents.citation_fetcher import CitationFetcher
            from abm_auto.agents.formatting_utils import format_citations_for_report
            fetcher = CitationFetcher(ctx.workspace.path)
            story_text = ctx.workspace.read_story()
            citations = fetcher.fetch_citations(story_text)
            if citations:
                ctx.citations_text = format_citations_for_report(citations)
                console.print(
                    f"  [green]✓ Fetched {len(citations.get('references', []))} citations[/green]"
                )
        except Exception as e:
            console.print(f"  [yellow]⚠ Citation fetching failed: {e}[/yellow]")


class BaselinePhase:
    """Phase 6f: Baseline comparison against an external CSV."""

    name = "Phase 6f (Baseline)"

    def should_run(self, ctx: PipelineContext) -> bool:
        return bool(ctx.baseline_path and ctx.baseline_path.exists())

    def run(self, ctx: PipelineContext) -> None:
        console.print("[bold cyan]Phase 6f: Comparing with baseline...[/bold cyan]")
        try:
            from abm_auto.agents.benchmark_comparator import BenchmarkComparator
            from abm_auto.agents.formatting_utils import (
                format_baseline_comparison_for_report,
            )
            comparator = BenchmarkComparator(ctx.workspace.path)
            comparison = comparator.compare(ctx.baseline_path)
            if comparison:
                ctx.comparison_text = format_baseline_comparison_for_report(comparison)
                console.print("  [green]✓ Baseline comparison complete[/green]")
        except Exception as e:
            console.print(f"  [yellow]⚠ Baseline comparison failed: {e}[/yellow]")
