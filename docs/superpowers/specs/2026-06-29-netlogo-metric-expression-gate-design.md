# NetLogo Metric Expression Gate Phase 1 - Design Spec

## Summary

Add a very small NetLogo metric expression evaluator and gate for the Virus on a
Network fixture family. This phase supports the metric expressions that already
appear in the committed fixture:

- `count turtles`
- `count turtles with [infected?]`
- `count turtles with [resistant?]`
- `count turtles with [not infected? and not resistant?]`
- plot-pen arithmetic built from those count expressions, such as
  `plot (count turtles with [infected?]) / (count turtles) * 100`

This is not a NetLogo parser. It is a deterministic metric-evidence cell that
lets MyMoMo evaluate one monitor/plot expression family against native
`NetLogoWorld` state.

## Why This Exists

The previous phases can ingest NetLogo controls, preserve monitor/plot text in
MIR, and package BehaviorSpace oracle outputs. They still cannot evaluate even
one monitor expression natively. This task adds the smallest useful evaluation
surface: SIR turtle-state counts and percentages. That makes the semantic
coverage map more honest: one expression family becomes native, while the broad
NetLogo language remains out of scope.

## Scope

### In Scope

- Add `abm_auto/netlogo_metrics.py`.
- Add `evaluate_netlogo_metric(world, expression)`.
- Add `netlogo_metric_expression_gate() -> tuple[bool, str]`.
- Support boolean predicates inside `with [...]` using:
  - turtle state variables such as `infected?` and `resistant?`;
  - unary `not`;
  - binary `and`.
- Support arithmetic over supported count expressions with:
  - parentheses;
  - numeric constants;
  - `+`, `-`, `*`, `/`.
- Support an optional leading `plot ` command prefix by evaluating the expression
  after `plot`.
- Reject unsupported expression forms with `ValueError`.
- Update NetLogo semantic coverage status.

### Out of Scope

- Full NetLogo expression parsing.
- `or`, comparison operators, reporter procedures, `of`, `sum`, `mean`,
  `link-neighbors`, `links`, patches, breeds, lists, strings, random reporters,
  or agent context.
- Executing NetLogo procedure code.
- Matching NetLogo floating-point edge cases beyond normal Python arithmetic for
  this limited expression family.

## API Design

```python
from abm_auto.netlogo_semantics import NetLogoWorld


def evaluate_netlogo_metric(world: NetLogoWorld, expression: str) -> int | float:
    ...


def netlogo_metric_expression_gate() -> tuple[bool, str]:
    ...
```

`evaluate_netlogo_metric(...)` should:

1. Strip whitespace.
2. Strip a leading `plot ` prefix when present.
3. Replace supported `count turtles with [...]` and `count turtles` terms with
   numeric values from `world`.
4. Evaluate only safe arithmetic syntax through Python `ast`, rejecting names,
   calls, attributes, lists, strings, and unsupported operators.

The evaluator must raise `ValueError` for unsupported expressions rather than
returning a misleading value.

## Predicate Semantics

Predicate text is limited to `and`-joined terms:

```text
infected?
resistant?
not infected?
not resistant?
not infected? and not resistant?
```

Each variable reads `bool(turtle.get(variable, False))`. Missing state keys are
therefore false for this phase. Empty predicates and unsupported operators fail.

## Gate Design

`netlogo_metric_expression_gate()` builds a synthetic `NetLogoWorld` with:

- 3 susceptible turtles: `infected? = False`, `resistant? = False`
- 2 infected turtles: `infected? = True`, `resistant? = False`
- 1 resistant turtle: `infected? = False`, `resistant? = True`

It evaluates the Virus fixture count and plot expressions:

```text
count turtles with [not infected? and not resistant?] -> 3
count turtles with [infected?] -> 2
count turtles with [resistant?] -> 1
plot (count turtles with [not infected? and not resistant?]) / (count turtles) * 100 -> 50.0
plot (count turtles with [infected?]) / (count turtles) * 100 -> 33.333333333333336
plot (count turtles with [resistant?]) / (count turtles) * 100 -> 16.666666666666668
```

The gate passes only if all values match within a small floating tolerance. The
returned message must state the boundary: this proves a limited metric
expression family, not general NetLogo execution.

## Tests

Add `tests/test_netlogo_metric_expressions.py`.

Tests:

1. Count expressions over a synthetic SIR turtle state.
2. Plot-percentage expressions from the Virus fixture.
3. Unsupported expressions fail clearly.
4. The gate passes and its message names the limited boundary.

## Documentation

Update `docs/reproduce/netlogo-semantic-coverage/STATUS.md`:

- add metric expression gate evidence;
- update monitors/plots rows to show one native expression family;
- remove `netlogo_metric_expression_gate` from next executable cells.

## Validation

Run:

```text
.venv/bin/python -m pytest tests/test_netlogo_metric_expressions.py -q
.venv/bin/python -m pytest tests/test_netlogo_metric_expressions.py tests/test_netlogo_semantics.py tests/test_netlogo_controls.py tests/test_netlogo_mir_adapter.py -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

The forbidden diff command must print nothing.

## Scientific Boundary

This phase proves that MyMoMo can evaluate one concrete NetLogo metric family
over native turtle state. It does not prove arbitrary NetLogo expression
compatibility, command execution, patch/link semantics, or NetLogo RNG parity.
