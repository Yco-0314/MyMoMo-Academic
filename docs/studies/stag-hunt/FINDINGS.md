# Stag Hunt coordination game (Skyrms 2004) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Genuine agent-based reproduction on
`abm_auto._platform`. Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the payoff sets, N, replicate count, x0 grid, update rule,
and seeds below were fixed before the run and were NOT tuned to make any clause pass.

## What was built

A well-mixed population of N=1000 `StrategyAgent`s, each a pure **Stag** or pure
**Hare** hunter, playing the symmetric 2x2 coordination game with payoffs
**R > T > P > S_**:

| | opponent Stag | opponent Hare |
|---|---|---|
| **play Stag** | R (payoff-dominant reward) | S_ (the "sucker": lone stag-hunter) |
| **play Hare** | T (safe hare while partner chased) | P (risk-dominant safe outcome) |

Each **generation** (one tick) is: (1) shuffle the roster and pair adjacent agents,
each pair plays one contest and accumulates its realised payoff; (2) **payoff-
proportional imitation** (Schlag 1998) — every agent draws one random *model* agent and,
iff that model scored strictly higher, copies the model's strategy with probability
`(model.payoff - self.payoff) / (R - S_)`. The update is staged then committed
(synchronous), reads exactly two agents (self + one model), and never consults the global
stag fraction — so the replicator flow **emerges** from N interacting agents rather than
being integrated as an ODE.

The analytic anchor (COMPARED against, never fed in) is the **unstable interior fixed
point** `x* = (P - S_) / ((R - T) + (P - S_))`, the fraction of Stag at which Stag and
Hare have equal expected payoff. It is the **separatrix** of the two basins: start above
it -> the population fixates on **all-Stag** (payoff-dominant); start below it -> **all-
Hare** (risk-dominant). Both pure states are absorbing (a uniform population has no
strictly-better model to copy). The canonical payoffs `(R,T,P,S_)=(4,3,2,0)` give
x*=0.667.

**Distinctness from Hawk-Dove (same platform, opposite geometry).** Hawk-Dove has a
single *stable* interior mixed ESS p*=V/C where Hawk and Dove coexist forever; the stag
hunt's interior point is *unstable* and every run fixates on ONE pure strategy. A
Hawk-Dove rerun converges to its interior mix (~0.5 at V=2,C=4); a stag-hunt rerun never
does — it lands on 0 or 1.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| N | 1000 |
| canonical payoffs (R,T,P,S_) | (4, 3, 2, 0) -> x*=0.667 |
| P3 payoff sets | (4,3,2,0)->0.667, (5,3,2,0)->0.500, (5,3,2,1.5)->0.200 |
| basin replicates (P2), x0~U(0,1) | 500 (seeds 0..499, seed also draws x0) |
| x0 grid (P1/P3 threshold) | 0.05 ... 0.95 step 0.05 (19 points) |
| P1 direct-start probes | x0=0.5 and x0=0.9, 40 seeds each |
| update rule | payoff-proportional imitation (mean field = replicator) |

## Results (raw)

**P1 — canonical basin threshold (x*=0.667).** Grid separatrix **x*_emp = 0.675**
(highest x0 that fixated Hare = 0.65; lowest that fixated Stag = 0.70). Direct-start
fixation over 40 seeds: **P(all-Stag | x0=0.5) = 0.000**, **P(all-Stag | x0=0.9) =
1.000**.

**P2 — basin of attraction, x0~U(0,1), 500 replicates.** **P(fixate Hare) = 0.692**,
**P(fixate Stag) = 0.308** (all 500 runs reached a pure absorbing state). The risk-
dominant Hare owns ~69% of the basin — as predicted, ~= x*=0.667 and strictly larger than
the Stag basin.

**P3 — threshold tracks the payoff formula.**

| payoffs (R,T,P,S_) | analytic x* | empirical x*_emp | \|err\| |
|---|---|---|---|
| (4, 3, 2, 0)   | 0.667 | 0.675 | 0.008 |
| (5, 3, 2, 0)   | 0.500 | 0.525 | 0.025 |
| (5, 3, 2, 1.5) | 0.200 | 0.225 | 0.025 |

The empirical separatrix moves with the payoffs across {0.667, 0.500, 0.200} — it is not
a fixed 50/50. Worst error 0.025, well inside the +-0.05 bar. (The small positive bias
reflects the grid resolution: x*_emp is the midpoint of a 0.05-wide bracket, so it reads
one grid step above the true crossover.)

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Bistable threshold at predicted x* | x*_emp in [0.62,0.72]; P(all-Stag)<=0.05 at x0=0.5, >=0.95 above x* | x*_emp=**0.675**; **0.000** / **1.000** | **REPRO** |
| **P2** | Risk-dominant Hare basin strictly larger | P(Hare)=0.667+-0.05 AND > P(Stag) | **0.692** > **0.308** | **REPRO** |
| **P3** | Threshold tracks the payoff formula | \|x*_emp - x*\| <= 0.05 for {0.667,0.500,0.200} | worst \|err\|=**0.025** | **REPRO** |

## Honest interpretation

- **Bistability, not mixing (P1).** From a start below the interior fixed point the
  population collapses to all-Hare; from above it climbs to all-Stag. At x0=0.5 (below
  the canonical x*=0.667) not one of 40 seeds reached Stag; at x0=0.9 all 40 did. The
  empirical separatrix (0.675) sits right on the analytic 0.667. This is the defining
  stag-hunt signature — two pure equilibria separated by an unstable threshold — and it
  is exactly what distinguishes this game from the single mixed ESS of Hawk-Dove.

- **Risk dominance beats payoff dominance in the basin (P2).** Over 500 random starts the
  risk-dominant Hare captured 69% of outcomes versus 31% for the payoff-dominant Stag.
  The safe strategy owns the larger basin even though mutual Stag is the collectively
  better outcome — the classic tension Skyrms studies. The measured 0.692 matches the
  predicted x*=0.667 (the fraction of (0,1) below the separatrix) within tolerance.

- **The threshold is a function of the payoffs, not a constant (P3).** Re-parameterising
  to push x* down to 0.500 then 0.200 moves the empirical separatrix in lockstep
  (0.525, 0.225). The dynamics honestly implement `x* = (P-S_)/((R-T)+(P-S_))`; a model
  that always split 50/50 would fail this clause outright.

**Bottom line:** the reproduction cleanly recovers all three pillars of the stag-hunt
result — a bistable two-basin structure, a larger basin for the risk-dominant
equilibrium, and a separatrix that tracks the analytic payoff formula — from a genuinely
agent-based imitation process, and it is structurally distinct from the co-existence
equilibrium of the Hawk-Dove reproduction on the same platform.

## Source

Skyrms, B. (2004). *The Stag Hunt and the Evolution of Social Structure.* Cambridge
University Press. doi:10.1017/CBO9781139165228. (Coordination-game lineage: Maynard
Smith & Price 1973, *Nature* 246:15-18.)

Scope: a faithful reproduction of a published coordination-game model; no real-world
data. The contribution is whether the harness + locked-prediction discipline reproduce
the bistable equilibrium selection, show the risk-dominant basin is larger, confirm the
separatrix tracks the analytic payoff formula, and would catch an artifact.
