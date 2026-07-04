# GIS Platform Layer — Floor Abstractions — Design Spec

**Status:** Draft. **Date:** 2026-06-24. **Repo:** MyMoMo-GIS-Academic.
**Implements:** [ADR-020](../decisions/ADR-020-gis-platform-layer.md) (the floor;
the 2 supporting seams + the `_dynamic_congestion` migration are deferred).

## Goal

Build the four Mesa-shaped floor abstractions that end the "5 hand-written step
loops" duplication (ADR-020), and prove them with one **real** reference model
(adapter #1) + its deterministic gate. The `_dynamic_congestion` migration and a
codegen `gis_abm_platform` capability are deferred (documented next steps).

## Scope (ships)

`abm_auto/gis/_platform.py`:

- **`GISAgent`** — base with `id`, a `model` back-reference, and a `step(self)`
  hook to override. No behaviour of its own.
- **`AgentSet`** — ordered agent collection + scheduler strategies
  **`sequential`** and **`random_order`** (the two the existing 5 models actually
  use; `concurrent`/`staged` deferred per ADR-020 YAGNI). Seeded `random_order`
  via the model RNG → deterministic.
- **`DataCollector`** — `{name: callable(model)->value}` spec; `collect(model)`
  appends a per-tick record; `series(name)` + `final` read it.
- **`GISModel`** — holds `space` (any existing RasterSpace/GeoNetwork/…, optional),
  seeded `rng`, `t`, an `AgentSet`, an optional `DataCollector`, and `running`.
  `step()` runs the schedule then `t += 1` then collects; `run(n_steps)` collects a
  t=0 baseline, steps until `n_steps` or `running` is False, returns the records.

Reference model (adapter #1, proves the floor) in `_platform.py` or a sibling:

- **`ContagionModel` / `ContagionAgent`** — a minimal real ABM ON the platform:
  agents in a line, S/I state, an infected agent's susceptible neighbours catch
  it with probability `beta` (model RNG). Exercises `GISAgent.step()` (sense+act),
  `AgentSet` scheduling, `DataCollector` (infected count per tick),
  `GISModel.run` + determinism.
- **`contagion_gate`** — deterministic signature: infected is monotone
  non-decreasing and ends above the seed (spreads); fails if it never spreads.

## Hard constraints

1. **Zero-change to `abm_auto/runtime/`, `codegen/`, `calibration/`, `agents/`,
   `pipeline/`.** Platform lives in `abm_auto/gis/_platform.py`.
2. **RNG discipline**: one seeded chain (`GISModel.rng`); two runs with the same
   seed are byte-identical (the existing models are deterministic; the platform
   must preserve that).
3. **No mandatory migration**: the 5 existing ABM modules are untouched; their
   tests must still pass.
4. Predictions locked before runs.

## Decomposition (TDD)

1. `GISAgent` + `AgentSet` (sequential/random_order). Test: order is the insertion
   order for sequential; a seeded `random_order` is a deterministic permutation;
   two same-seed runs match.
2. `DataCollector`. Test: `collect` records each metric; `series`/`final` read back.
3. `GISModel.step`/`run`. Test: `t` advances; reporter gets a t=0 baseline + one
   record per step; `running=False` halts early.
4. `ContagionModel` + `contagion_gate`. Test: infected monotone non-decreasing,
   ends > seed; two same-seed runs identical; gate PASS on a spreading run and
   FAIL on an isolated (no-neighbour) population.

## Validation

```
.venv/bin/python -m pytest tests/gis/test_platform.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline   # EMPTY
```

## Non-goals (deferred)

- `_dynamic_congestion` (and the other 4 models) migration — documented next step;
  the 6-phase tick is delicate and migrating byte-faithfully is its own task.
- `concurrent`/`staged` scheduler strategies — add when a model needs them.
- A `gis_abm_platform` codegen capability + template — next step (needs the
  migration to settle the emitted shape first).
- The 2 ADR-020 supporting seams (unified `Space` adapter, multi-layer
  orchestration) — until a second adapter forces them.
