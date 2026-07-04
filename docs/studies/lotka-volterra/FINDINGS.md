# Agent Lotka-Volterra Predator-Prey — FINDINGS

**Model:** Lotka (1925, *Elements of Physical Biology*) / Volterra (1926, *Nature*
118:558-560), reproduced as a **genuine agent-based model** in the standard NetLogo
"Wolf Sheep Predation" (Wilensky 1997) wolf-sheep-grass style on the neutral platform
(`abm_auto._platform`): individual `PreyAgent`s and `PredatorAgent`s step on a toroidal
grid; the model owns the grass resource + birth/death bookkeeping + a `DataCollector` for
the two population series. Graded on the LOCKED outcome: the prey & predator population
time series (survival fraction, peak counts, and the predator-vs-prey cross-correlation
lag). Predictions P1-P3 were locked BEFORE the run (`PREDICTIONS-locked.md`); the
parameters and analysis choices were fixed before the run and nothing below was tuned
after seeing a verdict.

## What was run

A 100x100 **toroidal** grid. Each tick, every living agent acts once in a single random
interleaved order:

- **Prey (the "sheep")** move to a uniformly-random Moore neighbour (paying 1 energy),
  eat the grass on the new cell if it is grown (gain +5 energy and reset that cell's
  regrow clock), die if energy < 0, then reproduce with probability 0.03 (splitting their
  energy in half with a new offspring on the cell).
- **Predators (the "wolves")** move (pay 1 energy), eat one living prey on their cell if
  present (gain +25 energy; that prey dies), die if energy < 0, then reproduce with
  probability 0.04 (split energy).
- **Grass** is the prey's food and the **carrying-capacity term**: a grazed cell regrows
  40 ticks later. Without this finite, regrowing resource the discrete stochastic system
  would not settle onto a sustained cycle (the prey would grow unbounded between predator
  crashes); the grass supplies the logistic ceiling that lets the limit cycle sustain.

**Locked configuration (fixed before the run, NOT tuned to a verdict):** L=100, prey0=500,
pred0=100, prey_gain=5, pred_gain=25, prey_reproduce=0.03, pred_reproduce=0.04,
move_cost=1, grass_regrow=40, 1000 ticks, seeds 0-9 (10 seeds). **Analysis choices (also
locked):** the macroscopic cycle is read off a 25-tick centred moving average of each
population series (the raw per-tick series carry heavy demographic noise); a peak must
rise at least 10% of the series' peak-to-trough amplitude above its flanking valleys to
count; the cross-correlation is searched over lags in [-200, +200] ticks with the
convention that a POSITIVE peak lag means the predator follows the prey.

## Results

**Survival fraction = 1.00 (10/10 seeds).** Neither species went extinct in any seed over
the full 1000 ticks. Populations cycle in sustained, coupled oscillations: prey roughly
in [450, 910] and predators roughly in [50, 225] across seeds.

| seed | survived | prey range | pred range | peaks prey/pred | last-third prey/pred | best lag | corr |
|------|----------|------------|------------|-----------------|----------------------|----------|------|
| 0 | yes | 466-867 | 53-203 | 30/20 | 2/8 | +119 | 0.158 |
| 1 | yes | 453-826 | 82-207 | 28/17 | 8/2 | +79  | 0.458 |
| 2 | yes | 477-842 | 58-206 | 29/20 | 10/1 | +200 | 0.207 |
| 3 | yes | 483-838 | 82-218 | 26/27 | 0/8 | +83  | 0.466 |
| 4 | yes | 471-842 | 63-194 | 31/25 | 1/11 | +81  | 0.327 |
| 5 | yes | 472-845 | 74-223 | 28/43 | 0/9 | +200 | 0.010 |
| 6 | yes | 462-870 | 56-225 | 26/23 | 1/9 | +185 | 0.011 |
| 7 | yes | 486-851 | 58-223 | 31/24 | 7/9 | +164 | 0.302 |
| 8 | yes | 474-912 | 52-204 | 38/31 | 8/10 | +71 | 0.323 |
| 9 | yes | 469-842 | 76-211 | 19/29 | 3/8 | +113 | 0.210 |

- **Both populations oscillate (>=2 peaks each) in 10/10 seeds.**
- **The cross-correlation peaks at a POSITIVE lag in all 10/10 surviving seeds**
  (best lags +71 to +200, median **+119**): the predator population peaks AFTER the prey
  population — the Lotka-Volterra signature.
- **Oscillation persists into the last third of the run** (both species show >=1 smoothed
  peak in the trailing third) in **8/10** surviving seeds.

## Verdicts on the LOCKED metrics

| # | Prediction | Pass clause | Measured | Verdict |
|---|------------|-------------|----------|---------|
| P1 | Sustained oscillations, no extinction | both species >=2 peaks AND neither extinct in >=60% of seeds | 10/10 = 1.00 (survival 1.00) | **REPRO** |
| P2 | Predator lags prey | cross-corr(prey, predator) peaks at a POSITIVE lag (majority of surviving seeds; positive median) | 10/10 positive, median lag +119 | **REPRO** |
| P3 | Persistence (not a single transient spike) | oscillation continues into the last third (both species peak there) in >=60% of surviving seeds | 8/10 = 0.80 | **REPRO** |

All three locked clauses **REPRO** (3/3).

## Honest caveats

- **Agent Lotka-Volterra is extinction-prone, and this is reported plainly.** At this
  locked parameterisation the predator is efficient enough to drive prey crashes yet the
  grass carrying-capacity floor keeps the prey from being wiped out, so all 10 seeds
  survived. This is a *property of the chosen regime*, not a universal feature — pushing
  predator efficiency higher, or removing the grass resource, makes one or both species
  extinction-prone and would correctly drop the survival fraction (and P1 would then be a
  MISS, by the locked >=60% clause). The parameters were chosen for a sustainable cycle
  before the run; they were not tuned afterward.
- **The cross-correlation magnitude is modest in some seeds** (corr ~0.01-0.47), and the
  lag is only *meaningful* where the correlation is clear. **Honest correction (LV review
  2026-06-30): P2's evidence is robust on the ~6-7 clear-cycle seeds** (corr ≳ 0.15: seeds
  0,1,3,4,7,8 → lags +71 to +164, predator clearly after prey). **On the 2 near-zero-corr
  seeds (5,6: corr ≈ 0.01) the reported "lag" (+200, +185) sits at / near the ±200 search
  boundary — there is no clear cyclic phase there, so that "positive lag" is an
  argmax-of-noise artifact, not real evidence.** So "positive lag in 10/10" is technically
  true but partly carried by no-signal seeds; the genuine predator-after-prey signature
  rests on the clear-cycle seeds. The weak correlation comes from (a) only a few full cycles
  fitting in 1000 ticks and (b) demographic noise. The locked P2 claim is about the *sign of the peak lag*
  (predator after prey), which holds cleanly; it is not a claim about a high correlation
  coefficient.
- **The continuous Lotka-Volterra ODEs are neutrally stable** (amplitude set by initial
  conditions). The agent model is NOT that idealisation — it is a stochastic, discrete,
  spatial system whose amplitude is set by demographic noise against the grass-imposed
  carrying capacity. We reproduce the *qualitative* LV result (sustained coupled
  oscillations, predator lagging prey), which is the standard and honest claim for the
  agent-based realisation; we do not claim to recover the ODEs' exact neutral cycles.
- **Synthetic-model reproduction.** No real-world data; the contribution is whether the
  harness + lock-first discipline reproduce the predator-prey oscillation-with-lag result
  and would catch an artifact (e.g. a sign-flipped lag, or an extinction the survival
  fraction would expose).
