# Terminology

**Purpose**: Domain-specific vocabulary for ABM-Auto users and contributors.

**Target Audience**: Academic researchers (primary), developers (secondary), LLM agents (tertiary).

---

## Agent-Based Modeling (ABM)

### Core Concepts

**Agent-Based Model (ABM)**  
A computational model that simulates autonomous agents interacting in an environment to study emergent macro-level phenomena from micro-level rules.

**Agent**  
An autonomous entity with:
- **State variables** (attributes like age, wealth, health status)
- **Behavioral rules** (decision-making logic)
- **Interaction capabilities** (sensing neighbors, exchanging information)

**Emergence**  
Macro-level patterns that arise from micro-level agent interactions without being explicitly programmed. Example: traffic jams emerge from individual driving decisions.

**Heterogeneity**  
Variation among agents in attributes or behaviors. Contrasts with "representative agent" models that assume all agents are identical.

**Bounded Rationality**  
Agents use heuristics or local information rather than global optimization. Example: "move if >30% of neighbors are different" vs. "find globally optimal location."

---

### ABM Suitability Criteria

**Micro-Macro Structure**  
A model has distinguishable individual-level (micro) and population-level (macro) dynamics. Required for ABM.

**Interaction-Driven Dynamics**  
System behavior depends on agent-to-agent interactions (e.g., contagion, coordination, competition).

**Distributional Effects**  
Outcomes depend on the distribution of agent attributes, not just averages. Example: wealth inequality affects consumption patterns differently than mean wealth.

---

### ODD Protocol

**ODD (Overview, Design concepts, Details)**  
Standardized documentation format for ABM (Grimm et al. 2020). Required for academic publication.

**ODD Sections**:
1. **Purpose and Patterns** — Research question and validation targets
2. **Entities, State Variables, Scales** — What exists in the model
3. **Process Overview and Scheduling** — What happens each time step
4. **Design Concepts** — Emergence, adaptation, sensing, stochasticity, etc.
5. **Initialization** — Starting conditions
6. **Input Data** — External data sources (if any)
7. **Submodels** — Detailed algorithms for each process

**Reference**: Grimm, V. et al. (2020). The ODD Protocol for Describing Agent-Based and Other Simulation Models. *JASSS*, 23(2), 7. https://doi.org/10.18564/jasss.4259

---

## Sensitivity Analysis (SA)

### Core Concepts

**Sensitivity Analysis**  
Systematic exploration of how model outputs change when input parameters vary. Answers: "Which parameters matter most?"

**Parameter Space**  
The multidimensional region defined by all possible parameter combinations. Example: if `infection_rate ∈ [0.01, 0.1]` and `recovery_days ∈ [7, 21]`, the space is a 2D rectangle.

**Global Sensitivity Analysis**  
Explores the entire parameter space (vs. local SA, which perturbs one parameter at a time around a baseline).

---

### SALib Methods

**Morris Method (Elementary Effects)**  
Screening method that identifies influential parameters using randomized one-at-a-time perturbations.

- **Output**: μ* (mean absolute effect), σ (interaction strength)
- **Use case**: Initial exploration with limited budget (10-20 trajectories)
- **Interpretation**: High μ* → important parameter; high σ → strong interactions

**Sobol Indices**  
Variance-based method that decomposes output variance into contributions from each parameter and their interactions.

- **Output**: S1 (first-order index), ST (total-order index)
- **Use case**: Detailed analysis after Morris screening
- **Sample requirement**: N × (2D + 2), where N = base samples, D = parameters
- **Interpretation**: S1 = direct effect; ST - S1 = interaction effects

**Statistical Power**  
Probability of detecting a true effect. Low sample sizes → low power → unreliable indices.

**Sobol Convergence**  
Sobol indices stabilize as sample size increases. Rule of thumb: N ≥ 64 for D ≤ 10 parameters.

---

### ABM-Auto SA Configuration

**Default Mode** (budget-conscious):
- Morris: 10 trajectories
- Sobol: 32 base samples → 32 × (2D + 2) total runs

**Enhanced Mode** (`--enhanced` flag):
- Morris: 20 trajectories
- Sobol: 64 base samples → 64 × (2D + 2) total runs
- Includes statistical power warnings

---

## Mesa Framework

**Mesa**  
Python library for agent-based modeling. ABM-Auto generates Mesa-compatible code.

**Key Mesa Classes**:

**`mesa.Model`**  
Top-level simulation container. Holds the schedule, grid/network, and data collector.

**`mesa.Agent`**  
Base class for agents. Subclass to define custom agent types.

**`mesa.time.RandomActivation`**  
Scheduler that activates agents in random order each step (prevents order effects).

**`mesa.space.MultiGrid`**  
2D grid where multiple agents can occupy the same cell.

**`mesa.datacollection.DataCollector`**  
Records model-level and agent-level metrics during simulation.

**`mesa.batch_run()`**  
Runs multiple simulations with different parameter combinations (used for SA).

---

## ABM-Auto System

### Pipeline Phases

**Phase 1: Design**  
LLM converts `STORY.md` (research narrative) into `DESIGN.md` (structured specification).

**Phase 1b: ODD Protocol**  
LLM generates `ODD.md` from `DESIGN.md` using Grimm et al. (2020) format.

**Phase 2: Code Generation**  
LLM writes Mesa model code (`model.py`, `agent.py`, `run.py`) from `DESIGN.md`.

**Phase 3: Verification**  
Automated testing + LLM-driven debugging until code runs without errors.

**Phase 4: Execution**  
Run simulation with current parameters, collect metrics.

**Phase 5: Analysis**  
LLM interprets results, generates insights.

**Phase 6: Optimization**  
LLM proposes next parameter values based on memory context.

**Phase 6e: Citation Fetching** (optional)  
Query Semantic Scholar API for relevant papers based on `STORY.md` keywords.

**Phase 6f: Benchmark Comparison** (optional)  
Compare simulation results against original study data (if `--baseline` provided).

**Phase 7: Reporting**  
LLM synthesizes all iterations into academic manuscript (`REPORT.md`).

---

### Memory System

**Working Memory**  
Session-scoped state (current hypothesis, last run metrics). Max 20 entries, priority-pruned.

**Episodic Memory**  
Append-only log of all simulation runs (params → metrics → insights). JSONL format.

**Semantic Memory**  
Cross-experiment knowledge base (validated patterns, rules, anomalies). Max 200 entries, confidence-ranked.

**Token Budget**  
Allocation of LLM context window tokens to each memory tier (default: 500 working, 1500 episodic, 1500 semantic).

**Memory Ingestion**  
Process of recording run results into episodic memory and extracting patterns into semantic memory.

---

### Agents (LLM Roles)

**DesignAgent**  
Converts `STORY.md` → `DESIGN.md`.

**CoderAgent**  
Converts `DESIGN.md` → Mesa code.

**VerifierAgent**  
Tests code, fixes errors.

**AnalyzerAgent**  
Interprets simulation output.

**OptimizerAgent**  
Proposes next parameters.

**ReporterAgent**  
Synthesizes final manuscript.

**OddWriter**  
Generates ODD protocol.

**SensitivityAnalyzer**  
Orchestrates Morris/Sobol analysis.

**CitationFetcher**  
Queries Semantic Scholar API.

**BenchmarkComparator**  
Compares results against baseline data.

**ReviewerAgent**  
Peer-review simulation (optional, `--peer-review` flag).

**SanityChecker**  
Pre-run validation (agent count, CSV paths, grid consistency).

---

### File Artifacts

**`STORY.md`**  
User-provided research narrative (input).

**`DESIGN.md`**  
Structured model specification (Phase 1 output).

**`ODD.md`**  
ODD protocol documentation (Phase 1b output).

**`model.py`**  
Mesa model class (Phase 2 output).

**`agent.py`**  
Mesa agent classes (Phase 2 output).

**`run.py`**  
Simulation execution script (Phase 2 output).

**`SimulatorScenarios.csv`**  
Parameter configurations for batch runs.

**`REPORT.md`**  
Final academic manuscript (Phase 7 output).

**`workspace/`**  
Timestamped directory containing all artifacts for one experiment.

**`memory/`**  
Subdirectory in workspace containing `working.json`, `episodic.jsonl`, `semantic.json`.

---

## Statistical Concepts

**RMSE (Root Mean Squared Error)**  
√(mean of squared differences). Measures prediction accuracy (lower = better).

**MAPE (Mean Absolute Percentage Error)**  
Mean of |actual - predicted| / |actual| × 100%. Measures relative error.

**R² (Coefficient of Determination)**  
Proportion of variance explained by the model (0 = no fit, 1 = perfect fit).

**Pearson Correlation**  
Linear relationship strength between two variables (-1 to +1).

**Confidence Interval**  
Range likely to contain the true parameter value (e.g., 95% CI).

---

## Academic Publishing

**Working Paper**  
Early-stage manuscript shared for feedback before journal submission.

**Conference Paper**  
Peer-reviewed paper presented at academic conference (shorter than journal articles).

**Journal Article**  
Peer-reviewed paper published in academic journal (highest prestige).

**Preprint**  
Manuscript posted to public server (e.g., arXiv, SSRN) before peer review.

**Replication Study**  
Re-implementing a published model to verify results.

**Validation**  
Comparing model output against real-world data or theoretical predictions.

---

## Citation Management

**DOI (Digital Object Identifier)**  
Persistent identifier for academic papers (e.g., `10.18564/jasss.4259`).

**BibTeX**  
Plain-text citation format used by LaTeX (e.g., `@article{key, author={...}, ...}`).

**APA Format**  
Citation style from American Psychological Association (e.g., "Author, A. (2020). Title. *Journal*, 1(2), 3-4.").

**Semantic Scholar**  
Free academic search engine with API for citation data.

**CrossRef**  
DOI registration agency with metadata API.

---

## Software Engineering

**CLI (Command-Line Interface)**  
Text-based program interface (e.g., `abm-auto run story.md`).

**JSONL (JSON Lines)**  
Text format with one JSON object per line (easier for streaming and diffs than JSON arrays).

**Flat File Storage**  
Using plain files (JSON, CSV) instead of databases (SQLite, PostgreSQL).

**Token Estimation**  
Approximating LLM token count from text length (~3 characters per token for mixed CJK/English).

**Workspace**  
Isolated directory for one experiment's artifacts (prevents cross-contamination).

**Executor**  
Component that runs Python subprocesses with timeout and error capture.

---

## Abbreviations

| Term | Full Name |
|------|-----------|
| ABM | Agent-Based Model |
| ODD | Overview, Design concepts, Details |
| SA | Sensitivity Analysis |
| LLM | Large Language Model |
| API | Application Programming Interface |
| CLI | Command-Line Interface |
| CSV | Comma-Separated Values |
| JSON | JavaScript Object Notation |
| JSONL | JSON Lines |
| RMSE | Root Mean Squared Error |
| MAPE | Mean Absolute Percentage Error |
| DOI | Digital Object Identifier |
| APA | American Psychological Association |
| GVR | Generate-Validate-Refine loop |

---

## Pipeline Architecture Patterns

### Generate-Validate-Refine (GVR) Loop

A first-class module (`abm_auto/refinement.py`) that wraps any
**(generator, validator)** pair into a self-healing retry loop with
structured feedback. Added 2026-05-25 after benchmark runs revealed that
50%+ of pipeline failures were caused by single-shot LLM non-determinism
that a feedback-driven retry would have fixed.

The pattern has three roles:

- **Generator** — produces an artifact; accepts optional free-text feedback
  from the previous failed attempt. Example: `DesignAgent.run(extra_feedback=...)`.
- **Validator** — checks the artifact and returns a `ValidationOutcome`
  (ok, reasons, severity, structured). May be deterministic (rule check),
  LLM-based (semantic judge), or hybrid. Example: `ViabilityChecker.check`.
- **`refine()` orchestrator** — calls generator, calls validator, on failure
  feeds the reasons back into generator, repeats up to `max_iters`.

**Exhaustion policy**: `on_exhaust="continue_best"` returns the attempt with
the fewest failure reasons (best-so-far) and writes a HIGH audit issue.
`on_exhaust="halt"` returns `accepted=False` and lets the caller halt.

**Current adapters** (two — real seam, per architecture review):
1. `DesignerViability` — Phase 1+1c. Closes the most-frequently-failing gate.
2. `CoderVerifier` — Phase 2+3. Validator now BOTH runs the import dry-run AND
   enforces the Calibration Contract (see below).

**When to add a new adapter**: any phase where (a) the output comes from an
LLM and (b) acceptance criteria can be checked programmatically. Candidate:
`BayesianCalibrator + PosteriorQuality` (once posterior identifiability
metric is defined).

### Research Mode (Reproduce vs. Originate)

`ResearchSpec.mode` is detected once at Phase −1 by `ModeDetector` from
`story.md`. Downstream agents calibrate their thresholds and prompts:

- **reproduce** — story names a paper / classic model. Strict thresholds
  (≤ 5 AI-ASSUMPTION tags), prompt `phase1_design_reproduce.md` enforces
  source-priority extraction (story → lit_notes → paper-canonical → assumption).
- **originate** — story describes a phenomenon. Looser thresholds (≤ 15
  assumptions), prompt `phase1_design_originate.md` anchors on
  `hypothesis.md` from the upstream `HypothesisAgent`. WhatIfOracle runs
  only in this mode.

User can force mode via `--mode reproduce|originate` (overrides detection).

### Calibration Contract

`ResearchSpec.calibration_param_specs` is a list of
`{name, min, max, unit}` dicts extracted from story.md. Three downstream
contracts:

1. **Name contract** — `CoderAgent` injects param names into the codegen
   prompt as a hard constraint. Post-codegen, `_check_calibration_contract()`
   validates every spec param appears as a column in `SimulatorScenarios.csv`.
   Violation → routed back to CoderAgent through CoderVerifier GVR.
2. **Unit contract** — each spec carries the original unit ("percent",
   "probability", etc.). CoderAgent prompt forbids unit conversion (no
   silent percent→probability). Without this, downstream prior bounds end
   up 100× off truth.
3. **Range contract** — `BayesianCalibrator._infer_priors(spec_overrides=…)`
   uses spec `min`/`max` instead of CSV-inferred ±50% bounds. Decouples
   prior width from accidental CSV default values.

### Audit Ledger

`abm_auto/audit/ledger.py` — append-only event stream
(`audit_ledger.jsonl` + rendered `.md`). Every agent writes `info` /
`raise_issue` / `resolve` events tagged with phase + actor. Used by
ReviewerAgent and by debugging to see "who made which decision when".

Adopted by all 14 agents (Round 1A complete).

### LLM Provider Abstraction (`abm_auto/llm.py`)

Single `LLMClient` wraps either Anthropic SDK (Claude) or OpenAI SDK
pointed at DeepSeek's compatible endpoint. Selected by env var
`LLM_PROVIDER=anthropic|deepseek`. Adding a third provider = a third
branch in `LLMClient.__init__` — no caller changes needed.

### Calibration Benchmark Suite

Three scripts for measuring the calibration pipeline against BEHAVE 2025 Brescia
challenge ground truth (`virus_spread_chance=4.4`, `recovery_chance=0.3`,
`gain_resistance_chance=25.0`):

1. `benchmark_calibration_challenge.py` — full pipeline (story → DESIGN →
   code → sim → calibrate → MSE). Stress-tests the whole stack.
2. `benchmark_calibration_handcrafted.py` — bypasses codegen by injecting
   a hand-written SIR-on-network simulator. Isolates calibration math
   from codegen reliability.
3. `benchmark_calibration_stability.py` — runs (2) N times, reports
   variance. Tells us if calibration is reproducible vs RNG-flaky.

Score format: per-parameter relative error + BEHAVE 2025-formula MSE (mean of
squared errors across `susceptible`, `infected`, `resistant` columns,
averaged over aligned ticks).

---

## Related Documentation

- [ABM Suitability Guide](../abm_auto/knowledge/abm-suitability.md) — When to use ABM
- [Memory System](memory-system.md) — 3-tier architecture details
- [Pipeline Phases](pipeline-phases.md) — Workflow breakdown
- [ODD Protocol Template](../abm_auto/prompts/odd.md) — LLM prompt for ODD generation
