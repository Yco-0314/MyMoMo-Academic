# NetLogo BehaviorSpace CLI Pack Phase 1 - Design Spec

## Summary

Add a reviewer-facing repro-pack writer for the existing NetLogo BehaviorSpace
manifest bridge. The pack turns a committed `.nlogo` model, a named
BehaviorSpace experiment, and an existing BehaviorSpace output table into a
small directory containing:

- `manifest.json`: the existing structured audit manifest;
- `MANIFEST.md`: a human-readable reviewer note with the exact headless command
  shape and deterministic reduction summary.

This phase does not execute NetLogo. It does not introduce a NetLogo interpreter,
procedure parser, expression parser, or native BehaviorSpace runner.

## Why This Exists

The current BehaviorSpace bridge can build a manifest in memory and write JSON,
but a reproduction reviewer still needs a stable package layout. This task
closes that packaging gap without expanding scientific claims. It makes the
oracle-backed NetLogo evidence easier to inspect, while keeping NetLogo itself
an external oracle.

## Scope

### In Scope

- Add `write_behaviorspace_repro_pack(...)` to
  `abm_auto/verification/netlogo_behaviorspace.py`.
- Add a CLI command exposed as:

```text
abm-auto netlogo-behaviorspace-pack <model> <experiment> <table> --out <dir>
```

- Write `manifest.json` and `MANIFEST.md`.
- Reuse `build_behaviorspace_manifest(...)` and
  `write_behaviorspace_manifest(...)`.
- Keep paths exactly as the caller provides them; this is an audit pack, not a
  copy/archive format.
- Render the headless command as a shell-safe argv string, so paths with spaces
  can be copied by reviewers.
- Reject pack generation when a BehaviorSpace experiment declares metric
  columns that are absent from the supplied output table.
- Avoid creating the output directory when experiment lookup or table validation
  fails.
- Test with the existing committed Virus-on-a-Network fixture and existing
  BehaviorSpace output tables.
- Update `docs/reproduce/netlogo-semantic-coverage/STATUS.md`.

### Out of Scope

- Running `netlogo-headless.sh`.
- Validating NetLogo installation beyond the existing manifest `tool.available`
  field.
- Copying model/table files into the pack.
- Normalizing paths to repo-relative paths.
- Adding native MyMoMo execution for BehaviorSpace experiments.
- Parsing monitor or plot expressions.
- Adding NetLogo patch/link/world semantics.

## API Design

```python
def write_behaviorspace_repro_pack(
    model_path: Path | str,
    experiment_name: str,
    output_table_path: Path | str,
    out_dir: Path | str,
) -> dict:
    ...
```

The returned dictionary has this shape:

```python
{
    "manifest": manifest_dict,
    "manifest_path": "/path/to/out/manifest.json",
    "readme_path": "/path/to/out/MANIFEST.md",
}
```

The manifest dictionary keeps schema
`netlogo-behaviorspace-manifest/v1`. The function also injects
`manifest_path` into the manifest before writing it, matching the existing
`build_behaviorspace_manifest(..., manifest_path=...)` behavior.

## `MANIFEST.md` Content

The Markdown file must state:

- the pack is an audit/repro pack and does not execute NetLogo;
- the model path;
- the experiment name;
- the output table path;
- NetLogo availability from the manifest;
- the shell-safe headless command shape from `manifest["command"]`;
- row count, run count, max step, and metric names from the reduction.

The Markdown body should be deterministic enough for tests to assert key lines,
but it does not need byte-for-byte golden testing.

## CLI Design

Add a top-level Typer command to `abm_auto/cli.py`:

```python
@app.command()
def netlogo_behaviorspace_pack(...):
    ...
```

Typer exposes that as `netlogo-behaviorspace-pack`.

Arguments:

- `model`: existing `.nlogo` / `.nlogox` path;
- `experiment`: BehaviorSpace experiment name;
- `table`: existing BehaviorSpace table output path;
- `--out` / `-o`: output directory, default
  `netlogo_behaviorspace_pack`.

On success, the command prints the two written paths. On invalid experiment
names or bad inputs, existing exceptions should surface through Typer as a
non-zero exit. No special network or external process access is required.

## Tests

Add `tests/test_netlogo_behaviorspace_cli_pack.py`.

Tests:

1. `write_behaviorspace_repro_pack(...)` writes both files, returns their paths,
   and the JSON contains the expected experiment and reduction.
2. `MANIFEST.md` contains the audit boundary text, experiment name, model path,
   output table path, command shape, and summary fields.
3. `MANIFEST.md` quotes paths with spaces in the rendered command.
4. The CLI command writes the pack and prints both file names.
5. An unknown experiment fails clearly through the CLI without leaving a partial
   output directory.
6. A mismatched experiment/output-table pair fails clearly when declared metrics
   are missing from the table.

Existing manifest tests remain unchanged.

## Documentation

Update `docs/reproduce/netlogo-semantic-coverage/STATUS.md`:

- add CLI pack evidence;
- update the BehaviorSpace row from "leave-as-is until CLI packaging" to "use
  pack writer for reviewer-facing oracle baselines";
- move the next executable cell to `netlogo_metric_expression_gate`.

## Validation

Run:

```text
.venv/bin/python -m pytest tests/test_netlogo_behaviorspace_cli_pack.py tests/test_netlogo_behaviorspace_manifest.py -q
.venv/bin/python -m pytest tests/test_netlogo_mir_adapter.py tests/test_netlogo_controls.py tests/test_netlogo_semantics.py tests/test_netlogo_behaviorspace_manifest.py tests/test_netlogo_behaviorspace_cli_pack.py -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

The forbidden diff command must print nothing.

## Scientific Boundary

This pack proves MyMoMo can preserve and package NetLogo BehaviorSpace oracle
evidence for review. It does not prove MyMoMo can execute arbitrary NetLogo
models or reproduce NetLogo random-number semantics natively.
