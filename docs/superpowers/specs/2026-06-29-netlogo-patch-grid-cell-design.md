# NetLogo Patch Grid Cell Phase 1 - Design Spec

## Summary

Add a minimal native NetLogo patch grid semantic cell on top of the existing
`NetLogoWorld`. The goal is to represent patches as askable, stateful grid
agents with integer `pxcor` / `pycor` coordinates. This closes the first
`patches` gap in the NetLogo semantic coverage map without implementing the
full NetLogo patch system.

## Scope

### In Scope

- Add `NetLogoPatch`.
- Add `NetLogoPatchSet`.
- Add `NetLogoWorld.create_patches(min_pxcor, max_pxcor, min_pycor, max_pycor, **state)`.
- Add `NetLogoWorld.patches`.
- Add `NetLogoWorld.patch_at(pxcor, pycor)`.
- Allow existing `NetLogoWorld.ask(...)` to run over both turtle agentsets and
  patch agentsets.
- Preserve snapshot semantics: patches created or mutated during an `ask` do
  not change the active ask roster.
- Keep turtle behavior and existing tests unchanged.

### Out of Scope

- Turtle movement, headings, `patch-here`, `sprout`, `neighbors`,
  `neighbors4`, `diffuse`, `in-radius`, wrapping, torus topology, patch colors,
  drawing, NetLogo command parsing, and automatic world dimensions from
  `.nlogo`.
- General NetLogo interpreter support.

## API Design

```python
world = NetLogoWorld(seed=0)
world.create_patches(-1, 1, -1, 1, heat=0)
patch = world.patch_at(0, 0)
patch["heat"] = 3
world.ask(world.patches, lambda p: p.set("heat", p["heat"] + 1))
```

`NetLogoPatch` should expose:

- `id`
- `pxcor`
- `pycor`
- `state`
- `__getitem__`, `__setitem__`, `get`, `set`

`NetLogoPatchSet` should mirror the minimal `NetLogoAgentSet` shape:

- `__len__`
- `__iter__`
- `snapshot()`
- `ordered()`
- `where(predicate)`

`create_patches(...)` should:

- require integer coordinates and reject booleans;
- reject inverted ranges;
- reject a second call if patches already exist;
- create one patch for every inclusive coordinate pair;
- keep deterministic insertion order by y then x:
  `(min_x, min_y)`, `(min_x + 1, min_y)`, ...

`patch_at(...)` should:

- require integer coordinates and reject booleans;
- return the exact patch object for existing coordinates;
- raise `ValueError` for absent coordinates.

## Tests

Extend `tests/test_netlogo_semantics.py`.

Tests:

1. Patch grid creation creates the expected inclusive coordinate set and stores
   patch state.
2. `patch_at(...)` returns stable patch objects and raises clear errors for
   absent coordinates / invalid coordinates.
3. `ask(world.patches, ...)` updates patch state in deterministic order and uses
   snapshot semantics.
4. Turtle and patch agentsets remain distinct; `world.turtles` excludes patches.

## Documentation

Update `docs/reproduce/netlogo-semantic-coverage/STATUS.md`:

- add patch grid cell evidence;
- update `patches-own` and `patches` rows from missing/partial to native
  minimal stateful patch grid;
- remove `patch_grid_cell` from next executable cells;
- set the next cell to `link_agent_cell`.

## Validation

Run:

```text
.venv/bin/python -m pytest tests/test_netlogo_semantics.py -q
.venv/bin/python -m pytest tests/test_netlogo_metric_expressions.py tests/test_netlogo_semantics.py tests/test_netlogo_controls.py tests/test_netlogo_mir_adapter.py -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

The forbidden diff command must print nothing.

## Scientific Boundary

This phase proves that MyMoMo has a native, askable patch grid cell with patch
state and coordinate lookup. It does not prove NetLogo spatial primitives,
wrapping, turtle movement, patch neighbors, or arbitrary NetLogo model import.
