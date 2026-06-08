# Locked predictions — Hawk-Dove e2e RE-RUN #2 (operator-use enforced + story self-consistent)

Locked to git BEFORE the run. Changes since re-run #1 (FINDINGS-e2e-rerun.md):
- `1480ff7` — operator wired onto the env (`self.environment.game = self.game`);
  phase2_code.md fixed (no more "construct in model.py"); **structural gate now
  FAILS the build if a declared interaction operator is never called**; template
  files re-restored through the GVR fix loop.
- `301f8d8` — Moran mutation in the inherit hook; story.md made self-consistent
  (μ=0.01 + an all-Hawk start), so convergence-from-extreme is now achievable.

Same provider (deepseek), mode (reproduce), `--iterations 1`, seed 42, synthesis
on. This run tests BOTH halves at once: **E5b** (does the operator actually get
called now that the gate enforces it?) and **E6** (does it converge from all-Hawk
now that mutation exists?).

## Scorecard (fill from the real workspace after the run)

| # | prediction | basis | result |
|---|---|---|---|
| E1 | design passes viability (maybe 1 refine) | unchanged path | ? |
| E2 | extraction emits payoff_games[hawk_dove, V/C] + population_dynamics{Moran, fitness} **AND mutation_rate≈0.01 / mutation_attr=strategy / mutation_values=[0,1]** AND an all-Hawk init (initial_hawk_proportion≈1.0) | story states μ + all-Hawk; mechanism_spec_json.md now documents the mutation fields | ? |
| E3 | Coverage Gate PASS | Moran tier-1 covered | ? |
| E4 | synthesis does NOT fire | no verifiable gap | ? |
| E5a | model.py constructs `self.game`+`self._moran`, **wires `self.environment.game = self.game`**, drives turnover, `_moran_inherit` **with the mutation re-draw line** | structural (template) | ? |
| **E5b** | **environment.py CALLS `self.game.play(...)`** — NOT a hand-rolled `play_against`. Either first try, or the gate catches the hand-roll → GVR fix → env rewritten to call it. The FINAL env.py references `self.game` (or the build halts) | the structural gate now enforces this | ? |
| **E6** | **converges from all-Hawk down to ESS ≈ 0.5** (hawk_fraction starts ≈1.0, mutation seeds Doves, selection balances to ~0.5) — true convergence-from-extreme | mutation now exists + all-Hawk init pinned | ? |
| E7 | template emits the spec's values faithfully (V/C, death_rate, μ) | structural | ? |
| E8 | the generated model.py `_moran_inherit` contains `if random.random() < <μ>: child.strategy = random.choice([0, 1])` | mutation end-to-end | ? |

## My call

- E1, E3, E4, E5a, E7: **HIT** (E5a/E7 structural).
- **E5b: HIT** — the gate now makes "operator never called" a build failure, so the
  final env.py must call `self.game` or the run halts. The first-try-vs-after-fix
  distinction is interesting but either lands on HIT.
  - **Honest risk**: if the LLM hand-rolls AND the GVR loop can't rewrite env.py to
    call `self.game` within `max_retries`, the build HALTS — E5b would then be
    "enforced but unfixed" (no result), which is a different failure than the
    silent E5b MISS of run #1, but still not a clean HIT. I predict the loop fixes
    it (the gate error names the exact attribute), but flag this.
- **E6: HIT** — with mutation + all-Hawk start the model can leave the monomorphic
  state and converge to ~0.5. This is the real convergence-from-extreme the first
  two runs never tested.
  - **Honest risk (the biggest one)**: this depends on **extraction capturing
    mutation** (E2/E8). If the LLM omits `mutation_rate` from the spec (despite the
    story stating it and the prompt now documenting it), mutation_rate stays 0 →
    all-Hawk FREEZES AGAIN → E6 MISS. This run is the test of whether the prompt
    change is enough to get mutation extracted. I predict HIT but this is where I'm
    least certain.
- E8: **HIT** iff E2 captures mutation; same risk as E6.

The two genuine uncertainties this run resolves: (1) does the GVR loop *act* on the
new gate failure, and (2) does extraction *capture* mutation from the story. I'm
predicting HIT on both; the run decides.
