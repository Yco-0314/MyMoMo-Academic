# Daisyworld (Watson & Lovelock 1983) — FINDINGS

**Status:** 2/3 locked clauses REPRO, 1/3 MISS (honest). Genuine agent-based, spatial.

## What was built

A genuine **agent-based, spatial** Daisyworld on a 50x50 toroidal grid. Each cell is a
`Patch` **agent** (rides `abm_auto._platform`: `Agent` / `AgentModel` / `DataCollector`)
that perceives its own local temperature and, on its turn, **acts**: an occupied daisy
patch dies at a fixed age-out rate gamma, and a daisy patch colonises an empty von-Neumann
neighbour with a probability set by a parabolic growth response to *that neighbour's* local
temperature. This is the spatial agent-based analogue of Watson & Lovelock's two-ODE box
model -- temperature regulation is **emergent from local selection**, with no global control
law.

The two experimental arms differ in **exactly one thing**: the presence of daisies. The bare
control uses the same grid, the same albedos, the same luminosity grid, the same seeds, and
the same temperature rule -- it just has no biota (FAIR).

### Temperature rule (the load-bearing physical assumption -- documented)

1. **Planetary mean** from a Stefan-Boltzmann energy balance
   `S * L_sol * (1 - A_bar) = sigma * T_K^4`, where `A_bar` is the mean planetary albedo.
   The solar constant `S` is chosen so an all-bare planet sits at the daisy optimum
   (22.5 C) at `L_sol = 1.0`.
2. **Local albedo correction** `T_cell = T_planet + q * (A_bar - albedo_cell)` with
   `q = 30 C` per unit albedo -- a darker cell (black daisy, low albedo) is locally
   **warmer**; a brighter cell (white daisy) locally **cooler**. This is the
   Watson-Lovelock local-heating term, and it is what couples life to climate at the patch
   level.
3. **Diffusion**: blend each cell 50% toward its Moore-8 neighbour mean (one pass), so heat
   spreads between patches (as in the NetLogo Daisyworld).

### Growth response

`beta(T) = max(0, 1 - k*(T_opt - T)^2)`, a downward parabola peaking at `T_opt = 22.5 C`,
reaching 0 at +/- 17.5 C from the optimum (so daisies grow roughly between 5 C and 40 C
local temperature). Black and white daisies share the **same** beta curve; they differ only
in albedo, so the selection between them is purely via the local temperature each colour
creates. Death is temperature-independent (gamma = 0.1/tick).

**FIXED before the run (no tuning):** L=50; albedos bare/black/white = 0.5/0.25/0.75;
T_opt=22.5; parabola curvature k; gamma=0.1; local_gain=30; diffuse=0.5; the L_sol grid
[0.7...1.3] (13 points); seeds {0,1,2}.

## Results (seed-averaged over 3 seeds, equilibrated 250 ticks, last 50 averaged)

| L_sol | WITH-daisy T (C) | black | white | bare | BARE-control T (C) |
|------:|-----------------:|------:|------:|-----:|-------------------:|
| 0.70 | -2.72 | 0.000 | 0.000 | 1.000 | -2.72 |
| 0.75 |  1.98 | 0.000 | 0.000 | 1.000 |  1.98 |
| 0.80 | 25.19 | 0.794 | 0.201 | 0.005 |  6.46 |
| 0.85 | 25.84 | 0.728 | 0.266 | 0.007 | 10.73 |
| 0.90 | 23.75 | 0.627 | 0.366 | 0.006 | 14.81 |
| 0.95 | 22.87 | 0.555 | 0.438 | 0.006 | 18.73 |
| 1.00 | 22.23 | 0.493 | 0.500 | 0.007 | 22.50 |
| 1.05 | 23.09 | 0.456 | 0.537 | 0.006 | 26.13 |
| 1.10 | 21.41 | 0.393 | 0.601 | 0.006 | 29.63 |
| 1.15 | 21.19 | 0.351 | 0.643 | 0.006 | 33.01 |
| 1.20 | 19.87 | 0.301 | 0.693 | 0.007 | 36.29 |
| 1.25 | 18.95 | 0.259 | 0.734 | 0.008 | 39.46 |
| 1.30 | 42.54 | 0.000 | 0.000 | 1.000 | 42.54 |

- **WITH-daisy temperature range over the FULL locked grid [0.7,1.3] = 45.26 C.**
- **BARE-control temperature range over the same grid = 45.26 C.**
- **WITHIN the populated window L_sol in [0.8, 1.25] (where daisies persist), the WITH-daisy
  range is only 6.89 C** while the bare control over that same window swings ~33 C.

## Verdicts (graded on the LOCKED metrics)

| # | Clause | Result | Number |
|---|--------|--------|--------|
| P1 | WITH daisies, temp range over L_sol[0.7,1.3] < 10 C | **MISS** | 45.26 C (need < 10) |
| P2 | BARE control temp range over the same grid >= 30 C | **REPRO** | 45.26 C (>= 30) |
| P3 | Daisy mix shifts black->white as L_sol rises | **REPRO** | white 0.20->0.73 |

## The regulation mechanism (what actually happens)

Within the populated window the homeostasis is textbook Watson-Lovelock and clearly
**emergent**: where the bare planet would be too cold (low L_sol), **black** daisies -- which
warm their own patches -- are selected and dominate (79% black at L_sol=0.8), raising local
temperatures back toward the 22.5 C optimum; where the bare planet would be too hot (high
L_sol), **white** daisies -- which cool their own patches -- take over (73% white at
L_sol=1.25) and pull the temperature back down. The black->white crossover sits right at
L_sol~1.0 (50/50), exactly where the bare planet is already at the optimum. The net effect:
the planet holds ~19-26 C across a luminosity range that swings the lifeless control by
~33 C. **This is the homeostasis result, and it is reproduced.**

## Why P1 is an honest MISS (not tuned away)

P1 is graded on the **full locked grid [0.7, 1.3]**, and over that full range the WITH-daisy
temperature range is 45 C -- a clean MISS of the <10 C band. The reason is **bounded
homeostasis**: at the two grid extremes the daisies cannot survive.

- **Cold death (L_sol = 0.7, 0.75):** the bare ground is -2.7...2.0 C. A lone black daisy at
  a bare-ground neighbour raises that patch by only ~7.5 C (because with no daisies A_bar=0.5,
  so q*(A_bar - albedo_black) = 30*0.25), landing near ~5 C -- at or below the growth
  threshold -- so colonisation cannot bootstrap from the seeded state. The daisies die out and
  temperature reverts exactly to the bare control.
- **Hot death (L_sol = 1.3):** even an all-white planet's local temperature exceeds the
  growth window, so white daisies cannot hold on; the world goes bare and hot.

This is **faithful** to Daisyworld: Watson & Lovelock's own model also collapses outside a
luminosity window -- homeostasis is strong *inside* the window and absent *outside* it. The
locked P1 grid [0.7,1.3] is simply **wider than this spatial model's homeostasis window**
([~0.78, ~1.26]). Per the study discipline ("if homeostasis is weaker than the locked <10 C
band -- parameter-sensitive -- report MISS honestly"), we report MISS rather than narrow the
grid or widen the parabola to manufacture a pass. The scientifically meaningful number -- the
**6.89 C within-window range** -- is recorded in `results.json`
(`ranges.with_daisies_populated_window`) and printed by the runner as explicitly NON-grading
context.

## Caveats / honesty

- **Genuine agent-based** (per-cell Patch agents that perceive + act), not a CA and not the
  mean-field box model. Disclosed as such.
- **Temperature rule is a modelling choice**, documented above; the local-heating coefficient
  q=30 and diffusion=0.5 follow the NetLogo Daisyworld convention. They were fixed before the
  run, not swept to hit a verdict.
- **Bounded homeostasis** is the headline caveat: the regulation is real and strong but only
  over a finite luminosity window; the full-grid P1 MISS reflects that the locked grid extends
  past that window into cold/hot death.
- Faithful reproduction of a published **synthetic** model; no real-world data. The
  contribution is whether the harness + lock-first discipline reproduce homeostasis and the
  albedo shift and would catch an artifact -- and whether they honestly report the boundary
  where the mechanism stops working.
