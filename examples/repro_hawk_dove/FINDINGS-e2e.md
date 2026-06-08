# Findings — Hawk-Dove full-pipeline e2e

Full live pipeline run (`workspace/20260608_111003_830465`, deepseek, reproduce
mode, synthesis enabled). Predictions locked pre-run in PREDICTIONS.md (7935b9b).
Read the real workspace before scoring.

## Scorecard

| # | prediction | result |
|---|---|---|
| E1 | design passes viability | **HIT** — failed once (8 tags), refined, passed (2 assumptions, 0 missing) |
| E2 | extraction emits the operator slots | **HIT** — `payoff_games: [{game: hawk_dove, params V/C, strategy_var}]` AND `population_dynamics: {Moran, fitness∝score, inherit strategy}`. Both correct. |
| E3 | Coverage Gate PASS | **HIT** — passed, build+verify none |
| E4 | synthesis does NOT fire | **HIT** — operators are tier-1 covered, no verifiable gap (correct) |
| E5 | **codegen USES the operators** | **MISS** — the headline finding (below) |
| E6 | runs to the ESS ~0.5 | **partial HIT** — ran 300 gens; hawk fraction 0.465 → 0.48 ≈ ESS 0.5. BUT initialised ~50/50, not from an extreme, so it tested equilibrium-holding, not convergence-from-extreme as the story asked. |

## The headline finding (E5): declaration flows through, USE does not

The operator pipeline is complete and correct on the DECLARATION side —
design → extraction → Coverage Gate all carry PayoffGame + MoranProcess through
perfectly (E1-E3). But the generated code does NOT use them:

- `environment.py` imports only `Environment` (no `PayoffGame`/`MoranProcess`).
- it calls `agents[i].play_game(agents[j])` — a HAND-ROLLED payoff method on the
  agent, not `self.game.play(a, b)`.
- the Moran turnover is HAND-WRITTEN inline (pick a parent ∝ fitness, pick a
  random death, copy the strategy) — not `MoranProcess.turnover(...)`. It even
  drifts from the spec (one birth-death/gen vs the spec's death_rate=0.5).

So the **CoderAgent hand-rolled both declared mechanisms** instead of calling the
provided operators, despite phase2_code.md telling it to use them.

## Why this matters + the fix direction

This is the operator analogue of the schema-driven-codegen principle (ADR-007):
the operators removed the EXPRESSIBILITY wall (a GAN-class mechanism is now
declarable, the gate covers it), but they did NOT remove the codegen-FIDELITY
wall — the CoderAgent writes the mechanism BODIES (agent.py / environment.py)
freely and hand-rolls the operator instead of calling it. The TemplateGenerator
emits the 5 boilerplate files deterministically from the spec, but operator
CONSTRUCTION + the call sites live in the LLM-filled bodies, where guidance alone
doesn't bind.

The fix (a clean next piece, not built): extend the TemplateGenerator to EMIT
the operator construction + wiring DETERMINISTICALLY from the spec's
`payoff_games` / `population_dynamics` / `vital_dynamics` / `reference_assets`
slots — `self.game = PayoffGame.hawk_dove(...)`, `self.moran =
MoranProcess(...)`, and the per-tick `turnover` / `play` call — exactly as
topology is wired today. Then the CoderAgent can only fill the genuinely-custom
glue, and cannot hand-roll (or stub, or drift) a declared operator. This makes
operator USE as deterministic as operator DECLARATION already is.

## Honest bottom line

The e2e proved the DECLARATION machinery works end-to-end on a real model
(design→extraction→gate→run, ESS-consistent result). It also proved the model
RAN and produced the right equilibrium — but via hand-rolled code, NOT the
operators, which defeats their purpose (verified, correct-once library code; the
hand-roll happened to be correct here, but that unreliability is exactly what the
operators exist to remove). The codegen-fidelity gap is the real, actionable
finding — and a clean next step.
