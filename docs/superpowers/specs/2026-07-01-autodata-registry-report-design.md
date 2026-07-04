# AutoData Registry Report Design

## Summary

The registry report renderer turns the machine-readable registry gate result into
a concise Markdown report for cross-agent handoff and human review.

## Scope

In scope:

- Run the same deterministic registry gate used by CI.
- Render overall PASS/FAIL, entry count, failed count, and per-entry status.
- Include the gate description for each challenge.
- Provide a CLI `registry-report` command.

Out of scope:

- No model execution.
- No answer generation.
- No scientific truth certification.
- No mutation of registry, pack, or answer files.

## Command

```bash
.venv/bin/python -m abm_auto.repro_challenge registry-report \
  docs/reproduce/autodata-challenges/registry.json \
  --repo . \
  --out /tmp/autodata-registry-report.md
```

The report is deliberately small and review-oriented. JSON remains the source of
truth for automation.
