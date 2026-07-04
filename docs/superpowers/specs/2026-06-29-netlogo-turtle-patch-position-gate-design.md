# NetLogo Turtle Patch Position Gate Design

**Date:** 2026-06-29
**Scope:** Add minimal integer turtle position over the native patch grid.

## Problem

The native NetLogo semantic cells have turtles and patches, but turtles are not
yet spatially located on patches. That blocks the smallest NetLogo-style spatial
loop: place a turtle on a patch, ask for `patch-here`, and mutate patch state
through that relationship.

## Decision

Add integer-only turtle position support:

- `NetLogoTurtle.xcor`
- `NetLogoTurtle.ycor`
- `NetLogoTurtle.setxy(xcor, ycor)`
- `NetLogoTurtle.patch_here()`

The implementation intentionally validates against the existing patch grid and
does not implement continuous coordinates, heading, wrapping, movement distance,
`fd`, `rt`, `patch-ahead`, or `turtles-on`.

## Semantics

- New turtles start at `(0, 0)`.
- `setxy(...)` accepts non-bool integers only.
- `setxy(...)` fails if the destination patch does not exist.
- `patch_here()` returns the exact `NetLogoPatch` at the turtle's current
  integer coordinates.
- `setxy(...)` mirrors `xcor` and `ycor` into turtle state so the usual dynamic
  state accessors remain useful.

## Gate

`netlogo_turtle_patch_position_gate()` constructs a small patch grid, moves a
turtle to a patch, mutates that patch through `patch_here()`, and verifies
invalid coordinates fail. The result message must state that this is an
integer-only position cell, not full NetLogo movement semantics.
