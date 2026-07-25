# ADR-026 Public v3 Projection Plan

1. Add tests for Lock Review v2, finite-system interpretations, bundle
   provenance, corpus summaries, and typed outcomes.
2. Add the additive review, interpretation, and typed-outcome modules.
3. Pin a synthetic example to committed source blobs and validate it.
4. Run focused and broad non-GIS checks, then scan the projection boundary.

The implementation must not modify protected base-engine directories and must
not change gate PASS or MISS semantics.
