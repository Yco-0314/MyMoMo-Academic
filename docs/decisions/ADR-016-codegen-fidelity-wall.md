# ADR-016: The codegen-fidelity wall is six layers — judge by invariant + reachability, never the generator's word

**Status**: Accepted (empirically validated). Five locked-prediction live reproductions of a textbook Hawk-Dove model (deepseek, reproduce mode, seed 42) found six distinct fidelity layers; each got a deterministic fix; run #5 is a clean 11/11 with E6 converging all-Hawk → ESS 0.5 via selection.
**Date**: 2026-06-09
**Deciders**: yco + Claude (Opus 4.8)
**Related**: [ADR-007](ADR-007-schema-driven-codegen.md) (TemplateGenerator owns boilerplate — the wall this ADR extends to operator USE), [ADR-014](ADR-014-coverage-gate.md) (coverage = can we EXPRESS it; this ADR = did we BUILD it faithfully), [ADR-012](ADR-012-method-transfer-engine.md) (anti-fabrication: trust deterministic checks, never the generator), [ADR-013](ADR-013-gate-harness.md) (the `Gate` seam; `StructuralFidelityGate` is a verification Gate). Evidence: `examples/repro_hawk_dove/FINDINGS-e2e-rerun{,2,3,4,5}.md`.

---

## Context

ADR-007 made the 5 boilerplate files deterministic (TemplateGenerator owns
them). ADR-014 made *expressibility* a gate (the Coverage Gate halts on a
mechanism no operator can cover). Together they imply a tempting conclusion: a
spec that is covered and whose boilerplate is template-owned will generate a
faithful model.

It will not. The mechanism BODIES — `core/agent.py`, `core/environment.py`, and
the extraction-filled slots of `mechanism_spec.json` — are LLM-owned, and that is
where a declared operator gets mis-wired. The model still compiles and runs; it
just reproduces nothing, or (worse) the right number for the wrong reason. We
named this the **codegen-fidelity wall** when the first Hawk-Dove e2e (run #1)
showed the CoderAgent hand-rolling a `PayoffGame` it had been handed.

Dogfooding the fix across five locked-prediction reproductions proved the wall is
**not one wall but six distinct layers**. Each is silent — the pipeline reports
success — and each was caught only because predictions were git-locked before each
run and the real CSV was read after (the locked-prediction discipline).
Run #2's model even settled at hawk-fraction 0.66 ≈ "looks like the ESS 0.5-ish",
a false pass that the V/C=0.5 coincidence nearly hid.

By the **deletion test**, "is this declared operator actually on the faithful
execution path?" is knowledge that lived nowhere — scattered across whatever the
LLM happened to emit. Concentrating it into deterministic spec-normalization +
structural gates is a real deepening.

## Decision

Treat codegen fidelity as a **catalogue of six layers**, each closed by a
deterministic check that owns one invariant. No layer trusts the LLM's word; every
verdict is a spec-normalization or an AST/regex structural check (ADR-012 lineage).

| # | layer (the silent failure) | fix | seam that owns it |
|---|---|---|---|
| 1 | declared operator **hand-rolled** in the body (payoff matrix re-implemented) | operator-USE check: declared PayoffGame/RuleTable/VitalDynamics must be called | `StructuralFidelityGate` |
| 2 | the **selected trait dropped** from `inherit_attrs` → turnover is a no-op on strategy | `_normalize_heritable_strategy`: force `strategy_var ∈ inherit_attrs` | `mechanism_spec.from_dict` |
| 3 | a **dead hand-rolled turnover** in env.py (parallel Moran) | no-hand-rolled-turnover check when `population_dynamics` is declared | `StructuralFidelityGate` |
| 4 | a **degenerate-but-valid rate** (`death_rate=0.001`) freezes the dynamics | `MORAN_DEATH_RATE_FLOOR=0.01` in `validate()` + story pins the rate + prompt guidance | `mechanism_spec.validate` + story + prompt |
| 5 | the selected trait placed in **`reset_attrs`** → reset to init every generation | `_normalize_heritable_strategy`: MOVE `strategy_var` out of reset, into inherit (two-sided invariant) | `mechanism_spec.from_dict` |
| 6 | the interaction is **orphaned in `agent.step()`** — the framework never calls it | reachability check: operator must be REACHED from `environment.step()`; prompt states `agent.step()` is never called | `StructuralFidelityGate` (`_env_step_reachable_src`) + prompt |

### The unifying principle

Every layer is one disease: **the generated code names a declared operator
somewhere that is not on the faithful execution path** — re-implemented (1, 3),
not heritable / wrongly reset (2, 5), starved of turnover (4), or stranded in an
uncalled method (6). The cure is always the same shape: **a deterministic check on
an INVARIANT or on REACHABILITY, never the LLM's say-so.** Two families:

- **Spec normalization** (`mechanism_spec.py`): the extraction fields a structural
  invariant wrong, and we fix it deterministically on load — the selected trait is
  inherited and never reset (a two-sided invariant); a constant-Moran death_rate
  below the freeze floor is rejected so the spec re-extracts. These are not
  judgement calls.
- **Structural gates** (`StructuralFidelityGate`, ADR-013 verification tier): the
  body mis-wires the operator, and a scan catches it — *used* (not hand-rolled),
  *not duplicated* (no parallel turnover), *reached* from `environment.step()`. The
  gate failure feeds the GVR loop, which moves the LLM toward the faithful wiring.

"Referenced" is not "reached": layer 6 is the sharp form — the operator-use scan
(layer 1) passed run #4 because `self.game` appeared in an orphaned `agent.step()`.
A fidelity gate must check the operator is on the per-tick path
(`environment.step()` is the framework's only call), not merely present.

## Evidence (the five-run arc)

| run | layers exposed | result |
|---|---|---|
| #1 | 1 (payoff hand-rolled) | declaration flows, USE does not |
| #2 | 2, 3 (strategy not inherited; dead hand-rolled Moran) | E5b WIN (gate caught the hand-roll); E6 false-pass at 0.66 (mutation drift) |
| #3 | 4 (death_rate degenerate) | chain composes; E6 frozen by `death_rate=0.001` |
| #4 | 5, 6 (strategy reset; orphaned interaction) | E6 frozen at 0.99; the re-sim drifted (orphaned game) |
| #5 | — | **11/11; E6: 1.000 → ≤0.60 by gen 11 → last-100 mean 0.515 (sd 0.042), ESS 0.5, via real selection** |

Run #5's `mean_score` swings −20 (all-Hawk) → +10 (mixed): the game is genuinely
played, so the convergence is selection, not run #2's coincidental drift.

## Test surface

- **`StructuralFidelityGate.self_test`** spans the failure modes: (e) operator
  called → pass, (f) never called → caught, (g) hand-rolled turnover → caught,
  (i) operator only in `agent.step()` → caught, (j) operator reached via an env
  helper `step()` calls → pass. Exhaustive over the check families → verification tier.
- **`mechanism_spec`** tests: strategy moved out of reset into inherit; death_rate
  floor rejects 0.001/0.009 and passes 0.05/0.5; mutation validation.
- **The e2e itself** is the integration test: locked predictions + real-CSV
  scoring per run. The discipline is load-bearing — it converted four "looks
  reproduced" into caught false-passes and one verified reproduction.

## Consequences

- **Locality**: "is this operator faithfully built?" now lives in two named seams
  (spec normalization + the structural gate), not in whatever the LLM emitted.
- **Leverage**: each new operator/mechanism class can add its fidelity invariant
  the same way (a contract row, a normalization, a gate fixture). The wall is now
  a catalogue you extend, not a surprise you rediscover.
- **Demand-driven, like ADR-014**: layers were found by dogfooding a real model,
  not enumerated a priori. The catalogue is the empirical record of what actually
  breaks.

## Honest residual / open questions

- **The catalogue is open.** Six layers is what one model (Hawk-Dove:
  PayoffGame + MoranProcess) exposed. A model exercising other operators
  (FeedforwardLearner, RuleTable, VitalDynamics) will likely expose a seventh —
  e.g. env.step plays but mis-sets fitness, or a collection-timing bug. The
  *principle* (invariant + reachability, never the LLM's word) generalizes; the
  *fixture list* will grow.
- **Reachability is best-effort static analysis.** `_env_step_reachable_src` walks
  the AST from `environment.step()` through `self.<m>()` helpers; on parse failure
  or no `step` it falls back to scanning the whole file (safe, less precise). It
  does not model the (discouraged) pattern of `environment.step()` activating
  agents — the prompt steers to env-driven interaction, and the gate enforces it.
- **Conservative by construction**: every check halts/fails toward "make the LLM
  fix it", matching ADR-014 — a false-fail costs a GVR iteration; a false-pass
  costs a silently-broken reproduction, and that asymmetry favours failing.
