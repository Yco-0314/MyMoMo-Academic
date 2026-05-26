# ABM-Auto Context Map

**Purpose**: Central navigation hub for understanding the ABM-Auto research automation system.

**Target Audience**: Academic researchers → Developers → LLM agents

---

## Quick Start

- **New to ABM-Auto?** → Start with [Getting Started Guide](guides/getting-started.md)
- **Running experiments?** → See [Pipeline Phases](context/pipeline-phases.md)
- **Extending the system?** → Read [Developer Guide](guides/developer-guide.md)
- **Understanding design decisions?** → Browse [Architecture Decision Records](decisions/)

---

## Core Concepts

### System Architecture
- [Memory System](context/memory-system.md) — 3-tier experiment memory (Working/Episodic/Semantic)
- [Pipeline Phases](context/pipeline-phases.md) — 7-phase research automation workflow
- [Agent Roles](context/agent-roles.md) — Specialized agents and their responsibilities
- [Terminology](context/terminology.md) — Domain-specific vocabulary and conventions

### Key Subsystems
- **Story Generation** (`story_generator.py`) — Convert research ideas to structured narratives
- **Code Generation** (`coder.py`) — Transform stories into executable Mesa models
- **Sensitivity Analysis** (`salib_optimizer.py`) — Parameter space exploration with SALib
- **Citation Management** (`citation_fetcher.py`) — Semantic Scholar API integration
- **Benchmark Comparison** (`benchmark_comparator.py`) — Statistical validation against original studies
- **Report Generation** (`reporter.py`) — Academic-quality manuscript synthesis

---

## Architecture Decisions

Critical design choices documented in [ADR format](https://adr.github.io/):

| ID | Title | Status | Impact |
|----|-------|--------|--------|
| [ADR-001](decisions/ADR-001-memory-architecture.md) | 3-Tier Memory Architecture | Accepted | High |
| [ADR-002](decisions/ADR-002-flat-file-storage.md) | Flat File Storage over SQLite | Accepted | Medium |
| [ADR-003](decisions/ADR-003-llm-orchestration.md) | LLM-Driven Orchestration Strategy | Accepted | High |
| [ADR-004](decisions/ADR-004-configuration-flexibility.md) | Configuration Flexibility Strategy | Proposed | High |

**Audit Reports**:
- [Flexibility Audit](decisions/FLEXIBILITY-AUDIT.md) — Comprehensive review of hardcoded limits (12 issues identified, 3 critical)

[View all ADRs →](decisions/)

---

## Knowledge Base

Domain-specific guides embedded in the system. All five live in
`abm_auto/mymomo_knowledge/` — the MyMoMo Knowledge Base, written from
scratch with no external attribution dependency:

- [01 — Runtime API](../abm_auto/mymomo_knowledge/01-runtime-api.md) — Canonical reference for every importable name in `abm_auto.runtime`
- [02 — Writing Models](../abm_auto/mymomo_knowledge/02-writing-models.md) — End-to-end walkthrough: story.md → calibrated simulation
- [03 — Modules](../abm_auto/mymomo_knowledge/03-modules.md) — Decision guide for Grid vs. Network vs. No-topology
- [04 — Data Contracts](../abm_auto/mymomo_knowledge/04-data-contracts.md) — The five file formats the pipeline reads/writes
- [05 — Anti-patterns](../abm_auto/mymomo_knowledge/05-anti-patterns.md) — LLM-codegen mistakes observed in real benchmark runs

---

## User Guides

### For Researchers
- [Getting Started](guides/getting-started.md) — Installation and first experiment
- [Configuration Guide](guides/configuration-guide.md) — Memory limits, timeout control, environment variables
- [Academic Usage Guide](guides/academic-usage.md) — Publishing-ready output configuration
- [Troubleshooting](guides/troubleshooting.md) — Common issues and solutions

### For Developers
- [Developer Guide](guides/developer-guide.md) — Contributing to ABM-Auto
- [Testing Strategy](guides/testing.md) — Test suite organization
- [Prompt Engineering](guides/prompt-engineering.md) — Optimizing LLM interactions

---

## File Organization

```
abm_auto/
├── agents/          # Specialized LLM agents (12 modules)
├── memory/          # 3-tier experiment memory system
├── knowledge/       # Domain expertise for LLM context
├── prompts/         # LLM prompt templates (17 files)
├── cli.py           # Command-line interface
├── pipeline.py      # Main orchestration logic
└── config.py        # System-wide configuration

docs/
├── CONTEXT-MAP.md   # This file
├── context/         # Conceptual documentation
├── decisions/       # Architecture Decision Records
└── guides/          # User and developer guides
```

---

## Maintenance Notes

**Last Updated**: 2026-04-30  
**Documentation Owner**: System maintainers  
**Review Cycle**: After major architectural changes

**Stale Content Policy**: If a document contradicts current code behavior, trust the code and file an issue to update the docs.

---

## External Resources

- [Mesa Documentation](https://mesa.readthedocs.io/) — ABM framework
- [SALib Documentation](https://salib.readthedocs.io/) — Sensitivity analysis library
- [Semantic Scholar API](https://api.semanticscholar.org/) — Citation data source
- [CrossRef API](https://www.crossref.org/documentation/retrieve-metadata/) — DOI resolution
