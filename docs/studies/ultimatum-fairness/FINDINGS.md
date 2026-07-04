# Evolution of Fairness in the Ultimatum Game (Nowak-Page-Sigmund 2000) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Genuine agent-based reproduction on
`abm_auto._platform`. Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the config below was fixed before the run and was NOT tuned to
make q̄/p̄ cross the P1/P2/P3 bars.

## What was built

A finite population of 200 `PlayerAgent`s, each carrying a **genotype (p, q) ∈ [0,1]²**:
`p` is the offer it makes as **proposer**, `q` is the minimum offer it accepts as
**responder** (its acceptance threshold). The population starts from a **fair random
init** — `p` and `q` each drawn uniformly on [0,1], so the mean genotype begins at ≈ 0.5
(neither selfish nor fair). Any drift toward selfishness or fairness is produced by
selection, not by seeding.

Each generation:

- **Encounters + fitness.** Every agent plays `rounds_per_gen = 10` encounters in *each*
  role — as proposer against random responders and as responder against random proposers.
  An offer `x` is accepted iff `x ≥ the responder's q`, paying the proposer `1 − x` and
  the responder `x`; a rejected offer (`x < q`) pays both 0. Fitness = the accumulated
  payoff across all encounters this generation.
- **Reputation channel (the single treatment knob).** In each encounter, with probability
  `w` the proposer **knows the responder's threshold** and best-responds — it offers
  exactly `q` (the minimum that still gets accepted, keeping `1 − q` for itself); with
  probability `1 − w` the proposer is **anonymous** and offers its own genotype `p`.
  `w = 0` is the anonymous one-shot game; `w = 1` is full reputation. Acceptance is always
  by the responder's own `q`.
- **Reproduction.** One generation of **fitness-proportional replication with mutation**
  (a Moran/replicator step at the population scale): each of the next generation's N
  genotypes is drawn from a parent chosen with probability proportional to fitness, then
  nudged on both `p` and `q` by an independent Gaussian of std `mutation = 0.02` (clamped
  into [0,1]). Synchronous: all parents are read from the current generation, then
  committed. Deterministic given a seed.

The **locked grading metrics** are the population-mean acceptance threshold **q̄** and
mean offer **p̄** at steady state (mean over the last 100 generations, averaged over 10
seeds). The reputation weight `w` is the ONLY thing that differs across the swept
treatments — N, the fair uniform init, `rounds_per_gen`, mutation, generation count, and
the seed set are identical across the w-grid.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| N | 200 |
| genotype init | p, q ~ Uniform[0,1] (fair, mean 0.5) |
| rounds per generation (per role) | 10 |
| mutation std (Gaussian on p, q) | 0.02 |
| reputation grid w | 0.0, 0.2, 0.5, 1.0 |
| seeds | 0…9 (10 seeds) |
| generations / measurement window | 500 / last 100 |

## Results (mean over 10 seeds; raw)

| w (reputation) | steady q̄ | q̄ range (std) | steady p̄ | p̄ range (std) |
|---|---|---|---|---|
| **0.0** (anonymous) | **0.064** | [0.059, 0.069] (0.003) | **0.190** | [0.181, 0.201] (0.006) |
| 0.2 | 0.142 | (0.017) | 0.281 | (0.014) |
| 0.5 | 0.470 | (0.019) | 0.580 | (0.018) |
| **1.0** (full reputation) | **0.967** | [0.966, 0.969] (0.001) | **0.570** | (0.201) |

`q̄` vs `w` = **[0.064, 0.142, 0.470, 0.967]** — strictly increasing.

From the fair start (q̄ ≈ 0.50), the **anonymous** game (w=0) collapses fast: q̄ falls to
≈ 0.085 by generation 50 and settles near 0.06; the mean offer p̄ drops to ≈ 0.19 and
holds. Under **full reputation** (w=1) q̄ instead *rises* to ≈ 0.97 within ~50 generations
and stays there, while p̄ climbs to ≈ 0.57.

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | No reputation → rational collapse | w=0: q̄ < 0.15 **and** p̄ < 0.20 | q̄ = **0.064**, p̄ = **0.190** | **REPRO** |
| **P2** | Reputation → fair offers | w≥0.8: q̄ > 0.30 **and** p̄ > 0.30 | q̄ = **0.967**, p̄ = **0.570** | **REPRO** |
| **P3** | Reputation is the cause | (q̄@w≥0.8 − q̄@w=0) ≥ 0.20 **and** q̄ non-decreasing in w | contrast = **0.903**, monotone ✓ | **REPRO** |

## Honest interpretation

- **Without reputation, reason wins — the population evolves toward the rational near-0
  offer (P1).** From a fair uniform start, the anonymous one-shot game drives the mean
  acceptance threshold down to q̄ ≈ 0.06 and the mean offer down to p̄ ≈ 0.19. This is the
  sub-game-perfect logic of the ultimatum game realised by selection: a responder that
  rejects a positive offer only hurts itself, so low thresholds are favoured; once
  thresholds are low, low offers are accepted, so low offers are favoured. Note p̄ = 0.190
  clears the 0.20 bar by only 0.01 — it is reported as the honest measured number, not
  tuned to fit; the offer does not go all the way to 0 because mutation continually
  reinjects genotype variance and anonymous proposers face a distribution of thresholds,
  leaving a small residual offer.

- **With reputation, fairness wins (P2).** When the proposer knows the responder's
  threshold (w=1) and must meet it to close the deal, a *high* acceptance threshold
  becomes an asset: it extracts a larger share from informed proposers. Selection then
  drives q̄ up to ≈ 0.97 and pulls offers up to p̄ ≈ 0.57 (a more-than-fair split). This
  is exactly the Nowak-Page-Sigmund result: reputation about acceptance behaviour is what
  lets fairness evolve.

- **Reputation is unambiguously the cause (P3).** The treatment contrast is enormous —
  q̄ goes from 0.064 (w=0) to 0.967 (w=1), a gap of **0.90**, far above the locked 0.20
  bar — and q̄ increases monotonically across the whole swept grid
  (0.064 → 0.142 → 0.470 → 0.967). The transition is smooth and threshold-like around
  w ≈ 0.5, mirroring the paper's finding that a *sufficient* amount of reputation flips the
  population from reason to fairness. Because the only thing that changes across arms is
  `w`, the contrast isolates reputation as the driver.

**Bottom line:** the reproduction cleanly demonstrates the central Nowak-Page-Sigmund
claim — fairness does not evolve in the anonymous ultimatum game (reason prevails toward
the near-0 offer), but a reputation channel about acceptance thresholds tips the same
population to fair offers — and the treatment sweep isolates reputation as the cause. All
three locked clauses reproduce with no tuning.

## Source

Nowak, M. A., Page, K. M. & Sigmund, K. (2000). *Fairness versus reason in the ultimatum
game.* Science 289(5485):1773–1775. doi:10.1126/science.289.5485.1773.

Scope: a faithful reproduction of a published synthetic model; no real-world data. The
contribution is whether the harness + locked-prediction discipline reproduce the
reputation-driven transition from the rational near-0 offer to fairness, isolate
reputation as its cause, and would catch an artifact.
