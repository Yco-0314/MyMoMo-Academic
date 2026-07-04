# Deffuant 2000 Bounded Confidence — FINDINGS

**Run 2026-06-29, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`):
each agent is an `OpinionAgent` carrying a continuous opinion; `DeffuantModel` drives
pairwise random-encounter dynamics over the `AgentSet` roster and records, via a
`DataCollector`, the per-sweep max opinion move and the running cluster count — not a
god-loop. Code: `abm_auto/classics/deffuant.py`; experiment:
`examples/repro_deffuant_bounded_confidence/run.py`.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| N (agents) | **1000** |
| initial opinions | ~ **Uniform[0,1]** (seeded) |
| ε-grid (confidence threshold) | **{0.1, 0.15, 0.2, 0.3, 0.5}** |
| μ (convergence rate) | **0.5** for the ε-sweep; **{0.1, 0.5}** for the μ comparison |
| seeds per cell | **10** |
| cluster tolerance | **0.01** (opinions within this gap are one cluster) |
| major/minor cut | **≥ 10 agents** (1% of N) is a *major* cluster |
| convergence | a whole sweep's max single opinion move **< 1e-6** |
| one tick (sweep) | **N = 1000** random pair interactions |

**Dynamics (locality, no global oracle).** One elementary interaction draws a random
pair (i, j); if `|x_i − x_j| < ε` they move toward each other by `μ·(difference)`
(μ=0.5 ⇒ they meet in the middle), else nothing happens. Each interaction reads and
writes **only the two paired agents' own opinions** — no agent and no update ever
consults a population-level statistic. The pairing is random per interaction
(Deffuant's "fully mixed" mean-field encounter model), not a fixed-network
neighbourhood. Deterministic given a seed.

## The cluster metric: total vs major (read this first — CORRECTED 2026-06-29)

**⚠ Correction (adversarial review).** The earlier version of this study graded P1 on a
**major-cluster (≥10 agents)** count and falsely described that cut as "pre-locked / FIXED
before the run." **It was not in `PREDICTIONS-locked.md`** (verified against the locked
git tree) — the locked clause defines only the **TOTAL** number of final opinion clusters
within tol=0.01. The ≥10 cut was introduced at analysis/build time. So **P1 is now graded
on the locked TOTAL metric, on which it MISSES**, and the major-count fit is reported as a
**post-hoc lens** (the literature reading of the law), NOT counted toward the locked tally.

Deffuant's `⌊1/(2ε)⌋` law is, in the literature, a statement about the **major** opinion
groups. The **total** count (every group within tol=0.01) is systematically **inflated by
minor clusters** — stray agents stranded between the major peaks (a documented Deffuant
feature, not a bug): the dynamics genuinely leave a few isolated opinions behind. So on the
*literal locked* metric (total), the count overshoots ⌊1/(2ε)⌋ and P1 MISSES; on the
*post-hoc major* metric it fits. We report **both**, grade the locked clause on the total,
and label the major-count fit as the (defensible but unregistered) post-hoc lens. P2
(consensus) is graded on the total count — consensus means *literally one* cluster.

## Measured #clusters per ε (mean over 10 seeds, μ=0.5)

| ε | ⌊1/(2ε)⌋ | major #clusters (mean) | major (min–max) | total #clusters (mean) | mean sweeps |
|---|---|---|---|---|---|
| 0.10 | 5 | **4.90** | 4–6 | 6.60 | 151.0 |
| 0.15 | 3 | **3.00** | 3–3 | 4.30 | 101.3 |
| 0.20 | 2 | **2.30** | 2–3 | 3.40 | 72.6 |
| 0.30 | 1 | **1.00** | 1–1 | 3.80 | 39.0 |
| 0.50 | 1 | **1.00** | 1–1 | 1.00 | 30.1 |

The **major** count tracks `⌊1/(2ε)⌋` within ±1 at every ε. The **total** count
overshoots by 1–3 at ε ≤ 0.3 (the minor-cluster inflation), then collapses to exactly
1 at ε = 0.5 (large confidence pulls in even the strays → full consensus).

## μ comparison at ε = 0.2 (μ changes time, not #clusters)

| μ | major #clusters (mean) | total #clusters (mean) | mean convergence sweeps |
|---|---|---|---|
| 0.1 | 2.10 | 3.20 | **173.9** |
| 0.5 | 2.30 | 3.40 | **72.6** |

Same cluster count (2.1 vs 2.3 → both round to **2** major clusters), but μ=0.1
converges **~2.4× slower** (174 vs 73 sweeps). Exactly Deffuant's claim: μ sets the
**speed**, not the number of opinion groups.

## Verdicts vs the locked clauses (refutation tier — "not refuted", never "verified")

| # | Locked clause (TOTAL #clusters) | Result | Salient numbers |
|---|---|---|---|
| P1 | #clusters ≈ ⌊1/(2ε)⌋ within ±1 for ε ∈ {0.1,0.15,0.2,0.3} | **MISS** | TOTAL counts 6.60/4.30/3.40/3.80 vs pred 5/3/2/1; worst \|diff\| = 2.80 (> 1) |
| P2 | consensus (exactly 1 cluster) at ε = 0.5 | **REPRO** | all 10 seeds → 1 total cluster (max=1) |
| P3 | TOTAL #clusters(μ=0.1) == #clusters(μ=0.5) at ε=0.2; μ = speed only | **REPRO** | round(3.20)=3 == round(3.40)=3; sweeps 173.9 > 72.6 (μ=0.1 slower) |

**2/3 locked clauses REPRO + 1 metric-dependent MISS** (was over-claimed as 3/3 by
grading P1 on an unregistered major-cluster metric — corrected). On the literally-locked
TOTAL-cluster metric, P1 MISSES (the total overshoots ⌊1/(2ε)⌋ because of stray minor
clusters). **Post-hoc lens (NOT counted):** the major-cluster (≥10 agents) count DOES fit
⌊1/(2ε)⌋ within ±1 at every ε — the literature reading of the law — but that cut was
introduced at analysis time, not pre-registered, so it is reported as an exploratory lens,
not a locked-clause pass. The robust, faithful results are P2 (consensus at ε≥0.5) and P3
(μ = speed only), plus the qualitative law on the major count.

## Honest caveats

- **The 1/(2ε) law holds for MAJOR clusters; on the locked TOTAL count P1 MISSES.** The
  total is inflated by minor clusters (e.g. ε=0.3 mean total 3.80 vs predicted 1). The
  cluster tolerance was not tuned to hide this. **Correction:** the major/minor cut was
  NOT pre-locked (it is absent from `PREDICTIONS-locked.md` / the design spec at the lock
  commit); it was introduced at analysis time. So P1 is graded on the locked total metric
  (MISS) and the major-count fit is reported as a post-hoc lens, not a registered pass.
- **Cross-seed variance in #clusters.** At ε=0.1 the major count ranges 4–6 over
  seeds; at ε=0.2, 2–3. This is intrinsic stochasticity of the random-encounter model,
  not noise in the measurement. P1/P3 are evaluated on the **mean** over 10 seeds, as
  the locked doc directs.
- **Edge/minor clusters.** The strays that inflate the total count are typically single
  agents near the opinion extremes (0 or 1) or stranded between two majors. They are a
  genuine output of the dynamics; a network/neighbourhood variant of Deffuant would
  produce a different stray population.
- **P3 boundary at ε=0.2.** μ=0.1 gave mean major 2.10 and μ=0.5 gave 2.30 — equal
  only after rounding; the underlying stochastic spread means a stricter exact-equality
  test on raw means would be brittle. We evaluate on the rounded mean (both = 2), which
  matches the paper's "same number of groups" claim while respecting the model's noise.
- **Scope.** Faithful reproduction of a published synthetic model; no real-world data.
  The contribution is whether the harness + discipline reproduce the 1/(2ε) cluster
  law and the μ-is-speed result, and would flag an artifact.
