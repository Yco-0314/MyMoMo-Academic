# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) loosely.
Versions track architectural milestones, not pip releases.

## v0.2 — 2026-05-29

The "story → working calibrated model + report" promise now holds for the
codegen path (not just `--external-model` bypass). 19 commits across one
day landing 7 architectural seams + 1 major bug fix + 65 tests in CI.

### Added

- **Topology seam** (`abm_auto.runtime.topologies`) — 5 callable adapters:
  `watts_strogatz`, `barabasi_albert`, `erdos_renyi`,
  `netlogo_spatially_clustered` (algorithm-faithful), `melodie_named`.
  `Network.setup_agent_connections(topology=...)` replaces the old
  `network_type=str` string API. Determinism via `Network._rng` injected
  from `scenario.seed`. (276c1a9)
- **`MechanismSpec` schema + `TemplateGenerator`** — structured JSON
  contract between Phase 1d and Phase 2; 5 boilerplate files
  (`model.py`, `scenario.py`, `data_collector.py`, `main.py`,
  `SimulatorScenarios.csv`) emitted deterministically. CoderAgent's
  job narrows to `agent.py` + `environment.py`. See
  [ADR-007](docs/decisions/ADR-007-schema-driven-codegen.md). (6e65abe)
- **Two-stage MechanismExtractor** — Stage 1 emits free-form markdown
  pseudocode; Stage 2 (separate LLM call, non-reasoning model)
  emits ONLY structured JSON matching `MechanismSpec`. Resolves the
  single-prompt JSON-drop pathology. (421883b, 596c930)
- **Anti-pattern scanner** (`abm_auto.codegen.anti_patterns`) —
  19 regex catalog entries pre-execution scanning generated code for
  known LLM hallucinations (`WattsStrogatzNetwork`, `network_type=`,
  `agent.gen_num`, etc.). Wired as first validator in CodegenPhase
  GVR chain. (31a4aa6)
- **`Phase` Protocol + `PipelineContext`** —
  `abm_auto.pipeline.phase` decomposes the 522-LoC `Pipeline.run()`
  god method into 23 sequential `Phase` adapters in
  `abm_auto/pipeline/phases/`. Adding a phase = one new file + one
  line in `_build_phases()`. (6d195c1)
- **Calibrator `fit` / `fit_from_files`** — standalone API decoupling
  calibration from Pipeline LLM phases. Powers
  `benchmark_calibration_lean.py` (~3× faster regression bench than
  full Pipeline). (3c3c15c)
- **Nelder-Mead refinement seam** (`abm_auto.calibration.refiners`) —
  second stage after screening. scipy bounded NM with adaptive simplex.
  (993d139)
- **Closest-sample point estimate** for ABC/RF backends — replaces
  posterior-mean, which collapsed to prior midpoint at small budgets.
  (2a706bc)
- **Pluggable `SummaryStats` + `COLUMN_ALIASES`** —
  `full_trajectory` (default, sharp loss surface) replaces
  `mean_std_last`. `normalize_columns` bridges `count_s` ↔ `susceptible`
  naming conventions. (5238aab)
- **NetLogo headless oracle** (`abm_auto.verification.netlogo_oracle`) —
  Python wrapper around netlogo-headless.sh; parses BehaviorSpace v2
  tables. 30-rep fixtures committed at
  `tests/fixtures/netlogo/output/`. KS-test gate in
  `tests/test_topologies.py`. (42eb1fc)
- **Multi-seed observed.csv tool**
  (`abm_auto.verification.generate_observed`) — averages NetLogo oracle
  trajectories to lower the calibration noise floor. (e9ee96a)
- **Cross-domain calibration examples** — Deffuant opinion dynamics
  + Schelling segregation, proving the seams are domain-portable.
  (3d8a8ea, b4a8703)
- **CLI flag `--observed PATH`** — explicit observed data injection
  with `InjectObservedDataPhase`. Plus auto-resolve relative to
  `--story` directory. (5238aab, 35adc7d)
- **Memory feedback into CoderAgent** — `CoderAgent.run(..., memory_context=...)`
  mirrors `OptimizerAgent`'s memory wiring. Closes one half of the
  dead-write semantic memory issue. (596c930)
- **Observability in `SimulatorWrapper.simulate`** —
  `_log_failure(kind, detail)` makes silent failures visible in
  stdout. Records the failure-kind on `_last_failure_kind` for
  diagnostic inspection. (35adc7d)
- **CI pipeline** (`.github/workflows/ci.yml`) — runs `pytest tests/`
  on every push + PR. 65 tests covering topology / anti-pattern /
  mechanism_spec / template_generator. (421883b)
- **Nightly dogfood CI** (`.github/workflows/dogfood.yml`) — runs
  full codegen path on a daily schedule + on PRs touching
  prompts/agents/pipeline/codegen/calibration/runtime. Asserts
  exit 0 + MSE < 500. ~$1/month at DeepSeek pricing.
- **ADR-006** — calibration recovery (14× MSE improvement)
- **ADR-007** — schema-driven codegen via MechanismSpec + templates
- **Dogfood diagnostic infra** —
  `tests/e2e/dogfood_codegen_path.py`,
  `tests/e2e/diagnose_calibrator_zero_sims.py`,
  + 5 `docs/dogfood/*` reports preserving the observation chain.

### Fixed

- **Calibrator silent "0 successful sims" bug** — pandas dtype
  mismatch in `SimulatorWrapper.write_scenario_params` raised
  TypeError when assigning a float to an int64-inferred CSV column.
  `try/except` swallowed all 100 sample sims silently. Fix: widen
  column dtype before assignment. (35adc7d)
- **GROUND_TRUTH typo** — BEHAVE 2025 PDF prints `recovery_chance = 0.3`
  but observed.csv requires `recovery_chance ≈ 2.5` (math-implied).
  Now `GROUND_TRUTH_INFERRED` (2.5) vs `GROUND_TRUTH_AS_PRINTED` (0.3)
  exposed; scoring uses inferred. (c08ddba)
- **CJK font fallback** — `VisualizerAgent` runtime-detects available
  CJK fonts via `font_manager.fontManager.ttflist`. Eliminates the
  ~14 glyph warnings per `lang=zh` run. (596c930)
- **Reporter prompt** — injects calibration `param_units_block` +
  `iteration_constraint`. Stops Reporter from misreading percent as
  probability and hallucinating non-existent runs. (596c930)
- **Removed dead template stub** — `_render_initial_setup` LLM-FILL
  marker had no reader; CoderAgent didn't fill it. Replaced with
  `environment.initialize()` hook in template's `model.setup()`.

### Changed

- **`Pipeline.run()`** decomposed into 23 phase adapters.
- **Default summary statistic** for calibration: `full_trajectory`
  (was `mean_std_last`). Sharp loss surface enables NM convergence.
- **Default calibrator backend** preference: RF > PyMC > ABC.
  Two-stage screen+refine wraps all three.
- **MechanismExtractor** runs two LLM calls instead of one (Stage 1
  markdown + Stage 2 JSON). Stage 2 uses non-reasoning model.

### Removed

- Old `network_type=str` + `network_params=dict` API — replaced by
  `topology=topologies.<name>(...)` callable. (276c1a9)
- `_render_initial_setup` LLM-FILL marker — replaced by
  `environment.initialize()` hook.

### Empirical results

| Indicator | v0.1 | v0.2 |
|---|---|---|
| Calibration MSE (codegen path, BEHAVE virus) | crashed | **23.3** |
| Calibration MSE (lean path) | 1480 | **99 ± 59** |
| Pipeline god method | 522 LoC inline | **23 phase adapters** |
| Architectural seams | 0 | **7** |
| Anti-pattern catalog | 0 | **19 fixtures** |
| Test count | 0 | **65 (in CI)** |
| End-to-end "story → MSE" | broken | **works** |
