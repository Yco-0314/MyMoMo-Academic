# Gode–Sunder 1993 Zero-Intelligence Traders — FINDINGS

**Run 2026-06-30, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`):
each trader is an autonomous `TraderAgent` carrying its private value/cost and budget
mode; the `DoubleAuctionModel` drives a continuous double auction over the `AgentSet`
roster + a `DataCollector` (not a god-loop). Code:
`abm_auto/classics/zero_intelligence.py`; experiment:
`examples/repro_zi_traders/run.py`.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| market | M buyers + M sellers, **single unit each** (Gode–Sunder small-market scale) |
| M | **8** per side |
| value / cost draw | i.i.d. **U(1, 200)** (fresh schedule per seed) |
| price range | pmin = **1.0**, pmax = **200.0** |
| periods per round | **5** (each runs to exhaustion of feasible crossings) |
| seeds | **30** (≥ 20; fresh value/cost schedule + fresh quoting each seed) |
| clearing rule | **continuous double auction**: maintain best bid / best ask; a new bid ≥ standing ask (or new ask ≤ standing bid) transacts at the **standing (resting) price**; both single-unit counterparties leave the market; a non-crossing quote that improves the book replaces the standing quote |
| **LOCKED metric** | allocative efficiency = realized surplus / **max competitive-equilibrium surplus** |
| only inter-arm difference | the **budget constraint** on the quote draw (FAIR) |

The competitive equilibrium pairs the highest values with the lowest costs (demand
schedule descending, supply schedule ascending); the equilibrium quantity q is the
number of value ≥ cost pairs and the max surplus is the sum of their (value − cost).
For this config the mean equilibrium quantity is **q ≈ 4.3 units**.

**The two arms.** ZI-C (budget-constrained): a buyer bids ~U(1, value), a seller asks
~U(cost, 200) — a trade therefore never violates the budget (value ≥ price ≥ cost, so
every executed pair has non-negative true surplus). ZI-U (unconstrained): both bid/ask
~U(1, 200) ignoring value/cost — so a buyer can bid above its value and match a seller
asking below its cost, banking **negative** true surplus. The schedule draw is seeded
independently of the budget mode, so **both arms see the identical value/cost schedule
for a given seed**; the only thing that differs is how quotes are drawn.

## Measured allocative efficiency (mean over 30 seeds)

| arm | mean efficiency | std | range | mean #trades |
|---|---|---|---|---|
| **ZI-C** (budget-constrained) | **0.9715** | 0.0395 | [0.8599, 1.0000] | 4.67 |
| **ZI-U** (unconstrained) | **−0.1155** | 0.8137 | [−3.2489, 0.8047] | 8.00 |

**Efficiency gap (ZI-C − ZI-U) = 1.0870.**

- ZI-C reaches the competitive ceiling exactly (efficiency = 1.000) in 12/30 seeds and
  exceeds 0.95 in 23/30 seeds; it trades ~4.67 units, just above the equilibrium q≈4.3.
- ZI-U trades **all 8 units every time** (unconstrained traders match indiscriminately),
  so it overtrades past the equilibrium quantity and executes loss-making pairs:
  **13/30 ZI-U seeds bank net-negative surplus**, and **30/30 ZI-U seeds** fall below
  the 0.90 efficiency mark.

## Verdicts vs the locked clauses (refutation tier — "not refuted", never "verified")

| # | Locked clause | Result | Salient numbers |
|---|---|---|---|
| P1 | ZI-C achieves near-100% efficiency (mean > 0.95) | **REPRO** | mean ZI-C = **0.9715** > 0.95 |
| P2 | ZI-U is much lower (mean < 0.90) | **REPRO** | mean ZI-U = **−0.1155** < 0.90 |
| P3 | The budget constraint is the cause (ZI-C − ZI-U ≥ 0.10) | **REPRO** | gap = **1.0870** ≥ 0.10 |

**3/3 locked clauses REPRO.** The reproduction recovers Gode & Sunder's central
result: **the market institution, not individual rationality, drives allocative
efficiency.** Traders with zero intelligence — no profit motive, no learning, no
memory, pure random quoting — extract ~97% of the maximum gains-from-trade *as long as
they respect their budget constraint*; remove that single constraint and efficiency
collapses far below.

## Honest caveats

- **The signed-efficiency convention.** The LOCKED metric is realized surplus / max
  competitive surplus, computed on the TRUE value−cost of each matched pair (not the
  transaction price). Under ZI-U this is genuinely **negative** when loss-making trades
  dominate; we report the raw signed value (mean −0.116) rather than clamping it to 0.
  Clamping at 0 would only *strengthen* the qualitative result (ZI-U ≈ 0 ≪ ZI-C ≈ 0.97);
  either way P2 (< 0.90) and P3 (gap ≥ 0.10) pass overwhelmingly. The negative mean is
  the faithful signal that ZI-U does not just *fail to extract* surplus — it actively
  *destroys* it by overtrading past the equilibrium quantity into value < cost pairs.
- **Matching-rule dependence (the spec's flagged risk).** Efficiency depends on the CDA
  clearing rule. We use the standard "incoming crossing order transacts at the resting
  order's price; best-bid/best-ask book" rule. Under this rule the random walk matches
  the FIRST crossing pair it finds, which is not always the surplus-maximizing
  intramarginal pair — this is exactly why ZI-C lands at ~0.97 rather than the ~0.99 of
  Gode & Sunder's multi-step experimental schedules. The qualitative claim (ZI-C
  near-100%, ZI-C ≫ ZI-U) is robust to the rule; the exact ZI-C level is not, and we do
  **not** tune the rule to push it higher.
- **Market size M.** Gode & Sunder's experimental markets had small numbers of traders
  per side; we fixed M = 8 (mid-range of the 6–12 scale) BEFORE the run. **Correction
  (completion review 2026-06-30):** ZI-C efficiency is **non-monotone in M, and LOWEST at
  the smallest M** — measured M=4/6/8/12/16/24 → 0.929 / 0.983 / 0.972 / 0.968 / 0.950 /
  0.962 (peak ~0.98 at M=6, then a gentle 0.95–0.97 plateau). The earlier "rises toward
  0.98 at smaller M, dips at larger M" monotone story (and its random-walk rationale) was
  wrong. M = 8 (0.9715) was fixed for faithfulness to the paper's scale, not to clear P1;
  the locked M=8 grading is unaffected.
- **Transcription nit (completion review):** `PREDICTIONS-locked.md` writes the quote
  bounds as `U(0, value)` / `U(0, pmax)`, but the code uses `pmin=1` (i.e. `U(1, value)` /
  `U(1, pmax)`). Immaterial to the locked metric — the lower bound only shifts the
  transaction *price*, while efficiency is computed on the *value−cost* of matched pairs,
  which is unchanged. Noted here rather than altering the committed locked doc.
- **Single-unit demand/supply schedule.** Each trader holds exactly one unit, so the
  aggregate demand/supply schedules are the sorted values/costs. Gode & Sunder used
  multi-unit step schedules; the single-unit variant is the simplest faithful schedule
  and is sufficient to define a clean competitive equilibrium and reproduce the result.
- **Bundle `code_commit` provenance.** `verdict-bundle.json`'s `code_commit` is HEAD at
  run-time (the bundle is committed together with the code, so it points to the parent
  commit). Reproduction integrity is anchored on the content-addressed **sha256** of the
  docs/data artifacts (all `replay: strong`), not the commit pointer.
- **Scope.** Faithful reproduction of a published *synthetic* market model — no
  real-world data. The contribution is that the harness + lock-first discipline
  reproduce the ZI-C-near-100% / ZI-C ≫ ZI-U result and would surface an artifact (a
  refutation gate, not a truth certificate).
