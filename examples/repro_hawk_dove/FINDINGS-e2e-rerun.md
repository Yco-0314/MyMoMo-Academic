# Findings — Hawk-Dove e2e RE-RUN (post codegen-fidelity fix)

Workspace `workspace/20260608_202625_9d0ff2`. Same story / deepseek / reproduce
/ `--iterations 1` / seed 42 / synthesis on as the first e2e. Predictions locked
pre-run (commit `e74d166`, PREDICTIONS-rerun.md). The only code change since the
first run (E5 MISS) is commit `0286668` — TemplateGenerator emits the operators.
Read the real workspace before scoring. **I read it; I missed E5b.**

## Scorecard (predicted → actual)

| # | predicted | actual | verdict |
|---|---|---|---|
| E1 | passes (maybe 1 refine) | passed at iter 2/3 (1 refine; first failed on an unjustified pairing-count) | **HIT** |
| E2 | re-emits operator slots | `payoff_games:[hawk_dove, V=2,C=4]` + `population_dynamics:{Moran, fitness=score, death_rate=0.05}` both present | **HIT** |
| E3 | Coverage Gate PASS | passed, build+verify none | **HIT** |
| E4 | synthesis no fire | did not fire | **HIT** |
| E5a | model.py CONSTRUCTS operators | YES — `self.game = PayoffGame.hawk_dove(V=2, C=4)`, `self._moran = MoranProcess(... death_rate=0.05 ...)`, `self._moran.turnover(...)`, `_moran_inherit` all emitted | **HIT** (structural, as predicted) |
| **E5b** | env.py CALLS the game, no hand-roll | **env.py hand-rolls `a.play_against(b)` on the agent; the agent re-implements the V=2/C=4 matrix; `self.game` is constructed but NEVER called — dead code** | **MISS** (I predicted HIT) |
| E6 | partial HIT (ESS ≈ 0.5) | froze all-hawk: `hawk_fraction = 1.0` for all 300 gens, mean_score_hawks → −4134 | **MISS** |
| E7 | template faithfully drives the spec's death_rate | YES — emitted `death_rate=0.05` and `V=2,C=4` exactly as the spec; no drift | **HIT** |

**6 HIT / 2 MISS.** The two misses are the whole story.

## E5b — the headline: construction ≠ use (my prediction was wrong)

I predicted the CoderAgent would call the constructed `self.game`. It did not.
`core/environment.py` imports only `Environment`, and its `step()` calls
`a.play_against(b)` — a hand-rolled payoff method on `core/agent.py` that
re-implements the exact Hawk-Dove matrix (Hawk-Hawk=(V−C)/2, Hawk-Dove=V, …).
The template-constructed `self.game = PayoffGame.hawk_dove(V=2, C=4)` is **dead
code** — built, handed to the model, never called.

I flagged this exact risk in the locked file ("the CoderAgent COULD still
hand-roll a `play_game()` even though `self.game` exists … construction-handoff
isn't enough on its own") — and then bet HIT anyway. The bet was wrong. Recording
the miss.

**What the fix DID close** (don't undersell it): the *turnover* half. In the first
run, env.py contained a hand-written Moran loop that drifted from the spec (1
birth-death/gen vs death_rate). This run, **env.py has no turnover loop at all** —
it is deterministic in model.py at the spec's exact `death_rate=0.05`, with the
`_moran_inherit` hook. So the turnover-fidelity gap is genuinely closed; the
payoff-call gap is not.

**Why construction wasn't enough, and the next fix.** The payoff CALL SITE lives
in the LLM-owned interaction body (`environment.step`), which decides *who plays
whom*. The template constructs the operator but does not put it in the LLM's
**path**: `environment.step(self, agents, scenario)` never receives `self.game`,
so re-deriving the matrix by hand is the path of least resistance. The clean next
seam: **pass the constructed operators into the interaction body** — e.g.
`environment.step(agents, scenario, ops)` (or expose `self.model.game`), so that
calling `ops.game.play(a, b)` is *easier* than re-implementing the matrix. Make
the operator the path, not a side table.

## E6 — the model froze all-hawk (a spec-degeneracy miss, separate from E5)

Independent of codegen fidelity, the run is scientifically degenerate:
- `scenario_params.initial_hawk_proportion = 1.0` → every agent starts Hawk.
- `agent_state_vars.strategy.init = "1"` (Hawk) reinforces it.
- `population_dynamics.inherit_attrs = []` → the Moran turnover propagates nothing;
  offspring strategy was undefined until the **Sanity_fix hand-patched**
  `child.strategy = deepcopy(parent.strategy)` into model.py.
- No mutation operator. With everyone Hawk and no way to introduce Doves,
  selection cannot create variation → frozen at `hawk_fraction = 1.0`, scores
  spiralling negative (all Hawk-vs-Hawk = −1 forever).

The first run reached ≈0.48 by the luck of a ~50/50 extracted init; this run drew
a degenerate spec. That is an **extraction/design** weakness, not a codegen one.

### Operator-coverage mismatch (new finding, F2)

The prose mechanism is **Wright-Fisher** ("weighted random sampling with
replacement at each generation" — whole-population, non-overlapping). Our only
population operator is **MoranProcess** (overlapping, fractional replacement).
Extraction shoehorned WF into Moran with `death_rate=0.05` and `inherit_attrs=[]`,
which is semantically not Wright-Fisher. The Coverage Gate PASSED it (Moran *is*
buildable — the gate judges buildability, not whether Moran is the *right* process)
but the result is a wrong turnover. This is the demand signal for a
**WrightFisherProcess** operator (whole-generation resample ∝ fitness), distinct
from Moran. Worth a Phase-3 operator if the corpus keeps wanting it.

## F1 — the template-ownership guarantee has a leak

`core/model.py` is template-owned ("DO NOT EDIT", restored by TemplateGenerator).
But the restore runs **once**, right after Phase 2 codegen (log line 63). The GVR
fix loops (`CoderVerifier-Simulation_fix`, `-Sanity_fix`) run **after** that and
**did edit model.py** — the `_moran_inherit` body carries an injected Chinese
comment ("关键修复…") and a hand-added `child.strategy` line that the template
never emits (the spec's `inherit_attrs` was empty). No re-restore followed, so the
edit stuck.

So "template-owned = untouchable" holds through codegen but **not through the
post-codegen fix loop**. To make the guarantee real, TemplateGenerator should
re-restore (or the fix loop should be barred from the 5 template files) after each
GVR fix that touches them. Filed as the next fidelity item.

## Honest bottom line

The fix did exactly half of what it set out to do, verifiably:
- **Turnover fidelity: closed.** No more hand-rolled/drifting Moran loop; the
  operator is constructed and driven deterministically at the spec's death_rate.
- **Payoff fidelity: still open.** The CoderAgent re-implements the matrix and
  ignores the constructed `self.game`, because the operator isn't in its call
  path. Construction + a prompt instruction is necessary but not sufficient — the
  operator must be passed INTO the interaction body. That's the next commit.

Two bonus findings the run surfaced: the template-ownership leak through the fix
loop (F1), and a real Wright-Fisher-vs-Moran operator-coverage gap (F2). And the
predict-first discipline did its job — it caught me betting HIT on E5b against my
own flagged risk, and made the miss impossible to rationalize away.
