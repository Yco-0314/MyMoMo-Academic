"""
Citation Fetcher Agent - Retrieves real citations from academic databases.

Integrates with:
- Semantic Scholar API (free, no key required)
- CrossRef API (free, no key required)

Extracts publication info from STORY.md and fetches:
- DOI, authors, year, venue
- Abstract
- Citation count
- BibTeX entry
"""

from __future__ import annotations
import re
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from rich.console import Console

console = Console()


class CitationFetcher:
    """Fetches real citations from Semantic Scholar and CrossRef APIs."""

    SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
    CROSSREF_API = "https://api.crossref.org/works"

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ABM-Auto/0.1 (mailto:research@example.com)"
        })

    def extract_publication_info(self, story_text: str) -> dict[str, Any]:
        """
        Extract publication metadata from STORY.md.

        Looks for:
        - **Publication**: Author (Year) Title. Journal.
        - **CoMSES URL**: https://www.comses.net/codebases/...
        - **Contributors**: Names
        - DOI patterns
        """
        info = {
            "title": None,
            "authors": [],
            "year": None,
            "venue": None,
            "doi": None,
            "comses_url": None,
        }

        # Extract publication line
        pub_match = re.search(
            r"\*\*Publication\*\*:\s*(.+?)(?:\n|$)",
            story_text,
            re.IGNORECASE
        )
        if pub_match:
            pub_line = pub_match.group(1).strip()

            # Parse: "Author1, Author2 (Year) Title. Journal."
            # Example: "Meysam Alizadeh, Claudio Cioffi-Revilla (2015) Activation Regimes..."
            author_year_match = re.match(
                r"^(.+?)\((\d{4})\)\s*(.+?)(?:\.\s*(.+?))?\.?\s*$",
                pub_line
            )
            if author_year_match:
                authors_str = author_year_match.group(1).strip()
                info["authors"] = [a.strip() for a in authors_str.split(",")]
                info["year"] = int(author_year_match.group(2))
                info["title"] = author_year_match.group(3).strip()
                if author_year_match.group(4):
                    info["venue"] = author_year_match.group(4).strip()

        # Extract DOI
        doi_match = re.search(
            r"(?:doi\.org/|DOI:\s*)(10\.\d{4,}/[^\s]+)",
            story_text,
            re.IGNORECASE
        )
        if doi_match:
            info["doi"] = doi_match.group(1).strip()

        # Extract CoMSES URL
        comses_match = re.search(
            r"\*\*CoMSES URL\*\*:\s*(https://www\.comses\.net/[^\s]+)",
            story_text,
            re.IGNORECASE
        )
        if comses_match:
            info["comses_url"] = comses_match.group(1).strip()

        # Extract contributors if no authors found
        if not info["authors"]:
            contrib_match = re.search(
                r"\*\*Contributors\*\*:\s*(.+?)(?:\n|$)",
                story_text,
                re.IGNORECASE
            )
            if contrib_match:
                contrib_str = contrib_match.group(1).strip()
                info["authors"] = [a.strip() for a in contrib_str.split(",")]

        return info

    def search_semantic_scholar(self, query: str, limit: int = 5) -> list[dict]:
        """
        Search Semantic Scholar by query string.

        Returns list of papers with:
        - paperId, title, authors, year, venue, citationCount, abstract, doi
        """
        try:
            url = f"{self.SEMANTIC_SCHOLAR_API}/paper/search"
            params = {
                "query": query,
                "limit": limit,
                "fields": "paperId,title,authors,year,venue,citationCount,abstract,externalIds"
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            console.print(f"  [yellow]Semantic Scholar search failed: {e}[/yellow]")
            return []

    def get_paper_by_doi(self, doi: str) -> dict | None:
        """Fetch paper details from Semantic Scholar using DOI."""
        try:
            url = f"{self.SEMANTIC_SCHOLAR_API}/paper/DOI:{doi}"
            params = {
                "fields": "paperId,title,authors,year,venue,citationCount,abstract,externalIds,references,citations"
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            console.print(f"  [yellow]Semantic Scholar DOI lookup failed: {e}[/yellow]")
            return None

    def search_crossref(self, title: str, author: str | None = None) -> dict | None:
        """
        Search CrossRef by title (and optionally author).

        Returns best match with DOI, title, authors, year, venue.
        """
        try:
            query_parts = [title]
            if author:
                query_parts.append(author)
            query = " ".join(query_parts)

            url = f"{self.CROSSREF_API}"
            params = {
                "query": query,
                "rows": 1,
                "select": "DOI,title,author,published-print,container-title,abstract"
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            items = data.get("message", {}).get("items", [])
            if items:
                return items[0]
            return None
        except Exception as e:
            console.print(f"  [yellow]CrossRef search failed: {e}[/yellow]")
            return None

    def fetch_citations(self, story_text: str) -> dict[str, Any]:
        """
        Main entry point: extract publication info from story and fetch citations.

        Returns:
        {
            "primary_paper": {...},  # The paper described in STORY.md
            "references": [...],      # Related papers from Semantic Scholar
            "bibtex": "...",          # BibTeX entry for primary paper
        }
        """
        console.print("[bold cyan]Fetching real citations...[/bold cyan]")

        # Read story from workspace if not provided
        if not story_text:
            story_path = self.workspace_path / "STORY.md"
            if story_path.exists():
                story_text = story_path.read_text(encoding="utf-8")
            else:
                console.print("  [yellow]⚠ No STORY.md found[/yellow]")
                return {}

        pub_info = self.extract_publication_info(story_text)
        console.print(f"  Extracted: {pub_info['title'][:60] if pub_info['title'] else 'No title found'}...")

        result = {
            "primary_paper": None,
            "references": [],
            "bibtex": "",
            "extracted_info": pub_info,
        }

        # Strategy 1: Try DOI lookup first (most reliable)
        if pub_info["doi"]:
            console.print(f"  Looking up DOI: {pub_info['doi']}")
            paper = self.get_paper_by_doi(pub_info["doi"])
            if paper:
                result["primary_paper"] = paper
                result["bibtex"] = self._generate_bibtex(paper)
                console.print(f"  [green]✓ Found via DOI[/green]")

                # Fetch references from this paper
                if paper.get("references"):
                    result["references"] = paper["references"][:10]

                return result

        # Strategy 2: Search by title + author
        if pub_info["title"]:
            console.print(f"  Searching by title...")
            author_query = pub_info["authors"][0] if pub_info["authors"] else None

            # Try Semantic Scholar
            papers = self.search_semantic_scholar(
                f"{pub_info['title']} {author_query or ''}".strip()
            )
            if papers:
                result["primary_paper"] = papers[0]
                result["bibtex"] = self._generate_bibtex(papers[0])
                result["references"] = papers[1:6]  # Next 5 as related work
                console.print(f"  [green]✓ Found via Semantic Scholar[/green]")
                return result

            # Fallback to CrossRef
            crossref_result = self.search_crossref(pub_info["title"], author_query)
            if crossref_result:
                result["primary_paper"] = self._normalize_crossref(crossref_result)
                result["bibtex"] = self._crossref_to_bibtex(crossref_result)
                console.print(f"  [green]✓ Found via CrossRef[/green]")
                return result

        console.print("  [yellow]⚠ Could not find paper in databases[/yellow]")
        return result

    def _generate_bibtex(self, paper: dict) -> str:
        """Generate BibTeX entry from Semantic Scholar paper object."""
        authors = " and ".join(
            f"{a.get('name', 'Unknown')}"
            for a in paper.get("authors", [])
        )

        title = paper.get("title", "Untitled")
        year = paper.get("year", "n.d.")
        venue = paper.get("venue", "")
        doi = paper.get("externalIds", {}).get("DOI", "")

        # Generate citation key: FirstAuthorYYYY
        first_author = paper.get("authors", [{}])[0].get("name", "Unknown").split()[-1]
        cite_key = f"{first_author}{year}"

        bibtex = f"""@article{{{cite_key},
  author = {{{authors}}},
  title = {{{title}}},
  journal = {{{venue}}},
  year = {{{year}}},"""

        if doi:
            bibtex += f"\n  doi = {{{doi}}},"

        bibtex += "\n}"
        return bibtex

    def _crossref_to_bibtex(self, item: dict) -> str:
        """Convert CrossRef result to BibTeX."""
        authors = " and ".join(
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in item.get("author", [])
        )

        title = item.get("title", ["Untitled"])[0]
        year = item.get("published-print", {}).get("date-parts", [[None]])[0][0] or "n.d."
        venue = item.get("container-title", [""])[0]
        doi = item.get("DOI", "")

        first_author = item.get("author", [{}])[0].get("family", "Unknown")
        cite_key = f"{first_author}{year}"

        bibtex = f"""@article{{{cite_key},
  author = {{{authors}}},
  title = {{{title}}},
  journal = {{{venue}}},
  year = {{{year}}},
  doi = {{{doi}}},
}}"""
        return bibtex

    def _normalize_crossref(self, item: dict) -> dict:
        """Normalize CrossRef result to match Semantic Scholar format."""
        return {
            "title": item.get("title", [""])[0],
            "authors": [
                {"name": f"{a.get('given', '')} {a.get('family', '')}".strip()}
                for a in item.get("author", [])
            ],
            "year": item.get("published-print", {}).get("date-parts", [[None]])[0][0],
            "venue": item.get("container-title", [""])[0],
            "doi": item.get("DOI"),
            "abstract": item.get("abstract", ""),
        }

    def save_citations(self, citations: dict) -> Path:
        """Save fetched citations to workspace as JSON."""
        output_path = self.workspace_path / "citations.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(citations, f, indent=2, ensure_ascii=False)
        console.print(f"  [green]✓ Citations saved to {output_path.name}[/green]")
        return output_path
