# Schelling 1971 Segregation — FINDINGS

**Run 2026-06-29, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`):
each resident is an autonomous `ResidentAgent` that inspects its Moore-8
neighbourhood and (if unhappy) relocates, under an `AgentSet` scheduler +
`DataCollector` (not a god-loop). The model holds the grid; agents query their
own neighbourhood locally. Code: `abm_auto/classics/schelling.py`; experiment:
`examples/repro_schelling_segregation/run.py`.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| grid | **50 x 50** (2,500 cells), hard edges (no wrap) |
| vacancy | **28%** -> 700 empty cells |
| occupied | **1,800** agents (type 0 = 900, type 1 = 900; equal) |
| neighbourhood | **Moore-8** (up-to-8 surrounding cells) |
| tolerance F | **1/3** (an agent is unhappy iff same-type fraction of OCCUPIED neighbours < 1/3) |
| move rule | each step, every unhappy agent relocates to a uniformly-random empty cell |
| stability | run until 0 unhappy (or max_steps = 200) |
| seeds | **12** (0..11) |

**Isolated-agent convention (documented):** an agent with NO occupied neighbours
counts as **HAPPY** (0 like-of-0 is vacuously satisfied; it has no grievance and
does not move). It contributes **0** to the segregation index (it has no
like-neighbours), so the reported index is a conservative lower bound on
clustering. Relocation is sequential within a sweep (a later agent sees earlier
agents' moves) — the standard Schelling sweep. Deterministic given the seed.

**Segregation index** = the mean, over all agents, of each agent's same-type
fraction among its occupied Moore-8 neighbours. A random placement gives ≈ 0.5
(each neighbour is independently same-type with prob ≈ 1/2).

## Measured per-seed initial -> final segregation index

| seed | initial (random) | final (stable) | steps | final unhappy |
|---|---|---|---|---|
| 0 | 0.4981 | 0.7371 | 11 | 0 |
| 1 | 0.4949 | 0.7456 | 9 | 0 |
| 2 | 0.4982 | 0.7281 | 12 | 0 |
| 3 | 0.4951 | 0.7684 | 9 | 0 |
| 4 | 0.5061 | 0.7343 | 9 | 0 |
| 5 | 0.4958 | 0.7222 | 11 | 0 |
| 6 | 0.5083 | 0.7291 | 13 | 0 |
| 7 | 0.4839 | 0.7306 | 10 | 0 |
| 8 | 0.4980 | 0.7374 | 9 | 0 |
| 9 | 0.5047 | 0.7144 | 7 | 0 |
| 10 | 0.4900 | 0.7382 | 8 | 0 |
| 11 | 0.5056 | 0.7254 | 8 | 0 |

**Cross-seed mean: initial = 0.4982 (random ≈ 0.5) -> final = 0.7342, delta = +0.2360.**
Every seed reaches a fully stable state (0 unhappy) in 7-13 sweeps.

## Verdicts vs the locked clauses (refutation tier — "not refuted", never "verified")

| # | Locked clause | Result | Salient numbers |
|---|---|---|---|
| P1 | Mild preference -> strong global segregation (final mean same-fraction ≥ 0.70) | **REPRO** | mean final = **0.7342** ≥ 0.70 |
| P2 | Segregation rises far above the random baseline (final − initial ≥ +0.15) | **REPRO** | delta = 0.7342 − 0.4982 = **+0.2360** ≥ +0.15 |
| P3 | Emergence: global segregation ≫ what any agent demands (final ≥ 2F = 0.667) | **REPRO** | mean final = **0.7342** ≥ 0.6667 |

**3/3 testable clauses REPRO.** The reproduction recovers Schelling's central,
counter-intuitive result: a *mild* individual preference (each agent merely wants
≥ 1/3 of its occupied neighbours to share its type) drives the population from a
well-mixed random state (index ≈ 0.50) to a strongly segregated stable state
(index ≈ 0.73) — an emergent global segregation more than twice the per-agent
demand. The headline: **mild 1/3 preference -> strong segregation.**

## Honest caveats

- **The index is a conservative lower bound.** Isolated agents (0 occupied
  neighbours) contribute 0 to the mean even though they are "happy", which drags
  the reported segregation index DOWN. The true clustering of occupied
  neighbourhoods is therefore at least as strong as the 0.73 reported; we do not
  exclude isolated agents (that would be a post-hoc choice that inflates the
  number toward the threshold).
- **Stability is genuine, not capped.** All 12 seeds reach 0 unhappy well within
  the 200-step cap (7-13 steps), so the final index is a true fixed point of the
  dynamics, not a snapshot of an unsettled run.
- **Sequential within-sweep relocation.** Unhappy agents move one at a time in a
  per-tick random order; a later mover sees the grid after earlier moves. This is
  the standard Schelling sweep and is deterministic given the seed (the move
  order and the random empty-cell targets are drawn from the model's seeded RNG).
  A fully synchronous (snapshot) variant would give quantitatively similar
  segregation; this choice was fixed before the run and not swept.
- **Initial baseline is ~0.50, as expected.** Random placement gives a mean
  same-type fraction of 0.4982 across seeds — the analytic ≈ 0.5 for two
  equal-size types — so P2's "+0.15 above baseline" is measured against a clean,
  not-tuned baseline.
- **No parameter tuning.** Grid (50x50), vacancy (28%), F (1/3), Moore-8, and the
  12-seed set were all fixed before the run; none was adjusted to clear a
  threshold. The final index 0.73 clears P1's 0.70 and P3's 0.667 with a real but
  modest margin — close enough that a stricter threshold (e.g. 0.80) would have
  been a MISS, which is the honest read.
- **Bundle `code_commit` provenance.** `verdict-bundle.json`'s `code_commit` is
  HEAD at run-time (the bundle is committed together with the code, so it points
  to the parent commit). Reproduction integrity is anchored on the
  content-addressed **sha256** of the docs/data artifacts (all `replay: strong`),
  not the commit pointer.
- **Scope.** Faithful reproduction of a published *synthetic* model — no
  real-world data. The contribution is that the harness + lock-first discipline
  reproduce Schelling's segregation result and would surface an artifact (a
  refutation gate, not a truth certificate).
