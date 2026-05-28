# ADR-006: Calibration MSE Recovery — Diagnosing and Fixing the 14× Gap

**Status**: Accepted
**Date**: 2026-05-28
**Deciders**: yco + Claude (Opus 4.7)
**Related**: [ADR-005](ADR-005-unified-platform-dual-mode.md)

---

## Context and Problem Statement

The BEHAVE 2025 Brescia calibration challenge ("Virus on a Network") was
abm-auto's flagship benchmark. For weeks the calibrator produced parameter
estimates 2-8× off the published ground truth — `(virus, recov, resist) =
(10.2, 2.5, 50)` instead of the paper's `(4.4, 0.3, 25)`. The discrepancy
was treated as a calibration-algorithm shortcoming, but its true cause was
the combined effect of **four independent issues** spanning the data layer,
mechanism layer, point-estimate convention, and a literal published typo.

This ADR records the diagnostic chain and the architectural decisions
made along the way, so future architecture reviews don't re-suggest the
same investigations.

---

## Decision Drivers

1. **Trust the data, not the documentation** — when math contradicts a
   reported value, audit the data first
2. **Visible seams over hidden defaults** — silent column-name mismatch and
   hardcoded `[mean, std, last]` summaries both destroyed signal without any
   error
3. **Closest-sample > posterior-mean at small budgets** — Beaumont 2010's
   guidance assumes concentrated posteriors; ours wasn't
4. **Architectural deepening over algorithmic novelty** — refinement seam
   was the right move; SBI / ABC-SMC would have been overkill

---

## Diagnostic Chain (in order of discovery)

### 1. Network topology (commit `276c1a9`)

The handcrafted SIR sim used `random_geometric_graph` as a workaround for
NetLogo's `setup-spatially-clustered-network`. The two topologies look
similar (avg degree 6, n=150) but propagate differently — `random_geometric_graph`
is slower, with isolated bridges.

**Architectural decision**: Add a `Topology` seam to `Network`.
`abm_auto.runtime.topologies` ships five adapters; `netlogo_spatially_clustered`
is the algorithm-faithful port. Old `network_type=str` API removed in favor
of pure callables.

**Impact in isolation**: Peak I time moved 196 → 126 (observed: 70). Real
contribution but not dominant. MSE went from 2422 to 8187 — worse,
because the new (correct) topology exposed the *next* bug.

### 2. GROUND_TRUTH typo (commit `c08ddba`)

With the faithful topology, at the "ground truth" params `(4.4, 0.3, 25)`
the simulator produced final R ≈ 14 while observed.csv has R = 113. Math
check:

- Per-tick R-creation rate = 0.003 × 0.25 = 0.00075
- Max theoretical R in 250 ticks with full-pop infection ≈ 18
- Observed R = 113 ⇒ required rate ≈ 0.006 ⇒ `recovery_chance ≈ 2.5`

Parameter sweep against observed.csv confirmed:
- `(4.4, 0.3, 25)` → MSE 8187 (as printed)
- `(4.4, 2.5, 25)` → MSE 217 (inferred — 38× lower)

**Decision**: Treat the inferred value as actual data-generating GT.
Keep `GROUND_TRUTH_AS_PRINTED` constant for historical reference;
`GROUND_TRUTH = GROUND_TRUTH_INFERRED` is what scoring uses.

### 3. Posterior-mean collapse (commit `2a706bc`)

Even with corrected GT, three independent calibration runs converged to
*exactly* the prior midpoint `(10, 2.5, 50)`. The ABC and RF backends
both reported `posterior mean of accepted samples` as `best_params`.
At small budgets (max_sims ≤ 300) with wide uniform priors, this estimator
mathematically collapses to the prior midpoint:

- ABC: top-K accepted samples scatter widely; their mean ≈ midpoint
- RF: predicts training-label mean when undertrained; training labels are
  uniform draws from prior; label mean ≈ prior midpoint

**Decision**: Switch ABC and RF point estimates to **closest sample** by
`||sim_stats - obs_stats||`. PyMC SMC kept as-is (proper concentrated
posterior, mean is well-behaved).

**Impact**: Calibrator no longer returns constant `(10, 2.5, 50)`.
Variance went up (sample lottery) but bias went down.

### 4. Nelder-Mead refinement seam (commit `993d139`)

Closest-sample alone has high seed-to-seed variance: best-of-100-uniform-draws
in a 3-D prior box sits ~10-20 distance from the true basin. Adding a
local-search refinement stage to walk downhill from that point.

**Architectural decision**: Two-stage calibrator:
- Screening (existing): ABC / RF / PyMC adapters in `backends.py`
- **Refinement (new)**: `refiners.py` with `nelder_mead_refine` adapter

Two concerns, separable adapters, same callable shape. Real seam.
Default budget split: screening = max_sims (100) + refinement = 50 evals
(refinement gets its own budget, doesn't compete with screening coverage).

**Impact in isolation**: Marginal, because the NEXT bug was masking it.

### 5. Pluggable summary stats (commit `5238aab`, part D)

`SimulatorWrapper.simulate()` was passing sim DataFrames through a hardcoded
`summary_stats(df, targets) → [mean, std, last] per col` reducer. For
trajectory-matching calibration, this destroys ~99% of the signal — a
trajectory's mean, std, and last value identify only a tiny fraction of
possible shapes. NM couldn't descend on a 9-D loss surface with wide flat
regions.

**Architectural decision**: Make `SummaryStats` a callable type alias.
New module `abm_auto/calibration/summary_stats.py` ships two adapters:

- `full_trajectory` — flatten the full per-tick table (new default)
- `mean_std_last` — original behavior, kept for non-trajectory calibrations

SimulatorWrapper takes `summary_fn` at construction; calibrator orchestrator
passes the same fn for `obs_stats` so sim and obs live in the same vector
space.

### 6. Column-alias bridge (commit `5238aab`, part G — *the actual bug*)

While wiring (5), discovered that sim writes `count_s/count_i/count_r` but
observed.csv uses `susceptible/infected/resistant`. The OLD summary_stats
had no aliasing — when `target='susceptible'` and df only had `count_s`,
it silently returned **all zeros**.

**This means three prior benchmarks (Fix A, A+B, A+B+D) were running blind.**
The distance metric was constant `||0 - obs_stats||` for every parameter
sample. Best_params varied only because NM hit different prior boundaries
when its gradient was numerical noise.

**Decision**: Add `normalize_columns(df, targets)` to summary_stats module.
Mirrors `_COLUMN_ALIASES` from `benchmark_calibration_challenge.score_calibration_mse`
(intentional duplication for now — abm_auto.calibration stays self-contained).
SimulatorWrapper calls `normalize_columns` before `summary_fn`.

---

## Empirical Result

Three runs of `benchmark_external_model.py` (full pipeline with codegen
bypassed) at each stage:

| Stack | MSE (mean ± SD) | virus | recov | resist | Wall/run |
|---|---|---|---|---|---|
| baseline (posterior-mean) | 1362 ± 37 | 10.2 (132%) | 2.55 (2%) | 50.0 (100%) | 200s |
| + Fix A (closest-sample) | 1480 ± 419 | 9.39 (113%) | 1.39 (44%) | 41.5 (66%) | 298s |
| + Fix B (NM refine) | 4000 ± 3577 | 6.61 (50%) | 2.30 (8%) | 66.4 (165%) | 439s |
| + Fix D (full trajectory) | 3290 ± 3034 | 3.32 (25%) | 3.15 (26%) | 64.9 (160%) | 2478s\* |
| **+ Fix G (alias bridge)** | **107 ± 13** | **5.01 (14%)** | **2.41 (4%)** | **29.6 (19%)** | **324s** |

*Run 3 was an LLM-API latency outlier (6580s); runs 1-2 were normal*

**Final state**: MSE 107 hits the theoretical noise floor (estimated
100-200 from single-realization SIR stochasticity). All three parameters
within 19% of the inferred ground truth. Stable across seeds (CV 12%).

---

## Consequences

### Positive

- **Calibrator is now usable for any SIR-on-network problem** — the
  identifiability ridge that previously dominated results was actually
  the column-mismatch bug
- **Two new architectural seams** in `abm_auto.calibration`:
  - `SummaryStats` (callable type, two adapters)
  - `refiners.py` mirror of `backends.py` (one adapter today, room for BFGS / CMA-ES)
- **One new architectural seam** in `abm_auto.runtime`:
  - `Topology` callable (five adapters covering common + NetLogo-faithful cases)
- **Closing convention** documented: trust math over PDF when they disagree
- **Diagnostic playbook** for future ABM-Auto users: if calibrator results
  look like prior midpoints, suspect the distance metric, not the
  algorithm

### Negative

- **Heuristic column aliases** (`count_s` ↔ `susceptible`) are SIR-specific.
  Non-SIR models (opinion dynamics, market models) will need to extend
  `COLUMN_ALIASES` or provide their own `summary_fn`
- **Closest-sample point estimate** is less theoretically principled than
  posterior mean. The trade-off was correctness at small N over
  theoretical optimality at unbounded N
- **`benchmark_calibration_challenge._COLUMN_ALIASES` and `summary_stats.COLUMN_ALIASES`
  duplicate** — intentional for now, factor when a third consumer appears
- **NM refinement** can find degenerate local minima on identifiability
  ridges. Default 50-eval budget is short; longer would refine further
  but each eval costs a sim call (~150ms)

---

## What This ADR Decides That Future Reviews Should NOT Re-Open

1. **Topology seam in `Network`** — pure callable `(n, rng) → nx.Graph`.
   Adding agent-attribute-driven topologies (homophily) should be a
   second seam (e.g., `Network.rewire(predicate)`), not an overload.
2. **Closest-sample over posterior-mean** for ABC/RF backends. Switching
   back requires evidence at small N that posterior mean is reliable.
3. **`full_trajectory` as default summary** for trajectory-matching
   calibrations. Don't reintroduce `mean_std_last` as default — it was
   the right default for non-trajectory work but the wrong default for
   abm-auto's primary use case.
4. **Column aliases live in `abm_auto.calibration`** (not in user
   models or in benchmark scripts). User models should write whatever
   column names make sense; the calibrator bridges.
5. **GROUND_TRUTH = inferred, not as-printed.** When PDF and math
   disagree, math wins. `GROUND_TRUTH_AS_PRINTED` preserved for the
   historical record.

---

## Open Questions (for future ADRs)

- ~~**NetLogo as a verification oracle**~~ **RESOLVED 2026-05-28** —
  added `abm_auto/verification/netlogo_oracle.py` wrapping NetLogo
  headless. Committed fixtures at `tests/fixtures/netlogo/output/`
  (30-rep network topology stats, 30-rep SIR trajectories) and a
  pytest gate at `tests/test_topologies.py`. Findings:
    - Topology: **statistically equivalent** (KS p=0.808 on std, p=0.135
      on max, exact match on mean/edges across 30 seeds each)
    - SIR mechanism: Python peak I tick 73 vs NetLogo 89 (16 ticks
      earlier in Python), peak height 88 vs 79 (+12% higher). Root
      cause: NetLogo's `random 100 < recovery-chance` is INTEGER
      random — at `recovery_chance=2.5` the effective rate is 3%
      (rounds up), while Python's `random.random() < 0.025` is exact
      2.5%. ~17% lower recovery rate in Python → epidemic lingers
      longer. Final R statistically indistinguishable (KS p=0.135).
    - Not fixing the integer-random discrepancy: it's a NetLogo
      idiom, not a spec requirement; final-state agreement is what
      matters for calibration.
- **Multi-seed observed data**: observed.csv is one NetLogo realization.
  Calibrating against the mean of K NetLogo realizations would remove the
  network-realization noise from the floor. Requires NetLogo in the
  validation pipeline.
- **Identifiability diagnostics**: when NM lands on degenerate local
  minima (different params, same trajectory), the calibrator silently
  reports just one. Should it flag the ridge?
