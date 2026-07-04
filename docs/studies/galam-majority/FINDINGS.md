# Galam Majority-Rule Opinion Model — FINDINGS

**Run 2026-06-30, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`): each
agent is an autonomous `OpinionAgent` carrying a binary opinion in {0,1}; the
`GalamModel` owns the seeded RNG, the partition/local-majority rule, and a
`DataCollector` (the per-step up-fraction series) — not a god-loop. The opinions live ON
the agents; each step reshuffles the population into fixed-size groups whose members all
adopt the group's local majority. Code: `abm_auto/classics/galam.py`; experiment:
`examples/repro_galam_majority/run.py`.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| population | **N = 10001** agents, binary opinion s in {0, 1} (1 = up) |
| initial state | up-fraction p0 (each agent 1 with prob p0, else 0; seeded) |
| update step | shuffle the population -> chunk into groups of size **g** -> every member of each full group adopts the group's **local majority** -> reshuffle next step |
| odd group | **g = 3**: a strict majority always exists; ties impossible |
| even group | **g = 4**: a 2-2 tie is broken toward **UP** (the fixed "prejudice"/status-quo bias) — this is the LOCKED tie rule |
| leftover | N mod g agents (1 for g=3, 1 for g=4) cannot fill a final full group -> left **unchanged** that step; reshuffled into full groups later |
| stop rule | run to **consensus** (all-0 or all-1) or a cap of **1000 steps** |
| g=3 p0-grid | 0.40, 0.42, 0.44, **0.45**, 0.46, 0.48, 0.50, 0.52, 0.54, **0.55**, 0.56, 0.60 |
| g=4 p0-grid | 0.05, 0.10, 0.15, 0.20, 0.22, 0.24, 0.25, 0.30, 0.35, 0.40, **0.45**, 0.50, 0.55 |
| seeds per p0 | **20** (seeds 0-19; each seed drives both the placement and every reshuffle) |
| locked metric | **which consensus is reached vs p0** (fraction of seeds -> all-up) |

Determinism: a single seeded RNG chain drives placement + every reshuffle, so the same
seed reproduces byte-identical output (pinned in `tests/classics/test_galam.py`).

## Measured outcomes — g=3 (odd, no ties), averaged over 20 seeds

| p0 | P(all-UP) | P(all-DOWN) | P(consensus) | mono | mean steps |
|---|---|---|---|---|---|
| 0.40 | 0.00 | 1.00 | 1.00 | 1.00 | 7.0 |
| 0.42 | 0.00 | 1.00 | 1.00 | 1.00 | 7.8 |
| 0.44 | 0.00 | 1.00 | 1.00 | 1.00 | 8.6 |
| **0.45** | **0.00** | **1.00** | **1.00** | 1.00 | 8.9 |
| 0.46 | 0.00 | 1.00 | 1.00 | 1.00 | 9.4 |
| 0.48 | 0.00 | 1.00 | 1.00 | 1.00 | 11.4 |
| **0.50** | 0.70 | 0.30 | 1.00 | 0.60 | 15.4 |
| 0.52 | 1.00 | 0.00 | 1.00 | 1.00 | 10.9 |
| 0.54 | 1.00 | 0.00 | 1.00 | 1.00 | 9.2 |
| **0.55** | **1.00** | **0.00** | **1.00** | 1.00 | 8.8 |
| 0.56 | 1.00 | 0.00 | 1.00 | 1.00 | 8.3 |
| 0.60 | 1.00 | 0.00 | 1.00 | 1.00 | 7.2 |

**Measured g=3 tipping point: p_c = 0.50** (first p0 with P(all-UP) >= 0.5). The initial
majority always wins; p0 = 0.50 is the unstable coin-flip (14 up / 6 down here over 20
seeds). Galam analytic prediction for odd groups: **p_c = 0.5**. (REPRO)

## Measured outcomes — g=4 (even, ties -> UP), averaged over 20 seeds

| p0 | P(all-UP) | P(all-DOWN) | P(consensus) | mono | mean steps |
|---|---|---|---|---|---|
| 0.05 | 0.00 | 1.00 | 1.00 | 1.00 | 2.9 |
| 0.10 | 0.00 | 1.00 | 1.00 | 1.00 | 4.0 |
| 0.15 | 0.00 | 1.00 | 1.00 | 1.00 | 5.0 |
| 0.20 | 0.00 | 1.00 | 1.00 | 1.00 | 7.2 |
| 0.22 | 0.00 | 1.00 | 1.00 | 0.95 | 9.4 |
| 0.24 | 0.90 | 0.10 | 1.00 | 0.85 | 11.6 |
| 0.25 | 1.00 | 0.00 | 1.00 | 1.00 | 9.1 |
| 0.30 | 1.00 | 0.00 | 1.00 | 1.00 | 6.2 |
| 0.35 | 1.00 | 0.00 | 1.00 | 1.00 | 5.2 |
| 0.40 | 1.00 | 0.00 | 1.00 | 1.00 | 4.9 |
| **0.45** | **1.00** | **0.00** | **1.00** | 1.00 | 4.2 |
| 0.50 | 1.00 | 0.00 | 1.00 | 1.00 | 4.0 |
| 0.55 | 1.00 | 0.00 | 1.00 | 1.00 | 3.9 |

**Measured g=4 (ties->up) tipping point: p_c = 0.24** (first p0 with P(all-UP) >= 0.5),
with the sharp crossover sitting between p0 = 0.22 and p0 = 0.25. This is the canonical
**minority-spreading** result: an initial up MINORITY as small as ~24% wins the all-up
consensus, because every 2-2 tie repeatedly tips toward up. The measured p_c ~ 0.24
matches Galam's famous analytic value **p_c ~ 0.23** for the 4-cell tie-bias case. The
locked discriminator — **p0 = 0.45 (a 45% up minority) -> all-UP in 20/20 seeds** — is
recovered. (REPRO)

## P3 — no interior stable fixed point

All **500 runs (both sweeps) reached an exact 0/1 consensus**; **zero runs were stuck at
an interior value**. This is the substantive P3 claim: the flow leaves the interior and
settles at 0 or 1 (no interior *stable* fixed point — only the unstable repeller at p_c).
Representative trajectories (seed 0):

- g=3, p0=0.45 -> 0.448, 0.426, 0.392, 0.333, 0.260, 0.165, 0.071, 0.017, 0.001, **0.000**
- g=3, p0=0.55 -> 0.548, 0.577, 0.616, 0.674, 0.754, 0.848, 0.940, 0.990, 1.000, **1.000**
- g=4, p0=0.45 -> 0.448, 0.606, 0.822, 0.982, **1.000**

Each marches monotonically away from p_c toward consensus. Supporting figures (from
results.json): **360/360 = 100%** of trajectories AWAY from the unstable fixed points are
strictly step-by-step monotone, and **488/500 = 97.6%** monotone OVERALL; the few
exceptions sit RIGHT ON the g=4 knife-edge (p0 = 0.22, 0.24), where
a finite-N trajectory wobbles by a few thousandths around p_c for a handful of steps
before committing decisively to 0 or 1 — the signature of an UNSTABLE fixed point, which
is exactly what P3 asserts (flow moves *away* from p_c). None of them gets stuck.

## Verdicts vs the locked clauses (refutation tier — "not refuted", never "verified")

| # | Locked clause | Result | Salient numbers |
|---|---|---|---|
| P1 | g=3: consensus + initial majority wins (tipping at p_c=0.5): p0=0.45->all-down AND p0=0.55->all-up | **REPRO** | g=3 p0=0.45: P(all-down)=**1.00**, P(cons)=1.00; p0=0.55: P(all-up)=**1.00**, P(cons)=1.00; measured p_c=**0.50** |
| P2 | g=4 (ties->up): up-tipping point p_c < 0.5 (minority spreading): p0=0.45->all-UP | **REPRO** | g=4 p0=0.45: P(all-up)=**1.00**; measured p_c=**0.24** < 0.5 (Galam ~ 0.23) |
| P3 | Flow moves away from p_c (no interior stable fixed point) | **REPRO** | trajectories ending at 0/1 = **500/500** (1.000); none stuck interior; monotone-away = 360/360 (1.000), overall 488/500 (0.976) |

**3/3 locked clauses REPRO.** The reproduction recovers Galam's central results: reshuffled
small-group majority rule drives a population to **consensus with a tipping point**; for
**odd groups (g=3)** the tipping point is the symmetric **p_c = 0.5** (initial majority
wins); for **even groups (g=4) with a tie-bias toward up** the tipping point shifts to
**p_c ~ 0.24 < 0.5**, so an initial **minority can spread to a full consensus** — Galam's
"minority opinion spreading." The flow has no interior *stable* attractor: every
trajectory ends at 0 or 1, away from the unstable p_c.

## Caveats / honesty notes

- **Faithful synthetic reproduction, no real-world data.** The contribution is whether the
  harness + locked-metric discipline reproduce the Galam tipping point and minority-spreading
  result and would catch an artifact — not a claim about any empirical population.
- **The minority-spreading magnitude depends on the tie-bias strength and group size.** The
  locked rule is g=4, ties->up; we did NOT tune the tie rule to force the result. With this
  fixed rule the measured p_c ~ 0.24. A weaker or differently-placed bias, or a different
  even g, would move p_c — that is a property of the model, not a free knob here.
- **p_c is a knife-edge, not a stable point.** At p0 = 0.50 (g=3) and p0 ~ 0.23-0.24 (g=4)
  the outcome is a finite-N coin flip; the few non-monotone trajectories live exactly there.
  This is consistent with — not contrary to — P3 (unstable fixed point).
- **Leftover convention.** N=10001 is not divisible by 3 or 4, so one agent per step is a
  leftover left unchanged. With N >> g this has negligible effect on the dynamics (the
  leftover is reshuffled into a full group on subsequent steps); it does not alter any verdict.
- **Refutation tier.** A passed clause means "not refuted by this gate," NOT "verified true."
