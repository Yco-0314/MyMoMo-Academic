# NetLogo Other AgentSet Gate Design

**Date:** 2026-06-29
**Scope:** Add minimal exclude-self agentset behavior.

## Problem

Radius queries currently include the source turtle. Many NetLogo models use
`other turtles in-radius ...` to avoid self-interaction. MyMoMo needs a small,
explicit equivalent before this semantic family is useful for local contagion or
interaction fixtures.

## Decision

Add:

- `NetLogoAgentSet.other_than(turtle)`
- `NetLogoTurtle.other_turtles_in_radius(radius)`

This avoids a NetLogo parser while still representing the semantic core of
exclude-self local interaction.

## Semantics

- `other_than(...)` requires a `NetLogoTurtle` from the same world.
- The returned agentset preserves deterministic order.
- `other_turtles_in_radius(radius)` delegates to `turtles_in_radius(radius)` and
  then excludes `self`.

## Non-goals

- No parser for `other turtles`, `with`, `of`, breed-specific `other` syntax,
  link agentsets, patch agentsets, or arbitrary agentset algebra.

## Gate

`netlogo_other_agentset_gate()` verifies that self is excluded from local
radius interaction while other nearby turtles remain in deterministic order.
