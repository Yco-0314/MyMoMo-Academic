# GIS Platform Layer (floor) — Locked Predictions (BEFORE any run)

**Locked:** 2026-06-24, BEFORE building/running. Anti-fabrication.
Spec: `docs/superpowers/specs/2026-06-24-gis-platform-layer-design.md`

- **PL1 scheduler order**: `AgentSet(schedule="sequential")` iterates insertion
  order; `schedule="random_order"` with a seeded RNG is a deterministic
  permutation; two same-seed AgentSets produce the same order.
- **PL2 DataCollector**: `collect(model)` appends one record of every declared
  metric; `series(name)` returns the per-tick list; `final` is the last record.
- **PL3 model loop**: `run(n)` collects a t=0 baseline then one record per step
  (n+1 records); `t == n` at the end; setting `running=False` halts early.
- **PL4 determinism**: two `ContagionModel` runs with the same seed produce
  identical DataCollector records.
- **PL5 contagion spreads + gate**: infected count is monotone non-decreasing and
  ends strictly above the seed; `contagion_gate` PASS on a connected line,
  FAIL on an isolated population (no neighbours).
- **PL6 zero-change**: SCIENCE + ENGINE PASS; base suite unchanged; the 5 existing
  ABM modules' tests still pass; forbidden diff empty.

Misses reported as misses.
