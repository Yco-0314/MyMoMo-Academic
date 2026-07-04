# Relative-Agreement with Extremists (Deffuant-Amblard 2002) — FINDINGS

**Status: 1/3 locked clauses REPRO (P2 double-extreme passes cleanly); P1 and P3 are
honest MISSes.** Genuine agent-based reproduction on `abm_auto._platform`. Predictions
were locked BEFORE running (`PREDICTIONS-locked.md`); the config below was fixed before
the run and was NOT tuned to make any clause pass. Falsified clauses are reported as
MISS (gate tier = `refutation`).

## What was built

200 `RAAgent`s, each carrying **two** state variables — an opinion `x in [-1, 1]` AND an
evolving **uncertainty** `u > 0` (its opinion is the segment `[x - u, x + u]`). This is
the feature that distinguishes the 2002 model from Deffuant (2000) bounded confidence
(`deffuant.py`), which is opinion-only with a constant global threshold.

The dynamics are pairwise random encounters over a **fully-connected** population. One
elementary interaction draws a random **ordered** pair `(i, j)` — influencer `i` acts on
influenced `j` (asymmetric: only `j` changes). With the segment overlap

    h_ij = min(x_i + u_i, x_j + u_j) - max(x_i - u_i, x_j - u_j),

the **relative-agreement** update fires **only if `h_ij > u_i`**, and then (with
`ra = h_ij / u_i - 1`):

    x_j += mu * ra * (x_i - x_j)
    u_j += mu * ra * (u_i - u_j)

The denominator is `u_i` (the influencer's uncertainty), **not** `2*u_i` — a
low-uncertainty, confident influencer yields a larger `ra` and a stronger pull, which is
exactly why the low-uncertainty extremists are so persuasive. One sweep is N random
ordered-pair interactions; runs go to the frozen attractor (max opinion change per sweep
drops to ~5e-7 by ~sweep 150; 400 sweeps is well past freezing, confirmed by identical
`y` at 400 vs 800 sweeps).

**Population set-up** (the paper's extremism experiment): a fraction `p_e = 0.2` of
agents are **extremists** — low uncertainty `u_e = 0.1`, opinions pinned at `+-1`. The
remaining moderates start with `x ~ Uniform[-1, 1]` and a common global uncertainty `U`.
A deterministic asymmetry `delta` splits the extremists between the poles: `n_+ =
round(p_e*N*(1+delta)/2)`, `n_- = round(p_e*N*(1-delta)/2)`.

**Metric (locked):** `y = p'_+^2 + p'_-^2`, where `p'_+-` is the final fraction of
**initially-moderate** agents ending near each extreme (`|x| > 0.8`). `y ~ 0` = moderates
stay central; `y ~ 0.5` = they split evenly between the poles (double-extreme); `y ~ 1` =
one pole captures ~all of them (single-extreme). Determinism is verified in the tests
(same seed -> identical run).

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| N | 200 |
| mu | 0.5 |
| p_e (extremist fraction) | 0.2 |
| u_e (extremist uncertainty) | 0.1 |
| x_extreme_tol (capture cut) | 0.8 |
| seeds | 0...19 (20 seeds) |
| sweeps | 400 (frozen ~150) |
| P1 condition | U = 0.4, delta = 0 |
| P2 condition | U = 1.2, delta = 0 |
| P3 condition | U = 1.4, delta = 0.1 |

## Results (mean over 20 seeds; raw)

| Condition | mean y | y range | mean capture | central \|x\| | \|mean x\| |
|---|---|---|---|---|---|
| **P1** (U=0.4, d=0) | **0.088** | [0.047, 0.128] | **0.408** | 0.221 | 0.061 |
| **P2** (U=1.2, d=0) | **0.506** | [0.494, 0.538] | **0.998** | 0.040 | 0.106 |
| **P3** (U=1.4, d=0.1) | 0.513 | - | 0.998 | - | - |

P3 single-pole capture (one pole > 0.9 of moderates AND the opposite < 0.1): **0 / 20
seeds** (mean p+ = 0.52, mean p- = 0.48).

The full U-sweep (delta=0) shows the expected monotone transition, confirming the model
is faithful in shape: `y` rises smoothly with U — U=0.2 -> y=0.03 (central), U=0.6 ->
y=0.20, U=1.0 -> y=0.50, U>=1.2 -> y~0.51 (saturated double-extreme). Capture rises in
lockstep (U=0.2 -> 0.22, U=0.4 -> 0.41, U=0.8 -> 0.87, U>=1.0 -> ~1.0).

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Central convergence (U=0.4) | y<0.1 AND capture<0.15 AND central\|x\|<0.3 | y=0.088 ok, **capture=0.408 FAIL**, central\|x\|=0.221 ok | **MISS** |
| **P2** | Double-extreme (U=1.2) | y in [0.35,0.65] AND capture>0.6 AND \|mean x\|<0.2 | y=0.506 ok, capture=0.998 ok, \|mean x\|=0.106 ok | **REPRO** |
| **P3** | Single-extreme (U=1.4, d=0.1) | >=60% seeds single-pole (...) | **0% of seeds single-pole** | **MISS** |

## Honest interpretation

- **P2 (double-extreme bipolarization) reproduces cleanly and decisively.** At the higher
  moderate uncertainty U=1.2 the two low-uncertainty extremist clusters pull the moderates
  apart: essentially all moderates (capture ~ 0.998) are drawn to a pole, split ~50/50
  between them (mean p+ ~ p- ~ 0.5, so y ~ 0.5), and the population stays balanced
  (`|mean x|` = 0.11 < 0.2). This is the headline Deffuant-Amblard result — high-uncertainty
  populations bipolarize under symmetric extremists — and it passes all three sub-clauses.
  The strict P1->P2 capture step in the lock (P1's <0.15 -> P2's >0.6) is respected in the
  data by a wide margin (0.41 -> 0.998).

- **P1 is an honest MISS on the capture sub-clause (0.41 vs the <0.15 bar), not on y.**
  Two of the three P1 sub-clauses pass — y=0.088 (<0.1) and central|x|=0.221 (<0.3) — but
  the moderate-capture fraction is **0.408**, far above the locked 0.15 ceiling, and it is
  robust across all 20 seeds (per-seed range 0.31-0.50, never near 0.15). What actually
  happens at U=0.4 is **partial bipolarization with a surviving central core**: ~40% of
  moderates are dragged to the poles (split roughly evenly, ~46 to +1 and ~24 to -1 in a
  typical seed), while ~60% form a central cluster. Because the captured moderates split
  nearly symmetrically, the *quadratic* metric y stays low (each p'_+- ~ 0.2, so y ~
  2*0.2^2 ~ 0.08) even though a large fraction is captured. The locked P1 clause demanded
  BOTH low y AND low capture AND a central core; this faithful implementation delivers low
  y and a central core but **not** low capture — at u_e=0.1 the confident extremists are
  persuasive enough to reach a substantial slice of even the low-U moderates, so pure
  central convergence (extremists fully isolated) does not occur at U=0.4. Reaching the
  <0.15 capture regime would require a **lower** U (the sweep shows U=0.2 -> capture 0.22,
  still above 0.15; capture < 0.15 needs U below ~0.15), or a smaller/less-confident
  extremist minority — all of which are locked knobs the discipline forbids changing. We
  report the honest number: the capture sub-clause is falsified.

- **P3 (single-extreme) is a clear MISS: 0/20 seeds show single-pole capture at the locked
  delta=0.1.** At U=1.4 with delta=0.1 (22 positive vs 18 negative extremists) the outcome
  is double-extreme, essentially identical to the symmetric P2 case — the small extremist
  imbalance nudges the split to p+~0.52 / p-~0.48 but never collapses to a single pole.
  The single-extreme attractor **does exist in this implementation** — we confirmed during
  characterization that increasing the asymmetry to delta=1.0 (all extremists positive)
  yields single-pole capture in exactly 60% of seeds with the + pole always winning, and
  delta=0.7 shifts the mean split to p+~0.73 — but the *locked* delta=0.1 is far too weak
  to break the double-extreme tie at N=200. The prediction that a delta=0.1 asymmetry alone
  drives >=60% of seeds to single-extreme is **falsified** in this faithful model; the
  deterministic asymmetry required is much larger than the locked value. Reported as a MISS.

**Bottom line:** the reproduction cleanly demonstrates the model's central *mechanism* —
low-uncertainty extremists at the poles drive high-uncertainty moderate populations to
**double-extreme bipolarization** (P2 REPRO, all sub-clauses) — and honestly reports the
two falsified quantitative predictions: at U=0.4 the moderates only *partially* stay
central (capture 0.41 >> 0.15, P1 MISS), and a delta=0.1 asymmetry is far too weak to
produce single-extreme convergence (0/20 seeds, P3 MISS), even though the single-extreme
attractor is reachable at much larger delta. The metric, thresholds, and every parameter
were locked before running; falsified clauses are reported, not tuned away.

## Source

Deffuant, G., Amblard, F., Weisbuch, G., Faure, T. (2002). *How can extremism prevail? A
study based on the relative agreement interaction model.* Journal of Artificial Societies
and Social Simulation 5(4):1. https://www.jasss.org/5/4/1.html

Scope: a faithful reproduction of a published synthetic model; no real-world data. The
contribution is whether the harness + locked-prediction discipline reproduce the
central / double-extreme / single-extreme regimes of the relative-agreement model, and
would catch an artifact.
