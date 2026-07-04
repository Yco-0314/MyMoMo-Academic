# Wright-Fisher Neutral Genetic Drift — FINDINGS

**Run 2026-06-30, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`): each
individual is an autonomous `AlleleAgent` carrying a single discrete heritable allele
(`A` or `a`); the `WrightFisherModel` owns the seeded RNG, the **generational resample**,
and the run-to-fixation stop rule — not a god-loop. The allele lives ON the agents; each
generation builds the whole next generation by sampling N parents uniformly **with
replacement** from the current generation and copying each sampled parent's allele.
Code: `abm_auto/classics/wright_fisher.py`; experiment:
`examples/repro_wright_fisher/run.py`.

## Model and the classic neutral results it claims

A population of N haploid gene copies, two alleles (`A` at initial frequency `p0`, `a`
otherwise), reproduces in **non-overlapping generations**: each new generation is formed
by N independent uniform draws (with replacement) of a parent from the current
generation; the offspring inherits the parent's allele. This is exactly the Wright-Fisher
binomial transition `#A(t+1) ~ Binomial(N, #A(t)/N)`, realised one Bernoulli parent-draw
at a time. There is no fitness — every individual is equally likely to be a parent
(neutral). Run to fixation (`#A = 0` or `#A = N`).

The classic results (Wright 1931 / Fisher 1930):
1. **Fixation probability = initial frequency.** A neutral allele at frequency `p0` fixes
   with probability `p0` (the martingale property `E[p(t+1) | p(t)] = p(t)` makes the
   absorption probability at the all-`A` boundary equal `p0`).
2. **Heterozygosity decays geometrically.** `H = 2p(1-p)`; the *expected* heterozygosity
   decays by a fixed per-generation factor:
   `E[H(t+1)] = (1 - 1/N) E[H(t)]` for a **haploid** population of N gene copies. (The
   textbook `1 - 1/(2N)` is the **diploid** statement with `2N` copies.)
3. **Neutral drift, no selection bias.** `E[Delta p] = 0` at every step, so the mean
   allele frequency across runs stays at `p0` until a run is absorbed.

**Wright-Fisher is GENERATIONAL** (the whole population is replaced each step), which is
distinct from the Moran process (one birth-death event per step). They share the neutral
fixation-prob = initial-frequency result but differ in the per-step dynamics and time scale.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| population | **N = 100** haploid individuals; each allele `A` or `a` |
| initial state | first `round(p0*N)` agents are `A`, the rest `a` (well-mixed -> only `#A` matters; layout irrelevant) |
| generation step | **sample N parents uniformly WITH replacement** from the current generation; offspring inherits the sampled parent's allele; N constant |
| stop rule | run to **fixation**: `#A = 0` (A lost) or `#A = N` (A fixed) |
| p0-grid | **0.2, 0.5, 0.8** |
| runs per p0 | **2000** independent runs (seeds 0-1999), each a fresh population at p0 |
| locked metrics | **fixation probability** of A; per-gen **mean-heterozygosity decay factor**; **E[Delta p]** / ensemble mean p(t) |
| analytic anchors | neutral fixation prob = `p0`; haploid decay factor `1 - 1/N = 0.99` — evaluated at the LOCKED N, p0, never fed into the dynamics |

Determinism: a single seeded RNG chain drives every parent draw, so the same seed
reproduces a byte-identical run (pinned in `tests/classics/test_wright_fisher.py`).

## Measured outcomes (2000 runs per p0; all runs absorbed)

| p0 | fixation prob | SE | analytic (=p0) | abs err | fixations/runs | mean-H decay factor | E[Delta p] | ensemble mean p(t=5) | mean gens | max gens |
|---|---|---|---|---|---|---|---|---|---|---|
| **0.2** | 0.2005 | 0.0090 | 0.2000 | 0.0005 | 401/2000 | 0.99001 | +0.000005 | 0.1978 | 95.4 | 740 |
| **0.5** | 0.4980 | 0.0112 | 0.5000 | 0.0020 | 996/2000 | 0.98993 | -0.000015 | 0.4963 | 134.2 | 740 |
| **0.8** | 0.7910 | 0.0091 | 0.8000 | 0.0090 | 1582/2000 | 0.99010 | -0.000090 | 0.7988 | 100.0 | 726 |

The fixation fraction's binomial SE is `sqrt(p(1-p)/runs)` (~0.009-0.011 here at 2000
runs), so the locked +-0.05 tolerance comfortably covers the sampling noise.

### How the heterozygosity decay factor is measured (and why the estimator matters)

The neutral law is a statement about the **ensemble mean** heterozygosity:
`E[H(t+1)] = (1 - 1/N) E[H(t)]`. We pool `H(t)` across all 2000 runs at each generation
index (a run absorbed early contributes `H = 0` thereafter, so the ensemble mean reflects
the mass lost to fixation), form the mean-`H` trajectory, and take the geometric mean of
the consecutive ratios `mean_H(t+1)/mean_H(t)` over the first 100 generations.

Measured: **0.98993 at p0=0.5** (and 0.990 at every p0) — essentially **exactly the
`1 - 1/N = 0.9900` haploid law**, and squarely inside the locked band `[1-2/N, 1-1/(4N)] =
[0.9800, 0.9975]`.

**Estimator caveat (honest):** a *per-run* geometric mean of `H(t+1)/H(t)` is the WRONG
estimator for this law — it is biased **low** (~0.977 here), because the geometric mean of
a ratio of correlated random variables is not the ratio of expectations (Jensen). The law
is about the ratio of **expected** `H`, which is the across-run ratio reported above. We
use and report the across-run ensemble estimator.

### How neutrality (P3) is measured (and a conditioning caveat)

We grade neutrality on the **direct martingale statement** `E[Delta p] ~= 0`: the mean
one-generation increment `p(t+1) - p(t)` pooled over all polymorphic steps. Measured
`|E[Delta p]| <= 9e-5` for every p0 — zero to Monte-Carlo precision. We also confirm the
equivalent "**mean A-fraction across runs ~= p0**" form: the ensemble mean of `p` at a
fixed early generation (t=5) sits within 0.004 of p0 for all three p0.

**Conditioning caveat (honest, and a trap avoided):** the mean A-fraction averaged over
**all polymorphic generations pooled** is NOT a neutrality measure and is NOT p0 — it is
pulled toward 0.5 (we observe 0.354 for p0=0.2 and 0.636 for p0=0.8). This is a
*conditioning* artefact, not a selection bias: runs heading toward `A`-fixation spend many
generations at high frequency while runs heading toward `A`-loss absorb sooner, so the
frequency *conditioned on still being polymorphic* drifts toward 0.5. The neutral process
is still a perfect martingale (`E[Delta p] = 0`); the conditioned time-average is reported
in `results.json` as `mean_pre_absorption_fraction_conditioned` purely for transparency
and is explicitly NOT the P3 grade.

## Verdicts (locked metrics; tier = refutation; honest — falsified would be MISS)

| # | Prediction | Pass clause | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Fixation prob = initial frequency | fixation prob within +-0.05 of p0 (each p0) | worst abs err **0.0090** | **REPRO** |
| **P2** | Heterozygosity decays ~(1-1/N)/gen | mean-H decay factor in `[1-2/N, 1-1/(4N)]` = `[0.98, 0.9975]` | **0.9899** (= 1-1/N) | **REPRO** |
| **P3** | Neutral drift, no selection bias | `E[Delta p] ~= 0` and ensemble mean p(t) ~= p0 | worst `|E[Delta p]|` **9e-5**; worst ensemble err **0.0037** | **REPRO** |

**3/3 locked clauses REPRO.** The genuine agent-based generational resample reproduces the
neutral Wright-Fisher results: fixation probability tracks the initial frequency, the mean
heterozygosity decays at the haploid `1 - 1/N` rate, and the drift is an unbiased
martingale (`E[Delta p] = 0`).

## Honesty notes / scope

- Faithful reproduction of a published **synthetic** model; no real-world data. The
  contribution is whether the harness + lock-first discipline reproduce the neutral
  fixation-prob = p0 and heterozygosity-decay results, and would catch an artifact.
- The measured `1 - 1/N` decay is the **haploid** rate (N gene copies); the diploid
  textbook value `1 - 1/(2N)` corresponds to `2N` copies. The locked P2 band
  `[1-2/N, 1-1/(4N)]` was set to bracket the `1/N`-scale law, and the measurement lands at
  its center, on `1 - 1/N` exactly.
- The two estimator caveats above (per-run-ratio bias for H decay; conditioned-time-average
  vs the martingale for drift) are the substantive honesty points: both name a *wrong*
  estimator that would mislead, and grade on the correct one.
- N, the p0-grid, and the run count were FIXED before the run; nothing was tuned to make a
  clause pass. Determinism is pinned by tests.

## Citations
- Wright, S. (1931). Evolution in Mendelian populations. *Genetics* 16(2):97-159.
  doi:10.1093/genetics/16.2.97.
- Fisher, R.A. (1930). *The Genetical Theory of Natural Selection*. Oxford: Clarendon Press.
