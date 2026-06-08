# Locked predictions — Hawk-Dove e2e RE-RUN (post codegen-fidelity fix)

Locked to git BEFORE the run (discipline: predict first, read real output, score
honestly). This is the A/B against the first e2e (FINDINGS-e2e.md, E5 = MISS).
The only thing that changed since that run is commit `0286668`: the
TemplateGenerator now EMITs the declared operators into model.py. Same story,
same provider (deepseek), same mode (reproduce), same `--iterations 1`, same
seed 42, synthesis on.

The headline question: **does E5 flip from MISS to HIT?**

## Scorecard (to fill in from the real workspace after the run)

| # | prediction | basis | result |
|---|---|---|---|
| E1 | design passes viability (maybe after 1 refine) | fix doesn't touch design; first run took 2 iters | ? |
| E2 | extraction re-emits the operator slots (payoff_games: hawk_dove V/C; population_dynamics: Moran, fitness, inherit strategy) | same story, deterministic-ish extraction | ? |
| E3 | Coverage Gate PASS, build+verify none | operators tier-1 covered | ? |
| E4 | synthesis does NOT fire | no verifiable gap | ? |
| **E5a** | **model.py CONSTRUCTS the operators** — imports `PayoffGame, MoranProcess`; `self.hawk_dove_game = PayoffGame.hawk_dove(V=…, C=…)`; `self._moran = MoranProcess(… death_rate=0.5 …)`; calls `self._moran.turnover(self.agents, inherit=self._moran_inherit)`; has `_moran_inherit` | **structural** — model.py is template-owned and TemplateGenerator restores it over CoderAgent edits | ? |
| **E5b** | **environment.py USES the constructed payoff game** (`self.model.hawk_dove_game.play(...)` or equivalent access) and contains **NO** hand-rolled Moran loop (no inline pick-parent-∝-fitness / random-death / copy-strategy) | LLM-dependent: env.py is genuinely LLM-owned, but the operator is now pre-built + phase2_code.md forbids re-building + no competing hand-rolled turnover to anchor on | ? |
| E6 | runs to ESS ≈ 0.5 (equilibrium-holding from ~50/50 init, like the first run) | ESS-consistent | ? |
| E7 | turnover fidelity: spec `death_rate=0.5` is faithfully driven (≈ N·0.5 replacements/gen via MoranProcess), NOT the first run's drifted ~1 birth-death/gen | structural — emitted from the spec slot | ? |

## My call

- E1–E4, E5a, E7: **HIT** (E5a + E7 are structurally guaranteed by commit `0286668`; verified against the saved spec already — model.py regenerated correctly and compiles).
- **E5 overall hinges on E5b**, the LLM-dependent half. **I predict E5b = HIT**: the
  game is constructed for the CoderAgent and handed to the model as
  `self.hawk_dove_game`, phase2_code.md now explicitly says CALL not rebuild, and
  the Moran turnover is gone from env.py so there's no hand-roll pattern to anchor.
- **Honest risk on E5b**: env.py is still LLM-owned, so the CoderAgent COULD still
  hand-roll a `play_game()` on the agent even though `self.model.hawk_dove_game`
  exists — if it does, E5b = MISS and the lesson is that construction-handoff
  isn't enough on its own (we'd then need to pass the game INTO `environment.step`
  or have the agent call it). I'm calling HIT but flagging this as the real
  uncertainty the run resolves.
- E6: **partial HIT** again (equilibrium-holding, not convergence-from-extreme,
  unless the now-faithful death_rate=0.5 changes the trajectory shape).
