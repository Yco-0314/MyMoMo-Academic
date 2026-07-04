# NetLogo Sprout Gate Design

**Date:** 2026-06-29
**Scope:** Add minimal patch-origin turtle creation.

## Problem

Patch-local aggregation can now find turtles on a patch, but patches still
cannot create turtles. Many NetLogo spatial ABMs use `sprout` for local births,
resources, and initialization.

## Decision

Add minimal sprout support:

- `NetLogoPatch.sprout(n, breed="turtles", **state)`
- `NetLogoWorld.sprout(patch, n, breed="turtles", **state)`

The created turtles are placed at the source patch's integer coordinates and
returned as a normal `NetLogoAgentSet`.

## Semantics

- `patch` must belong to the world.
- `n` uses the existing `create_turtles(...)` validation.
- Any supplied `xcor` / `ycor` state is ignored; sprouted turtles inherit the
  source patch coordinate.
- Other supplied turtle state is preserved.

## Non-goals

- No NetLogo command parser, breed declaration lifecycle, shape/color defaults,
  random heading, continuous coordinates, wrapping, or patch-owned birth rules.

## Gate

`netlogo_sprout_gate()` creates turtles from a patch, verifies their position
and state, and confirms patch-local aggregation sees them.
