# NetLogo Virus Random Selection + Network Slice Design

## Summary

This phase adds the first native executable slice driven by the committed
`Virus_on_a_Network.nlogo` fixture audit. The slice covers seeded random
selection and the smallest network-generation operation needed to express the
fixture's setup topology in explicit Python.

This is not a NetLogo interpreter. It does not parse or execute `.nlogo`
procedures, does not implement arbitrary agentset algebra, and does not claim
NetLogo RNG parity.

## Problem

The current semantic coverage map already has native turtles, patches, links,
`ask`, ticks, monitors, limited metric expressions, radius queries, diffusion,
and link-neighbor reporters. The fixture audit still reports these pressure
points for `Virus_on_a_Network.nlogo`:

- `random_selection`: `n-of`, `one-of`;
- `network_generation`: `min-one-of`, `distance`, `create-link-with`;
- `agentset_expression_parser`: `other turtles with [not link-neighbor? myself]`;
- `code_tab_procedure_execution`;
- `visual_layout`.

The next useful step is to remove only the primitive pressure that blocks a
manual native Virus setup slice. The larger parser and layout gaps remain
explicitly out of scope.

## Design

Add minimal random-selection helpers to `abm_auto/netlogo_semantics.py`:

- `NetLogoWorld.one_of(agentset_or_sequence)`;
- `NetLogoWorld.n_of(n, agentset_or_sequence)`;
- convenience forwarding methods on `NetLogoAgentSet`, `NetLogoPatchSet`, and
  `NetLogoLinkSet` where they match the existing style.

Selection uses the world's existing seeded Python RNG and works over snapshots.
`one_of` rejects empty collections. `n_of` rejects bool, non-integer, negative,
and oversized counts. `n_of(0, ...)` returns an empty same-world agentset when
the input is a NetLogo agentset, or an empty list for plain sequences.

Add a minimal network-generation helper to `NetLogoWorld`:

- `create_link_with_nearest_unlinked(source, candidates=None, *, directed=False,
  breed="links", **state)`.

The helper models the fixture operation:

```text
min-one-of (other turtles with [not link-neighbor? myself]) [distance myself]
create-link-with choice
```

It validates that `source` belongs to the world, filters out `source` and
already linked turtles, chooses the nearest candidate by squared Euclidean
distance over `xcor`/`ycor`, breaks ties by turtle id for determinism, and
creates one link when a candidate exists. If no candidate exists, it returns
`None`, matching the fixture's `if choice != nobody` boundary.

Add a deterministic gate:

- `netlogo_virus_network_setup_slice_gate() -> tuple[bool, str]`.

The gate builds a small seeded world, creates turtles at explicit coordinates,
uses `one_of` / `n_of` / `create_link_with_nearest_unlinked`, and verifies:

- seeded selections are stable for the same seed;
- links are never self-links or duplicates;
- nearest unlinked candidate selection is deterministic;
- the message states this is a manual native setup slice, not procedure
  execution.

## Audit Boundary

Update `abm_auto/netlogo_gap_audit.py` so the audit can distinguish:

- native support now exists for `random_selection`;
- a minimal native slice now exists for Virus-style `network_generation`;
- `agentset_expression_parser`, `code_tab_procedure_execution`, and
  `visual_layout` remain gaps.

The audit must not report `Virus_on_a_Network.nlogo` as runnable. It still has
unclassified Code-tab text and parser/layout gaps.

Recommended labels:

- `random_selection` moves to `supported`;
- `network_generation_minimal` appears in `supported`;
- `network_generation` remains in `gaps` if the fixture contains broader
  unparsed network expressions such as `min-one-of` and `distance`.

This keeps the report honest: MyMoMo can express the operation natively in
Python, but cannot parse the fixture's NetLogo source into that operation.

## Tests

Extend `tests/test_netlogo_semantics.py`:

- `one_of` is deterministic for a fixed seed and rejects empty collections;
- `n_of` is deterministic, returns no duplicates, preserves same-world agentset
  behavior for agentset inputs, and rejects invalid counts;
- nearest-unlinked network generation creates exactly one expected link, avoids
  duplicates/self-links, and returns `None` when no candidate exists;
- `netlogo_virus_network_setup_slice_gate` passes with cautious wording.

Extend `tests/test_netlogo_gap_audit.py`:

- the Virus fixture reports `random_selection` in supported evidence;
- the Virus fixture reports `network_generation_minimal` in supported evidence;
- the fixture remains `can_run_natively == False`;
- parser/procedure/layout gaps remain visible.

## Non-Goals

- No `.nlogo` procedure execution.
- No full NetLogo parser or AST.
- No general `with`, `min-one-of`, `distance`, or reporter expression parser.
- No `layout-spring`.
- No claim of NetLogo RNG equivalence.
- No change to base-engine directories.

## Verification

Run the focused gates first:

```text
.venv/bin/python -m pytest tests/test_netlogo_semantics.py tests/test_netlogo_gap_audit.py -q
```

Then run project safety checks:

```text
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
git diff --name-only <base>..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

If the local execution budget permits it, also run the non-GIS suite:

```text
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
```

## Acceptance Criteria

- A manual native Virus setup slice can be written without private helpers.
- The deterministic gate passes and states the scientific boundary.
- The fixture audit shows real progress without claiming full NetLogo execution.
- Existing NetLogo semantic tests continue to pass.
- Forbidden base-engine diff is empty.
