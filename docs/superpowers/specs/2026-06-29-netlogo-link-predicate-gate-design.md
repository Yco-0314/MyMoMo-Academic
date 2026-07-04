# NetLogo Link Predicate Gate Design

**Date:** 2026-06-29
**Scope:** Add a tiny native metric cell for filtered link-neighbor counts.

## Problem

The link metric gate can count all links and all undirected neighbors for a
turtle context, but network ABM fixtures often need one more semantic shape:
"how many of my link-neighbors satisfy a turtle-state predicate?" Without that
cell, MyMoMo can express a link graph but cannot pin a common network contagion
measurement pattern.

## Decision

Extend the limited metric evaluator with exactly:

```text
count link-neighbors with [<existing turtle predicate>]
```

This reuses the existing predicate subset:

- `<var>?`
- `not <var>?`
- `and` between supported terms

The expression is evaluated against the undirected link-neighbors of the
provided turtle `context`.

## Semantics

- `context` is required and must be a `NetLogoTurtle` from the same world.
- Directed links remain excluded from `link-neighbors`.
- The predicate is applied to neighbor turtles, not all turtles.
- Existing arithmetic wrapping remains supported after substitution.

## Non-goals

- No `link-neighbor? target` variable binding.
- No `my-links`, in/out directed neighbor reporters, `of`, `or`, comparison
  expressions, breed-specific link syntax, or arbitrary NetLogo reporter AST.
- No turtle movement, network generation, procedure parsing, or full NetLogo
  execution.

## Gate

`netlogo_link_predicate_gate()` constructs a tiny link world and checks that a
context turtle can count infected, susceptible, and mixed-state undirected
neighbors while directed-only neighbors are excluded.
