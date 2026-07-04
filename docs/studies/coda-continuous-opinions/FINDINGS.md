# Martins CODA (Continuous Opinions, Discrete Actions, 2008) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Genuine agent-based reproduction on
`abm_auto._platform`. Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the config below was fixed before the run and was NOT
tuned to make any clause pass.

## Framing (binding honesty disclosure)

This is a **genuine agent-based model**, not a cellular automaton. Each of the
N = 2500 agents on a 50×50 **periodic** lattice carries a **hidden, continuous**
belief — the log-odds `l = ln(p/(1−p))` of the probability `p` that option A is
better — and exposes **only a discrete action** `σ = sign(p − 0.5) = sign(l)`
(act for A iff `l ≥ 0`). No agent ever sees another's continuous `p`; it observes
only neighbours' discrete actions.

**The unit of action is one asynchronous single-observation update.** Each step a
randomly chosen agent observes **one** randomly chosen von-Neumann neighbour's
discrete action and Bayesian-updates its own hidden belief. In log-odds the
single-observation Bayesian update is **exactly additive** (Martins 2008, Eq. 3):

```
l → l + ν   if the observed neighbour acts for A (σ_j = +1)
l → l − ν   if the observed neighbour acts for B (σ_j = −1)
```

with the fixed step `ν = ln(α/(1−α))` set by the likelihood `α = 0.7`, so
**ν = ln(0.7/0.3) = 0.8473**. Because the step is additive and unbounded, repeated
agreeing observations drive `|l|` to arbitrarily large values: beliefs **diverge to
certainty (extremization)**.

**Distinctness signature.** This *inverts* bounded-confidence averaging
(Deffuant / Hegselmann–Krause), where continuous opinions are *averaged* toward
moderation. CODA's discrete-action Bayesian update **diverges to certainty** — an
averaging model cannot produce this, which is the whole point of the comparison.

## What was built

A flat numpy array of log-odds (length N) with a precomputed periodic von-Neumann
neighbour table (N×4). The hot loop applies the asynchronous additive update one
observation at a time (true random-sequential, never vectorised into a synchronous
sweep). Each update consumes exactly one RNG draw from `[0, 4N)`, decomposed into a
target agent and one of its 4 neighbours — so `update_batch` is a pure prefix of the
update stream and snapshotting at 2M on the way to 4M continues the *same* trajectory
(load-bearing for the P1 "double the run" growth check). Each lattice site is a
`CODAAgent` whose `l` is a live view onto the array, so the agent roster and the
vectorised state never disagree. Deterministic given a seed (numpy PCG64).

**Metrics.** `max_i |l_i|/ν` (extremity / P1); the fractions with `|l|/ν ≥ 50` and
`|l|/ν < 1` (bimodality / P2); the like-neighbour bond fraction; and the number of
connected same-action components under 4-connectivity **with wrap-around** (domain
count / P3). The connected-component labelling stitches the four torus seams; it is
tested equal to an independent union-find on the periodic von-Neumann graph.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| lattice L | 50 (N = 2500), periodic, von Neumann (4 nb) |
| likelihood α | 0.7 → additive step ν = 0.8473 |
| init band | p_i ~ U(0.4, 0.6) → every \|l_i\| < ν (NO extremists at t=0) |
| seeds | 0, 1, 2 (3 seeds) |
| horizon | 4×10⁶ updates, snapshot at 2×10⁶ for the P1 growth check |

## Results (per seed; raw)

| Seed | max\|l\|/ν @2M | max\|l\|/ν @4M | growth 4M/2M | median\|l\|/ν @4M | frac≥50 | frac<1 | like-nb | components @4M | macro domains (sizes) |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 891.7 | 1726.6 | 1.936 | 1532.7 | 0.949 | 0.0016 | 0.880 | 7 | 2 (1279, 1003) |
| 1 | 896.8 | 1755.8 | 1.958 | 1547.1 | 0.953 | 0.0032 | 0.886 | 8 | 4 (1502, 542, 162, 136) |
| 2 | 879.0 | 1726.3 | 1.964 | 1524.2 | 0.945 | 0.0028 | 0.871 | 8 | 3 (1248, 974, 170) |

**Random-start baselines (no updates):** components = 336, 337, 301; macro domains
2–3; like-neighbour fraction ≈ 0.50; median `|l|/ν` < 1 (no extremists).

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Opinions extremize without bound | max\|l\|/ν ≥ 100 @2M **and** ≥1.3× when doubled to 4M | min max@2M = **879**; min growth = **1.94** | **REPRO** |
| **P2** | Final distribution U-shaped / extremist-dominated | frac(\|l\|/ν ≥ 50) > frac(\|l\|/ν < 1) at the end | **≈0.95** vs **≈0.003** (≈300× gap) | **REPRO** |
| **P3** | Agreeing agents form contiguous same-action domains | connected same-action clusters ≤ 0.1·N = 250, far below the random start | **7–8** components (vs **~330** at random start) | **REPRO** |

## Honest interpretation

- **Extremization is unbounded and ongoing (P1, REPRO decisively).** Starting from
  `U(0.4, 0.6)` with every `|l_i| < ν` (no extremists), the most extreme belief
  reaches `|l|/ν ≈ 890` by 2×10⁶ updates and **≈1730** by 4×10⁶ — i.e. it
  essentially **doubles** when the run doubles (growth ≈ 1.94×, far above the locked
  1.3× bar). This is the signature of an *additive, unbounded* log-odds step: there
  is no plateau, no bounded-confidence-style ceiling. The growth is linear in
  update count, exactly as the additive Bayesian update predicts.

- **The final distribution is bimodal and extremist-dominated (P2, REPRO).** By the
  end ≈ 95% of agents sit at `|l|/ν ≥ 50` (deep in a certainty mode) while only
  ≈ 0.3% remain near indifference (`|l|/ν < 1`) — a ≈ 300× gap. The opinion
  histogram is strongly U-shaped: almost everyone is certain, split between the two
  actions, with a near-empty middle.

- **Agreeing agents form contiguous same-action domains (P3, REPRO).** The number of
  connected same-action components collapses from **≈ 330 at random start to 7–8**
  once the dynamics has run — two orders of magnitude below the locked bar of
  `0.1·N = 250`, and far below the random-start count. The like-neighbour bond
  fraction rises from ≈ 0.50 (random) to ≈ 0.88 (spatially ordered).

- **Global consensus is NOT forced — domains coexist.** This is the subtle point the
  locked methodology flags. Even at the long 4×10⁶ horizon the torus does **not**
  coarsen to a single action: seeds hold **2, 4, and 3** macroscopic (≥ 5% N)
  domains respectively, each containing hundreds to ~1500 agents, *while* the hidden
  beliefs inside them are extremizing without bound (median `|l|/ν ≈ 1530`). So the
  result is two (or more) large, mutually certain, oppositely-acting domains — not a
  uniform consensus. The locked P3 clause (cluster count ≤ 0.1·N) passes by a wide
  margin under either reading.

- **The distinctness from bounded confidence is real.** A Deffuant/HK averaging model
  on the same lattice would pull continuous opinions *together toward the mean*
  (moderation, shrinking spread). CODA does the opposite: discrete-action Bayesian
  updating pushes hidden beliefs *apart toward certainty* (extremization, growing
  spread) while organising the discrete actions into contiguous domains. The 3/3
  reproduction recovers exactly this inversion.

**Bottom line:** the faithful agent-based CODA reproduction recovers all three locked
phenomena — unbounded extremization of hidden beliefs, a bimodal extremist-dominated
final distribution, and contiguous same-action spatial domains that persist without
collapsing to global consensus — and does so as the *opposite* of bounded-confidence
averaging, which is CODA's distinctness signature.

## Source

Martins, A. C. R. (2008). *Continuous opinions and discrete actions in opinion
dynamics problems.* Int. J. Mod. Phys. C 19(4):617–624.
doi:10.1142/S0129183108012339. (arXiv:0711.1199.)

Scope: a faithful reproduction of a published synthetic model; no real-world data.
The contribution is whether the harness + lock-first discipline reproduce
extremization and same-action domain formation, and would catch an artifact.
