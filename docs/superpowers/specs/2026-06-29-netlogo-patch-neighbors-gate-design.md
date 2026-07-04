# NetLogo Patch Neighbors Gate Design

**Date:** 2026-06-29
**Scope:** Add minimal bounded patch neighborhood reporters.

## Problem

The native patch grid can create and look up patches, and turtles can now locate
their current patch. A common NetLogo spatial pattern still lacks a native cell:
asking a patch for nearby patches.

## Decision

Add bounded patch neighborhood support:

- `NetLogoPatch.neighbors4()`
- `NetLogoPatch.neighbors()`
- `NetLogoWorld.patch_neighbors4(patch)`
- `NetLogoWorld.patch_neighbors(patch)`

The order is deterministic and row-major around the patch. Missing out-of-grid
neighbors are omitted. There is no wrapping.

## Semantics

- `neighbors4()` returns north/south/east/west equivalents within the existing
  grid, in deterministic row-major order.
- `neighbors()` returns the Moore neighborhood within the existing grid, also in
  deterministic row-major order.
- Patches from another world and non-patch objects fail clearly.

## Non-goals

- No wrapping, torus world, diffuse, sprout, `patch-ahead`, radius reporters,
  distance reporters, or full NetLogo spatial primitive set.

## Gate

`netlogo_patch_neighbors_gate()` verifies center and corner counts on a 3x3 grid
and states the bounded/no-wrapping boundary.
