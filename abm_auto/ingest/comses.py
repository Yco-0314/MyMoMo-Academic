"""
CoMSES Computational Model Library → story.md converter.

Fetches model metadata from CoMSES API, optionally downloads code archives,
and generates story.md files suitable for the abm-auto pipeline.

API: https://www.comses.net/codebases/?query=<topic>&format=json
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import urllib.request
import urllib.parse

COMSES_API = "https://www.comses.net/codebases/"


@dataclass
class ComsesModel:
    """Parsed representation of a CoMSES model."""
    identifier: str = ""
    title: str = ""
    description: str = ""
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    contributors: list[str] = field(default_factory=list)
    language: str = ""
    framework: str = ""
    publication: str = ""
    references: str = ""
    url: str = ""
    download_count: int = 0
    peer_reviewed: bool = False
    version: str = ""


def search_models(
    query: str,
    max_results: int = 20,
    timeout: int = 30,
) -> list[ComsesModel]:
    """Search CoMSES for models matching query. Returns parsed metadata."""
    params = urllib.parse.urlencode({"query": query, "format": "json"})
    url = f"{COMSES_API}?{params}"

    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "abm-auto/1.0 (research pipeline; +https://github.com/abm-auto)",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())

    results = data.get("results", [])
    models = []

    for item in results[:max_results]:
        m = ComsesModel(
            identifier=item.get("identifier", ""),
            title=item.get("title", ""),
            description=_clean_html(item.get("description", "")),
            summary=_clean_html(item.get("summarizedDescription", "")),
            tags=[t.get("name", "") for t in item.get("tags", [])],
            contributors=[
                c.get("name", "") for c in item.get("allContributors", [])
            ],
            publication=item.get("associatedPublicationText", ""),
            references=item.get("referencesText", ""),
            url=f"https://www.comses.net/codebases/{item.get('identifier', '')}/",
            download_count=item.get("downloadCount", 0),
            peer_reviewed=item.get("peerReviewed", False),
            version=item.get("latestVersionNumber", ""),
        )
        models.append(m)

    return models


def to_story_md(model: ComsesModel, enriched_details: str = "") -> str:
    """Convert a CoMSES model to story.md format.

    Args:
        model: Parsed CoMSES metadata.
        enriched_details: Optional additional context (e.g., from LLM reading
            the associated paper or code archive).
    """
    parts = []

    parts.append(f"# Story: {model.title}")
    parts.append("")

    # Research Motivation
    parts.append("## Research Motivation")
    parts.append("")
    if model.description:
        # Take first 3 paragraphs
        paragraphs = [p.strip() for p in model.description.split("\n\n") if p.strip()]
        parts.append("\n\n".join(paragraphs[:3]))
    elif model.summary:
        parts.append(model.summary)
    parts.append("")

    # Research Goal
    parts.append("## Research Goal")
    parts.append("")
    if model.summary and model.summary != model.description:
        parts.append(model.summary)
    else:
        parts.append(
            f"Replicate and extend the {model.title} model. "
            "Analyze emergent dynamics through parameter exploration and sensitivity analysis."
        )
    parts.append("")

    # Agent Description
    parts.append("## Agent Description")
    parts.append("")
    if enriched_details:
        parts.append(enriched_details)
    else:
        parts.append(
            "Agent types and behavioral rules should be inferred from the model description above. "
            "Use the associated publication for detailed specifications if available."
        )
    parts.append("")

    # Tags / Domain
    if model.tags:
        parts.append("## Domain Tags")
        parts.append("")
        parts.append(", ".join(model.tags))
        parts.append("")

    # Parameters of Interest
    parts.append("## Parameters of Interest")
    parts.append("")
    parts.append("To be determined from model specification.")
    parts.append("")

    # Output of Interest
    parts.append("## Output of Interest")
    parts.append("")
    parts.append("Key aggregate metrics and time series as described in the research goal.")
    parts.append("")

    # Mode
    parts.append("## Mode")
    parts.append("")
    parts.append("Simulator")
    parts.append("")

    # Source
    parts.append("## Source")
    parts.append("")
    parts.append(f"- **CoMSES URL**: {model.url}")
    if model.publication:
        parts.append(f"- **Publication**: {model.publication[:300]}")
    if model.contributors:
        parts.append(f"- **Contributors**: {', '.join(model.contributors[:5])}")
    if model.peer_reviewed:
        parts.append("- **Peer Reviewed**: Yes")
    parts.append("")

    return "\n".join(parts)


def fetch_and_convert(
    query: str,
    output_dir: Path,
    max_models: int = 5,
) -> list[Path]:
    """Search CoMSES, convert top results to story.md files.

    Returns list of created story.md paths.
    """
    models = search_models(query, max_results=max_models)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for model in models:
        # Sanitize folder name
        folder_name = re.sub(r"[^\w\s-]", "", model.title.lower())
        folder_name = re.sub(r"[\s]+", "_", folder_name.strip())[:60]

        model_dir = output_dir / folder_name
        model_dir.mkdir(exist_ok=True)

        story = to_story_md(model)
        story_path = model_dir / "story.md"
        story_path.write_text(story, encoding="utf-8")

        # Also save raw metadata
        meta_path = model_dir / "comses_metadata.json"
        meta_path.write_text(
            json.dumps({
                "identifier": model.identifier,
                "title": model.title,
                "url": model.url,
                "tags": model.tags,
                "publication": model.publication,
                "peer_reviewed": model.peer_reviewed,
                "download_count": model.download_count,
            }, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        paths.append(story_path)

    return paths


def _clean_html(text: str) -> str:
    """Strip HTML tags from text."""
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"&nbsp;", " ", clean)
    clean = re.sub(r"&amp;", "&", clean)
    clean = re.sub(r"&lt;", "<", clean)
    clean = re.sub(r"&gt;", ">", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()
