# Public Goods + Punishment — FINDINGS

**Authored before the L3 bundle** (the bundle fingerprints this file). Numbers are the
raw output of `examples/repro_public_goods_punishment/run.py` on the locked config.
Honest report: all three locked clauses REPRO.

## What was reproduced

Fehr & Gächter (2000, 2002): in a public-goods game cooperation **collapses** without a
way to punish free-riders, but is **sustained** once a peer-punishment option exists. We
reproduce that as an *evolutionary* agent-based model — not the lab experiment, but the
cooperation-evolution abstraction of the same result (Boyd & Richerson / Hauert / Sigmund
tradition): a well-mixed population whose strategies spread by payoff-based imitation.

## Model (fixed, locked before running)

- Well-mixed population **N = 1000** `PlayerAgent`s.
- Each round: randomly partition into **groups of n = 5**. Each group plays one PGG with
  **contribution c = 1**, **multiplier r = 3**, pot split equally among the 5 members.
- Strategies: **Cooperator** (contributes), **Defector** (contributes nothing), and —
  *with-punishment treatment only* — **Punisher** (contributes AND pays **beta = 1** per
  defector in its group; each punished defector loses **gamma = 3** per punisher in its group).
- **Strategy update = payoff-proportional pairwise imitation**: each agent picks one random
  model agent and, if the model out-earned it this round, copies the model's strategy with
  probability proportional to the payoff gap (normalised by the max single-round span). Only
  payoff *differences* matter, so the negative payoffs punishment creates need no shifting.
- **Two treatments**, identical in every PGG parameter, update rule, and seeds —
  differing in whether the Punisher strategy exists.
- Init mixing (standard, not rigged): **no-punishment = equal halves C/D**;
  **with-punishment = equal thirds C/D/P**.
- **Caveat (adversarial review 2026-06-30): the two arms are NOT identical in the
  initial defector fraction** — the equal-thirds with-punishment arm starts at ~33%
  defectors vs ~50% in the no-punishment arm (because a Punisher third displaces some
  defectors). This is a mild unfairness; the review verified it does NOT drive the
  collapse-vs-sustain result (no-punishment collapses from 50% defectors smoothly to
  ~0 cooperation; the result is governed by the punishment dynamics, not the 50%-vs-33%
  init). The load-bearing assumption is the initial *punisher* fraction (caveat below),
  not the defector fraction.
- **Outcome (locked metric)** = steady-state mean cooperation = fraction *contributing*
  (C + P), mean over the last 50 of 300 rounds, averaged over **10 seeds** (0-9).

## Results (raw, 10 seeds, 300 rounds)

| Treatment | Steady mean cooperation | Range over seeds |
|---|---|---|
| No-punishment (C/D) | **0.0010** | [0.0000, 0.0020] |
| With-punishment (C/D/P) | **1.0000** | [1.0000, 1.0000] |
| **Difference (with - without)** | **0.9990** | - |

Seed-averaged trajectories (cooperation fraction; sampled every 30 rounds, t=0..300):

- No-punishment: `0.500 -> 0.316 -> 0.179 -> 0.092 -> 0.045 -> 0.022 -> 0.011 -> 0.005 -> 0.002 -> 0.001 -> 0.001`
  - a smooth collapse to ~0; final populations are ~999-1000 Defectors.
- With-punishment: `0.667 -> 1.0 -> 1.0 -> ...` - cooperation reaches >= 0.99 by **round 16** and
  stays pinned at 1.0; defectors are driven extinct in every seed.

## Verdicts (locked clauses P1-P3)

| # | Clause | Pass threshold | Measured | Verdict |
|---|---|---|---|---|
| P1 | No-punishment cooperation collapses | < 0.20 | 0.0010 | **REPRO** |
| P2 | With-punishment cooperation sustained | > 0.50 | 1.0000 | **REPRO** |
| P3 | Punishment makes the difference | >= 0.30 | 0.9990 | **REPRO** |

**3/3 REPRO.** Punishment sustains cooperation that otherwise collapses - the central
Fehr-Gachter result, reproduced on the shared platform with the metric locked before the run.

## Caveats (honest)

- **Second-order free-riding is present but does not destabilise cooperation.** Once
  defectors are extinct, a Punisher pays nothing (beta*0 = 0) and earns exactly what a plain
  Cooperator earns. So the C/P split is *payoff-neutral* and drifts: the with-punishment
  population settles to ~**61% C / 39% P** (avg over seeds), not all-P. Cooperation stays at
  1.0 because **both** C and P contribute - the second-order free-rider (a Cooperator who
  reaps the punishment-stabilised public good without paying to punish) survives, but it does
  no harm to the *cooperation* outcome within the well-mixed, no-mutation horizon here. This
  is the known weak point of peer punishment: we do **not** claim punishers are evolutionarily
  protected against second-order free-riders, only that cooperation (contribution) is
  sustained. Adding rare mutation / a longer horizon could let C slowly displace P and, if a
  defector mutant then re-invaded a punisher-poor population, re-open the door to collapse -
  not tested here.
- **Init sensitivity.** Equal-thirds seeding gives punishers ~333/1000 at the start, which is
  comfortably enough for them to invade and wipe out defectors. With punishers seeded much
  rarer (e.g. a few percent), invasion is not guaranteed under proportional imitation - the
  classic second-order problem. We used a **standard, documented, fixed** seeding (equal
  thirds) and did **not** tune it to force the result; a rarer-punisher seed is a known
  harder regime and was not the locked config.
- **This is the evolutionary model, not the lab experiment.** The reproduction target is the
  qualitative result (collapse without / sustained with punishment), graded on the locked
  steady-cooperation metric - not the specific contribution levels or the spite/emotion
  mechanisms of the human experiments.
- Refutation-tier verdicts: passing means the locked clause was *not refuted* on this fixed
  config, not that the claim is universally verified.
