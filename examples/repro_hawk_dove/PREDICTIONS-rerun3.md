# Locked predictions — Hawk-Dove e2e RE-RUN #3 (capstone: whole chain composes live)

Locked to git BEFORE the run. Changes since re-run #2 (FINDINGS-e2e-rerun2.md):
- `6fd4d14` — bug A (`_normalize_heritable_strategy`: strategy_var forced into
  inherit_attrs when population_dynamics + payoff_games coexist) + bug B (the
  structural gate now fails the build on a hand-rolled turnover/selection method
  in env.py/agent.py when population_dynamics is declared).
- `5d255df` — A-fix already confirmed deterministically (selection → ESS 0.5).

Same provider (deepseek), mode (reproduce), `--iterations 1`, seed 42, synthesis
on. This run confirms the WHOLE chain composes on one live run:
extraction → gate (operator-use AND no-hand-rolled-turnover) → GVR → a
selection-driven reproduction.

## Scorecard (fill from the real workspace after the run)

| # | prediction | basis | result |
|---|---|---|---|
| E1 | design passes viability (≤1 refine) | unchanged | ? |
| E2 | extraction emits payoff_games + population_dynamics{Moran, μ=0.01} + all-Hawk init | story + prompt | ? |
| E3 | Coverage Gate PASS | Moran tier-1 | ? |
| E4 | synthesis no fire | no gap | ? |
| E5a | model.py constructs+wires self.game, drives self._moran.turnover, _moran_inherit with μ | structural | ? |
| E5b | env.py CALLS self.game.play (gate enforces; first try or after GVR fix) | gate | ? |
| **E6** | **converges from all-Hawk to ESS ≈ 0.5 via SELECTION** — hawk_fraction starts ≈1.0, drops to fluctuate in [0.4, 0.6] (last-30 mean ≈ 0.5), reached FAST (~tens of gens, not a slow plateau at 0.66) | **bug A guarantees strategy ∈ inherit_attrs regardless of extraction** | ? |
| E7 | template emits spec values faithfully (V/C, death_rate, μ) | structural | ? |
| E8 | model.py _moran_inherit has the μ re-draw line | mutation e2e | ? |
| **E9** | **final env.py/agent.py define NO hand-rolled turnover** (no moran/turnover/reproduce/wright_fisher/birth_death method) — either the LLM doesn't write one, or the gate catches it and GVR removes it | **bug B gate enforces** | ? |
| **E10** | **strategy IS heritable end-to-end** — final spec population_dynamics.inherit_attrs contains "strategy" AND model.py _moran_inherit has `child.strategy = copy.deepcopy(parent.strategy)` | bug A from_dict normalization | ? |

## My call

- E1–E5a, E7, E8: **HIT** (structural / unchanged-or-already-confirmed).
- **E5b: HIT** — proven in re-run #2; the gate enforces it.
- **E6: HIT** — this is the capstone, and it is now deterministically backed: bug
  A's from_dict normalization puts strategy in inherit_attrs even if extraction
  omits it, so the live Moran turnover propagates the fit parent's strategy →
  selection drives all-Hawk to the true ESS 0.5 (confirmed in isolation,
  `5d255df`). I expect fast convergence + fluctuation around 0.5, NOT the run-#2
  drift-to-0.66.
- **E10: HIT** — guaranteed by A (from_dict always normalizes on the codegen path).
- **E9: HIT** — the gate fails a hand-rolled turnover; the prompt also tells the
  LLM not to write one.

## Honest risks

1. **Dual-constraint GVR thrash (E5b × E9).** The LLM must now satisfy BOTH: CALL
   self.game.play in env.step AND define NO turnover method (rely on model.py's
   self._moran.turnover, which it can't see/edit). If it "helpfully" hand-rolls a
   moran_process that calls self.game inside, operator-use passes but the
   hand-rolled-turnover gate fails; the GVR loop must get it to delete the method.
   This could take extra iters or, worst case, exhaust max_retries and HALT. I
   predict a clean resolution (the prompt explains turnover is model-driven), but
   this is the real uncertainty this run resolves.
2. **E6 init.** Story pins an all-Hawk start; if extraction somehow draws a mixed
   init, E6 still converges (selection works) but doesn't test convergence-from-
   extreme. Low risk (story is explicit).

The one genuinely new thing this run tests: does bug B's gate + the GVR loop
compose WITHOUT thrashing against the operator-use gate. Predicting HIT; the run
decides.
