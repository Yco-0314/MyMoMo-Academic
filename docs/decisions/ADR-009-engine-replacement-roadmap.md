# ADR-009: Engine Replacement Roadmap — Phased Melodie Decommission

**Status**: Roadmap (no code changes this ADR)
**Date**: 2026-05-31
**Deciders**: yco + Claude (Opus 4.7)
**Related**: [ADR-005](ADR-005-unified-platform-dual-mode.md), [ADR-008](ADR-008-multi-fidelity-calibration.md)

---

## Context and Problem Statement

The runtime engine — the layer that orchestrates Scenario → Model →
Agent execution and produces output CSVs — is currently a mix of:

- **Our standalone code** in `abm_auto/runtime/_*.py`: Agent, GridAgent,
  NetworkAgent, Grid, Network, Model, Environment, topologies (7 files,
  696 LoC total)
- **Melodie-delegated** at `runtime/__init__.py`: AgentList,
  DataCollector, Scenario, Config, Simulator, Calibrator, Trainer

The `__init__.py` docstring already names this the "engine replacement
contract": "To swap the underlying simulation engine, update ONLY this
file."

Three things motivate replacement:

1. **Strategic positioning** — owning the engine is the difference
   between "thin wrapper over a third-party simulator" and "calibration
   research platform." For BEHAVE 2025 and follow-on academic work, the
   former is hard to defend as a contribution.
2. **Pin specific Melodie versions** has bitten us — the published
   `Melodie==2.x` shipped without `setup-spatially-clustered-network`
   which we needed for topological fidelity (ADR-006 §1).
3. **Multi-fidelity (ADR-008) and future research extensions** want
   hooks Melodie doesn't expose (per-call fidelity scaling, seed-set
   averaging, custom callbacks at tick boundaries).

This ADR does NOT extract any engine code. It records the **phased
roadmap** so future architecture reviews don't re-litigate the order
of operations, and so the work can be picked up across sessions
without re-deriving the dependency graph.

## Decision Drivers

1. **Each phase must be independently shippable** — full engine
   replacement is a multi-week effort; we ship value at every layer
2. **Zero-regression gate per phase** — cross-domain lean + SIR dogfood
   pass at the end of each layer
3. **Phase ordering by call-graph dependency** — replace LEAVES first
   (Scenario is a pure data carrier; Simulator orchestrates everything)
4. **Per-phase ADR amend** — each layer gets a follow-up amendment to
   this ADR with the actual code seam + rollback plan

## The dependency graph (call-edge view)

```
  Simulator                                ←─ orchestrator (entry point)
    ├─ Config                              ←─ project paths
    ├─ Scenario  (one per CSV row)         ←─ parameter struct
    ├─ Model                               ←─ user-subclassed; we own
    │   ├─ AgentList                       ←─ agent container
    │   ├─ Grid / Network                  ←─ we own
    │   ├─ Environment                     ←─ we own
    │   └─ DataCollector                   ←─ per-tick metrics → CSV
    └─ (Calibrator / Trainer)              ←─ parameter sweeps (optional)
```

Leaves on the right (Model, AgentList, DataCollector) are called BY
Simulator. Roots on the left (Config, Scenario) carry data INTO
Simulator. Replacing the root requires either (a) keeping the
Simulator able to consume both old + new shapes during transition, or
(b) replacing Simulator at the same time.

## Phased plan

### Phase 1 — Scenario (leaf, smallest surface, highest leak)

**Why first**: Scenario appears in user-written code more than any
other delegated class. Every example's `core/scenario.py` is
`class FooScenario(Scenario): def setup(self): self.x = ...`. The
class is essentially a typed dict with a CSV-override convention. Pure
data; no methods we depend on (`copy()`, `get_dataframe()`,
`get_matrix()` are unused in our codebase).

**Surface to replace**:
- `__init__(self, id_scenario)`
- `setup()` callback hook
- Attribute assignment in `setup()` overridden by CSV row values

**Approach**:
1. Build `abm_auto/runtime/_scenario.py` as a standalone class with
   the same surface. No Melodie import.
2. The CSV-override behavior is currently done by the Simulator
   (Melodie code). For Phase 1 we keep Melodie's Simulator and only
   replace the class — Melodie's Simulator instantiates our class via
   `scenario_cls=` and the override mechanism still works because
   Melodie reads attributes by name, not by type.
3. Swap the seam in `runtime/__init__.py`: import `Scenario` from
   `runtime._scenario` instead of `Melodie`.
4. Cross-domain lean + SIR dogfood as the 0-regression gate.

**Risk**: Melodie's Simulator may use type-introspection or
`isinstance(scenario, Melodie.Scenario)` checks. If so, Phase 1 needs
either a `class Scenario(Melodie.Scenario)` parent for back-compat or
a duck-typed wrapper. Investigate in C1.

**Effort**: 1-2 days. Mostly investigation + a 30-line dataclass.

### Phase 2 — DataCollector (leaf, output owner)

**Why second**: DataCollector is called by every example's Model class
to record per-tick metrics that end up in the result CSVs that
SimulatorWrapper consumes. The output CSV format IS our calibration's
ground truth — controlling it means controlling our test surface.

**Surface to replace**:
- `add_environment_property(name)` registration
- `add_agent_property(category, name)` registration
- Per-tick collection (called by Model.run loop)
- CSV serialization at end of run

**Approach**:
1. `abm_auto/runtime/_data_collector.py` — pandas-based, writes the
   same CSV format Melodie does (columns: scenario_id, run_num, period,
   <metric_name>...).
2. Phase 1's Scenario replacement gives Phase 2 a partner — together
   the Phase 1+2 prelude lets us own the entire INPUT (Scenario) and
   OUTPUT (DataCollector) contract while Melodie still drives the
   middle.
3. Regression gate: cross-domain + SIR dogfood AND a row-for-row
   diff of result CSVs between Phase 2 and Melodie (sample param set,
   N=5 sims, files must be byte-identical for the metric columns).

**Effort**: 2-3 days.

### Phase 3 — AgentList (container)

**Why third**: AgentList is used in Model.setup as
`self.agents = self.create_agent_list(AgentCls, agent_num)`, then
iterated in Model.run. It's a thin list-with-typed-iteration. Phase 1
+ Phase 2 didn't touch it; Phase 3 can land independently.

**Surface to replace**:
- `__init__(model, agent_cls, n)`
- `__iter__`, `__len__`, indexing
- `setup()` per-agent

**Approach**:
1. `abm_auto/runtime/_agent_list.py` — wraps a Python list, exposes
   Melodie's API.
2. Drop CSV-loading temporarily — examples don't use
   AgentParams.csv. If we need it later, add it back as a separate seam.

**Effort**: 1 day.

### Phase 4 — Simulator + Config (the big one)

**Why last**: Simulator is the orchestrator. It instantiates Scenario,
Model, Calibrator, runs the iter loop, manages I/O. Replacing it
means we own the entire engine. Until Phase 4, Melodie's Simulator
glues Phases 1-3 together; after Phase 4, we're standalone.

**Surface to replace** (roughly, full list pending C1 investigation):
- `Config(input_folder, output_folder, project_root, ...)`
- `Simulator(config, model_cls, scenario_cls, df_loader_cls?)`
- `simulator.run()` — single scenario
- `simulator.run_parallel(...)` — multi-scenario
- Output CSV writing convention (one folder per scenario_id?)

**Approach**:
1. Phase 4a: drop multi-scenario support if our code doesn't use it
   (check: examples + cross-domain run ONE scenario each from CSV
   row 0, so multi-scenario may already be vestigial in our usage)
2. Phase 4b: rewrite Simulator.run as a deterministic single-shot
3. Phase 4c: replace Calibrator + Trainer with our own (we have
   SimulatorWrapper anyway — these may not be needed at all)

**Effort**: 1 week. Includes the regression-fixture build-out for the
output-CSV byte-equality check.

### Phase 5 — Calibrator + Trainer (probably delete, not replace)

**Why**: We already have our own calibration pipeline
(`abm_auto.calibration.*`). Melodie's Calibrator/Trainer are unused
in the current codebase. Investigate; if confirmed unused, remove from
`runtime/__init__.py` exports without replacement.

**Effort**: 1 day investigation + 30-minute removal commit.

## What this ADR explicitly does NOT decide

- The exact dataclass shape for replaced Scenario — deferred to
  Phase 1's investigation
- Whether to keep CSV-driven scenario override as a convention or
  introduce explicit `from_csv(row)` constructors — deferred to Phase 1
- Whether to add new hooks while replacing (fidelity callbacks,
  seed-set averaging) — phase replacements are 1:1 with current
  Melodie behavior; new features land as separate ADRs
- Timeline — phases land when they earn time, not on a fixed calendar

## Considered Alternatives

### Alt A: Big-bang rewrite

Build a complete standalone engine in a feature branch, swap on
merge. Rejected because:
- 4-week branch divergence is a known failure mode
- No regression gate per layer
- Reviewer has to read all the code at once

### Alt B: Pin to specific Melodie commit, never replace

Stay on the third-party engine forever. Rejected because:
- Strategic-positioning argument (above) becomes increasingly weak as
  the rest of the platform matures
- We've already paid the cost of standalone Agent/Grid/Network — the
  marginal cost of finishing is lower than starting over

### Alt C: Fork Melodie into vendor/

Copy Melodie's source into our repo, change it as needed. Rejected
because:
- Inherits all of Melodie's design decisions (e.g., DataCollector's
  particular CSV format) without our being able to justify them
- Forks rot — every Melodie release means manual reconciliation

## Verification per phase

Each phase MUST pass:

1. `pytest tests/ --ignore=tests/e2e` — all unit tests green
2. `python tests/e2e/cross_domain_lean.py` — all 3 domains PASS
   under seed=42 with current MSE thresholds
3. Hand-comparison of `calibration_final_sim.csv` between
   pre-phase and post-phase runs on ONE seed — values within 1e-9

If (3) fails (binary diff non-zero), the phase has changed the
sim's output, which is a regression even if MSE thresholds still
PASS. Investigate before merging.

## Open Questions

**OQ#1**: Does Melodie's Simulator do `isinstance(scenario, Melodie.Scenario)` checks?
Determines whether Phase 1 needs a Melodie.Scenario parent class for
back-compat during transition.

**OQ#2**: Is there cross-domain semantics in the existing examples
that depend on Melodie behaviors not yet captured by abm_auto/runtime/?
(e.g., a particular tick-ordering convention, agent-update-order
guarantee). Build a fixture for this before Phase 4.

**OQ#3**: Calibrator/Trainer — are they truly unused, or is something
in the Pipeline still calling them? Phase 5 investigation will
answer.

## Status tracking

| Phase | Status | Branch/commit |
|---|---|---|
| 1 — Scenario | investigation complete (see amend below) | — |
| 2 — DataCollector | not started | — |
| 3 — AgentList | not started | — |
| 4 — Simulator + Config | not started | — |
| 5 — Calibrator + Trainer removal | not started | — |

---

## Amend 1 — Phase 1 Scenario investigation (2026-05-31)

Source-read of `Melodie/simulator.py`, `Melodie/scenario_manager.py`,
`Melodie/data_loader.py`, `Melodie/element.py` to resolve OQ#1 and
scope the actual Phase 1 work.

### OQ#1 resolved: no isinstance checks

`grep -n "isinstance\|issubclass" Melodie/simulator.py` returns ONE
hit, and it's for `df_loader_cls` (unrelated to Scenario):

    line 61:  assert issubclass(self.df_loader_cls, DataLoader)

The Simulator instantiates the user's scenario class via
`self.scenario_cls()` (data_loader.py:367) and never type-checks the
result. **Phase 1 can ship a non-Melodie-subclass Scenario without a
back-compat parent class.**

### Methods Simulator actually calls on a Scenario instance

From `grep -nE "scenario\.|scenarios\["` across simulator.py +
data_loader.py:

| Call site | What it does |
|---|---|
| `scenario_cls()` (no args) | construct from CSV row generator |
| `scenario.manager = self` | mutable attribute set |
| `scenario._setup(row)` | lifecycle: `setup()` → setattr from row → `load_data()` → `setup_data()` |
| `scenarios[0].copy()` | deep copy for per-run instances |
| `scenario.to_dict()` | logging |
| `scenario.id_run = id_run` | per-run mutable attribute |

### Methods our examples USE (vs ones Melodie offers)

Every `core/scenario.py` in our handcrafted examples is exactly:

    class FooScenario(Scenario):
        def setup(self):
            self.periods = ...
            self.foo = ...

That's it. We use `setup()` and inherit `__init__`. The other
machinery (`copy`, `to_dict`, `load_data`, `setup_data`,
`load_dataframe`, `load_matrix`, `to_json`, `initialize`,
`_parameters`) is called by Melodie's framework, never by user code.

### Minimum viable replacement surface

A standalone `abm_auto/runtime/_scenario.py` Scenario must provide:

```python
class Scenario:
    def __init__(self, id_scenario: int | str | None = 0):
        self.id = id_scenario
        self.id_run = -1
        self.run_num = 1
        self.period_num = 0
        self.manager = None       # set by framework
        self._parameters = []     # unused by us, kept for parity

    def setup(self) -> None:
        """User override."""

    def setup_data(self) -> None:
        """User override (optional)."""

    def load_data(self) -> None:
        """User override (optional)."""

    def _setup(self, data: dict | None = None) -> None:
        self.setup()
        if data is not None:
            for col_name, value in data.items():
                setattr(self, col_name, value)
        self.load_data()
        self.setup_data()

    def initialize(self) -> None:
        self._setup()

    def copy(self) -> "Scenario":
        import copy as _copy
        new = self.__class__()
        for k, v in self.__dict__.items():
            setattr(new, k, _copy.deepcopy(v) if k != "manager" else v)
        return new

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_") and k != "manager"}
```

~40 LoC. The `manager` reference is intentionally NOT deepcopied —
the framework re-assigns it after copy anyway, and deepcopying it
would walk the entire Simulator/DataLoader tree.

`load_dataframe`/`load_matrix` go to `manager.data_loader` — only
needed when a user model uses agent CSVs. None of our handcrafted
models do, but generated code might. Phase 1 ships stubs that raise
NotImplementedError with a helpful message; Phase 2/3 land real
versions when DataCollector / AgentList replacements arrive.

### Risk: `manager` is the Calibrator / Simulator / DataLoader

Setting `scenario.manager = self` works because the manager object
exposes `.data_loader`. When we eventually replace Simulator (Phase 4),
the new Simulator must keep the same `manager.data_loader` shape
(or our Phase 1 Scenario's `load_dataframe` will break). Document
the contract; don't fix it now.

### Byte-equal regression fixture

`tests/e2e/test_engine_phase1_baseline.py` (added this session)
captures the SIR handcrafted_model's `calibration_final_sim.csv` at
deterministic params (seed=42, fixed best_params). Phase 1 swap
must produce a byte-identical file or the test fails. Same approach
will land for the other domains as their phases arrive.

### Phase 1 code estimate (post-investigation)

- `abm_auto/runtime/_scenario.py`: ~40 LoC
- `abm_auto/runtime/__init__.py` seam swap: 1 line
- Unit tests: ~80 LoC (init defaults, copy semantics, _setup overrides,
  to_dict purity, manager not deepcopied)
- Reference fixture: already in place (this commit)

**Total: ~120 LoC of new code, 1 line of swap. Pick up in fresh session.**

### Remaining open questions

OQ#2 (cross-domain semantics): only relevant for Phase 4. Defer.

OQ#3 (Calibrator/Trainer usage): grep `from Melodie import` across
`abm_auto/` shows zero direct uses of Melodie.Calibrator or
Melodie.Trainer. Phase 5 likely becomes "remove from runtime/__init__.py
exports + check pipeline phases for indirect use" — half a day.
