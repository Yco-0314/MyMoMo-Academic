"""Helper methods for citation fetcher and benchmark comparator."""

from __future__ import annotations
from pathlib import Path


def format_citations_for_report(citations: dict) -> str:
    """Format fetched citations for inclusion in report."""
    if not citations or not citations.get("primary_paper"):
        return "No citations available."

    lines = []

    # Primary paper
    paper = citations["primary_paper"]
    if paper:
        lines.append("### Primary Reference\n")
        authors = ", ".join(a.get("name", "") for a in paper.get("authors", []))
        title = paper.get("title", "Untitled")
        year = paper.get("year", "n.d.")
        venue = paper.get("venue", "")
        doi = paper.get("externalIds", {}).get("DOI", paper.get("doi", ""))

        lines.append(f"**{authors}** ({year}). *{title}*. {venue}.")
        if doi:
            lines.append(f"DOI: [{doi}](https://doi.org/{doi})")
        lines.append("")

    # BibTeX
    if citations.get("bibtex"):
        lines.append("### BibTeX Entry\n")
        lines.append("```bibtex")
        lines.append(citations["bibtex"])
        lines.append("```\n")

    # Related references
    if citations.get("references"):
        lines.append("### Related Work\n")
        for i, ref in enumerate(citations["references"][:5], 1):
            ref_title = ref.get("title", "Untitled")
            lines.append(f"{i}. {ref_title}")
        lines.append("")

    return "\n".join(lines)


def format_baseline_comparison_for_report(comparison: dict) -> str:
    """Format baseline comparison results for inclusion in report."""
    if not comparison or not comparison.get("metrics"):
        return "No baseline comparison available."

    lines = []
    lines.append("### Model Validation\n")
    lines.append(f"Baseline data: `{Path(comparison['baseline_path']).name}`\n")

    metrics = comparison["metrics"]

    # Summary table
    lines.append("| Variable | R² | RMSE | Correlation |")
    lines.append("|----------|-----|------|-------------|")

    for var, stats in metrics.items():
        r2 = stats.get("R²", 0)
        rmse = stats.get("RMSE", 0)
        corr = stats.get("Correlation", 0)
        lines.append(f"| {var} | {r2:.3f} | {rmse:.3f} | {corr:.3f} |")

    lines.append("")

    # Overall assessment
    avg_r2 = sum(m.get("R²", 0) for m in metrics.values()) / len(metrics)

    if avg_r2 > 0.8:
        assessment = "The model shows **strong agreement** with baseline data (R² > 0.8)."
    elif avg_r2 > 0.6:
        assessment = "The model shows **moderate agreement** with baseline data (R² > 0.6)."
    else:
        assessment = "The model shows **weak agreement** with baseline data (R² < 0.6). Further calibration recommended."

    lines.append(assessment)
    lines.append("")

    return "\n".join(lines)
