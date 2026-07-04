# NetLogo Controls-to-Spec Phase 1 - Design Spec

**Status:** Draft for review.
**Date:** 2026-06-29
**Repo:** MyMoMo-GIS-Academic
**Parent:** `docs/reproduce/netlogo-semantic-coverage/STATUS.md`

## Summary

Add a structured, non-executing NetLogo controls spec to the existing NetLogo
ingest path. This phase should parse NetLogo interface controls into a stable
data object that later MIR/codegen/DSL work can consume:

- sliders;
- switches;
- choosers;
- input boxes;
- monitors;
- plots, including plot pens where available.

This phase does not execute NetLogo procedures, does not parse command blocks
into an AST, does not generate runnable MyMoMo models, and does not claim
arbitrary `.nlogo` compatibility.

## Why

The previous `agentset_ask_tick` cell proved a minimal native runtime semantic:
agentsets, ask-over-snapshot, ticks, globals, and monitor collection. The next
missing NetLogo semantic layer is authoring and experiment controls.

NetLogo models often encode scientific parameters and observed outputs in the
Interface tab rather than only in code:

- sliders define numeric parameters and default values;
- switches define boolean interventions;
- choosers define categorical modes;
- input boxes define user-provided constants or expressions;
- monitors define observed scalar metrics;
- plots and plot pens define output time series.

The current ingest path extracts sliders and plot names only. That is enough for
a rough `story.md`, but too weak for MyMoMo's longer-term goal: translating a
NetLogo-style model into MIR/gated/codegen-ready structure.

## Current State

`abm_auto/ingest/netlogo.py` currently provides:

- `NetLogoModel`;
- `parse_nlogo(path)`;
- `.nlogo` text parsing;
- `.nlogox` XML parsing;
- partial extraction of `globals`, `breed`, `turtles-own`, `patches-own`;
- slider parsing into `model.sliders`;
- plot name extraction into `model.plots`;
- `to_story_md(model)`.

The committed Virus-on-a-Network fixture shows a common `.nlogo` interface
shape:

- `SLIDER` blocks are line-based and may contain numeric values or expressions
  such as `number-of-nodes - 1`;
- `PLOT` blocks contain a name, axes, bounds, flags, and `PENS` lines with plot
  update commands;
- existing parser keeps only a simplified slider dict and plot name.

`docs/reproduce/netlogo-semantic-coverage/STATUS.md` currently marks sliders
and plots as `partial`, and switches/choosers/input boxes as `missing`.

## Design Choice

Use a backward-compatible structured controls object.

### Option A - Extend `NetLogoModel` In Place

Add new fields directly to `NetLogoModel` while keeping existing `sliders` and
`plots` unchanged.

**Pros:** minimal import churn; existing callers keep working.
**Cons:** raw model dataclass grows.

### Option B - Separate `NetLogoControlsSpec`

Add a small controls dataclass and attach it as `NetLogoModel.controls`, while
leaving legacy fields as compatibility views.

**Pros:** clearer boundary; future MIR adapter can consume one object.
**Cons:** requires a small migration inside `netlogo.py`.

### Option C - Map Directly To MIR

Skip a NetLogo-specific controls spec and write directly into MIR `run` and
`metrics`.

**Pros:** fastest path toward unified IR.
**Cons:** loses source-specific detail too early; makes parser tests harder;
mixes ingest with MIR policy.

## Recommendation

Use Option B with compatibility fields.

`NetLogoControlsSpec` becomes the source-preserving intermediate object. The
existing `model.sliders` and `model.plots` remain populated exactly enough for
`to_story_md(...)` and old tests. New code consumes `model.controls`.

This keeps the migration narrow: one ingest module, one test file, no runtime
execution, no MIR mutation yet.

## Proposed API

Add dataclasses in `abm_auto/ingest/netlogo.py` or a sibling module if the file
becomes too large:

```python
NetLogoControlValue(raw: str, number: float | None)
NetLogoSlider(name, label, minimum, maximum, default, step, units, orientation)
NetLogoSwitch(name, label, default)
NetLogoChooser(name, label, choices, default)
NetLogoInputBox(name, label, default, multiline)
NetLogoMonitor(name, reporter)
NetLogoPlotPen(name, interval, mode, color, update_command)
NetLogoPlotSpec(name, x_axis, y_axis, pens)
NetLogoControlsSpec(sliders, switches, choosers, input_boxes, monitors, plots)
```

Each dataclass should expose `to_dict()` so tests and future MIR adapters can
assert stable structures without importing implementation internals.

`NetLogoModel` should gain:

```python
controls: NetLogoControlsSpec
```

Compatibility:

- `model.sliders` stays a list of legacy dicts with `name`, `min`, `max`,
  `default`, `step`;
- `model.plots` stays a list of plot names;
- existing story generation remains unchanged except it may use richer controls
  later.

## Parsing Rules

### Text `.nlogo`

Parse interface blocks conservatively using the existing line-based approach.

Required Phase 1 widgets:

- `SLIDER`
- `SWITCH`
- `CHOOSER`
- `INPUTBOX`
- `MONITOR`
- `PLOT`

`BUTTON` may be ignored in this phase. Procedure binding belongs to a later
setup/go/parser phase.

Numeric fields should preserve both:

- raw NetLogo text, e.g. `"number-of-nodes - 1"`;
- parsed float only when unambiguously numeric.

This matters because NetLogo sliders often use expressions in min/max fields.
The ingest layer should not evaluate those expressions.

### `.nlogox`

Parse common XML widget elements into the same controls spec. XML attribute
names vary by NetLogo version, so the implementation should accept a small set
of obvious aliases and preserve raw strings when unsure.

Phase 1 tests should use a tiny synthetic `.nlogox` fixture rather than relying
on a local NetLogo install.

## Data Flow

```text
.nlogo/.nlogox
  -> parse_nlogo(path)
  -> NetLogoModel.controls
  -> compatibility fields model.sliders/model.plots
  -> to_story_md(model) unchanged
```

Future flow, explicitly out of scope for this phase:

```text
NetLogoModel.controls
  -> MIR.run.params + MIR.metrics
  -> codegen capability / DSL layer
```

## Tests

Add or extend tests under `tests/test_netlogo_ingest.py` or
`tests/test_netlogo_controls.py`.

Required TDD cases:

1. Text `.nlogo` slider parsing preserves numeric values and raw expressions.
2. Text `.nlogo` switch parsing produces boolean default.
3. Text `.nlogo` chooser parsing preserves ordered choices and default.
4. Text `.nlogo` input box parsing preserves raw default.
5. Text `.nlogo` monitor parsing preserves reporter text.
6. Text `.nlogo` plot parsing preserves plot name and pen update command.
7. `.nlogox` synthetic fixture maps the same widget family into
   `NetLogoControlsSpec`.
8. Existing `model.sliders`, `model.plots`, and `to_story_md(...)` behavior
   remain compatible.

## Validation

Target validation for implementation:

```text
.venv/bin/python -m pytest tests/test_netlogo_controls.py tests/test_netlogo_semantics.py -q
.venv/bin/python -m pytest tests/test_topologies.py tests/test_benchmark_adapter.py -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis --ignore=tests/closed_extension
git diff --name-only HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

The closed extension directory is excluded while Claude's closed extension covariate work is dirty and
in progress. Do not modify closed extension files in this task.

## Non-Goals

- No NetLogo procedure parser.
- No expression evaluator for slider min/max/default.
- No runnable `.nlogo` translation.
- No MIR write path yet.
- No BehaviorSpace manifest; that is the next bridge task.
- No patches/links implementation.
- No changes to `abm_auto/runtime/`, `abm_auto/codegen/`,
  `abm_auto/calibration/`, `abm_auto/agents/`, or `abm_auto/pipeline/`.
- No edits to Claude's in-progress closed extension or classics files.

## Risks

1. **Line-based `.nlogo` widgets vary by NetLogo version.**
   Mitigation: preserve raw values, test a minimal synthetic fixture and the
   committed Virus fixture shape.

2. **Parser scope can creep into expression execution.**
   Mitigation: Phase 1 stores expressions as raw strings and only parses
   obvious numbers.

3. **Compatibility fields can drift from richer controls.**
   Mitigation: tests assert `model.sliders` and `model.plots` remain populated
   from `model.controls`.

## Success Criteria

- `switches`, `choosers`, `input_boxes`, `monitors`, and richer `plots` move
  from `missing`/`partial` to structured ingest evidence in the semantic
  coverage table.
- Existing story conversion remains compatible.
- The new controls object is stable enough for a later MIR adapter without
  forcing that adapter now.
- No base-engine directory is touched.
