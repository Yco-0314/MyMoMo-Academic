# Indirect Reciprocity by Image Scoring (Nowak & Sigmund 1998) — FINDINGS

**Status: 1/3 locked clauses REPRO. P2 (the information threshold q > c/b) REPRO; P1
(no-mutation fixation to exactly k=0) and P3 (group-size decay of cooperation) are honest
MISSes — both are genuine, documented features of the *faithful* plain image-scoring
model, not tuning failures.** Genuine agent-based reproduction on `abm_auto._platform`.
Predictions were locked BEFORE running (`PREDICTIONS-locked.md`); the config below was
fixed before the run and NOT tuned to make any clause pass.

## What was built

`n` `PlayerAgent`s, each carrying an integer **image score** `s` (public reputation,
bounded to [-5, +5]; everyone starts each generation at s = 0) and an integer
**strategy** `k` — a discrimination threshold in [-5, +6]. A donor with threshold `k`
**helps** a recipient iff the recipient's image `s >= k`:

- `k = -5` = unconditional cooperator (helps everyone, since s >= -5 always);
- `k = +6` = pure defector (helps no one, since s <= +5 < 6 always);
- `k = 0` = the **stern discriminator** — help only those with a non-negative image.

Each **generation** plays `m = 10n` **donation-game** interactions. Each interaction
draws a donor and a distinct recipient uniformly at random (no repeated pairing — this is
*indirect*, not direct, reciprocity). Helping pays cost `c = 0.1` and gives benefit
`b = 1.0` (`b > c`). Helping raises the donor's image by +1, refusing lowers it by -1
(both capped to [-5, +5]) — but the image only moves when the act is **observed**, which
happens with probability `q` (the information parameter). Payoffs accumulate over the
generation; then a new generation of `n` strategies is drawn by **payoff-proportional
(roulette) reproduction** (min-shift so only payoff differences matter), with **mutation
probability `mu`** (a mutated offspring gets a fresh uniform-random threshold). Image
scores reset to 0 at the start of each generation (a newborn has a neutral reputation);
strategies are the only heritable trait.

The model is deterministic given a seed (one seeded RNG chain). Neighbour-free and
well-mixed; the interaction round is O(m) = O(10n) per generation.

**Distinctness (kept):** a discriminator conditions its move on the recipient's
**third-party image** — what the recipient did to OTHERS — which the direct-reciprocity
world (`axelrod_ipd`, repeated pairings + TFT) and the within-group peer-punishment world
(`public_goods`) have no representation of. There are no repeated pairings here.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| benefit b / cost c | 1.0 / 0.1 (c/b = 0.1) |
| image range | [-5, +5], start 0 |
| strategy range k | [-5, +6] (12 strategies) |
| interactions / generation | m = 10n |
| seeds | 0..19 (20 seeds) |
| generations / window | 500 / last 100 |
| **P1** | n = 100, q = 1.0, mu = 0.0 |
| **P2** | n = 100, mu = 0.0, q in {0, 0.05, 0.1, 0.2, 0.5, 1.0} |
| **P3** | q = 1.0, mu = 0.01, n in {20, 50, 100} |

## Results (mean over 20 seeds)

### P1 — no-mutation, full-info fixation to k=0

| Metric | Measured | Pass bar | Verdict |
|---|---|---|---|
| k=0 frequency | **0.20** | > 0.95 | MISS |
| \|mean k\| | **2.40** | < 0.5 | MISS |
| k=0 modal in seeds | **20%** (4/20) | >= 90% | MISS |
| cooperative-act fraction | **1.00** | (context) | — |

Per-seed modal k: -2, -1, 0, 0, 0, -1, -4, 0, -4, -3, -4, -5, -2, -1, -1, -5, -4, -5, -1,
-5. **P1 = MISS.**

### P2 — information threshold q > c/b (c/b = 0.1)

| q | cooperative-act fraction | cooperative-strategy fraction |
|---|---|---|
| 0.00 | 0.000 | 0.83 |
| 0.05 | 0.000 | 0.88 |
| 0.10 | 0.150 | 0.70 |
| 0.20 | 0.787 | 0.97 |
| 0.50 | 1.000 | 1.00 |
| 1.00 | 1.000 | 1.00 |

Cooperative **acts** collapse to 0 for q <= 0.05 (< 1%), rise across the c/b = 0.1
threshold (0.00 -> 0.15 -> 0.79 as q goes 0.05 -> 0.1 -> 0.2), and are sustained at
q = 1.0 (coop-strategy fraction 1.00 > 0.6). **P2 = REPRO.**

### P3 — group-size effect WITH mutation (q = 1.0, mu = 0.01)

| n | cooperative-strategy fraction | cooperative-act fraction | target |
|---|---|---|---|
| 20 | ~0.89 | ~0.86 | 0.90 +/- 0.10 |
| 50 | ~1.00 | ~0.99 | 0.47 +/- 0.12 |
| 100 | ~1.00 | ~0.99 | 0.18 +/- 0.10 |

Cooperation stays HIGH at all n and does **not** decrease monotonically with group size.
**P3 = MISS.** (Live numbers in `results.json`.)

## Honest interpretation

- **P2 is the headline reproduction, and it passes decisively.** Nowak & Sigmund's
  central quantitative claim is an *information* threshold: cooperation via image scoring
  is favored when the probability of an act being known, `q`, exceeds the cost-to-benefit
  ratio `c/b`. Here `c/b = 0.1`, and the cooperative-act fraction is pinned at 0 for
  q <= 0.05, then rises sharply across q ~ 0.1-0.2 to full cooperation. That is the
  reproduction of the paper's information-threshold result, on a genuinely agent-based
  model where the threshold is an emergent property of the reputation dynamics, not
  hard-coded.

- **P1 is an honest MISS because the *faithful* plain image-scoring model DRIFTS.** With
  full information and **no mutation**, cooperation is fully established (coop-act
  fraction = 1.00) — but the population does **not** fix on exactly the stern
  discriminator k = 0. It fixes on *some* cooperative strategy (k <= 0), and which one is
  neutral drift: once everyone helps and all images saturate at +5, every strategy with
  k <= 0 helps everyone and they are **payoff-indistinguishable**. With no selective
  gradient among them, the population drifts (here toward more-generous k < 0, mean
  k = -2.4). This is a **documented, load-bearing feature** of image scoring, not an
  implementation error: the stern discriminator k = 0 becomes specially selected **only
  when mutation reintroduces defectors** — k = 0 is the most generous strategy that still
  *refuses to help a defector*, so it resists ALLD invasion while over-generous strategies
  (k < 0, ALLC) do not. In the mutation-free, defector-free limit there is nothing to
  select it. This is exactly why image scoring was later shown *not* to be evolutionarily
  stable (Leimar & Hammerstein 2001; the "standing" strategy was proposed as the fix). The
  lock's P1 states the paper's idealized k = 0 claim; the faithful model falsifies the
  "no-mutation" version of it, and we report that as a MISS rather than switch mutation on
  (which the locked P1 config forbids) to force it.

- **P3 is an honest MISS because under the lock's own `m = 10n` rule, group size does not
  degrade information.** The published group-size effect (cooperation falling as n grows)
  arises when the **total number of rounds per generation is fixed**, so in a larger group
  each individual's reputation is built from proportionally *fewer* observed acts —
  effectively per-capita information decays as n grows. The lock specifies `m ~ 10n`
  interactions per generation, which holds the per-agent donor count constant (~10) at
  every n. Under that faithful rule the information available about each individual is the
  same at n = 20 and n = 100, so cooperation does not decay with group size — the
  cooperative-strategy fraction stays ~0.9-1.0 across the grid instead of falling to
  ~0.47 / ~0.18. We report the null (no monotone decrease) honestly rather than switch to
  a fixed-total-rounds schedule to manufacture the target curve.

**Bottom line:** the reproduction cleanly recovers the paper's *mechanistic* headline —
the information threshold q > c/b that lets indirect reciprocity sustain cooperation — and
honestly reports two falsifications that are real properties of the faithful model: the
neutral drift among cooperative discriminators without mutation (P1), and the absence of a
group-size decay under the `m = 10n` schedule the lock itself specifies (P3). No parameter
was tuned to flip any clause.

## Source

Nowak, M. A. & Sigmund, K. (1998). *Evolution of indirect reciprocity by image scoring.*
Nature 393:573-577. doi:10.1038/31225.

Scope: a faithful reproduction of a published synthetic model; no real-world data. The
contribution is whether the harness + locked-prediction discipline reproduce the
indirect-reciprocity information threshold and would honestly report the plain-image-
scoring drift + group-size null as MISSes rather than tune them away.
