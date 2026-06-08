# Locked predictions — Hawk-Dove e2e RE-RUN #4 (final: clean reproduction)

Locked BEFORE the run. Since re-run #3: `4970e4b` (bug C) — story.md pins
death_rate=0.5 + 10 opponents; validate() rejects a constant-Moran death_rate
below 0.01; the extraction prompt guides 0.05–0.5. With every prior fix in place
(operators, gate operator-use, #2 template ownership, A heritable strategy, B
no-hand-rolled-turnover, mutation), this run should finally produce the clean
reproduction. Same deepseek / reproduce / --iterations 1 / seed 42 / synthesis on.

## The bar this run must clear

**E6 — converge from all-Hawk to ESS ≈ 0.5 via SELECTION.** Every freeze cause
found so far is now closed:
- payoff hand-roll → operator-use gate (re-run #2 proved it).
- strategy not inherited → bug A (inherit_attrs normalized).
- dead hand-rolled turnover → bug B gate.
- death_rate degenerate → bug C (story pins 0.5, floor rejects <0.01).

Expectation: hawk_fraction starts ≈ 1.0, drops within tens of generations, and
fluctuates around 0.5 (last-30 mean in [0.4, 0.6]). NOT frozen at 1.0, NOT a slow
plateau at 0.66.

## Scorecard

| # | prediction | result |
|---|---|---|
| E1 | viability passes (≤1 refine) | ? |
| E2 | operators + μ=0.01 + all-Hawk init + **death_rate ≥ 0.05** (floor + story) | ? |
| E3 | Coverage Gate PASS | ? |
| E4 | synthesis no fire | ? |
| E5a | model.py wires self.game + drives turnover + inherit(strategy)+μ | ? |
| E5b | env.py CALLS self.game.play (gate enforces) | ? |
| **E6** | **all-Hawk → fluctuates around ESS 0.5, fast (not frozen, not 0.66)** | ? |
| E7 | template faithful to spec values | ? |
| E8 | _moran_inherit has μ re-draw | ? |
| E9 | env.py has NO hand-rolled turnover | ? |
| E10 | strategy heritable e2e (inherit_attrs + model.py) | ? |

## My call — and an honest caveat

I predict **E6 HIT** at last: the convergence is deterministically proven at sane
params (the A-fix test ran at death_rate=0.5 → ESS 0.5), and bug C closes the only
remaining freeze path. E1–E5, E7–E10: HIT.

**But: I have predicted E6 HIT three times and missed three times** — mutation
(run #1 story), inherit_attrs (run #2), death_rate (run #3) — each a DIFFERENT
layer the run exposed. So while every *known* freeze cause is closed and I expect
convergence, I hold the prediction loosely: if a FOURTH unanticipated layer exists
(another underspecified param extracted degenerately, a fitness-sign quirk, a
collection-timing issue), E6 could miss a fourth way. The run decides; I read the
real CSV before claiming the reproduction.
