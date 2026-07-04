# NetLogo Link Metric Gate Design

**Date:** 2026-06-29
**Scope:** Add a tiny native metric cell for NetLogo-style link counts.

## Problem

The native NetLogo semantic cell now has minimal link agents, but the metric
expression layer still only evaluates turtle-count expressions. A small
NetLogo-derived model can therefore build links, but cannot expose simple link
metrics through the same deterministic gate used for monitors and plot pens.

## Decision

Extend the limited metric evaluator with exactly two link reporters:

- `count links`
- `count link-neighbors`, only when evaluated with a turtle context

The evaluator remains deliberately small. It is not a NetLogo parser, does not
execute procedures, and does not implement the broader link reporter family.

## Semantics

- `count links` returns the number of native `NetLogoLink` agents in the world.
- `count link-neighbors` requires `context=<NetLogoTurtle>` and returns the
  number of undirected neighbors reported by `NetLogoWorld.link_neighbors(...)`.
- Directed links count as links, but do not contribute to undirected
  `link-neighbors`.
- A context turtle from another world is rejected.
- Arithmetic over these substituted counts continues to use the existing safe
  arithmetic evaluator.

## Non-goals

- No `my-links`, `in-link-neighbors`, `out-link-neighbors`, `link-neighbor?`,
  link breeds in expressions, `of`, `with`, or general reporter parsing.
- No movement, layout, network generation, or NetLogo procedure execution.
- No changes to base-engine runtime/codegen/calibration/agent/pipeline modules.

## Gate

`netlogo_link_metric_gate()` constructs a tiny world with three links and checks
that:

- `count links` sees all link agents;
- `count link-neighbors` sees only undirected neighbors for a turtle context;
- the result message states the limited boundary.
