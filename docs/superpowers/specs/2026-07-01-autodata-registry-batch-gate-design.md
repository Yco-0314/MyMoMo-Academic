# AutoData Registry Batch Gate Design

## Summary

The registry batch gate runs every registered challenge answer through the
deterministic pack validation and answer grader. It is the CI-friendly acceptance
surface for Claude/Codex challenge handoffs.

## Scope

In scope:

- Load a registry.
- For each entry, require a `pack` and `answer` path.
- Run `repro_challenge_gate` for each entry.
- Return a compact JSON summary with per-entry descriptions.
- Expose a CLI `registry-gate` command.

Out of scope:

- No model execution.
- No answer generation.
- No mutation of challenge packs, answers, or registry files.
- No scientific truth certification.

## Command

```bash
.venv/bin/python -m abm_auto.repro_challenge registry-gate \
  docs/reproduce/autodata-challenges/registry.json \
  --repo .
```

The result is a deterministic answer/evidence-alignment gate for all registered
challenge answers.
