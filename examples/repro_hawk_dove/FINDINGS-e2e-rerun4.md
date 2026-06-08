# Findings — Hawk-Dove e2e RE-RUN #4 (two more layers; the chase meets the long tail)

Workspace `workspace/20260608_232210_0c6a7c`. Predictions locked pre-run
(`ce886ad`). I predicted E6 HIT but flagged a possible fourth layer. There were
TWO: a fifth (strategy in reset_attrs) and a sixth (orphaned interaction). E6 MISS
again — and the picture is now clear enough to name.

## What worked (the architecture held, again)

- **death_rate sane (bug C)** — extraction produced `death_rate=0.5` first try, no
  invalid-JSON retry. The story-pin + floor + prompt guidance worked. E2/E7 good.
- **operator-use gate (E5b)** — caught "declared PayoffGame self.game is never
  called", GVR fixed it. **#2 held** — log: "restored 2 template file(s) that
  Verifier fix loop had edited". **E9** — env.py has no hand-rolled turnover.

## Fifth layer — strategy in `reset_attrs` (E6 freeze, FIXED `2eeace3`)

The live run froze at `hawk_fraction ≈ 0.99` for all 300 gens. Cause: extraction
put `strategy` in `reset_attrs`, so the generated `_moran_inherit` did
`child.strategy = 1` (reset to init=Hawk) EVERY turnover — wiping the evolving
distribution back to all-Hawk each generation. Worse, my re-run #2 normalization
had a defensive guard ("skip if in reset_attrs") that PRESERVED this. Fixed: the
invariant is two-sided — the selected trait must be INHERITED and NEVER RESET — so
`_normalize_heritable_strategy` now MOVES strategy_var out of reset_attrs into
inherit_attrs. A deterministic re-sim with the fix unfreezes (population evolves
off all-Hawk).

## Sixth layer — the interaction is orphaned (NEW, unfixed)

But the unfrozen re-sim drifts to ~0.14, not the ESS — because run #4's
interaction never actually runs. `core/agent.py:step()` plays the game
(`self.model.game.play(...)`), but the framework NEVER calls `agent.step()`:
the template's `model.run()` drives only `environment.step()` + turnover, and
`environment.step()` here only counts hawks (no game, no scoring). So every
agent's `fitness` stays at its init, MoranProcess sees flat fitness, selection is
UNIFORM, and the trajectory is neutral drift + mutation — not selection toward the
ESS.

The operator-use gate PASSED this: `self.model.game` is referenced in agent.py, so
"the operator is called" is satisfied — but the call sits in a method that is
never on the execution path. **The gate checks that the operator is REFERENCED,
not that it is REACHED from `environment.step()`.** That is its blind spot, and
the sixth distinct way this one model has been mis-wired.

## The meta-picture: architecture proven, codegen-wiring is a long tail

Four live runs, six distinct failure layers, each a DIFFERENT bug:

| run | layer | class | status |
|----|-------|-------|--------|
| #1 | payoff hand-rolled | codegen fidelity | fixed (operator-use gate) |
| #2 | strategy not inherited | spec completeness | fixed (bug A) |
| #2 | dead hand-rolled turnover | codegen fidelity | fixed (bug B gate) |
| #3 | death_rate degenerate | extraction quality | fixed (bug C) |
| #4 | strategy reset each gen | spec completeness | fixed (A refinement) |
| #4 | interaction orphaned in agent.step | codegen wiring | OPEN |

The systematic-architecture bugs (operators, gates, ownership, spec
normalization) are closed and proven — every one of those fixes composes and
holds across runs. What remains (layer 6, and likely a 7th behind it) is
LLM-codegen WIRING variance: the long tail of ways an LLM can place correct logic
where it won't run. The e2e has been an excellent dogfood — it found six real
bugs — but "get E6 to exactly ESS 0.5 on a fresh live run" is now a chase of that
long tail, not of architecture.

## Honest bottom line + the fork

My E6 prediction was wrong a fourth time; the discipline caught two more layers.
The reproduction is not clean on a live run yet, and one more fix will likely
surface a seventh wiring quirk. Three honest paths:

1. **Declare the architecture proven, stop the live-E6 chase.** The systematic
   work is done; the e2e validated it by finding six bugs. Document layer 6.
2. **External-model reference repro.** Hand-write a correct `environment.py`
   (env-driven, plays the game, sets fitness) and run it through `--external-model`
   — isolates "does the SCIENCE reproduce" (it does: the A-fix re-sim at sane
   params converged to 0.5) from "does the LLM wire it" (the long tail). Same move
   as Yaman Path-2.
3. **Build the interaction-completeness gate.** Verify the operator is REACHED from
   `environment.step()` (light call-graph), + a prompt fix that `agent.step()` is
   never called so env.step must drive the whole interaction. Closes layer 6 as a
   class, but is a real piece of work and won't guarantee no layer 7.
