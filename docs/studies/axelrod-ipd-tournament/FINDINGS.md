# Axelrod 1984 IPD Tournament — FINDINGS

**Run 2026-06-29, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`):
each entrant is an autonomous `StrategyAgent` whose `decide()` returns C or D each
round from the LOCAL match history (its own + the opponent's past moves) — a real
per-round decision, never a precomputed sequence. A `Match` runs the iterated PD;
the `TournamentModel` owns the round-robin schedule + score table. Code:
`abm_auto/classics/axelrod_ipd.py`; experiment:
`examples/repro_axelrod_ipd_tournament/run.py`.

## Config (FIXED before the run; pool + metric not tuned)

| param | value |
|---|---|
| structure | round-robin — every strategy plays every strategy **including itself** |
| rounds / match | **200** |
| payoffs | **T=5, R=3, P=1, S=0** (Axelrod's) |
| metric (LOCKED) | **total score** across all matches (incl. self-play), **mean over seeds** |
| seeds | **(0, 1, 2, 3, 4)** — only the Random strategy is stochastic |
| pool (8) | TitForTat, AllD, AllC, Random(p=0.5), Grudger, TitForTwoTats, SuspiciousTFT, Pavlov |
| NICE (never first to defect) | TitForTat, AllC, Grudger, TitForTwoTats, Pavlov |

Determinism: the only stochastic strategy is `Random`, seeded per match
(`Random(seed*1_000_003 + match_index)`), so each whole tournament is reproducible
from one integer and two seeds give independent Random play. Verified identical
across repeated calls.

## Full strategy ranking by total score (mean over 5 seeds; the LOCKED metric)

| rank | strategy | mean score | min | max | stdev | nice |
|---|---|---|---|---|---|---|
| 1 | **TitForTwoTats** | **4767.8** | 4743 | 4788 | 18.70 | Y |
| 2 | **TitForTat** | **4756.2** | 4741 | 4766 | 9.28 | Y |
| 3 | Grudger | 4601.4 | 4569 | 4623 | 22.06 | Y |
| 4 | Pavlov | 4550.8 | 4525 | 4592 | 25.84 | Y |
| 5 | AllC | 4522.8 | 4515 | 4545 | 12.66 | Y |
| 6 | Random | 3874.6 | 3843 | 3907 | 23.20 | n |
| 7 | AllD | 3420.0 | 3408 | 3436 | 10.20 | n |
| 8 | SuspiciousTFT | 3360.6 | 3343 | 3377 | 13.52 | n |

The top five places are ALL nice strategies; the bottom three are ALL non-nice.

## Did TIT-FOR-TAT win?

**Not outright — TitForTat finished rank 2.** TitForTwoTats edged it: 4767.8 vs
4756.2, a gap of **11.6 points = 0.243%** of the top score. That is **inside the
locked P1 tie band** ("rank 1, or tied-1 within <1% of the top"), so P1 is REPRO as
a tied-1 finish, but the honest headline is that *TitForTat did not strictly win
this pool — a more forgiving nice variant (TitForTwoTats) did, by a hair.*

Per-seed, the two trade the top slot but stay neck-and-neck: TitForTwoTats is #1 in
4 of 5 seeds (seeds 0,1,2,4), TitForTat is #1 in seed 3. In every seed the two are
within ~30 points of each other and far ahead of everyone else.

## Verdicts vs the locked clauses (refutation tier — "not refuted", never "verified")

| # | Locked clause | Result | Salient numbers |
|---|---|---|---|
| P1 | TitForTat ranks 1 (or tied-1 within <1% of the top) | **REPRO** (tied-1) | TFT gap-to-top = 0.243% < 1.0%; TFT rank 2, top = TitForTwoTats |
| P2 | Nice strategies dominate (mean rank NICE < mean rank non-nice) | **REPRO** | mean rank NICE = 3.0 < non-nice = 7.0 |
| P3 | Greedy defection does NOT win (AllD not rank 1) | **REPRO** | AllD rank = 7 (!= 1) |

**3/3 locked clauses REPRO.** The reproduction recovers Axelrod's two central
results cleanly — *nice strategies dominate* (the entire top half is nice, the entire
bottom half is not; mean ranks 3.0 vs 7.0) and *greedy all-out defection loses
badly* (AllD next-to-last at rank 7). TIT-FOR-TAT lands in the top bracket but is
pipped for the outright #1 by TitForTwoTats within the locked tie tolerance.

## Honest caveats

- **TitForTat did not strictly win; TitForTwoTats did (by 0.243%).** This is the
  well-known **pool-dependence** of Axelrod's result: *which* nice strategy wins
  depends on the exact entrant set, the number of rounds, and whether noise is
  present. With this 8-strategy noiseless pool, the more forgiving TitForTwoTats
  collects slightly more by not retaliating against the single defections that the
  suspicious/random opponents throw, while never being seriously exploited here.
  Axelrod himself noted TitForTwoTats would have *won his first tournament* had it
  been entered. We do **not** drop TitForTwoTats or add a strategy to make TFT win —
  the pool was fixed before the run; the result stands as a faithful, interesting
  outcome and is reported as a tied-1 under the pre-registered <1% clause.
- **Near-tie at the top.** The #1/#2 gap (11.6 pts, 0.243%) is comparable to the
  per-strategy seed-to-seed stdev (~9-19 pts), so the *ordering* of the top two is
  not statistically robust across seeds (they swap: 4-1). The *pair* (TitForTat,
  TitForTwoTats) occupying the top two slots, however, is stable across all seeds.
- **No noise / no ecological dynamics.** This is the round-robin *tournament* (total
  score), not the *evolutionary* (replicator) variant and not the noisy-IPD variant.
  In noisy IPD, unconditional TitForTat suffers from echo effects and Pavlov / generous
  TFT do relatively better; that is out of scope for the locked claim, which is the
  1984 tournament's total-score ranking.
- **Self-play is included** (Axelrod's convention): every strategy also plays a copy
  of itself, and that match's points count toward its total. Nice strategies score
  R=3*200=600 against themselves (mutual cooperation); AllD scores only P=1*200=200,
  which is part of why defectors rank low.
- **Scope.** Faithful reproduction of a published *synthetic* tournament — no
  real-world data. The contribution is that the harness + lock-first discipline
  reproduce TFT's top-bracket finish, the nice-strategy advantage, and the failure of
  greedy defection, and would surface an artifact (a refutation gate, not a truth
  certificate).
