# ADR-026: Auditable Modeling Outcomes

**Status:** Accepted
**Date:** 2026-07-25

## Decision

The public academic distribution records modeling work as separate, typed
statements rather than a single success label. A completed workflow can have a
successful execution and a scientific MISS at the same time. Those statements
must remain independently reviewable.

Prediction locks may have an optional pre-run construct review. A construct
review explains whether a locked metric is a sound proxy for its stated claim.
After a run, optional realization information may explain what the result is
evidence for. Neither layer changes the original PASS or MISS decision.

## Policy

- Preserve the original gate verdict and its tier.
- Keep construct review prospective when it is used for a non-sound
  classification.
- Treat an unexecuted test as a coverage state, not a model result.
- Record finite-system measurement risks before interpreting a strict numeric
  bar as a model-level failure.
- Require source provenance for typed outcome records when repository
  validation is requested.

## Consequences

The public surface gains an auditable interpretation layer, a finite-system
vocabulary, and a typed record for seven independent workflow outcomes. It does
not add an execution backend, comparative scoring, domain payloads, or a claim
of scientific truth.
