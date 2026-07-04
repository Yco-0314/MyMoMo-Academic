# NetLogo Heading Movement Gate Design

**Date:** 2026-06-29
**Scope:** Add minimal cardinal turtle heading and forward movement.

## Problem

The native NetLogo layer now supports integer turtle position over patches, but
it cannot yet express the smallest movement lifecycle: set a heading, move
forward, and observe the turtle on a new patch.

## Decision

Add cardinal-only movement support:

- `NetLogoTurtle.heading`
- `NetLogoTurtle.set_heading(heading)`
- `NetLogoTurtle.rt(degrees)`
- `NetLogoTurtle.lt(degrees)`
- `NetLogoTurtle.fd(distance=1)`

This is intentionally narrower than NetLogo. It supports only headings
`0/90/180/270`, where `0` is north, `90` east, `180` south, and `270` west. It
supports only positive integer forward distances. It fails if the destination
patch is outside the existing grid.

## Semantics

- New turtles start with `heading == 0`.
- `heading` is mirrored into turtle state.
- `set_heading(...)` accepts non-bool integers that are multiples of 90 after
  modulo 360 normalization.
- `rt(...)` and `lt(...)` accept non-bool integers that are multiples of 90.
- `fd(...)` accepts non-bool positive integers and moves in the current cardinal
  direction to an existing patch.
- Failed movement does not partially update turtle coordinates.

## Non-goals

- No continuous coordinates, arbitrary trigonometric headings, wrapping,
  collision handling, pen drawing, `back`, `face`, `towards`, `patch-ahead`,
  `move-to`, or NetLogo command parsing.

## Gate

`netlogo_heading_movement_gate()` creates a bounded patch grid, moves a turtle
with `set_heading`, `rt`, `lt`, and `fd`, verifies patch occupancy updates, and
checks that out-of-grid movement fails without partial coordinate mutation.
