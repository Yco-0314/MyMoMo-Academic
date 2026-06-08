# ADR-018: Machine-Driven Literature Corpus Pipeline (three-stage collect → screen → snowball)

> Renumbered from a duplicate "ADR-013" (collided with [ADR-013](ADR-013-gate-harness.md), the canonical Gate-harness ADR) during the 2026-06-09 docs hygiene pass. Content unchanged.

**Status**: Proposed (thesis; design only; no code change in this ADR)
**Date**: 2026-06-01
**Deciders**: yco + Claude (Opus 4.8)
**Related**: [ADR-010](ADR-010-abm-platform-vision.md), [ADR-011](ADR-011-six-wedge-benchmark-thesis.md), [ADR-012](ADR-012-method-transfer-engine.md)

---

## Context

The current `LitReviewAgent` (`abm_auto/agents/lit_reviewer.py`, 290 LoC)
does a light search: Semantic Scholar + arXiv, ~12 papers (3+5+4), writes
`lit_notes.md`. No dedup, no multi-stage screening, no citation
snowballing, no provenance ledger. It is a "grab a few references"
helper, not a corpus builder.

The user proposes upgrading this into a **machine-driven, high-quality
reference-corpus construction pipeline**, modeled on how a systematic
review is actually done. The motivating shape (user's spec):

- **Collect**: combinatorial-keyword search across Google Scholar / Web
  of Science / Scopus; dedup → ~3,000 papers.
- **Screen**: title → abstract → full-text review → ~150 core papers.
- **Snowball + expert add**: backward/forward citation chasing + manual
  domain additions → ~180-paper representative corpus.

## Why this belongs in abm-auto (not scope creep)

Three of the six wedges consume literature, and all currently rely on
the thin LitReviewer:

- **W2 (LLM-codegen / reproduce mode)**: reproducing a paper (Yaman,
  GeomHerd) starts with *finding and reading the right paper*. The
  reproduce work this session was bottlenecked exactly here — I had to
  be handed PDFs by the user because the pipeline cannot build a corpus
  or fetch full text.
- **W5 (mechanism search)**: ranking candidate mechanisms against the
  literature needs a real corpus to rank against.
- **W7 (method transfer, ADR-012)**: the "novel-finding recall" benchmark
  (ADR-012 OQ#3) requires a corpus of known method×domain results to
  test rediscovery against.

A corpus pipeline is shared infrastructure under all three. It is the
*input* side of the platform, symmetric to the *output* side
(report generation). Today the output side is far more developed than
the input side — this rebalances.

## Design — three stages, each with an auditable artifact

The ADR-012 discipline applies directly: **each stage emits a
machine-checkable artifact; trust moves to those artifacts, not to the
agent's say-so.** A corpus pipeline is a perfect target for
fabrication (an agent could invent plausible-looking citations — the
classic LLM failure), so provenance is the moat.

### Stage 1 — Collect (broad, ~3000)

- Combinatorial keyword expansion (LLM proposes term sets; deterministic
  cross-product builds queries).
- Sources: start with what has real APIs — **Semantic Scholar (already
  wired), arXiv (already wired), OpenAlex, Crossref**. Google
  Scholar/WoS/Scopus have no clean open API + ToS constraints; treat as
  optional manual-import lanes, not automated scrapers (legal + fragility
  reasons — honest constraint, see Negative).
- **Dedup** by DOI, then by normalized-title fuzzy match.
- Artifact: `corpus/stage1_collected.jsonl` — one record per paper with
  source, query that found it, DOI, title, abstract, year, citation
  count. Every paper traceable to the query that surfaced it.

### Stage 2 — Screen (narrow, ~150)

- Three sub-passes, each an LLM relevance judgment **with a recorded
  reason + score**, applied progressively to cheaper→richer text:
  title → abstract → (fetched) full text.
- A paper dropped at any pass records *why* (the reason string), so the
  screen is auditable, not a black box.
- **Anti-fabrication guard**: every retained paper must have a real DOI
  that resolves; a paper the agent "knows" but that has no resolvable
  identifier is rejected (this is the citation-hallucination guard —
  the literature analogue of ADR-012's deterministic verification).
- Artifact: `corpus/stage2_screened.jsonl` + per-paper decision log.

### Stage 3 — Snowball + expert add (~180)

- Backward (references-of) + forward (cited-by) chasing via Semantic
  Scholar / OpenAlex citation graph, N hops, re-screened through Stage 2.
- Manual expert additions lane (user drops DOIs/PDFs; merged with
  provenance = "expert").
- Artifact: `corpus/stage3_final.jsonl` + a citation-graph edge list.

## The fabrication risk is the central design driver

Literature work is the **highest fabrication-risk surface in the whole
platform** — higher than the CSD demo. An LLM asked for references will
readily produce plausible-but-nonexistent papers (well-documented
failure mode). So the guard is non-negotiable and structural:

1. **No paper enters the corpus without a resolvable external
   identifier** (DOI / arXiv ID / S2 paper ID that the API confirms).
   The agent's belief that a paper exists is never sufficient.
2. **Every corpus record carries provenance**: which query/citation-edge/
   expert-add surfaced it. Unprovenanced = not in corpus.
3. **Full-text claims trace to fetched text**, exactly like this
   session's PDF extraction (`_extract_pdf*.py`) — a quote about a paper
   must point at extracted bytes, not memory.

This is the same lesson as the session's fabrication incident,
generalized: the input pipeline must be as fabrication-resistant as we
now demand the output/result pipeline to be.

## Consequences

### Positive
- Unblocks reproduce mode (W2): pipeline can find + fetch papers instead
  of needing hand-delivered PDFs.
- Provides the corpus W5 + W7 benchmarks need.
- Provenance-first design makes the corpus citable and auditable — a
  research-grade artifact, not a pile of links.

### Negative
- **Google Scholar / WoS / Scopus have no clean automated access** (no
  open API; scraping violates ToS and is fragile). The honest pipeline
  uses OpenAlex/Crossref/S2/arXiv for automation and treats the
  closed databases as manual-import lanes. The "~3000 from Scholar/WoS/
  Scopus" target is therefore semi-manual at the collect stage, not
  fully machine-driven. State this plainly rather than pretend to scrape.
- Full-text fetch is paywall-limited; many papers screen on abstract
  only. Open-access full text (arXiv, PMC, OA DOIs) is the automatable
  subset.
- Real engineering: this is a multi-week build, not a demo.

### Neutral
- Extends the existing `LitReviewAgent` rather than replacing it; the
  current 12-paper search becomes a degenerate (corpus-size=12) config
  of Stage 1.

## Open questions

- **OQ#1**: Is the goal a *general* systematic-review tool, or
  specifically a corpus to feed reproduce/W5/W7? The former is a product
  in itself; the latter is narrower and faster. Recommend narrower first.
- **OQ#2**: Where does this sit against the 9-13mo v1.0 plan — is it a
  7th wedge (input-side), or infrastructure under W2/W5/W7? Leaning
  infrastructure, surfaced when a wedge needs it (same gating as ADR-012).
- **OQ#3**: How much full-text can we legally + technically fetch? Bounds
  how much Stage 2 is full-text vs abstract-only.

## Status

| Step | Status |
|---|---|
| ADR-018 thesis pinned | proposed 2026-06-01 (this doc) |
| Stage 1 collect (OpenAlex/Crossref/S2/arXiv + dedup + provenance) | not started |
| Stage 2 screen (3-pass + DOI-resolve guard) | not started |
| Stage 3 snowball + expert lane | not started |
| Integration with reproduce mode / W5 / W7 | not started |
