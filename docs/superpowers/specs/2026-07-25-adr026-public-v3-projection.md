# ADR-026 Public v3 Projection

## Scope

This projection publishes only public-neutral outcome and interpretation
capabilities:

- Lock Review v2 with optional finite-system bar metadata.
- Replay-bundle and study-corpus interpretation summaries.
- D7 typed outcome records with Git-blob provenance.
- A synthetic worked example.

## Boundary

The projection preserves original PASS and MISS semantics. Interpretation is
optional metadata and cannot upgrade a failed verdict. The synthetic example is
schema evidence only; it is not a model, dataset, benchmark, or reproduction
claim.

No execution backend, comparative metric suite, domain-specific source, local
path, or non-public artifact belongs in this projection.
