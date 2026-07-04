# NetLogo Radius Query Gate Design

**Date:** 2026-06-29
**Scope:** Add minimal bounded radius queries over the native patch grid.

## Problem

The native NetLogo layer can move turtles over patches and aggregate turtles on
a single patch, but it cannot yet express the common local-query shape:
"which patches or turtles are within a radius of this patch or turtle?"

## Decision

Add bounded, integer-radius query support:

- `NetLogoPatch.patches_in_radius(radius)`
- `NetLogoPatch.turtles_in_radius(radius)`
- `NetLogoTurtle.patches_in_radius(radius)`
- `NetLogoTurtle.turtles_in_radius(radius)`
- matching `NetLogoWorld.patches_in_radius(center, radius)` and
  `NetLogoWorld.turtles_in_radius(center, radius)`

The query uses Euclidean distance over current integer patch coordinates and
returns existing patches/turtles in deterministic world order. There is no
wrapping.

## Semantics

- `radius` must be a non-bool non-negative integer.
- `patches_in_radius(0)` includes the source patch.
- `turtles_in_radius(0)` includes turtles exactly at the source coordinate,
  including the source turtle if the center is a turtle.
- Turtles are evaluated from current `xcor`/`ycor`, so movement changes later
  query results.
- Centers from another world and unsupported center objects fail clearly.

## Non-goals

- No NetLogo `in-radius` parser, `other`, arbitrary agentset expression,
  continuous coordinate distances, wrapping, torus worlds, radius caching,
  collision logic, or performance spatial indexing.

## Gate

`netlogo_radius_query_gate()` verifies bounded patch radius, turtle radius, and
post-movement query updates on a 3x3 grid.
