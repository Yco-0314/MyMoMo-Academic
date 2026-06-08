# Findings — Hawk-Dove e2e RE-RUN #2 (operator-use enforced + story self-consistent)

Workspace `workspace/20260608_214600_fb558c`. Predictions locked pre-run
(`0a09d45`, PREDICTIONS-rerun2.md). Changes under test: `1480ff7` (operator wired
onto env + gate enforces operator USE + template re-restored through the fix
loop) and `301f8d8` (Moran mutation in the inherit hook + story self-consistent).
Read the real workspace before scoring. **7 HIT / 1 MISS — and the MISS is the
most interesting result yet.**

## Scorecard (predicted → actual)

| # | predicted | actual | verdict |
|---|---|---|---|
| E1 | passes (maybe 1 refine) | passed iter 1/3, assumptions=1 | **HIT** |
| E2 | operators + mutation + all-Hawk init captured | payoff_games[hawk_dove V/C] + population_dynamics{Moran} + **mutation_rate=0.01, mutation_attr=strategy, mutation_values=[0,1]** + strategy.init=1 (all-Hawk) | **HIT** |
| E3 | Coverage Gate PASS | passed, build+verify none | **HIT** |
| E4 | synthesis no fire | did not fire | **HIT** |
| E5a | model.py constructs + wires + drives + mutation in inherit | all present (self.game, self.environment.game, self._moran.turnover, _moran_inherit with the μ re-draw) | **HIT** |
| **E5b** | env.py CALLS self.game (gate enforces) | **the gate CAUGHT the hand-roll → GVR loop REWROTE env.py to call self.game.play → accepted at iter 2/5** | **HIT** ✅ |
| **E6** | converges from all-Hawk to ESS ≈ 0.5 | 1.0 → plateau **0.66** via **mutation drift, NOT selection** — see below | **MISS** |
| E7 | template faithful to spec values | V=2/C=4, death_rate=0.5, μ=0.01 all emitted exactly | **HIT** |
| E8 | model.py _moran_inherit has the μ re-draw line | `if random.random() < 0.01: child.strategy = random.choice([0, 1])` | **HIT** |

## E5b — the headline WIN: the gate closed the loop end-to-end

This is exactly what #1 was built to do, and it worked on a real run:

```
GVR CoderVerifier: iter 1 failed → environment.py/agent.py: declared
  PayoffGame `self.game` is never called …
GVR CoderVerifier: refine attempt 2/5
  Applied fixes to: ['core/environment.py']
  Fix: environment.py 手动实现了 Hawk-Dove 收益计算，但 model.py 已声明
       PayoffGame.hawk_dove 并通过 self.game 传给环境，必须调用 self.game.play()
       而不是手写支付矩阵。
GVR CoderVerifier: accepted at iter 2/5
```

The CoderAgent hand-rolled the payoff again (its default move). The new structural
gate FAILED the build with the exact attribute name, the GVR loop fed that to the
LLM, and the LLM rewrote `environment.py` to `pa, pb = self.game.play(agent.strategy,
opponent.strategy)`. Construction + a prompt was not enough (run #1 proved that);
**construction + wiring + a deterministic gate IS.** The payoff-fidelity wall is
down, verifiably, on a live run.

## E6 — converged to the right number for the wrong reason (a false pass)

The trajectory looks like a reproduction: all-Hawk (1.0) falls and settles near
0.66, mean fitness climbs from −9 to +2.2. But it is **not** the ESS reached by
selection. The spec extracted `inherit_attrs: []` — so the operator's live
`_moran_inherit` is:

```python
def _moran_inherit(self, child, parent):
    child.score = 0.0
    child.fitness = 0.0
    if random.random() < 0.01:
        child.strategy = random.choice([0, 1])
```

There is **no `child.strategy = parent.strategy`**. The offspring never inherits
the selected parent's strategy, so fitness-proportional selection has **zero
effect on strategy** — a dead agent keeps its own strategy. The only thing that
changes strategy is the 1% mutation. So the population drifts toward the **uniform
mutation equilibrium (0.5)**, not the **ESS reached by selection (also 0.5)**. The
two coincide for V/C = 0.5, which masks the break — for V/C = 0.3 this same code
would drift to 0.5 and FAIL to reproduce ESS = 0.3. The slow 1.0→0.66 drift (300
gens at ~0.5%/gen, not yet equilibrated) is the signature of mutation-only change;
working selection would snap to 0.5 in tens of generations.

The kicker: the LLM DID write correct inheritance — `new_strategy = parent.strategy`
— but inside a **hand-rolled `moran_process` method in environment.py that is never
called** (model.run drives `self._moran.turnover`, the operator). So the right
logic is dead code, and the live operator's inherit hook is incomplete.

My E6 prediction was HIT. It is a MISS. The locked-prediction discipline caught a
result that would otherwise read as "✓ reproduced ESS 0.5" — the number is right,
the mechanism is broken, and only the V/C=0.5 coincidence hides it.

## Two root bugs (the actionable findings)

**A — `inherit_attrs` drops the strategy under selection (the root cause).**
For an evolutionary game, the `payoff_games[].strategy_var` IS the heritable trait
selection acts on; it MUST be in `inherit_attrs` or the turnover is a no-op on
strategy. Extraction set `inherit_attrs: []` (its `description` even says "offspring
inherit strategy" — it described it but didn't field it). This is deterministic to
fix: when `population_dynamics` and `payoff_games` coexist, ensure each
`strategy_var ∈ inherit_attrs` (auto-normalize in the spec, or a validate() error
forcing re-extraction). The strategy under selection being heritable is an
invariant, not a judgement call.

**B — a hand-rolled turnover in environment.py slipped past the gate.**
The operator-use gate enforces PayoffGame / RuleTable / VitalDynamics use but does
NOT flag the env DEFINING its own `moran_process` / selection / reproduction loop
when `population_dynamics` is declared (Moran is model-driven; the env must not
re-implement it). The dead `moran_process` here was harmless only because it isn't
called — but it's the same hand-roll instinct the gate exists to stop. Extend the
gate: if `population_dynamics` is declared and environment.py/agent.py defines a
selection/turnover/reproduction method, fail the build (call `self._moran` via the
model, don't re-roll it).

## Honest bottom line

- **#1 (operator-in-path + gate) is a verified success**: the payoff hand-roll was
  caught and auto-fixed on a live run — E5b HIT, the thing two runs failed at.
- **#2 (template ownership through the fix loop) held**: no sanity-fix hand-patched
  model.py this run; model.py stayed template-faithful.
- **The mutation work (E8/E2) succeeded**: extraction captured μ, the template
  emitted it, mutation introduced Doves into an all-Hawk start.
- **But E6 exposed the next layer**: enforcing PayoffGame use doesn't enforce a
  COMPLETE turnover — `inherit_attrs=[]` silently drops strategy inheritance, the
  LLM compensates in dead code, and a V/C=0.5 coincidence almost let a broken
  mechanism pass as a reproduction. Bugs A and B are the clean next pieces.

## A-fix confirmation (deterministic, no LLM run) — commit `6fd4d14`

After fixing bug A (`_normalize_heritable_strategy` puts the strategy back in
`inherit_attrs`) the model.py was regenerated from this same spec and re-run on
the SAME workspace (same GVR-fixed env.py calling `self.game.play`, same seed 42).
Only the inherit hook changed (it now does `child.strategy =
copy.deepcopy(parent.strategy)` before the mutation). `trajectory-A-fixed-deterministic.csv`:

| | run #2 (broken, inherit_attrs=[]) | A-fixed (inherit_attrs=[strategy]) |
|---|---|---|
| mechanism | mutation drift | fitness selection |
| first hawk_fraction ≤ 0.55 | never (plateau 0.66) | **gen 9** |
| endpoint | 0.66 (mutation eq, ≠ ESS) | **fluctuates around 0.5** (last-30 mean 0.531) |
| mean_fitness | stuck ≈ +2 | rises to ≈ +5 |

Selection now drives all-Hawk → ESS 0.5 quickly and the population fluctuates
around it (0.40–0.64, finite-N noise at N=200) — the textbook evolutionary-game
result, reached for the RIGHT reason. The broken run's coincidental 0.66 is gone.
This isolates the fix: nothing but the heritability normalization changed, and it
turned a mutation-drift false-pass into a genuine selection-driven reproduction.

A full live re-run (#3) would additionally confirm that extraction now keeps the
strategy heritable end-to-end and that bug B's gate stops the dead `moran_process`
from being written — but the mechanism itself is proven here, deterministically.
