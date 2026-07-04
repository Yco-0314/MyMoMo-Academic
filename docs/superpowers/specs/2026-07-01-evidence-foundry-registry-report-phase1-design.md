# Evidence Foundry Registry Report Phase 1 Design

**Status:** Design for minimal implementation.
**Date:** 2026-07-01
**Scope:** Render the Evidence Foundry batch gate result into a concise Markdown
report for human review and cross-agent handoff.

## Summary

The batch gate now produces a compact machine-readable JSON result. Phase 1 adds
a reader-facing report layer that runs the same batch gate and renders:

- report title;
- registry title;
- overall PASS/FAIL;
- entry count;
- failed count;
- per-entry id, kind, and gate status;
- platform capability classification summary when the batch includes the
  capability registry;
- per-entry gate description;
- explicit boundary note.

JSON remains the source of truth for automation. The Markdown report is for
review, handoff, and branch landing notes.

## Architecture

Extend:

```text
abm_auto/evidence_foundry_batch.py
```

Add:

```python
render_evidence_foundry_batch_report(batch: dict, repo: Path | None = None) -> str
write_evidence_foundry_batch_report(batch: dict, out: Path, repo: Path | None = None) -> Path
```

Add CLI:

```bash
.venv/bin/python -m abm_auto.evidence_foundry_batch report \
  docs/reproduce/evidence-foundry/batch-registry.json \
  --repo . \
  --out docs/reproduce/evidence-foundry/BATCH-REPORT.md
```

## Non-Goals

- No new gate logic.
- No model execution.
- No HTML dashboard.
- No LLM-generated prose.
- No scientific truth certification.

## Acceptance Criteria

- Unit tests verify report rendering, failed-entry rendering, CLI output file
  writing, and committed seed report content.
- The committed report is generated from the seed batch registry.
- Platform capability registry includes `evidence_foundry_registry_report`.
- Forbidden base-engine diff remains empty.
