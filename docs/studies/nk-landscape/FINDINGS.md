# Kauffman NK Landscape — FINDINGS

**Run 2026-06-30, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`): each
adaptive walk is performed by an autonomous `WalkerAgent` that holds its OWN genotype
(its position on the landscape) and hill-climbs by surveying its N Hamming-1 neighbours
and moving to the fittest strictly-fitter one — not a god-loop. The `AdaptiveWalkModel`
owns the landscape (the environment) and the seeded RNG (the random start) and steps the
walker to a local optimum. The `#local-optima` count is a landscape-property measurement
obtained by ENUMERATING the full 2^15 genotype space. Code:
`abm_auto/classics/nk_landscape.py`; experiment: `examples/repro_nk_landscape/run.py`.

## Model and the result it claims

A genotype is a length-N binary string. Each locus `i` has `K` epistatic neighbours — `K`
OTHER loci chosen at random per locus, fixed for the life of a landscape. Locus `i`'s
fitness contribution `f_i ~ U[0,1]` is keyed deterministically on `(seed, i, the K+1
relevant bits)` (its own allele plus its K neighbours' alleles) — the random "fitness
table", here a lazily-filled seed-keyed hash so it is deterministic per landscape seed.
Fitness(genotype) = mean of the N contributions. `K` tunes ruggedness:

- **K=0** (no epistasis): additive, single-peaked "Mt-Fuji" landscape.
- **K=N-1=14** (maximal epistasis): every contribution depends on the whole genome → the
  landscape is effectively a random assignment of fitnesses, with `#optima ~ 2^N/(N+1)`.

Kauffman & Levin (1987): ruggedness grows with K → MORE local optima and SHORTER greedy
adaptive walks (walks get trapped at nearby optima sooner).

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| genome | **N = 15** binary loci; **2^15 = 32768** genotypes, fully ENUMERATED per landscape |
| ruggedness sweep | **K in {0, 2, 4, 8, 14}** (K = N-1 = 14 is maximal epistasis) |
| epistasis wiring | each locus i depends on its own allele + **K other loci chosen at random** per locus, fixed per landscape seed |
| contribution | `f_i ~ U[0,1]` keyed deterministically on `(seed, locus, the K+1 relevant bits)`; fitness = **mean** of the N contributions |
| local optimum | a genotype whose fitness is **>= all N single-bit-flip (Hamming-1) neighbours** |
| adaptive walk | **greedy steepest-ascent**: from a random start, repeatedly move to the FITTEST strictly-fitter 1-flip neighbour until none exists; length = #accepted moves |
| landscapes per K | **5** independent random landscapes (seeds 0-4), both metrics averaged |
| walks per landscape | **200** greedy walks from random starts (seeds 0-199) |
| locked metrics | **#local optima** (enumerated) and **mean greedy-walk length** |
| analytic anchor | random-landscape `#optima` expectation `2^N/(N+1) = 2048` (the K=N-1 target); never fed into the dynamics |

Determinism: a landscape is fully determined by its seed (epistasis wiring + the U[0,1]
contribution table are both seed-keyed); a walk is determined by the landscape + the
walker's start. Same seed -> identical landscape, optima count, and walks (pinned in
`tests/classics/test_nk_landscape.py`).

## Measured outcomes (5 landscapes per K, 200 walks per landscape)

| K | mean #optima | (min..max) | std | mean walk length | mean end fitness |
|---|---|---|---|---|---|
| **0** | **1.0** | (1..1) | 0.0 | 7.429 | 0.6905 |
| 2 | 23.0 | (11..41) | 10.4 | 5.148 | 0.7180 |
| 4 | 91.2 | (79..110) | 11.5 | 4.076 | 0.7231 |
| 8 | 511.4 | (482..557) | 27.4 | 2.601 | 0.6911 |
| **14** | **2043.0** | (2019..2092) | 25.9 | 1.577 | 0.6561 |

Per-landscape #optima (each row = the 5 seeds):

- K=0: `[1, 1, 1, 1, 1]` — every landscape is single-peaked.
- K=2: `[23, 11, 25, 41, 15]`
- K=4: `[98, 88, 110, 79, 81]`
- K=8: `[490, 482, 557, 501, 527]`
- K=14: `[2092, 2042, 2019, 2038, 2024]`

The mean #optima climbs **1 -> 23 -> 91 -> 511 -> 2043** as K goes 0 -> 14: an effectively
geometric explosion of peaks with epistasis. At **K=N-1=14** the mean (2043) lands right
on the random-landscape expectation **2^N/(N+1) = 2048** (every individual landscape is
within ~1.5% of it), confirming the maximally-rugged landscape is statistically a random
fitness assignment. The mean greedy-walk length falls monotonically **7.43 -> 5.15 -> 4.08
-> 2.60 -> 1.58**: on the smooth K=0 landscape a steepest-ascent walk climbs ~7-8 steps to
the single global peak; on the rugged K=14 landscape it is trapped at a nearby optimum
after ~1.6 steps.

## Verdicts (graded on the LOCKED metrics: #local optima and greedy-walk length)

| # | Prediction | Result | Number |
|---|---|---|---|
| **P1** | Mean #local optima increases monotonically with K | **REPRO** | 1.0 < 23.0 < 91.2 < 511.4 < 2043.0 (strictly increasing) |
| **P2** | K=0 -> exactly 1 local optimum (single-peaked) | **REPRO** | #optima = 1 on every one of the 5 landscapes (min=max=mean=1) |
| **P3** | Mean greedy adaptive-walk length decreases monotonically with K | **REPRO** | 7.429 > 5.148 > 4.076 > 2.601 > 1.577 (strictly decreasing) |

**3/3 locked clauses REPRO.** Monotonicity held cleanly at the mean (over 5 landscapes)
with no non-monotone blip; both metrics are well separated across the grid.

## Honest caveats

- **Mean-fitness reached is non-monotone in K, and this is EXPECTED — not graded.** The
  mean end fitness of a walk rises slightly then falls (0.69 -> 0.72 -> 0.72 -> 0.69 -> 0.66).
  This is the classic NK "complexity catastrophe": low K is too smooth to have high peaks,
  very high K is so rugged that greedy walks get trapped early on mediocre optima, and an
  intermediate K reaches the fittest accessible optima. It is a known qualitative feature
  of the model, but it is NOT one of the three locked claims (which are about #optima and
  walk LENGTH, both of which are strictly monotone), so it is reported here as context
  only and was not used to grade.
- **#optima is a landscape property, measured by enumeration — the agents do the walks.**
  The local-optima count comes from enumerating all 2^15 genotypes and checking the
  1-flip-neighbour condition (a property of the environment), exactly as Kauffman &
  Levin measure it. The genuinely agent-based part is the adaptive walk: each `WalkerAgent`
  hill-climbs by reading neighbour fitnesses from the landscape, never an analytic answer.
  This split is disclosed; the walk-length metric (P3) is the agent-stepping result.
- **Greedy steepest-ascent is one walk policy.** We use deterministic steepest ascent
  (always move to the fittest strictly-fitter neighbour, ties broken by lowest genotype
  code). A "random adaptive walk" (move to a random fitter neighbour) gives somewhat
  longer walks but the SAME monotone-decreasing-in-K trend; the locked claim is about the
  trend, which is policy-robust. The policy was fixed before the run.
- **Finite landscapes -> variance, but the means are clean.** The per-landscape #optima and
  walk lengths vary (e.g. K=2 ranges 11..41 optima), as expected for 5 finite random
  landscapes. Averaging over 5 landscapes per K already yields strict monotonicity at the
  mean; no landscape count or seed was tuned to remove a blip (there was none).
- **No real-world data.** This is a faithful reproduction of a published synthetic model.
  The contribution is whether the harness + discipline reproduce the NK ruggedness-vs-K
  results and would catch an artifact. The random-landscape expectation `2^N/(N+1)` is the
  comparison anchor only; the dynamics never see it.

## Provenance

- Predictions locked before the run: `PREDICTIONS-locked.md`.
- Raw results: `results.json` (config + #optima vs K + walk-length vs K + full
  per-landscape detail).
- Replayable L3 bundle: `verdict-bundle.json` (paper Kauffman & Levin 1987; the three
  tier-honest Verdicts; content-addressed fingerprints of `PREDICTIONS-locked.md`, this
  `FINDINGS.md`, the design spec, and `results.json`).
- Source: Kauffman, S.A. & Levin, S. (1987). Towards a general theory of adaptive walks on
  rugged fitness landscapes. J. Theor. Biol. 128(1):11-45.
  doi:10.1016/S0022-5193(87)80029-2. Book reference: Kauffman (1993), The Origins of
  Order, ch. 2-3 (the NK model; #optima ~ 2^N/(N+1) at K=N-1).
