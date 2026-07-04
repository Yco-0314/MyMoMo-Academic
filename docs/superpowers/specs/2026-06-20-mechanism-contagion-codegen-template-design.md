# Mechanism Contagion Codegen Template Design

## Summary

Make `mechanism_contagion` the second runnable mechanism-library codegen
capability. The generated model stays synthetic and small: it builds a
deterministic chain `neighbors_of(i)` callable, calls `run_contagion`, and
verifies a new contagion-specific gate.

This closes the remaining mechanism-library registered codegen gap created by
the self-extension scaffold phase. It does not add GIS layer adapters, observed
data, stochastic calibration, traffic flow, code generation self-modification,
or a shared `CoupledModel`.

## Architecture

The mechanism seam remains `neighbors_of(i) -> Iterable[int]`. Runtime
mechanisms know only integer agents and neighbor callables; spatial layers adapt
to that seam elsewhere.

`mechanism_contagion_gate` belongs in `abm_auto/gis/_mechanisms.py` next to
`mechanism_space_gate`, because it verifies the same mechanism-neighbor seam but
for stochastic contagion instead of threshold adoption. The codegen registry is
the truth-table for renderability: `mechanism_contagion` can become renderable
only after the gate exists and the template includes all required runtime calls.

## Key Changes

- Add `mechanism_contagion_gate(...) -> tuple[bool, str]`.
  - Default connected neighbor callable: chain.
  - Default isolated neighbor callable: empty.
  - Run `run_contagion` with identical `n_agents`, `beta`, `steps`, `seed`, and
    `seeds` for connected and isolated cases.
  - Pass only when connected spread exceeds the initial seed count, isolated
    stays at the initial seed count, and connected final adoption exceeds
    isolated final adoption.
  - Reject invalid contagion parameters through existing runtime behavior or
    clear gate failures; do not silently coerce into a different mechanism.
  - Description must state this is contagion over the neighbor seam, not a
    spatial validation claim.

- Mark `mechanism_contagion` renderable in `abm_auto/gis/_capabilities.py`.
  - Required tokens: `run_contagion`, `mechanism_contagion_gate`.
  - Gate: `mechanism_contagion_gate`.

- Add a deterministic `_MECHANISM_CONTAGION` template in
  `abm_auto/gis/_templates.py`.
  - Build `_chain_neighbors(n_agents)`.
  - Call `run_contagion(...)`.
  - Call `mechanism_contagion_gate(...)`.
  - Keep generated imports limited to `abm_auto.gis`.

- Update extractor and self-extension tests indirectly through the registry.
  - Extractor prompt should include `mechanism_contagion` once renderable.
  - Explicit LLM output for `mechanism_contagion` should be accepted.
  - Self-extension preflight should classify `mechanism_contagion` as
    `renderable`, not `registered_gap`.
  - Scaffold tests must move to a different still-nonrenderable registered
    capability if one remains, or assert renderable refusal for
    `mechanism_contagion`.

- Update `docs/reproduce/coupled-seam/STATUS.md`.
  - Record that both mechanism-library codegen cells are now runnable.
  - Keep the YAGNI boundary: this proves mechanism template coverage, not a
    shared coupled/dynamic lifecycle abstraction.

## Tests

- `tests/gis/test_mechanisms.py`
  - connected chain contagion gate passes;
  - no-effect isolated/empty contagion gate fails.

- `tests/gis/test_capabilities.py`
  - `mechanism_contagion` is renderable;
  - required tokens include `run_contagion` and `mechanism_contagion_gate`;
  - renderable capability list includes `mechanism_contagion`.

- `tests/gis/test_codegen.py`
  - explicit `mechanism_contagion` spec validates without `data_path`;
  - rendered code contains `run_contagion` and `mechanism_contagion_gate`, not
    threshold adoption;
  - generated model executes and prints `PASS`.

- `tests/gis/test_codegen_gate.py`
  - clean generated `mechanism_contagion` code passes;
  - removing `mechanism_contagion_gate` fails through registry required tokens.

- `tests/gis/test_extractor.py`
  - prompt lists `mechanism_contagion`;
  - explicit `mechanism_contagion` output is accepted.

- `tests/gis/test_self_extension.py`
  - preflight classifies `mechanism_contagion` as renderable;
  - scaffold refuses it as already renderable;
  - scaffold gate uses another registered gap if available.

## Final Verification

Run from the feature worktree:

```bash
.venv/bin/python -m pytest tests/gis/test_mechanisms.py tests/gis/test_capabilities.py tests/gis/test_codegen.py tests/gis/test_codegen_gate.py tests/gis/test_extractor.py tests/gis/test_self_extension.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

## Non-Goals

- No real-world contagion data demo.
- No spatial-layer-specific contagion template beyond `neighbors_of`.
- No codegen self-modification.
- No `CoupledModel`.
- No base-engine changes.
