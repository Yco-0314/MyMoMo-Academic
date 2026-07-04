# Optional Public Goods with Loners (Hauert et al. 2002) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Genuine agent-based reproduction on
`abm_auto._platform`. Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the config below was fixed before the run and was NOT tuned to
make any clause pass.

## What was built

A population of `PlayerAgent`s, each carrying a strategy in {C (cooperator), D (defector),
L (loner)}. Every generation is a **synchronous** imitation-with-mutation update: from one
start-of-generation snapshot of the three expected payoffs, every agent meets one random
peer and adopts the peer's strategy with probability proportional to the positive payoff
gap (pairwise comparison / replicator imitation); with tiny probability `mu` it instead
mutates to a random strategy; then all new strategies commit at once. This is a genuine
agent-based IBM — each agent decides for itself; there is no god-loop.

The payoffs are the **exact** optional public-goods form of Hauert et al. (2002), cost
`c = 1`, group size `N = 5`, multiplication factor `r`, loner payoff `sigma` with
`0 < sigma < r-1`:

- A group of `N` is sampled; only participants (C or D, not L) play. With `S`
  participants and `n_c` cooperators among them, the pot `r*n_c*c` is split over all `S`
  participants: a **defector** keeps its share `P_d = r*n_c/S`; a **cooperator** paid the
  cost, `P_c = P_d - 1`.
- A **loner** always earns `sigma`.
- A **lone participant** (`S = 1`) cannot play and is forced to `sigma` — the crucial term
  that makes small cooperator clusters viable once loners abound (C beats L).

The closed-form per-strategy expected payoff (exact expectation over the binomial group
sampling) is verified equal to a 200k-trial Monte-Carlo group-sampling estimate in the
tests.

The **compulsory control** is the *same* model with the loner strategy **removed** (only
C and D). Every other knob — `pop`, `r`, `sigma`, `N`, `mu`, the seeds — is identical.
This isolates "voluntary participation is what rescues cooperation".

### Why the tiny-mutation, bounded-horizon protocol (from the lock)

The interior fixed point `Q` of the C/D/L replicator flow is a **neutrally-stable
center**: the flow circles it on closed orbits, and a finite population with pure
imitation performs a random walk along those orbits that eventually drifts to the simplex
boundary and **fixates** — a finite-size artifact that would read as a FALSE miss of the
coexistence prediction. Per the locked PROTOCOL we run a **large** population
(`pop = 5000`) with a **tiny** mutation rate (`mu = 1e-3`) over a **bounded** horizon
(3000 generations, time-averaged over the last 2000), across **5 seeds**. The mutation is
exploration that keeps the orbit off the boundary; it does not manufacture the cycle.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| population | 5000 |
| group size N | 5 |
| mutation mu | 1e-3 |
| seeds | 0,1,2,3,4 (5 seeds) |
| generations / burn-in | 3000 / measure from 1000 |
| regime HI | r = 3.0, sigma = 1.0 (r > 2) |
| regime LO | r = 1.8, sigma = 0.5 (r <= 2) |
| cost c | 1 |

`sigma` is kept strictly inside `(0, r-1)` in both regimes (HI: 1 in (0,2); LO: 0.5 in
(0,0.8)).

## Results (mean over 5 seeds; raw)

| Arm | mean time-avg fC | mean fD | mean fL | coop amplitude |
|---|---|---|---|---|
| **VOLUNTARY r=3, sigma=1** | **0.287** | 0.352 | 0.362 | **0.961** |
| **COMPULSORY r=3** (loner removed) | **0.0018** | 0.998 | 0.000 | 0.004 |
| **VOLUNTARY r=1.8, sigma=0.5** | 0.0022 | 0.0021 | **0.996** | 0.282 |

Per-seed voluntary-HI fC: 0.290, 0.287, 0.286, 0.287, 0.283 (std ~ 0.002).
Per-seed voluntary-HI fL: 0.362, 0.362, 0.361, 0.360, 0.364.
Per-seed compulsory-HI fC: 0.002 across all five seeds.
Per-seed voluntary-LO fL: 0.996, 0.996, 0.993, 0.996, 0.997.

The voluntary r=3 run does not settle to the interior point — it **cycles** around it: the
cooperator frequency swings across nearly the whole [0,1] range (peak-to-trough amplitude
~ 0.96) in the never-ending D->L->C->D chase (the Red Queen), while the **time-average** of
each strategy sits near a third. Turning off voluntary participation (the compulsory
control) collapses the population to essentially all-defect (fC ~ 0.002). Dropping to
r=1.8 (below the r=2 threshold) makes participating unprofitable enough that the loner
takes over almost entirely (fL ~ 0.996) while cooperation nearly vanishes.

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | RPS three-strategy coexistence (r=3, sigma=1) | each of C/D/L time-avg in (0.05, 0.90) AND coop amplitude > 0.10 | C=0.287, D=0.352, L=0.362; amp=0.961 | **REPRO** |
| **P2** | Voluntary prevents all-D collapse | compulsory coop < 0.05; voluntary coop >= 0.15 AND exceeds compulsory by >= 0.10 | comp=0.002, vol=0.287, gap=0.285 | **REPRO** |
| **P3** | Regime flip across r=2 | r=1.8: loner > 0.5 AND coop < 0.15; r=3: coop >= 0.15 | r=1.8: L=0.996, C=0.002; r=3: C=0.287 | **REPRO** |

## Honest interpretation

- **The loner opt-out induces genuine RPS cycling and coexistence (P1).** With voluntary
  participation, no strategy fixates: the time-averaged frequencies of C, D and L all sit
  comfortably inside the (0.05, 0.90) coexistence band (0.29 / 0.35 / 0.36), and the
  cooperator frequency does not hold steady — it **cycles** with peak-to-trough amplitude
  ~ 0.96, the never-ending D->L->C->D chase of the Red Queen. This is exactly the finite-N
  behaviour Hauert et al. describe: circulation around the neutrally-stable interior
  center, sustained (not collapsed onto the boundary) by the tiny mutation the locked
  protocol prescribes. Time-averaged coexistence + large amplitude are both met.

- **Voluntary participation is unambiguously the cause of the rescue (P2).** The
  compulsory control — the same model with the loner strategy removed — collapses to
  essentially all-defect (cooperator time-average ~ 0.002), the sterile Nash outcome of
  the ordinary public-goods game. Restoring the opt-out lifts the cooperator time-average
  to 0.287, a gap of 0.285 over the compulsory arm. That contrast *is* the Hauert result:
  the ability to abstain, not any change to the payoffs, is what keeps cooperation alive.

- **The regime flips across r = 2, with the loner as a release valve (P3).** At r = 1.8
  (below the threshold where a full group of cooperators beats a loner) participating
  rarely pays, so the loner strategy takes over almost entirely (fL ~ 0.996) and
  cooperation nearly vanishes (fC ~ 0.002). At r = 3 (above the threshold) cooperation
  persists on time-average (fC ~ 0.287). The loner absorbs the population precisely when
  the public good is too weak to be worth joining, and steps aside when it is worth
  joining — the "release valve" behaviour.

- **These are robust, not seed artifacts.** Across all five seeds the time-averaged
  frequencies are tight (voluntary-HI fC std ~ 0.002; compulsory fC = 0.002 on every seed;
  loner-LO fL >= 0.993 on every seed). The results do not hinge on a lucky seed.

**Bottom line:** the reproduction cleanly demonstrates all three claims of Hauert et al.
(2002) — loner-induced RPS coexistence with genuine cycling, voluntary participation as
the cause of the rescue from all-defect collapse, and the r = 2 regime flip with the loner
as a release valve — with tight seed-to-seed agreement.

## Source

Hauert, C., De Monte, S., Hofbauer, J. & Sigmund, K. (2002). *Volunteering as Red Queen
mechanism for cooperation in public goods games.* Science 296:1129-1132.
doi:10.1126/science.1070582.

Scope: a faithful reproduction of a published synthetic model; no real-world data. The
contribution is whether the harness + locked-prediction discipline reproduce the
loner-induced RPS coexistence, isolate voluntary participation as the rescue of
cooperation, and would catch an artifact.
