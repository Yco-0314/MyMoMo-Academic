# NetLogo Fixture Gap Audit Design

**Date:** 2026-06-29
**Scope:** Add a deterministic semantic gap audit for real NetLogo fixtures.

## Problem

The native NetLogo semantic layer now has a meaningful Phase 1 core, but the
next work should be driven by actual fixture pressure. Without a small audit
tool, future work can drift into speculative primitive accumulation or overclaim
that arbitrary `.nlogo` execution is near-complete.

## Decision

Add `abm_auto/netlogo_gap_audit.py` with:

- `NetLogoSemanticAudit`
- `audit_netlogo_model(model)`

The audit reads an already parsed `NetLogoModel`, scans the Code tab and
Interface controls, and returns:

- `supported`: semantic families already covered by the native layer;
- `gaps`: unsupported semantic families still blocking native execution;
- `unclassified`: source text that still cannot be assigned to a safe audited
  family;
- `can_run_natively`: true only when no gaps and no unclassified Code-tab text
  remain.

This is a deterministic feature-family audit, not a parser or evaluator.

## Initial Fixture

Use the committed `tests/fixtures/netlogo/Virus_on_a_Network.nlogo` fixture as
the first pressure test. It should report native support for turtle/link/control
families and explicit gaps for random selection, network construction,
procedure execution, visual/layout primitives, and richer agentset predicates.

## Non-goals

- No AST parser.
- No `.nlogo` execution.
- No automatic codegen.
- No broad NetLogo primitive catalog.
- No claim that supported feature families imply runnable native execution.

## Gate

Tests must prove the Virus fixture audit reports both:

- useful support already earned by the native semantic cells;
- concrete next gaps, especially `random_selection`, `network_generation`,
  `visual_layout`, and `code_tab_procedure_execution`.
