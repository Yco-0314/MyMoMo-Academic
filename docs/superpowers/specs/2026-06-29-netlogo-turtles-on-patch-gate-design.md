# NetLogo Turtles On Patch Gate Design

**Date:** 2026-06-29
**Scope:** Add minimal patch-local turtle aggregation.

## Problem

The native NetLogo layer now has patches, bounded patch neighbors, and integer
turtle positions. The next common spatial ABM shape is patch-local aggregation:
"which turtles are on this patch?"

## Decision

Add scan-based occupancy reporters:

- `NetLogoPatch.turtles_here()`
- `NetLogoWorld.turtles_on(patch)`

These return a normal `NetLogoAgentSet`, so existing `where(...)` and
`with_breed(...)` filters continue to work.

## Semantics

- A turtle is on a patch when `(turtle.xcor, turtle.ycor)` equals
  `(patch.pxcor, patch.pycor)`.
- Results are computed from current turtle coordinates and reflect later
  `setxy(...)` changes.
- Non-patch objects and patches from another world fail clearly.

## Non-goals

- No `turtles-on` expression parser.
- No spatial index, radius query, `in-radius`, `sprout`, collision handling,
  heading-based movement, or continuous coordinate semantics.

## Gate

`netlogo_turtles_on_patch_gate()` creates a tiny world, moves turtles onto and
off a patch, and verifies the patch-local agentset changes deterministically.
