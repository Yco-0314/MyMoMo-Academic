# Locked predictions — Hawk-Dove e2e RE-RUN #5 (interaction-completeness gate; layer-6 close)

Locked BEFORE the run. Since re-run #4: `2eeace3` (bug A refinement — MOVE strategy
out of reset_attrs) and `16aa73a` (interaction-completeness gate — operator must be
REACHED from environment.step(); phase2_code.md says agent.step() is never called).
Every layer found so far (1–6) now has a fix. Same deepseek / reproduce /
--iterations 1 / seed 42 / synthesis on.

## The bar

**E6 — converge from all-Hawk to ESS ≈ 0.5 via SELECTION, for real this time.**
The chain that must compose:
- env.step() actually plays the game (gate forces it onto the execution path;
  prompt says agent.step() is never called) → real scores → real fitness.
- strategy inherited, never reset (bug A + refinement) → selection acts on it.
- death_rate ≥ 0.05 (bug C) → real turnover.
- mutation seeds Doves into the all-Hawk start.
Expectation: hawk_fraction starts ≈ 1.0, falls within tens of generations,
fluctuates around 0.5 (last-30 mean in [0.4, 0.6]). Not frozen, not drifting.

## Scorecard

| # | prediction | result |
|---|---|---|
| E1 | viability passes (≤1 refine) | ? |
| E2 | operators + μ + all-Hawk + death_rate≥0.05; strategy inherited not reset | ? |
| E3 | Coverage Gate PASS | ? |
| E4 | synthesis no fire | ? |
| E5a | model.py wires self.game + drives turnover + inherit(strategy)+μ | ? |
| **E5b** | env.step() PLAYS the game (`self.game.play` reached from step) — first try, or the new gate catches an orphan/hand-roll → GVR moves it into env.step() | ? |
| **E6** | all-Hawk → fluctuates around ESS 0.5 via selection (real fitness now) | ? |
| E7 | template faithful to spec values | ? |
| E8 | _moran_inherit has μ re-draw + inherits strategy | ? |
| E9 | env.py has no hand-rolled turnover | ? |
| E10 | strategy heritable e2e (in inherit_attrs, not reset_attrs) | ? |

## My call — fifth time, stated plainly

I predict **E6 HIT**. Every one of the six layers has a fix that is verified in
isolation: the gate catches the real run-#4 orphan; the A-refinement re-sim
evolves off all-Hawk; the C floor + story give a sane death_rate; the A-fix re-sim
at sane params reached 0.5. If they compose, E6 converges.

**My record: predicted E6 HIT four times, missed four times** — mutation,
inherit_attrs, death_rate, reset_attrs+orphan. Each was a distinct layer the run
exposed. I hold this loosely. The specific new risks this run resolves:

1. **Does the gate's "not reached" message drive a successful fix?** The GVR loop
   must get the LLM to MOVE the play into env.step(). It did the analogous move for
   the payoff hand-roll (E5b, run #2), so I expect yes — but a move is harder than
   an in-place edit, and worst case it exhausts retries and HALTS.
2. **Layer 7.** Four runs found six layers; a seventh wiring/extraction quirk
   (env.step plays but mis-sets fitness; a fitness-sign issue; a collection-timing
   bug) could miss E6 a fifth way. If so, I read the real CSV, name it, and stop
   guessing it's the last one.

The run decides. I read the workspace before claiming the reproduction.
