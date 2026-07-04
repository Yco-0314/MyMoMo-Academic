# NetLogo BehaviorSpace Manifest Phase 1 - Design Spec

**Status:** Draft for implementation.
**Date:** 2026-06-29
**Repo:** MyMoMo-GIS-Academic
**Parent:** `docs/reproduce/netlogo-semantic-coverage/STATUS.md`

## Summary

Add a small manifest bridge for NetLogo BehaviorSpace experiments. The bridge
records enough information to audit or replay a NetLogo headless run without
claiming MyMoMo can execute arbitrary NetLogo models.

This phase is not a NetLogo runtime. It packages:

- model path;
- experiment name;
- headless command shape;
- output table path;
- BehaviorSpace setup/go/time-limit/metrics/parameters;
- local NetLogo availability status;
- deterministic reductions over an existing BehaviorSpace output table.

## Why

MyMoMo already has `abm_auto/verification/netlogo_oracle.py`, which can run a
BehaviorSpace experiment through NetLogo headless if NetLogo is installed. That
is useful but not yet a reusable reproducibility artifact. A reviewer cannot
look at a single manifest and see:

- which experiment was intended;
- which output table belongs to it;
- what metrics were recorded;
- what parameter values were locked;
- how the table was reduced into scalar evidence;
- whether NetLogo was available locally at manifest creation time.

The manifest bridge turns NetLogo into an explicit audit baseline. This supports
the broader architecture rule: use mature ABM platforms as oracles/baselines
when appropriate, without pretending to absorb their full language semantics.

## Current State

Existing support:

- `abm_auto/verification/netlogo_oracle.py`
  - resolves `NETLOGO_DIR` and `JAVA_HOME`;
  - checks availability;
  - runs `netlogo-headless.sh --model ... --experiment ... --table ...`;
  - parses NetLogo table CSV;
  - summarizes trajectories.
- `tests/fixtures/netlogo/Virus_on_a_Network.nlogo`
  - contains two BehaviorSpace experiments:
    - `oracle_sir_network_GT`;
    - `oracle_network_topology`.
- `tests/fixtures/netlogo/output/*.csv`
  - committed NetLogo table outputs.

Missing support:

- parse BehaviorSpace experiment metadata from `.nlogo`;
- build a portable manifest;
- reduce an existing table into stable scalar summaries;
- write/read a manifest JSON file for reproduction bundles.

## Design

Add a focused module:

```text
abm_auto/verification/netlogo_behaviorspace.py
```

This keeps manifest packaging next to `netlogo_oracle.py`, but separate from the
actual external process runner.

### Public API

```python
extract_behaviorspace_experiments(model_path) -> list[BehaviorSpaceExperiment]
find_behaviorspace_experiment(model_path, experiment_name) -> BehaviorSpaceExperiment
build_behaviorspace_manifest(model_path, experiment_name, output_table_path, *, manifest_path=None) -> dict
write_behaviorspace_manifest(manifest, path) -> Path
summarize_behaviorspace_output(table_path, *, metrics=None, max_tick=None) -> dict
```

`BehaviorSpaceExperiment` should carry:

- `name`;
- `setup`;
- `go`;
- `repetitions`;
- `run_metrics_every_step`;
- `time_limit_steps`;
- `metrics`;
- `enumerated_values`.

The manifest should be JSON-serializable and stable:

```json
{
  "schema": "netlogo-behaviorspace-manifest/v1",
  "model_path": "...",
  "experiment_name": "...",
  "output_table_path": "...",
  "command": [".../netlogo-headless.sh", "--model", "...", "--experiment", "...", "--table", "..."],
  "tool": {
    "netlogo_dir": "...",
    "java_home": "...",
    "available": false
  },
  "experiment": {
    "name": "...",
    "setup": "setup",
    "go": "go",
    "repetitions": 30,
    "run_metrics_every_step": true,
    "time_limit_steps": 250,
    "metrics": ["..."],
    "enumerated_values": {"number-of-nodes": ["150"]}
  },
  "reduction": {
    "row_count": 7530,
    "run_count": 30,
    "max_step": 250,
    "metrics": {
      "count turtles with [infected?]": {
        "final_mean": 1.93,
        "max_mean": 37.4
      }
    }
  }
}
```

Exact numeric values are produced by tests from committed fixtures; the design
does not require hard-coded values here.

## Parsing Rules

For legacy `.nlogo`, the BehaviorSpace XML appears after the model sections in
a literal `<experiments>...</experiments>` block. Phase 1 should:

- locate the first `<experiments>` block by string search;
- parse it with `xml.etree.ElementTree`;
- extract each `<experiment>`;
- extract `<setup>`, `<go>`, `<timeLimit steps="...">`, `<metric>`, and
  `<enumeratedValueSet variable="..."><value value="..."/></...>`;
- preserve parameter values as raw strings.

For `.nlogox`, Phase 1 may support the same `<experiments>` block if present.
No NetLogo install is required for parsing.

## Reduction Rules

`summarize_behaviorspace_output(...)` should use the existing
`netlogo_oracle.parse_table(...)` parser. It should produce a stable dict:

- `row_count`;
- `run_count`;
- `max_step`;
- per-metric:
  - `final_mean`;
  - `max_mean`.

If `metrics` is omitted, reduce every numeric column except known run/parameter
columns and `[step]`.

If `max_tick` is supplied, ignore rows after that tick before reduction.

## Tests

Add `tests/test_netlogo_behaviorspace_manifest.py`.

Required tests:

1. Extracts both committed fixture experiments and their setup/go/time limit,
   repetitions, metrics, and enumerated values.
2. Missing experiment raises a clear `ValueError`.
3. Builds a manifest for `oracle_sir_network_GT` with command shape,
   availability metadata, experiment metadata, and reduction from the committed
   `sir_trajectories.csv`.
4. Writes and reads manifest JSON round-trip with stable sorted keys.
5. Reduces the committed topology output table with `row_count`, `run_count`,
   `max_step`, `final_mean`, and `max_mean`.

## Non-Goals

- No actual NetLogo run in tests.
- No change to `netlogo_oracle.run_experiment(...)`.
- No CLI command yet.
- No MIR write path.
- No NetLogo procedure parsing.
- No claim that a manifest proves MyMoMo compatibility with the model.
- No changes to `abm_auto/runtime/`, `abm_auto/codegen/`,
  `abm_auto/calibration/`, `abm_auto/agents/`, or `abm_auto/pipeline/`.

## Validation

Target validation:

```text
.venv/bin/python -m pytest tests/test_netlogo_behaviorspace_manifest.py tests/test_netlogo_controls.py tests/test_netlogo_semantics.py -q
.venv/bin/python -m pytest tests/test_topologies.py tests/test_benchmark_adapter.py -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

## Success Criteria

- BehaviorSpace moves from ad hoc oracle fixture use to an explicit manifest
  bridge.
- Existing oracle execution remains unchanged.
- The manifest can be generated entirely from committed fixtures when NetLogo is
  not installed.
- The coverage table can mark BehaviorSpace as `oracle_backed` with manifest
  evidence, not just raw fixture evidence.
