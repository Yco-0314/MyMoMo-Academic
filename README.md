# abm-auto

[![Tests](https://github.com/Yco-0314/MyMoMo-Academic/actions/workflows/ci.yml/badge.svg)](https://github.com/Yco-0314/MyMoMo-Academic/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> 📖 中文文档:[README.zh.md](README.zh.md)

> Also known as **MyMoMo-Academic** — the repository / project name. `abm-auto` is the Python package and CLI; both refer to the same system.

**Autonomous Agent-Based Modeling Research Pipeline** — from natural language to simulation results in one command.

`abm-auto` is a fully autonomous ABM research system that takes a plain-text research scenario and produces executable simulations, parameter explorations, and academic-quality research reports — with zero human intervention.

## Quickstart

```bash
pip install abm-auto            # installs the `abm-auto` (and `mymomo`) CLI
abm-auto quickstart             # scaffold a starter .env + example story.md
# edit .env: set ANTHROPIC_API_KEY=...
abm-auto run story.md           # run the full autonomous ABM pipeline
```

## What's New (v0.3 — 2026-05-31)

10 commits across three thrusts: **dogfood coverage** (originate-mode +
Grid model + cross-domain CI), **calibration diagnostics** (α
trajectory features + β identifiability + ε execution verifier), and
**multi-fidelity calibration** infrastructure. Plus a 5-phase roadmap
([ADR-009](docs/decisions/ADR-009-engine-replacement-roadmap.md)) for
replacing the underlying Melodie engine.

Cross-domain lean CI now runs **three independent quality gates per domain**:

1. **MSE threshold** — calibration converged near truth
2. **β profile_likelihood** — parameters individually identifiable
3. **ε verify_execution** — qualitative direction matches story.md

Latest reproducible (`seed=42`) baseline:

| Domain | MSE | β | ε |
|---|---|---|---|
| SIR (virus) | 152 (≤200) | all identified | all match |
| Opinion (deffuant) | 0.025 (≤0.5) | all identified | all match |
| Schelling | 0.000 (≤0.5) | all identified | all match |

Total CI wall: ~6 min, ε auto-skips when `DEEPSEEK_API_KEY` is absent
(so fork PRs stay zero-LLM-cost).

Architectural changes:

- **Multi-fidelity calibration infrastructure** (`Fidelity` dataclass +
  `_run_mf_screen` scheduler) — coarse-to-fine sim budget split via
  `periods_scale`. Defaults OFF; lean per-sim wall is subprocess-bound
  so MF earns its keep only in expensive Pipeline contexts. See
  [ADR-008](docs/decisions/ADR-008-multi-fidelity-calibration.md).
- **α `trajectory_features` summary** — 4 shape features per target
  `[peak_tick, peak_val, final_val, mean]` (12-D vs 750-D
  `full_trajectory` on SIR). Cross-domain portable.
- **β `profile_likelihood` + `fisher_info_eigen`** in
  `abm_auto.calibration.identifiability_profile` — local
  identifiability diagnostics; markdown-renderable reports with FLAT
  detection. Closes ADR-006 OQ#3.
- **ε `verify_execution`** in `abm_auto.verification.execution_verifier`
  — LLM extracts qualitative claims from story.md, classifier diffs
  against actual sim trajectory. Catches mechanism-semantics bugs
  no MSE threshold catches.
- **Grid/Network contradiction validator** in CodegenPhase — catches
  originate-mode bug where LLM picks a network topology for an
  inherently-spatial model.
- **Originate-mode example** (`examples/originate_segregation_phenomenon/`)
  — phenomenon-only story that asks the system to PROPOSE the
  mechanism. Validates the dual-mode promise.

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

# 3. Run a calibration example end-to-end (virus-on-a-network SIR — ~5 min, ~$0.03)
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

[Apache License 2.0](LICENSE) — Copyright 2026 Cong Yu. See also [NOTICE](NOTICE).
