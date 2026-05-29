# abm-auto

**Autonomous Agent-Based Modeling Research Pipeline** — from natural language to simulation results in one command.

`abm-auto` is a fully autonomous ABM research system that takes a plain-text research scenario and produces executable simulations, parameter explorations, and academic-quality research reports — with zero human intervention.

## What's New (v0.2 — 2026-05-29)

19 commits landing the **codegen path end-to-end**. Until v0.2, the BEHAVE 2025 SIR story would crash mid-pipeline. Now: 5-minute wall, MSE 23, calibrated params within 22% of truth — with no manual intervention.

Architectural changes:

- **Pluggable Topology seam** (`abm_auto.runtime.topologies`) — `netlogo_spatially_clustered`, `watts_strogatz`, `barabasi_albert`, `erdos_renyi`, `melodie_named`. NetLogo "spatially-clustered-network" finally expressible.
- **Schema-driven codegen** — `MechanismSpec` (JSON contract) + `TemplateGenerator` (5 deterministic boilerplate files) replace LLM-written boilerplate. See [ADR-007](docs/decisions/ADR-007-schema-driven-codegen.md).
- **Calibration recovery** — MSE 1480 → 99 on the lean benchmark (14× improvement). Two-stage screen+refine, full-trajectory summary stats, pandas dtype fix, observability instrumentation. See [ADR-006](docs/decisions/ADR-006-calibration-recovery.md).
- **Pipeline decomposed** — 522-line god method → 23 `Phase` adapters in `abm_auto/pipeline/phases/`.
- **Anti-pattern validator** — `abm_auto/codegen/anti_patterns.py` catches 19 known LLM hallucinations pre-execution.
- **NetLogo headless oracle** + statistical fidelity tests.
- **3 calibration examples** (SIR + Opinion Dynamics + Schelling) proving the seams are domain-portable.

New CLI flags:

- `--observed PATH` — copy observed data into workspace for calibration
- `--external-model PATH` — bypass codegen, use prebuilt simulator

New benchmarks:

- `benchmark_calibration_lean.py` — 3-run regression bench, ~5 min wall (vs ~16 min via full pipeline)
- `benchmark_external_model.py` — validates pipeline minus codegen
- `tests/e2e/dogfood_codegen_path.py` — end-to-end codegen verification

Full history: [CHANGELOG.md](CHANGELOG.md).

## Architecture

```
story.md → [Design Agent] → [Code Agent] → [Verify & Fix Loop] → [Simulator]
                                                                       ↓
              [Report Agent] ← [Optimizer Agent] ← [Analyzer Agent] ← Results
```

**Core innovation**: LLM-driven autonomous research loop with self-healing code generation, sanity checking, sensitivity analysis, and cross-run memory.

### Pipeline Stages

1. **Design** — LLM reads story.md, produces DESIGN.md with agent specs, parameters, and ODD protocol
2. **Code Generation** — LLM generates complete Python simulation code from design
3. **Verification & Self-Healing** — Auto-compiles and fixes errors (up to 5 retry cycles)
4. **Execution** — Runs simulation using the MyMoMo Runtime ABM framework as runtime engine
5. **Sanity Checking** — Detects degenerate outputs (constant columns, no state transitions)
6. **Analysis** — LLM interprets CSV results, extracts insights
7. **Parameter Optimization** — LLM proposes hypothesis-driven parameter changes
8. **Iteration** — Repeats run→analyze→optimize cycle N times
9. **Sensitivity Analysis** — Optional SALib Morris/Sobol analysis
10. **Report Generation** — Produces structured research report

## Quickstart

```bash
# 1. Install
cd abm-auto
uv sync

# 2. Set your API key (Claude or DeepSeek)
cp .env.example .env
# Edit .env: ANTHROPIC_API_KEY=sk-ant-...
#       or: DEEPSEEK_API_KEY=sk-... + LLM_PROVIDER=deepseek

# 3. Run a calibration example end-to-end (BEHAVE 2025 SIR — ~5 min, ~$0.03)
uv run abm-auto run examples/calibration_challenge_virus/story.md \
    --mode reproduce \
    --no-lit-review \
    --iterations 2 \
    --observed examples/calibration_challenge_virus/observed.csv

# 4. Skip codegen, use a prebuilt simulator (for benchmarking calibration alone)
uv run abm-auto run examples/calibration_challenge_virus/story.md \
    --external-model examples/calibration_challenge_virus/handcrafted_model \
    --observed examples/calibration_challenge_virus/observed.csv

# 5. Iterate on calibrator quickly (fast feedback loop, no LLM)
uv run python benchmark_calibration_lean.py 3
```

## Usage

```bash
# Basic run
abm-auto run story.md

# English paper output with more iterations
abm-auto run story.md --lang en --iterations 5

# With literature notes for context
abm-auto run story.md --lit-notes lit_notes.md

# Resume optimization on existing workspace
abm-auto optimize workspace/20241201_143022_abc123/ --iterations 2

# Ingest NetLogo models
abm-auto ingest-netlogo ~/models/Virus.nlogo -o examples/virus/story.md

# Fetch models from CoMSES Computational Model Library
abm-auto ingest-comses "opinion dynamics" -n 5 -o examples/opinion/
```

## Model Ingest

`abm-auto` can automatically convert models from external sources:

- **NetLogo** (.nlogo/.nlogox) — Parses code, sliders, plots, and documentation into story.md
- **CoMSES** (comses.net API) — Fetches model metadata and generates story.md

## Validated Models

The pipeline has been tested on **50 models** across 15+ domains:

| Domain | Example Models | Success Rate |
|--------|---------------|--------------|
| Epidemiology | SIR, Virus, HIV, Virus on Network | 100% |
| Ecology | Wolf Sheep, Rabbits Grass, Daisyworld | 100% |
| Social Science | Segregation, Ethnocentrism, Voting, Rebellion | 100% |
| Economics | Wealth Distribution, Sugarscape, Hotelling's Law | 100% |
| Game Theory | PD Evolutionary, Minority Game, Public Goods | 100% |
| Network Science | Small Worlds, Preferential Attachment | 100% |
| Opinion Dynamics | Bounded Confidence, Axelrod Culture | 100% |
| Collective Behavior | Flocking, Ants, Termites, Slime | 100% |

## Project Structure

```
abm_auto/
├── agents/          # LLM agent modules (designer, coder, verifier, analyzer, ...)
├── analysis/        # Trajectory analysis, sensitivity analysis
├── ingest/          # NetLogo & CoMSES model converters
├── memory/          # Cross-run insight memory store
├── prompts/         # LLM prompt templates
├── runner/          # Workspace management & simulation executor
├── pipeline.py      # Main orchestrator
└── cli.py           # CLI entry point

runtime_templates/   # Simulation code templates (MyMoMo Runtime framework)
examples/            # 50+ validated model scenarios
```

## Configuration

Environment variables (`.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | API key for Claude | required |
| `ANTHROPIC_BASE_URL` | Custom API endpoint | Anthropic default |
| `ABM_MODEL` | Model for standard agents | claude-sonnet-4-6 |
| `ABM_STRONG_MODEL` | Model for design/code/report | claude-sonnet-4-6 |

## License

MIT
