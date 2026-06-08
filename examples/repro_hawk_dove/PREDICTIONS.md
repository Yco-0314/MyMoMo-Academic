# Pre-registered predictions — Hawk-Dove full-pipeline e2e

Locked to git BEFORE running the live pipeline (the discipline: read real output
before any conclusion). The goal: do the Phase-2 operators flow through the WHOLE
live pipeline — design declares them, extraction emits the spec slots, the
Coverage Gate covers them, codegen uses them, the model runs and reproduces the
ESS?

Run: `ABM_ENABLE_SYNTHESIS=1 python -m abm_auto run examples/repro_hawk_dove/story.md
--mode reproduce --iterations 1 --seed 42`

## Predictions

- **E1 — design**: DESIGN.md declares a payoff-matrix game (Hawk-Dove) AND a
  Moran / fitness-proportional turnover. Passes the viability gate (well-specified;
  ≤5 assumptions).
- **E2 — extraction**: mechanism_spec.json carries a `payoff_games` entry
  (hawk_dove or matrix) and a `population_dynamics` entry (fitness ∝ score).
- **E3 — Coverage Gate**: PASS. Both mechanisms are operator-covered
  (PayoffGame, MoranProcess) — NOT uncovered, NOT halted.
- **E4 — synthesis**: does NOT fire. Both mechanisms are tier-1 operators, so
  there is no verifiable gap to synthesize (this is correct, not a miss).
- **E5 — codegen**: the generated model imports + uses `PayoffGame` and
  `MoranProcess` (does not hand-roll the matrix or the turnover loop).
- **E6 — run**: the model runs to completion and the Hawk fraction ends near the
  ESS p* = V/C = 0.5 (say within [0.35, 0.65]).

## Honest falsification / expected walls

Any of these is a real finding, recorded as-is:
- viability gate rejects (too many assumptions) → halt at Phase 1c.
- extraction puts the game in the wrong slot (e.g. reference_assets) → a
  mis-extraction finding.
- CoderAgent drift: ignores the operators and hand-rolls (or stubs) the
  mechanism → codegen-fidelity finding.
- the run crashes or the Hawk fraction does NOT approach 0.5 → mechanism-drift
  finding.

n=1 live run; the LLM phases are stochastic + the classifier is flaky.
