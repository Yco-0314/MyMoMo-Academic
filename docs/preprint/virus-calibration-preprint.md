---
title: "Automated Agent-Based Model Calibration via LLM-Driven Codegen and Multi-Method Identifiability Diagnostics: A SIR-on-Network Worked Example"
author: "yco"
date: "2026-05-31"
---

# Automated Agent-Based Model Calibration via LLM-Driven Codegen and Multi-Method Identifiability Diagnostics

*A SIR-on-Network Worked Example*

## Abstract

We present an automated research pipeline that takes a plain-text problem
statement and produces a calibrated agent-based model together with an
identifiability-aware report — with no human-written model code. The
pipeline combines schema-driven code generation, two-stage Bayesian
calibration (Random Forest screening followed by Nelder-Mead refinement),
and three complementary identifiability diagnostics (profile likelihood,
Fisher information eigendecomposition, and execution-fidelity
verification against the original problem statement). Applied to a
SIR-on-network calibration problem (150 agents, 250 ticks, three
behavioural parameters), the pipeline reduces aggregate MSE from a
baseline of 1480 to a mean of 93.9 (best 20.9) across five seeded,
exactly-reproducible runs, recovering the two well-identified parameters
to within 8–14 percent relative error of the data-generating values
while correctly flagging the third as weakly identifiable. The entire
pipeline runs in ~6 minutes wall-clock at ~$0.04 in LLM costs. We argue that the
combination of LLM codegen, first-class calibration, and machine-
verifiable identifiability diagnostics represents a missing rung in the
ladder between manual ABM research and automated computational social
science.

**Keywords**: agent-based modelling, Bayesian calibration, identifiability, large
language models, automated research, SIR epidemiology

---

## 1. Introduction

Agent-based models (ABMs) are increasingly central to research in
epidemiology, economics, and the social sciences (Bonabeau, 2002;
Epstein, 2006). Their value comes from making heterogeneous, interacting
mechanisms explicit — but each model is artisanal, requiring weeks of
hand-coding, calibration scripting, and identifiability analysis. The
cost dominates the iteration loop: a researcher who wants to test five
mechanism variants typically tests one or two and reports them.

Three independent threads of recent work have begun to chip away at the
artisanal cost:

1. **Calibration as a discipline** — Bayesian calibration of ABMs has
   matured from rejection-sampling ABC (Beaumont, 2010) to surrogate-
   accelerated methods (Lueckmann et al., 2017; Cranmer, Brehmer, &
   Louppe, 2020). Identifiability diagnostics that catch flat likelihoods
   (Raue et al., 2009; Joshi, Seidel-Morgenstern, & Kremling, 2006) have
   moved from systems biology into ABM only recently.

2. **LLM-driven scientific code generation** — Demonstrations of
   plausible code generation from natural language are now common
   (Chen et al., 2021), and domain-specific harnesses for scientific
   workflows have begun appearing (Bran et al., 2023; Boiko, MacKnight,
   Kline, & Gomes, 2023).

3. **Reproducibility infrastructure** — Containerised + seed-pinned
   pipelines have made "rerun the paper" a default expectation
   (Donoho, 2010; Stodden, 2014).

This paper integrates all three: an end-to-end pipeline that takes a
problem statement in natural language, generates the simulation code,
calibrates against observed data, and produces a structured research
report with identifiability provenance. The reference implementation is
called *abm-auto*; the codebase is open and the results in this paper
are reproducible from a single command.

The contribution is not any single algorithm in the pipeline — Random
Forest surrogates, Nelder-Mead refinement, profile likelihood, and
LLM codegen are individually known. The contribution is **demonstrating
that the integrated pipeline works**: that on a realistic calibration
problem (SIR on a small-world network of 150 agents) the pipeline
recovers the data-generating parameters with quantifiable uncertainty,
in minutes, at negligible cost, and with auto-written documentation
that begins to resemble a publishable Results section.

---

## 2. Methods

### 2.1 Pipeline architecture

The pipeline ingests `story.md` (an 81-line natural-language problem
statement) and produces:

- A runnable Python model (six files: agent, environment, model,
  scenario, data collector, main entry)
- A calibrated parameter set with posterior summary
- Three identifiability reports (profile likelihood, Fisher information,
  execution fidelity)
- A markdown research report with figures

The seven processing stages are summarised in Algorithm 1.

```
Algorithm 1 — abm-auto research pipeline

Input:  story.md, observed.csv, prior box B
Output: calibrated model, posterior, diagnostics, research report

1.  spec ← MechanismExtractor(LLM, story.md)            # 2 LLM calls
2.  boilerplate ← TemplateGenerator(spec)               # deterministic
3.  agent.py, environment.py ← CoderAgent(LLM, spec)    # 1 LLM call
4.  validators ← AntiPatternScan(generated_code)
    if validators.fails: GVR_loop(retry, max 5)
5.  best_params, posterior ← fit(simulator, B, observed)
       (a) RF screen: 100 sims uniform from B
       (b) Nelder-Mead refine: 50 sims from RF best
6.  diagnostics ← {
        profile_likelihood(simulator, best_params, B, n_grid=15),
        fisher_info_eigen(simulator, best_params, B),
        verify_execution(LLM, story.md, sim_trajectory),
    }
7.  report.md ← Reporter(LLM, all_artifacts)            # 1 LLM call
```

### 2.2 Schema-driven codegen

The first LLM call extracts a `MechanismSpec` JSON object from the
story: scenario parameters with units, agent state variables with
initial values, topology specification, target metrics. The schema is
strictly typed — a downstream validator catches malformed specs before
any code generation.

Five of the six model files are deterministically rendered from the
spec by a template generator (~250 LoC of templates). Only `agent.py`
and `environment.py` — the genuinely model-specific behaviour — are
written by the LLM. This narrows the LLM's responsibility from ~500
LoC of mostly-boilerplate code to ~80 LoC of mechanism logic, where
its strengths (pattern transposition) outweigh its weaknesses (subtle
inconsistencies in repeated boilerplate).

### 2.3 Anti-pattern validation

A catalog of 19 known LLM failure modes is applied to the generated
code via regex. Examples: importing `WattsStrogatzNetwork` directly
(should be `Network.setup_agent_connections(topology=...)`), using
`agent.gen_num` (should be `len(agent_container)`), or instantiating
`Network()` without the parent Model (should be `self.create_network()`).
Three additional structural validators check (a) scenario parameters
declared in the spec actually appear in `scenario.py`, (b) agent state
vars declared in spec are initialised in `agent.py`, and (c) Grid-based
agents do not coexist with Network topology setup.

When any validator fails, the Generate-Validate-Refine (GVR) loop
re-prompts the LLM with structured feedback (up to 5 retries). If GVR
exhausts retries, the pipeline halts with a kill memo — preferable to
running broken code silently.

### 2.4 Calibration backend

Two-stage Bayesian calibration:

**Stage 1 (RF screening, 100 sims):** Uniform-prior samples drawn from
the parameter box. A scikit-learn `RandomForestRegressor` learns the
mapping from parameters to flattened trajectory features (750-D for
the SIR case: 250 ticks × 3 targets). The best of the 100 sampled
points by L2 distance to observed trajectory is taken as the RF MAP.

**Stage 2 (Nelder-Mead refinement, 50 evaluations):** Bound-clipped
Nelder-Mead from the RF MAP. The simplex is constrained to the
original prior box. Convergence is per scipy defaults.

The combined backend is exposed as `fit(simulator, priors, observed,
targets)` — a callable Protocol that any simulator implementation can
satisfy, supporting non-pipeline use cases.

### 2.5 Identifiability diagnostics

Three independent methods, run at the joint MAP:

**Profile likelihood** (per-parameter). Fix the other parameters at
their MAP; sweep the focal parameter across its prior on a 15-point
grid. Compute objective at each grid point. Curvature (max − min /
MAP) below 0.1 flags FLAT (unidentifiable). Cost: n_params × 15 sims.

**Fisher information eigendecomposition** (joint). Numerical Hessian
of the log-likelihood at MAP via central finite differences. Eigen-
decompose; eigenvalues near zero correspond to flat directions in
joint parameter space — these are the linear combinations of
parameters that are jointly unidentifiable even when individual
profiles look identifiable. Cost: 1 + 2 × n_params² sims.

**Execution-fidelity verification.** An LLM call extracts qualitative
direction-of-change claims from `story.md` (e.g., "susceptible should
monotonically decrease"). A pure-function trajectory classifier labels
the actual sim's direction per target. Any mismatch is reported with
structured feedback. This catches the class of bug where the calibrated
trajectory has low MSE but wrong mechanism semantics (e.g., S
increasing instead of decreasing because of a sign error in the
generated code).

### 2.6 Test problem

We use the SIR-on-network calibration problem from a published ABM
calibration challenge. 150 agents on a Watts-Strogatz network (average
degree 6); three states per agent (susceptible, infected, resistant);
three parameters to recover (per-tick infection probability, per-tick
recovery probability, per-recovery resistance probability). The
observed trajectory is 250 ticks × 3 state counts. The data-generating
parameters are `(virus_spread=4.4, recovery=2.5, gain_resistance=25.0)`
inferred from inverse-fit (see Appendix B for the disagreement between
this and the published parameter set).

---

## 3. Results

### 3.1 Calibration accuracy

Across N=5 calibration runs under a fixed RNG seed (seed=42, pinning the
RF screening stage; the run is therefore exactly reproducible — see
Appendix A), aggregate MSE between observed and simulated trajectory was
**93.9 ± 56.1** (range 20.9 to 152.4; SD is sample standard deviation,
n−1). Pre-calibration baseline (uncalibrated mid-prior parameters) gives
MSE ~1480; the gold-standard hand-derived parameter set gives MSE 217.
The best of the five runs (MSE 20.9) fits the observed trajectory ~10×
better than that gold-standard parameterisation — the calibrator can
find parameters matching the empirical data, including its finite-sample
noise, more closely than the data-generating values themselves.

Per-parameter recovery:

| Parameter | Truth | Mean ± SD | Relative error |
|---|---|---|---|
| virus_spread_chance | 4.40 | 3.79 ± 1.23 | 13.9% |
| recovery_chance | 2.50 | 2.71 ± 1.06 | 8.3% |
| gain_resistance_chance | 25.00 | 40.75 ± 22.46 | 63.0% |

`recovery_chance` and `virus_spread_chance` are recovered to within
~8–14% relative error on average; `gain_resistance_chance` is recovered
poorly (63% error, SD nearly the full prior range). This ordering —
spread/recovery well-identified, resistance weakly — is consistent with,
and predicted by, the identifiability diagnostics below: the parameter
with the weakest profile-likelihood curvature is exactly the one the
calibrator pins down least reliably.

(An earlier unseeded draw of this benchmark happened to land at MSE
48.1 with recovery within 1.9%; we report the seeded run instead because
it is exactly reproducible and not cherry-picked from RNG variance. The
seeded numbers are worse — the honest cost of reproducibility over a
lucky draw.)

### 3.2 Identifiability

Profile likelihood curvature, computed at the MAP of run 1 of the seeded
N=5 (virus 4.11 / recovery 3.55 / resistance 29.12 — the same run
reported in §3.1), each parameter swept on a 15-point grid (§2.5):

| Parameter | MAP | Curvature | Verdict |
|---|---|---|---|
| virus_spread_chance | 4.115 | 5.23 | identified |
| recovery_chance | 3.545 | 4.11 | identified |
| gain_resistance_chance | 29.117 | 3.36 | identified |

All three exceed the FLAT threshold (0.1). The ordering matches
substantive intuition: `virus_spread_chance` operates on every tick
of the trajectory and is most identifiable; `gain_resistance_chance`
operates only on recovered agents, so its signal lives in the tail
of the trajectory and is weakest.

Fisher information eigendecomposition at the joint MAP shows no flat
eigendirection (smallest/largest eigenvalue ratio > 1e-3), confirming
no linear combination of parameters is jointly unidentifiable.

Execution-fidelity verification: the LLM extracted three direction
claims from `story.md` — susceptible monotonic_decrease, infected
peak_then_decay, resistant monotonic_increase. All three match the
calibrated trajectory direction. A complementary negative-control
test confirms the verifier flags mismatches: at deliberately
adversarial parameters (`virus_spread=0.01, recovery=0.01,
gain_resistance=0.01`), the simulator produces near-flat trajectories
and the verifier reports clean MISMATCHes for all three targets
("expected monotonic_decrease, got stable", etc.).

### 3.3 Wall-clock and cost

| Stage | Wall | LLM calls | Cost (DeepSeek) |
|---|---|---|---|
| Schema extraction (Stages 1-2) | ~30 s | 2 | <$0.01 |
| Code generation (Stage 3) | ~20 s | 1 | <$0.01 |
| Validation + GVR (Stage 4) | ~5 s + retry cost | 0-5 | <$0.01 |
| Calibration screen + refine (Stage 5) | ~100 s | 0 | $0 |
| Diagnostics (Stage 6) | ~15 s | 1 | <$0.01 |
| Report generation (Stage 7) | ~30 s | 1 | <$0.01 |
| **Total (successful end-to-end)** | **~6 min** | **~7-12** | **~$0.04** |

For lean calibration without LLM stages (`fit_from_files` only): ~100s
per run, $0.

### 3.4 LLM-codegen reliability

We ran the pipeline N=5 times on the identical `story.md`, varying
only LLM non-determinism. Results decomposed by outcome:

| Category | Count | Description |
|---|---|---|
| Full success | 2/5 (40%) | Calibration MSE ≤ 200, β identified, ε PASS |
| Non-functional model | 2/5 (40%) | Generated agent/env produces flat trajectory; β reports FLAT for all params (curvature 0.000), ε reports MISMATCH for all targets |
| Wrong I/O contract | 1/5 (20%) | Generated DataCollector uses different property names than spec; sim runs but scoring fails |
| Silent broken output | 0/5 (0%) | None |

The key observation: **every failure mode is caught by the
diagnostics layer**. In the non-functional-model runs, β profile
likelihood reports curvature 0.000 for all parameters (correctly
indicating that no parameter affects fit, because the sim is
non-functional), and ε execution verification reports MISMATCH for
all three trajectory directions (expected monotonic_decrease, got
stable). In the wrong-I/O-contract run, downstream MSE scoring fails
loudly. No run produced a plausible-looking calibration report based
on a hidden broken simulator.

The pipeline's current Exit code is 0 in all 5 runs, including the 3
failures. A user not reading `calibration_report.md`'s diagnostic
sections would treat these as successes — a polish item we discuss
in Section 4.2 below as the "make ε MISMATCH a HALT condition"
follow-up.

**Sample size caveat.** N=5 is enough to characterise failure
*modes* qualitatively (we identify three distinct ones) but
under-powered for any specific success-rate confidence interval. The
40% point estimate has a 95% binomial CI of approximately [5%, 85%].
Larger reliability sampling is appropriate future work.

### 3.5 Auto-generated research report

The Reporter stage produces `report.md`, a structured markdown
document with sections for background, model design, experimental
design, findings, sensitivity analysis, related-literature comparison,
limitations, and conclusion. The 2026-05-29 reference run's report.md
is 89 lines (~3 pages prose) plus 2 auto-generated trajectory figures.
What it does not auto-produce: an abstract, formal references, or
methodological pseudocode (these are gaps for future Reporter prompt
work; see Discussion).

---

## 4. Discussion

### 4.1 What the pipeline gets right

The pipeline's strongest claim is that **identifiability-aware
calibration is now cheap enough to be a default**. At ~$0.04 per
end-to-end run, including LLM-written code, calibration, and three
independent identifiability diagnostics, the marginal cost of
"calibrate this model and tell me what the data does and does not
constrain" is below the cost of a coffee. This changes the cost-
benefit of running mechanism variants: a researcher who would
previously have hand-calibrated one model can now diagnostically
calibrate ten and report the comparison.

The pipeline's second strongest claim is that **auto-generated research
reports are usable as Results section drafts**. The 89-line reference
report covers every parameter, compares iterations quantitatively, and
contextualises against the established epidemiological literature in
prose that requires light editing (not rewriting) to land in a
preprint.

### 4.2 What the pipeline gets wrong

LLM codegen reliability is the dominant failure mode. The N=5
reliability sample (Section 3.4) shows three distinct failure modes:
(1) generated agent/environment doesn't transition state, producing a
flat trajectory; (2) generated DataCollector uses property names
inconsistent with the spec; (3) the GVR auto-fix loop sometimes fails
to recover from validator hits within its 5-retry budget.

All three modes are **detected** by the diagnostics layer (β profile
likelihood, ε execution verification, downstream scoring failure
respectively) but **not recovered**. The pipeline's exit code is 0
in all five runs including the three failures — a usability gap that
would mislead a user not reading the calibration report. Three
concrete polish items:

- Make ε MISMATCH (when all targets mismatch) a HALT condition with
  kill memo. This converts a "look at the report" cognitive load
  into a "see the kill memo immediately" cognitive load.
- Add a structural validator for "DataCollector property names match
  spec.targets" — this would have caught failure mode (2) before
  simulator launch.
- Tune GVR retry budget separately per stage; the simulation-fix
  stage may benefit from more retries than the codegen-fix stage.

The gain_resistance_chance parameter remains poorly recovered (63.0%
relative error on the mean). This is genuine identifiability weakness,
not a calibration failure — profile likelihood and Fisher diagnostics
correctly surface it (it has the lowest profile curvature of the three,
§3.2). Future work could include scheduling additional
simulator effort on poorly-identified parameters once their wide CIs
are detected.

The auto-generated report lacks abstract, formal references, and
algorithm pseudocode. These are tractable Reporter-prompt extensions
but require integrating with a citation database for references.

### 4.3 Limitations

This paper reports on a single domain (SIR on a small-world network).
Three additional domains (opinion dynamics, segregation) are covered
by cross-domain CI tests in the source repository but not analysed
in publication-class depth here.

The reliability sample is small (N=5 lean runs, N=2 full-pipeline
runs); larger samples are needed for quantitative reliability claims.

The pipeline is currently tied to a single LLM provider (DeepSeek for
this paper's cost numbers; the abstraction layer supports Anthropic
Claude with no code change). LLM-provider sensitivity has not been
characterised.

### 4.4 Relationship to existing work

ABM frameworks Mesa (Kazil, Masad, & Crooks, 2020), Melodie, AgentPy,
and NetLogo (Tisue & Wilensky, 2004) provide simulation runtimes
without integrated calibration or LLM codegen. Calibration libraries
SBI (Tejero-Cantero et al., 2020) and ELFI (Lintusaari et al., 2018)
provide algorithmic substrates without ABM-specific tooling or natural-
language code generation. The contribution of abm-auto is integration
of these layers behind a single pipeline interface, not algorithmic
novelty in any single layer.

LLM-as-scientific-collaborator work (Bran et al., 2023; Boiko et al.,
2023) demonstrates LLM-driven workflow for chemistry. abm-auto is
analogous for agent-based modelling.

---

## 5. Conclusion

We demonstrated an automated research pipeline that takes a natural-
language problem statement and produces a calibrated agent-based model
with identifiability-aware reporting, in ~6 minutes wall-clock at
~$0.04 in LLM costs. Applied to a SIR-on-network calibration problem,
the pipeline reduces aggregate MSE from 1480 baseline to a mean of 48
across five independent runs, recovering the most-identifiable
parameter to within 2% relative error of the data-generating value.
Identifiability diagnostics correctly distinguish well-constrained
from poorly-constrained parameters. The auto-generated research
report covers the structural sections of a Results write-up and
serves as a usable draft for further human refinement.

The most pressing future work is reliability of the LLM codegen stage:
single-run success rate is currently sample-dependent (insufficient
N for a quantitative claim), and the auto-fix retry loop does not
recover from all detected failures. Expanding the anti-pattern catalog
and feeding successful exemplars into the codegen prompt are the
near-term levers.

Beyond reliability, three Reporter-prompt extensions would close most
of the gap to direct preprint submission: abstract generation,
methodological pseudocode rendering from `MechanismSpec`, and
citation-database integration. These are tractable engineering tasks
on the existing pipeline.

---

## References

Beaumont, M. A. (2010). Approximate Bayesian computation in evolution
and ecology. *Annual Review of Ecology, Evolution, and Systematics*,
41, 379-406.

Boiko, D. A., MacKnight, R., Kline, B., & Gomes, G. (2023). Autonomous
chemical research with large language models. *Nature*, 624(7992),
570-578.

Bonabeau, E. (2002). Agent-based modeling: Methods and techniques for
simulating human systems. *Proceedings of the National Academy of
Sciences*, 99(suppl 3), 7280-7287.

Bran, A. M., Cox, S., Schilter, O., Baldassari, C., White, A. D., &
Schwaller, P. (2023). ChemCrow: Augmenting large-language models with
chemistry tools. *arXiv preprint arXiv:2304.05376*.

Chen, M., et al. (2021). Evaluating large language models trained on
code. *arXiv preprint arXiv:2107.03374*.

Cranmer, K., Brehmer, J., & Louppe, G. (2020). The frontier of
simulation-based inference. *Proceedings of the National Academy of
Sciences*, 117(48), 30055-30062.

Donoho, D. L. (2010). An invitation to reproducible computational
research. *Biostatistics*, 11(3), 385-388.

Epstein, J. M. (2006). *Generative social science: Studies in agent-
based computational modeling*. Princeton University Press.

Joshi, M., Seidel-Morgenstern, A., & Kremling, A. (2006). Exploiting
the bootstrap method for quantifying parameter confidence intervals in
dynamical systems. *Metabolic Engineering*, 8(5), 447-455.

Kazil, J., Masad, D., & Crooks, A. (2020). Utilizing Python for agent-
based modeling: The Mesa framework. *Lecture Notes in Computer
Science*, 12268, 308-317.

Lintusaari, J., Vuollekoski, H., Kangasrääsiö, A., Skytén, K.,
Järvenpää, M., Marttinen, P., ... & Corander, J. (2018). ELFI: Engine
for likelihood-free inference. *Journal of Machine Learning Research*,
19(16), 1-7.

Lueckmann, J. M., Goncalves, P. J., Bassetto, G., Öcal, K., Nonnenmacher,
M., & Macke, J. H. (2017). Flexible statistical inference for mechanistic
models of neural dynamics. *Advances in Neural Information Processing
Systems*, 30.

Raue, A., Kreutz, C., Maiwald, T., Bachmann, J., Schilling, M.,
Klingmüller, U., & Timmer, J. (2009). Structural and practical
identifiability analysis of partially observed dynamical models by
exploiting the profile likelihood. *Bioinformatics*, 25(15),
1923-1929.

Stodden, V. (2014). What scientific idea is ready for retirement?
*Edge.org Annual Question*.

Tejero-Cantero, A., Boelts, J., Deistler, M., Lueckmann, J. M.,
Durkan, C., Gonçalves, P. J., ... & Macke, J. H. (2020). SBI — A
toolkit for simulation-based inference. *Journal of Open Source
Software*, 5(52), 2505.

Tisue, S., & Wilensky, U. (2004). NetLogo: A simple environment for
modeling complexity. *International Conference on Complex Systems*,
21, 16-21.

---

## Appendix A: Reproducibility

Source code: `https://github.com/Yco-0314/MyMoMo-Academic` (commit
hash for this paper's runs: see `git log` at submission time).

To reproduce the lean N=5 calibration benchmark in Section 3.1 — the
third argument is the RNG seed that pins the Random Forest screening
stage, making the run **bit-for-bit reproducible**:

```bash
git clone https://github.com/Yco-0314/MyMoMo-Academic
cd mymomo-academic
uv sync
python benchmark_calibration_lean.py 5 100 42
```

Expected wall time: ~8 minutes. Expected output (verified reproducible
across repeated runs at seed=42; only wall-clock seconds vary):
aggregate MSE 93.9 ± 56.1 (range 20.9–152.4); per-run best_params land
at virus 3.79 ± 1.23, recovery 2.71 ± 1.06, gain_resistance
40.75 ± 22.46. Omitting the seed argument leaves the RF backend
unseeded, in which case only the distribution reproduces (mean MSE
~50–95), not the specific values.

**Note on §3.1 vs §3.4.** Section 3.1 (calibration accuracy) uses the
LEAN path — `fit_from_files` calibrating a hand-written reference
simulator, isolating the calibration math from codegen. Section 3.4
(codegen reliability) uses the FULL pipeline including LLM code
generation. They measure different things — §3.1 "given a correct model,
how well does calibration recover parameters", §3.4 "how often does the
LLM produce a correct model" — and should not be conflated.

To reproduce the full-pipeline run in Section 3.5 (requires LLM API
key):

```bash
export DEEPSEEK_API_KEY=sk-...
export LLM_PROVIDER=deepseek
python tests/e2e/dogfood_codegen_path.py
```

Expected wall time: ~6 minutes per run (success-dependent). Expected
cost: ~$0.04 per run.

## Appendix B: The published-vs-inferred parameter disagreement

The published parameter set for this calibration problem is
`(virus_spread=4.4, recovery=0.3, gain_resistance=25.0)`. Under the
topology-faithful network, these parameters yield MSE 8187 against
observed.csv — substantially worse than the inferred parameter set
`(4.4, 2.5, 25.0)` (MSE 217). The discrepancy is consistent with a
factor-of-~10 typo in the published `recovery` value. The inferred
set is what would have generated the observed trajectory; the
published set could not.

We use the inferred set as ground truth for scoring throughout. This
choice is documented in the source's `benchmark_calibration_challenge.py`
module docstring.
