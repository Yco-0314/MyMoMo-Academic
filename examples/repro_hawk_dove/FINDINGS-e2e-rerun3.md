# Findings — Hawk-Dove e2e RE-RUN #3 (capstone: the chain composes; bug C surfaces)

Workspace `workspace/20260608_224903_c84af2`. Predictions locked pre-run
(`d0c59e6`, PREDICTIONS-rerun3.md). Under test: bug A (heritable strategy), bug B
(flag hand-rolled turnover), and #2 (template ownership through the fix loop), all
composing on one live run. **10 HIT / 1 MISS — every fix worked; E6 froze on a
NEW, third-class extraction degeneracy (`death_rate=0.001`).**

## Scorecard (predicted → actual)

| # | predicted | actual | verdict |
|---|---|---|---|
| E1 | passes (≤1 refine) | passed iter 2/3 | **HIT** |
| E2 | operators + μ=0.01 + all-Hawk init | all captured (payoff hawk_dove V/C; Moran; mutation 0.01/strategy/[0,1]; strategy.init=1) | **HIT** |
| E3 | Coverage Gate PASS | passed | **HIT** |
| E4 | synthesis no fire | did not fire | **HIT** |
| E5a | model.py wires self.game + drives turnover + inherit w/ μ | all present | **HIT** |
| E5b | env.py CALLS self.game.play (gate enforces) | gate caught the hand-roll → GVR fix → `self.game.play(...)`, accepted iter 2/5 | **HIT** |
| **E6** | converges all-Hawk → ESS ≈ 0.5 via selection | **FROZEN: proportion_hawks = 1.000 for all 300 gens** — see below | **MISS** |
| E7 | template faithful to spec values | V/C, μ, death_rate all emitted exactly as the spec | **HIT** |
| E8 | model.py _moran_inherit has μ re-draw | present | **HIT** |
| **E9** | final env.py has NO hand-rolled turnover | env.py is interaction-only — no moran/turnover/reproduce method | **HIT** |
| **E10** | strategy heritable e2e (inherit_attrs + model.py) | spec `inherit_attrs:['strategy']` + model.py `child.strategy = copy.deepcopy(parent.strategy)` | **HIT** |

## What the capstone CONFIRMED (the wins compose live)

- **E5b again** — the operator-use gate caught the payoff hand-roll ("declared
  PayoffGame `self.game` is never called"), the GVR loop rewrote env.py to call
  `self.game.play(...)`, accepted at iter 2/5. Repeatable, not a fluke.
- **E9** — env.py is clean: it does ONLY the interaction (`self.game.play` + score
  + fitness), no hand-rolled turnover. The LLM did not re-roll Moran this time, so
  bug B's gate didn't need to fire live (its enforcement is proven deterministically
  on re-run #2's artifact). No dual-constraint thrash — the risk I flagged didn't
  materialise.
- **E10 / bug A** — the spec carries `inherit_attrs: ['strategy']` and model.py
  inherits the parent's strategy. Whether extraction set it or
  `_normalize_heritable_strategy` added it, the selected trait is heritable
  end-to-end. The run-#2 root cause is closed.
- **#2 fired and held** — the log shows `TemplateGenerator restored 2 template
  file(s) that Verifier fix loop had edited`: the Sanity_fix edited the DO-NOT-EDIT
  model.py, and the re-restore reverted it. The template-ownership guarantee held
  THROUGH the fix loop (the run-#2 leak is closed).

## E6 — frozen by `death_rate=0.001` (bug C, a NEW class)

`proportion_hawks` is 1.000 for all 300 generations — a flat freeze, not the
mutation-drift of run #2. The cause is NOT inheritance (fixed) and NOT a hand-roll
(none). It is the extracted `death_rate=0.001`: the Moran turnover replaces ~0.2
of 200 agents per generation, so over 300 gens there are ~60 births total, and the
chance any of them mutates into a Dove is ≈ `200·300·0.001·0.01·0.5 ≈ 0.3`. Zero
Doves ever appear → frozen all-Hawk.

The value is **valid but degenerate**. The first extraction tried `death_rate=0.0`
(rejected by validate()), and the retry picked `0.001` — just above the floor, and
absurd for a Moran process. The story says only "some individuals die and are
replaced", giving no rate, so the LLM anchored on its rejected 0.0 and crept just
over the line.

**Interaction with #2 (correct, but worth noting):** the Sanity_fix tried to cure
the constant output by editing model.py ("force initial strategy in
model.setup"), and #2 reverted it. That edit would not have helped (the init is
fine — every agent IS Hawk as intended; the problem is no turnover to change
them), so #2 lost nothing real. But it shows the shape of bug C: a degenerate spec
VALUE lives in template-owned model.py, so the fix loop cannot patch it (correctly
— model.py must mirror the spec). Degenerate spec values now fail LOUDLY (persistent
sanity warning) instead of being silently hand-patched. The fix belongs at
extraction/validation, which is exactly where #2 forces it to surface.

## Bug C — the clean next piece

`death_rate` (and any unspecified rate the story leaves open) can be extracted at a
valid-but-degenerate value that freezes the dynamics. Options, in order of
directness:
- **Story self-consistency** (cheapest, same move as mutation): pin the turnover in
  story.md — e.g. "each generation ~50% of the population is replaced" — so
  extraction has a number. This is the honest fix for THIS reproduction.
- **A Moran-sensible floor in validate()/normalization**: a constant-death Moran
  with `death_rate < ~0.01` is almost always a modelling error; warn or clamp.
- **Sanity-aware re-extraction**: when output is all-constant, re-extract the rate
  params with a "your dynamics froze" hint, instead of trying to patch code.

## Honest bottom line

The capstone did its job: it proved the whole chain composes on a live run —
operator-use enforced, no hand-rolled turnover, template ownership held through the
fix loop, strategy heritable end-to-end. Every fix from this arc (operators →
gate → #2 → A → B) worked together. E6 still missed, but for the THIRD distinct and
newly-isolated reason — a degenerate `death_rate`, an extraction-quality issue, not
an architecture one. My E6 prediction (HIT) was wrong again; the locked-prediction
discipline caught a third failure mode I hadn't anticipated. The architecture is
sound; the remaining gap is the story underspecifying its rates and extraction
filling them degenerately.
