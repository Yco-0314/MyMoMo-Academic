# NetLogo Link Agent Cell Phase 1 - Design Spec

## Summary

Add a minimal native NetLogo link-agent semantic cell on top of `NetLogoWorld`.
This phase supports links as stateful agents between two turtles, a `links`
agentset, endpoint lookup, duplicate prevention, and simple neighbor queries.

This does not implement the full NetLogo network language. It gives MyMoMo the
first native link surface needed to model NetLogo-style turtle relations and to
move the semantic coverage map from "no link agents" to "native-minimal".

## Scope

### In Scope

- Add `NetLogoLink`.
- Add `NetLogoLinkSet`.
- Add `NetLogoWorld.create_link(end1, end2, directed=False, breed="links", **state)`.
- Add `NetLogoWorld.links`.
- Add `NetLogoWorld.link_between(end1, end2, directed=False)`.
- Add `NetLogoWorld.link_neighbors(turtle)`.
- Allow existing `NetLogoWorld.ask(...)` to run over link agentsets.
- Preserve turtle and patch behavior.
- Reject invalid endpoints and duplicate links.

### Out of Scope

- Parsing NetLogo `links-own`, directed-link-breed, undirected-link-breed, or
  link commands.
- `create-link-with`, `create-links-with`, `link-neighbors` syntax parsing,
  `my-links`, layout primitives, network generation, `tie`, hidden links, link
  colors, weights beyond arbitrary state, and breed-specific linksets.
- Multi-edges between the same endpoint pair.
- Full directed/undirected coexistence semantics beyond the explicit
  `directed` flag.

## API Design

```python
world = NetLogoWorld(seed=0)
turtles = world.create_turtles(3, breed="people")
a, b, c = turtles.ordered()
link = world.create_link(a, b, weight=2)
world.create_link(b, c, directed=True, label="flow")
world.link_between(a, b) is link
world.link_neighbors(b) == [a]
```

`NetLogoLink` should expose:

- `id`
- `end1`
- `end2`
- `directed`
- `breed`
- `state`
- `__getitem__`, `__setitem__`, `get`, `set`

`NetLogoLinkSet` should mirror the existing agentset shape:

- `__len__`
- `__iter__`
- `snapshot()`
- `ordered()`
- `where(predicate)`
- `with_breed(breed)`

`create_link(...)` should:

- require both endpoints to be `NetLogoTurtle`;
- require both endpoints to belong to the same `NetLogoWorld`;
- reject self-links;
- reject duplicate undirected links regardless of endpoint order;
- reject duplicate directed links with the same endpoint order;
- create a stateful `NetLogoLink`, add it to the platform agent roster, and
  return it.

`link_between(...)` should:

- return the exact link object for an existing pair;
- for undirected lookup, treat `(a, b)` and `(b, a)` as the same pair;
- for directed lookup, require exact order;
- raise `ValueError` when no such link exists.

`link_neighbors(turtle)` should:

- return turtle neighbors over undirected links touching `turtle`;
- ignore directed links for Phase 1, because NetLogo directed in/out neighbor
  semantics are deferred;
- preserve deterministic link insertion order while de-duplicating neighbors.

## ID Strategy

Turtle ids stay non-negative. Patch ids are negative starting at `-1`. Link ids
should use a separate negative band starting at `-1000000` to avoid accidental
collision in the platform `AgentSet`.

## Tests

Extend `tests/test_netlogo_semantics.py`.

Tests:

1. Link creation stores endpoints, breed, directed flag, state, and appears in
   `world.links`.
2. Undirected lookup is stable in both endpoint orders and duplicates fail.
3. Directed lookup requires exact order and reverse directed link may exist as a
   separate link.
4. Invalid endpoints, cross-world endpoints, and self-links fail clearly.
5. `ask(world.links, ...)` updates link state over a snapshot.
6. `link_neighbors(turtle)` returns undirected neighbors only, with stable order.

## Documentation

Update `docs/reproduce/netlogo-semantic-coverage/STATUS.md`:

- add link agent cell evidence;
- update `links` row from missing to `native-minimal`;
- update the verdict and boundary text;
- replace next executable cell with `netlogo_link_metric_gate`.

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

This phase proves that MyMoMo has native minimal link agents between turtles. It
does not prove NetLogo network generation, directed-link neighbor reporters,
link-breed parsing, `link-neighbors` expression parsing, or arbitrary NetLogo
model import.
