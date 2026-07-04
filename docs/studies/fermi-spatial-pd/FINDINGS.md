# Fermi-Rule Spatial Prisoner's Dilemma (Szabó-Tőke 1998) — FINDINGS

**Status: 1/3 locked clauses REPRO. P1 REPRO. P2 and P3 are honest MISSes — both on a
QUANTITATIVE sub-clause, while the qualitative physics each targets is reproduced.**
Genuine agent-based reproduction on `abm_auto._platform`. Predictions were locked BEFORE
running (`PREDICTIONS-locked.md`); the config below was fixed before the run and was NOT
tuned to make any clause pass, and NO parameter, fit window, or extinction criterion was
searched after the fact to move a MISS toward REPRO.

## What was built

A square LxL **periodic** lattice of pure cooperators (C=1) / defectors (D=0), updated by
the genuine **random-sequential Fermi (pairwise-comparison) rule**. Weak-PD payoffs (the
Szabó-Tőke rescaling): against each neighbour a C scores R=1 per C partner and S=0 per D;
a D scores T=b per C partner and P=0 per D. One elementary step picks a random focal x
and one random von Neumann neighbour y; x adopts y's strategy with probability

    W = 1 / (1 + exp(-(E_y - E_x)/K)),

where E_x, E_y are the two sites' accumulated payoffs and K is the selection noise. One
Monte-Carlo **sweep** = L^2 elementary steps. The stationary cooperator density `c` is
averaged over the last measurement sweeps after a transient.

This is the *same* spatial PD as `nowak_may_pd`, but with a STOCHASTIC update instead of
deterministic best-takes-over. That single change gives it three properties the
deterministic model does not have: a smooth intermediate coexistence density, a
**continuous** (not discrete-step) extinction transition, and an **optimal intermediate
noise** K. All three are reproduced qualitatively here; two of the three have a locked
*quantitative* bar that this few-minutes reproduction does not clear.

**Two specs, as the lock permits (documented per clause):**

- **P1, P2** use the 1998 **primary** model: von Neumann z=4 **with self-interaction**
  (each site also plays its own strategy - R for a C, P=0 for a D).
- **P3** uses the **no-self-interaction** von Neumann spec, where the noise
  non-monotonicity is clean (the lock instructs P3 be measured here; a Moore
  neighbourhood is monotone-decreasing and is deliberately NOT used).

**Vectorisation (keeps L=400-500 tractable, ~0.03 s/sweep at L=400):** a sweep is
realised as conflict-free vectorised batches over a random permutation of focal sites.
Payoffs are recomputed from the live lattice before each batch, and within a batch no
site is both a focal and a chosen neighbour (and no neighbour is targeted twice), so every
elementary step reads the current lattice and commits immediately - faithful
random-sequential dynamics at numpy speed. Tests pin the payoff matrix, the z=4 periodic
neighbourhood, the self-interaction convention, the exact Fermi logistic, the conflict-free
invariant, absorbing all-C / all-D states, and same-seed determinism (16 tests, all green).

## Locked config (FIXED before the run; not tuned)

| Clause | Spec | L | K | sweeps (measure) | grid |
|---|---|---|---|---|---|
| P1 | self-int vN z=4 | 400 | 0.1 | 400 (last 40) | b in {1.4, 1.9} |
| P2 | self-int vN z=4 | 500 | 0.5 | 300 (last 50) | b = 1.40..1.78 step 0.02 |
| P3 | **no**-self-int vN z=4 | 200 | grid | 500 (last 60) | K in {0.05,0.20,0.32,0.50,1.0,1.5}, b_cr by bisection |

## Results (graded run)

### P1 - cooperators survive above b=1 (K=0.1, self-interaction) -> REPRO
- **c(b=1.4, K=0.1) = 0.5411** - inside the locked window [0.35, 0.65] (paper 0.515). A
  smooth intermediate density: not 0, not 1. A deterministic best-takes-over rerun of the
  same lattice cannot produce this.
- **c(b=1.9, K=0.1) = 0.00042** - extinction. b=1.9 sits at/above the paper's b_c2~1.85-1.90,
  where the all-D state is absorbing. The residual ~4 cooperators per 10^4 sites is
  finite-size / finite-K flicker, not coexistence; graded as extinct (c <= 0.01).
- **Verdict: REPRO.**

### P2 - the C->extinction transition (K=0.5): CONTINUOUS shape, but non-DP exponent -> MISS
The C-density falls **smoothly and monotonically** from c=0.576 (b=1.40) to ~0 near
b_c2~1.74, with NO discrete step:

```
b:  1.40 1.44 1.48 1.52 1.56 1.60 1.64 1.66 1.68 1.70 1.72 1.74
c: 0.576 .497 .429 .365 .305 .240 .168 .123 .077 .034 .010 .003
```

- **Continuity sub-clause PASSES:** the largest single Delta-b=0.02 drop in c is 0.046,
  far below the 0.20 "looks discrete" bar. The transition is unmistakably second-order,
  not a first-order jump - exactly the property that separates the stochastic Fermi PD
  from the deterministic Nowak-May model.
- **DP-exponent sub-clause FAILS:** the fitted c ~ (b_c2 - b)^beta gives **beta ~ 1.3**
  over the full coexistence range (and rises to 1.8-3.5 if restricted to the near-critical
  tail), versus the locked directed-percolation window [0.45, 0.75] (paper 0.59). A DP
  transition has beta < 1 (c drops STEEPLY, concave, into b_c2); our finite-L data drops
  smoothly, almost linearly, giving beta > 1. This is a real quantitative miss, not a
  fit artifact: no admissible (b_c2, window) choice brings beta into [0.45,0.75] - narrowing
  to the tail makes it WORSE, not better.
- **Verdict: MISS** (continuous transition reproduced; the DP critical exponent is not,
  under a plain power-law fit at this system size).

### P3 - noise NON-monotonicity: an optimal intermediate K (no self-interaction) -> MISS
The survival threshold b_cr(K) is **peaked at intermediate K**, exactly the shape the
paper reports:

| K | 0.05 | 0.20 | 0.32 | 0.50 | 1.00 | 1.50 |
|---|---|---|---|---|---|---|
| b_cr (L=200) | 1.023 | 1.086 | 1.102 | 1.086 | 1.070 | 1.070 |

- **Peak-K sub-clause PASSES:** the peak sits at K=0.32, inside the locked [0.2, 0.5] band.
  The non-monotonicity (rise then fall) is unambiguous.
- **Rise-magnitude sub-clause FAILS:** b_cr(0.32) - b_cr(0.05) = 1.102 - 1.023 = 0.078,
  just below the locked >=0.10 bar.
- **Verdict: MISS** (non-monotonicity and peak location reproduced; the magnitude of the
  rise is ~0.02 short of the locked bar).

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Stochastic + spatial coexistence | c(1.4,0.1) in [0.35,0.65] AND c(1.9)~0 | c=0.541, c=0.0004 | **REPRO** |
| **P2** | Continuous DP transition at K=0.5 | no Delta-b=0.02 jump>0.20 AND beta in [0.45,0.75] | jump 0.046 OK; beta~1.3 | **MISS** (exponent) |
| **P3** | Optimal intermediate K (no self-int) | b_cr(0.32)-b_cr(0.05)>=0.10 AND peak K in [0.2,0.5] | rise 0.078; peak K=0.32 OK | **MISS** (magnitude) |

## Honest interpretation

- **All three qualitative Szabó-Tőke phenomena are reproduced, and all three separate the
  stochastic Fermi model from the deterministic Nowak-May model.** At K=0.1 cooperators
  reach a smooth ~0.54 coexistence density at b=1.4 and go extinct by b=1.9 (P1, REPRO).
  At K=0.5 the collapse to all-D is a **continuous** second-order transition, not a
  discrete step (P2 continuity sub-clause, PASS). And the survival threshold is
  **non-monotonic in the noise K**, peaking at intermediate K=0.32 (P3 peak-K sub-clause,
  PASS). The K-noise dependence, the continuous transition, and the optimal-noise effect
  all require the stochastic pairwise-comparison rule; the deterministic model has none of
  them. That mechanistic contrast is the point of the reproduction, and it holds.

- **Where the reproduction falls short is on the two QUANTITATIVE critical-region bars,
  and it falls short in the direction a finite, short reproduction predictably would.**
  Both the DP exponent beta=0.59 (P2) and the dramatic b_cr rise (P3) are near-critical /
  large-system quantities: the paper extracts them with careful finite-size scaling on
  large lattices and long runs. This reproduction uses L=500 (P2) / L=200 (P3) and a few
  hundred sweeps per point - enough to see the correct SHAPE of each effect, but not to
  resolve the asymptotic critical exponent or the full threshold rise. Our finite-L
  density curve is smoother than the true singularity (beta comes out ~1.3 instead of
  ~0.6), and our b_cr rise saturates ~0.02 below the locked bar. These are honest
  MISSes, reported as such. The discipline forbids searching for a b_c2, a fit window, an
  extinction criterion, or a lattice size that would nudge either number across its bar,
  and we did not: the P2 beta is out of the window under EVERY admissible fit, and the P3
  rise is reported at the locked grid.

- **A note on the locked bars.** The locked P2 (beta in [0.45,0.75]) and P3 (rise >= 0.10,
  no-self-interaction von Neumann) thresholds are set to the paper's large-system values.
  A faithful "few-minutes" reproduction on 200-500-site lattices reproduces the
  qualitative physics but not those exact critical-region numbers. The value of the run is
  that the harness + locked-prediction discipline (a) reproduce the mechanisms, (b)
  distinguish this stochastic model from its deterministic sibling, and (c) report the
  quantitative shortfalls honestly rather than tuning to hit the bar.

**Bottom line:** 1/3 clauses REPRO (P1). P2 and P3 are honest MISSes on their quantitative
critical-region sub-clauses - the DP exponent (beta~1.3 vs locked [0.45,0.75]) and the
noise-driven threshold rise (0.078 vs locked >=0.10) - even though the continuous-transition
shape (P2) and the optimal-intermediate-noise peak location (P3) are both reproduced.

## Source

Szabó, G. & Tőke, C. (1998). *Evolutionary prisoner's dilemma game on a square lattice.*
Physical Review E 58:69-73. doi:10.1103/PhysRevE.58.69.

Scope: a faithful reproduction of a published synthetic model; no real-world data. The
contribution is whether the harness + locked-prediction discipline reproduce the Fermi
spatial PD's stochastic coexistence, its continuous (directed-percolation) transition, and
its optimal-intermediate-noise effect - none of which the deterministic `nowak_may_pd`
model has - and would catch an artifact.
