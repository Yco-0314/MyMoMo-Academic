# NetLogo Controls-to-MIR Phase 1 - Design Spec

**Status:** Draft for implementation.
**Date:** 2026-06-29
**Repo:** MyMoMo-GIS-Academic
**Parent:** `docs/reproduce/netlogo-semantic-coverage/STATUS.md`

## Summary

Map parsed NetLogo controls into MIR without adding execution or codegen. The
adapter takes a `NetLogoModel` from `abm_auto.ingest.netlogo.parse_nlogo(...)`
and returns an open-core `MIR` whose:

- `metadata` records NetLogo provenance;
- `run.params` records sliders, switches, choosers, and input boxes;
- `metrics` records monitors, plots, and plot pens;
- `trace` preserves the source controls payload for audit;
- `extensions` remains empty.

This phase does not interpret NetLogo expressions, execute monitors/plot pens,
generate runnable Python, or claim `.nlogo` compatibility.

## Why

The controls-to-spec phase made NetLogo interface widgets structured. The next
step is to make that structure consumable by the unified semantic layer. MIR is
the correct boundary because it is the open contract used by the broader
platform strategy.

The adapter should remain thin, following the existing GIS adapter style:
source-specific structure goes in open MIR fields when meaning is stable, and
raw source details remain in `trace`. Closed overlays are not read or written.

## API

Add:

```text
abm_auto/mir/_netlogo_adapter.py
```

Public functions:

```python
netlogo_model_to_mir(model: NetLogoModel) -> MIR
netlogo_controls_to_mir(model: NetLogoModel) -> MIR
```

The second function is an alias for readability in tests and docs. There is no
reverse MIR-to-NetLogo adapter in Phase 1.

## Mapping

### Metadata

```python
MIRMetadata(
    name=model.name,
    domain="netlogo",
    description=<first non-empty info line or empty>,
    provenance={
        "source": "netlogo_controls_to_mir",
        "has_code_text": bool(model.code_text),
        "has_info_text": bool(model.info_text),
    },
)
```

### Run Params

`MIR.run.params` is a dict keyed by control variable name:

- slider:
  - `kind="slider"`
  - `default`, `minimum`, `maximum`, `step`
  - `units`, `label`
  - each value carries `raw` and `number`
- switch:
  - `kind="switch"`
  - `default`
  - `label`
- chooser:
  - `kind="chooser"`
  - `default`
  - `choices`
  - `label`
- input box:
  - `kind="input_box"`
  - `default`
  - `multiline`
  - `label`

Raw NetLogo expressions are preserved. They are not evaluated.

### Metrics

`MIR.metrics` contains:

- monitor rows:
  - `kind="monitor"`
  - `name`
  - `reporter`
- plot rows:
  - `kind="plot"`
  - `name`
  - `x_axis`
  - `y_axis`
  - `pens`, each with `name`, `interval`, `mode`, `color`, `update_command`

Reporter and update commands are raw text, not executable ASTs.

### Trace

`MIR.trace` should include:

```python
{
  "source_format": "netlogo",
  "controls": model.controls.to_dict(),
  "legacy_sliders": model.sliders,
  "legacy_plots": model.plots,
}
```

### Empty Clusters

Do not populate:

- `entities`;
- `state`;
- `relations`;
- `layers`;
- `fidelity`;
- `extensions`.

This preserves the open/closed contract and avoids pretending that controls
alone define executable model dynamics.

## Tests

Add `tests/test_netlogo_mir_adapter.py`.

Required cases:

1. Synthetic controls model maps sliders/switches/choosers/input boxes into
   `mir.run.params`.
2. Monitors and plots map into `mir.metrics`.
3. Raw expression values survive JSON round-trip.
4. `extensions` remains `{}` and empty clusters remain empty.
5. Committed Virus fixture maps controls into MIR with `average-node-degree`
   maximum raw expression and `Network Status` plot pens.

## Validation

```text
.venv/bin/python -m pytest tests/test_netlogo_mir_adapter.py tests/test_netlogo_controls.py tests/test_netlogo_semantics.py tests/test_netlogo_behaviorspace_manifest.py -q
.venv/bin/python -m pytest tests/test_topologies.py tests/test_benchmark_adapter.py -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

## Non-Goals

- No NetLogo expression evaluator.
- No procedure parser.
- No runnable codegen.
- No MIR-to-NetLogo reverse adapter.
- No BehaviorSpace execution.
- No changes to `abm_auto/runtime/`, `abm_auto/codegen/`,
  `abm_auto/calibration/`, `abm_auto/agents/`, or `abm_auto/pipeline/`.

## Success Criteria

- NetLogo controls become part of the open MIR contract.
- The adapter preserves raw source details for audit.
- The adapter does not weaken the open/closed `extensions` boundary.
- Existing NetLogo ingest, controls, semantic, and BehaviorSpace tests remain
  green.
