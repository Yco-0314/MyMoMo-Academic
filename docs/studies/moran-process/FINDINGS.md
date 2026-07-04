# Moran Process with Selection — FINDINGS

**Run 2026-06-30, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`): each
individual is an autonomous `IndividualAgent` carrying a discrete heritable type
(MUTANT, fitness `r`, or RESIDENT, fitness 1); the `MoranModel` owns the seeded RNG, the
Birth-Death event, and the run-to-fixation stop rule — not a god-loop. The type lives ON
the agents; each elementary step picks a reproducer with probability proportional to
fitness and a dier uniformly at random, and the offspring overwrites the dier's type.
Code: `abm_auto/classics/moran_process.py`; experiment:
`examples/repro_moran_process/run.py`.

## Model and the exact result it claims

A single mutant of relative fitness `r` introduced into a resident population of size `N`
(residents fitness 1) fixes (reaches frequency 1) with the **exact Moran (1958)
probability**

```
rho = (1 - 1/r) / (1 - 1/r**N)        (r != 1)
rho = 1/N                             (r == 1, neutral).
```

**NOTE (a locked claim of this study):** the large-`N` limit of the Moran fixation
probability is `1 - 1/r ~= s` (the selection coefficient `s = r - 1` for small `s`), and
is **NOT** the Wright-Fisher diffusion result `2s`. For `r = 1.2` (`s = 0.2`) the Moran
large-N limit is `1 - 1/1.2 = 0.1667`, far from `2s = 0.4`. At `N = 100` the finite-N
formula gives 0.1667 here (essentially the large-N value already, since `1/r**N` is tiny
for `r > 1`). We reproduce the EXACT Moran formula, not the WF approximation.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| population | **N = 100** well-mixed individuals; each type MUTANT (fitness r) or RESIDENT (fitness 1) |
| initial state | exactly **ONE** mutant (the rest residents); start position irrelevant (well-mixed -> only the count m matters) |
| elementary step | **BIRTH** reproducer proportional to fitness (mutant chosen w.p. `r*m/(r*m + (N-m))`), **DEATH** dier uniform, **REPLACE** offspring (reproducer's type) overwrites the dier; N constant |
| stop rule | run to **fixation**: m = 0 (mutant lost) or m = N (mutant fixed) |
| r-grid | **1.0, 1.05, 1.1, 1.2, 2.0** (neutral + four advantageous mutants) |
| runs per r | **2000** independent runs (seeds 0-1999), each a fresh single mutant |
| locked metric | **fixation probability** = fraction of runs in which the mutant fixed |
| analytic anchor | `rho = (1-1/r)/(1-1/r**N)`, `1/N` at r=1 — evaluated at the LOCKED r,N, never fed into the dynamics |

Determinism: a single seeded RNG chain drives every BIRTH and DEATH draw, so the same
seed reproduces a byte-identical run (pinned in `tests/classics/test_moran_process.py`).

## Measured outcomes (2000 runs per r)

The measured fixation fraction is a Monte-Carlo estimate; its binomial standard error is
`SE = sqrt(rho(1-rho)/runs)` (~ 0.002-0.011 across this grid at 2000 runs), so the
locked +-0.03 / +-0.01 tolerances comfortably cover the sampling noise.

| r | measured fixation | SE | analytic rho | abs error | fixations/runs | mean events |
|---|---|---|---|---|---|---|
| **1.0** (neutral) | 0.0095 | 0.0022 | 0.0100 (=1/N) | 0.0005 | 19/2000 | 557.3 |
| 1.05 | 0.0495 | 0.0049 | 0.0480 | 0.0015 | 99/2000 | 708.6 |
| 1.1 | 0.0885 | 0.0064 | 0.0909 | 0.0024 | 177/2000 | 729.9 |
| 1.2 | 0.1685 | 0.0084 | 0.1667 | 0.0018 | 337/2000 | 751.3 |
| 2.0 | 0.4875 | 0.0112 | 0.5000 | 0.0125 | 975/2000 | 694.0 |

Every measured value sits within ~1.1 SE of the exact Moran rho. The worst absolute error
is 0.0125 at r = 2.0 (~ 1.1 SE; rho = 0.5 has the largest binomial variance, so the
largest expected MC spread). Fixation increases strictly and monotonically with r.

## Verdicts (graded on the LOCKED metric: fixation probability)

| # | Prediction | Result | Number |
|---|---|---|---|
| **P1** | Fixation prob matches rho=(1-1/r)/(1-1/r^N) at r in {1.05,1.1,1.2,2.0} within +-0.03 | **REPRO** | worst abs err = 0.0125 <= 0.03 |
| **P2** | Neutral r=1.0 -> fixation ~= 1/N = 0.01 (+-0.01) | **REPRO** | err = 0.0005 <= 0.01 (measured 0.0095) |
| **P3** | Fixation prob monotone increasing in r | **REPRO** | strictly increasing: 0.0095 < 0.0495 < 0.0885 < 0.1685 < 0.4875 |

**3/3 locked clauses REPRO.**

## Honest caveats

- **Monte-Carlo estimate, not exact.** The reported fixation fractions are estimates from
  2000 runs; the +-SE band is reported per r. At r = 2.0 the error (0.0125) is the largest
  in absolute terms precisely because rho = 0.5 maximises the binomial variance — this is
  expected sampling noise, not a model defect, and it is still ~1.1 SE and well inside the
  locked +-0.03.
- **No real-world data.** This is a faithful reproduction of a published synthetic model.
  The contribution is whether the harness + discipline reproduce the exact Moran fixation
  probability and would catch an artifact. The analytic rho is the comparison anchor only;
  the agents never see it.
- **State collapse is a property, not a shortcut.** Because death is uniform and the model
  is well-mixed, the dynamics depend only on the mutant count m, so the per-individual
  process is mathematically a biased random walk on m in {0,...,N}. The implementation
  still steps genuine per-individual agents (each holds its own type; the model draws a
  reproducer fitness-weighted over the real roster and a dier uniformly over the real
  roster) — the collapse is an emergent consequence of the rules, not an analytic
  shortcut substituted for the agent dynamics.
- **N = 100 is already near the large-N regime for r > 1.** `1/r**N` is negligible for
  r > 1 at N = 100, so the finite-N rho ~= the large-N limit `1 - 1/r`. The neutral case
  (r = 1) is the one where the finite N matters: rho = 1/N = 0.01 exactly.

## Provenance

- Predictions locked before the run: `PREDICTIONS-locked.md`.
- Raw results: `results.json` (config + per-r measured vs analytic fixation + SE + run
  counts + mean events).
- Replayable L3 bundle: `verdict-bundle.json` (paper Moran 1958; the three tier-honest
  Verdicts; content-addressed fingerprints of `PREDICTIONS-locked.md`, this `FINDINGS.md`,
  the design spec, and `results.json`).
- Source: Moran, P.A.P. (1958). Random processes in genetics. Math. Proc. Camb. Phil.
  Soc. 54(1):60-71. doi:10.1017/S0305004100033193. Modern reference: Nowak (2006),
  Evolutionary Dynamics, ch. 6-7.
