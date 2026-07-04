# NetLogo Diffuse Gate Design

**Date:** 2026-06-29
**Scope:** Add minimal bounded scalar patch diffusion.

## Problem

The native patch layer now has bounded neighbors and radius queries, but it
does not yet support a basic patch-to-patch field update. Many NetLogo spatial
models use `diffuse` to move scalar patch state through a grid.

## Decision

Add one explicit bounded diffusion method:

- `NetLogoWorld.diffuse_patch_scalar(name, fraction)`

The method reads a numeric patch state variable from every patch, computes a
simultaneous update, and writes the new value back to the same state variable.

## Semantics

- `name` must be a non-empty string.
- `fraction` must be a non-bool number in `[0, 1]`.
- Missing patch values default to `0`.
- Existing patch values must be numeric and non-bool.
- Each patch keeps `(1 - fraction)` of its value and distributes
  `fraction * value` evenly across existing bounded Moore neighbors.
- Edge patches distribute only to existing neighbors; no value leaves the grid.
- Updates are simultaneous, not in-place sequential updates.

## Non-goals

- No NetLogo command parser, wrapping topology, torus diffusion, patchset-scoped
  diffusion, anisotropic kernels, stochastic diffusion, conservation under
  missing/non-numeric data, or performance optimization.

## Gate

`netlogo_diffuse_gate()` uses a 3x3 grid with heat at the center, verifies
simultaneous distribution to the eight neighbors, then verifies corner diffusion
keeps mass inside the bounded grid.
