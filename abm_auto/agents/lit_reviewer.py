"""
Phase 0: Automatic Literature Review Agent.

Runs before DesignAgent to give it real academic context.
Without this, DesignAgent can only guess at mechanisms — it must rely on
story.md alone, producing excessive AI-ASSUMPTIONs.

Workflow:
  story.md
    → LLM extracts search terms (title, domain, ABM concepts)
    → Semantic Scholar API  (primary: 200M papers, TLDRs, citation counts)
    → arXiv API             (secondary: preprints, cs.MA + domain)
    → LLM synthesises into lit_notes.md
    → DesignAgent reads lit_notes.md as context

APIs used (no keys required):
  Semantic Scholar: https://api.semanticscholar.org/graph/v1/paper/search
  arXiv:           https://export.arxiv.org/api/query  (Atom XML)
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from typing import Any

from rich.console import Console

from abm_auto.agents.base import BaseAgent

console = Console()

_SEMANTIC_SCHOLAR = "https://api.semanticscholar.org/graph/v1/paper/search"
_ARXIV = "https://export.arxiv.org/api/query"
_S2_FIELDS = "title,abstract,year,citationCount,authors,tldr,externalIds"
_USER_AGENT = "ABM-Auto/2.0 (mailto:research@example.com)"


def _http_get(url: str, params: dict, timeout: int = 15) -> str | None:
    """Simple HTTP GET using stdlib urllib."""
    full_url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full_url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None


class LitReviewAgent(BaseAgent):
    """Phase 0: searches academic databases and writes lit_notes.md.

    Called once per pipeline run, before DesignAgent.  If the workspace
    already contains a non-empty lit_notes.md (e.g., provided by the user),
    this agent is a no-op to avoid overwriting deliberate human input.
    """

    def run(self) -> str:
        """Search literature, synthesise, write lit_notes.md. Returns the text."""
        # Skip if user already supplied lit notes
        existing = self.workspace.read_lit_notes()
        if existing and len(existing.strip()) > 100:
            console.print("  [dim]Phase 0: lit_notes.md already present — skipping auto search.[/dim]")
            return existing

        console.print("[bold cyan]Phase 0: Literature review...[/bold cyan]")

        story = self.workspace.read_story()
        if not story:
            console.print("  [yellow]⚠ No story.md — skipping lit review[/yellow]")
            return ""

        # Step 1: Extract search terms via LLM
        console.print("  Extracting search terms...")
        terms = self._extract_terms(story)
        console.print(f"  [dim]Terms: {terms}[/dim]")

        # Step 2: Search Semantic Scholar
        papers: list[dict] = []
        if terms.get("title"):
            papers += self._search_s2(terms["title"], limit=3)
            time.sleep(0.5)  # respect rate limit
        if terms.get("domain_query"):
            papers += self._search_s2(terms["domain_query"], limit=5)
            time.sleep(0.5)

        # Step 3: Search arXiv (good for ABM / computational social science preprints)
        if terms.get("arxiv_query"):
            papers += self._search_arxiv(terms["arxiv_query"], max_results=4)

        # Deduplicate by title
        seen: set[str] = set()
        unique: list[dict] = []
        for p in papers:
            key = (p.get("title") or "")[:60].lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(p)

        console.print(f"  [green]✓ Found {len(unique)} unique papers[/green]")

        if not unique:
            console.print("  [yellow]⚠ No papers found — DesignAgent will proceed without lit context[/yellow]")
            return ""

        # Step 4: LLM synthesis into lit_notes.md
        console.print("  Synthesising literature notes...")
        lit_notes = self._synthesise(story, unique[:12], terms)

        self.workspace.write_lit_notes(lit_notes)
        console.print(f"  [green]✓ lit_notes.md written ({len(lit_notes)} chars)[/green]")
        return lit_notes

    # ── Search helpers ───────────────────────────────────────────────────────

    def _search_s2(self, query: str, limit: int = 5) -> list[dict]:
        """Search Semantic Scholar. Returns list of paper dicts."""
        try:
            raw = _http_get(_SEMANTIC_SCHOLAR, {
                "query": query, "fields": _S2_FIELDS, "limit": limit,
            })
            if not raw:
                return []
            data = json.loads(raw)
            results = []
            for p in data.get("data", []):
                tldr = ""
                if p.get("tldr") and isinstance(p["tldr"], dict):
                    tldr = p["tldr"].get("text", "")
                results.append({
                    "source": "Semantic Scholar",
                    "title": p.get("title", ""),
                    "year": p.get("year"),
                    "citations": p.get("citationCount", 0),
                    "authors": ", ".join(
                        a.get("name", "") for a in (p.get("authors") or [])[:3]
                    ),
                    "abstract": (p.get("abstract") or "")[:400],
                    "tldr": tldr,
                    "doi": (p.get("externalIds") or {}).get("DOI", ""),
                })
            return results
        except Exception as e:
            console.print(f"  [dim]S2 search error: {e}[/dim]")
            return []

    def _search_arxiv(self, query: str, max_results: int = 4) -> list[dict]:
        """Search arXiv. Returns list of paper dicts (parses Atom XML)."""
        try:
            raw = _http_get(_ARXIV, {
                "search_query": query,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending",
            })
            if not raw:
                return []

            # Parse Atom XML
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(raw)
            results = []
            for entry in root.findall("atom:entry", ns):
                title_el = entry.find("atom:title", ns)
                summary_el = entry.find("atom:summary", ns)
                published_el = entry.find("atom:published", ns)
                authors = [
                    a.find("atom:name", ns).text
                    for a in entry.findall("atom:author", ns)
                    if a.find("atom:name", ns) is not None
                ]
                results.append({
                    "source": "arXiv",
                    "title": (title_el.text or "").strip() if title_el is not None else "",
                    "year": int((published_el.text or "")[:4]) if published_el is not None else None,
                    "citations": None,
                    "authors": ", ".join(authors[:3]),
                    "abstract": (summary_el.text or "")[:400].strip() if summary_el is not None else "",
                    "tldr": "",
                    "doi": "",
                })
            return results
        except Exception as e:
            console.print(f"  [dim]arXiv search error: {e}[/dim]")
            return []

    # ── LLM helpers ─────────────────────────────────────────────────────────

    def _extract_terms(self, story: str) -> dict[str, str]:
        """Use LLM to extract search terms from story.md."""
        system = (
            "You are a research librarian. Extract search terms from a story description "
            "of an ABM paper to reproduce. Output ONLY valid JSON, no other text."
        )
        prompt = (
            "## Story\n"
            f"{story[:1500]}\n\n"
            "Extract:\n"
            '- "title": the paper title if explicitly stated, else empty string\n'
            '- "domain_query": 5-8 keywords for Semantic Scholar (ABM + domain concepts, e.g. '
            '"agent-based model opinion dynamics social influence network")\n'
            '- "arxiv_query": arXiv query string, prefer cs.MA or econ.GN categories '
            '(e.g. "all:opinion dynamics agent-based AND (cat:cs.MA OR cat:econ.GN)")\n\n'
            "Return JSON only: {\"title\": ..., \"domain_query\": ..., \"arxiv_query\": ...}"
        )
        try:
            raw = self.call_llm(system, prompt, max_tokens=256)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
            return json.loads(raw)
        except Exception:
            # Fallback: use first 80 chars of story as query
            fallback = story[:80].replace("\n", " ")
            return {
                "title": "",
                "domain_query": f"agent-based model {fallback}",
                "arxiv_query": f"all:{fallback} AND cat:cs.MA",
            }

    def _synthesise(self, story: str, papers: list[dict], terms: dict) -> str:
        """LLM synthesises papers into a structured lit_notes.md."""
        papers_text = ""
        for i, p in enumerate(papers, 1):
            papers_text += (
                f"\n### Paper {i}: {p['title']}\n"
                f"- Source: {p['source']} | Year: {p.get('year', '?')} "
                f"| Citations: {p.get('citations', '?')}\n"
                f"- Authors: {p.get('authors', '?')}\n"
                f"- TLDR: {p.get('tldr') or '(none)'}\n"
                f"- Abstract: {p.get('abstract', '')}\n"
            )
            if p.get("doi"):
                papers_text += f"- DOI: {p['doi']}\n"

        system = (
            "You are an ABM research specialist. "
            "Synthesise the search results into a structured literature note "
            "that will help a design agent build a correct ABM. "
            "Focus on: agent types, interaction rules, key parameters, measurable outputs. "
            "Write in Chinese if the story is in Chinese, otherwise English."
        )

        prompt = (
            "## Story (what we are trying to reproduce)\n"
            f"{story[:800]}\n\n"
            "## Search results\n"
            f"{papers_text}\n\n"
            "Write lit_notes.md with these sections:\n"
            "1. **Source Paper** — identify the paper being reproduced (title, year, authors, DOI if found)\n"
            "2. **Key Mechanisms** — agent behaviour rules and interaction logic extracted from abstracts\n"
            "3. **Key Parameters** — parameter ranges/values mentioned in papers\n"
            "4. **Expected Dynamics** — what phenomena the paper reports (equilibria, phase transitions, etc.)\n"
            "5. **Related Work** — 2-3 most relevant other papers with why they matter\n"
            "6. **Design Guidance** — concrete suggestions for DesignAgent (module choices, data structures)\n\n"
            "Be concise and specific. No generic statements."
        )

        return self.call_llm(system, prompt, max_tokens=2048)
