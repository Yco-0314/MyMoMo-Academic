# ADR-014: The Coverage Gate — verify buildability, not just spec quality

**Status**: Accepted (design; grilled 2026-06-04 via improve-codebase-architecture, mattpocock/skills variant). No code yet — this records the interface decisions so implementation and future reviews share one shape.
**Date**: 2026-06-04
**Deciders**: yco + Claude (Opus 4.8)
**Related**: [ADR-013](ADR-013-gate-harness.md) (the `Gate` seam — the Coverage Gate is a new verification Gate; anti-fabrication: trust deterministic checks + verification, not the generator's word), [ADR-007](ADR-007-schema-driven-codegen.md) (the typed `MechanismSpec` the gate inspects), [terminology.md](../context/terminology.md#research-harness-gate-vocabulary)

---

## Context

The operator harvest (W2 `FeedforwardLearner`, W3 `RuleTable`, W4
`MoranProcess`) lets the design phase DECLARE hard mechanisms instead of
inventing them as `AI-ASSUMPTION` tags. A cross-domain boundary dogfood
(a 4-component conditional GAN for fund-manager strategies, ICAIF'25) then
exposed a gap that is **not** an operator gap:

- The design phase described the GAN faithfully (all `[paper-canonical]`,
  4 assumptions) and the **viability gate PASSED it**.
- But the design is **unbuildable**: the mechanism methods are `pass`
  stubs referencing four deep neural components the runtime does not
  provide. The CoderAgent would have to hand-write a conditional GAN — the
  exact W2 wall, quadrupled.

**The viability gate measures specification QUALITY (assumption count, the
8 required elements, an LLM judge). It does not measure BUILDABILITY.** For
deep-ML methods these diverge: a model can be perfectly specified yet
impossible for the pipeline to generate. The failure is currently silent
and scattered — it only surfaces downstream as `pass` stubs or a
hallucinated mechanism. By the **deletion test**, the knowledge "what can
this pipeline actually build" lives nowhere today; concentrating it into
one seam is a real deepening, not a pass-through.

This is ADR-013's lesson recurring one level up: the W2 wall was the
generator silently flattening a trainable net into scalars; here the *gate*
risks silently flattening an unbuildable mechanism into a "pass". Trust must
move to deterministic contract checks + empirical verification, never to
resemblance or the LLM's say-so.

## Decision

Introduce a new verification `Gate` (ADR-013), the **Coverage Gate**, after
mechanism extraction and before codegen.

### 1. Interface (what's behind the seam)

- **Input**: the typed `mechanism_spec.json` **and** `DESIGN.md` (the typed
  slots under-represent the mechanism — the GAN landed in pseudocode, not in
  `learned_operators` — so the gate must read the prose too).
- **Output**: `PASS` | `HALT(uncovered: list[Mechanism])`, where each
  uncovered entry **names the missing capability** ("needs an operator
  covering adversarial multi-network training"). Demand-driven: the halt
  tells you which operator to build next.
- **Polarity**: a verification Gate (hard door). "Cannot build" halts the
  pipeline (`pipeline_halted`), reusing the design-phase halt mechanism.

### 2. Detection: a D-LLM split (not a pure LLM judge)

A judge containing an LLM cannot be self-tested. So detection splits
(per ADR-013's D-LLM rule):

- **LLM half (generation / evidence, not verdict)**: decompose the model
  into discrete *mechanisms*; for each, emit a closed-vocabulary
  classification + a faithfulness rating. Closed enums are testable and
  keyword-backstoppable; they are hints, never the verdict.
- **Deterministic half (judgment / self-testable)**: the shape-check + tier
  + verifiability logic below. This is what PASS/HALT actually turns on.

### 3. Anti-flatten guard: contract-triple shape-check + faithfulness rating

The D-LLM split's failure mode is the LLM flattening in classification
(labelling a Q-network as `FeedforwardLearner`). Two fused signals (the
"C" guard from grilling):

**(a) Operator contract = a closed-enum triple, not an architecture.**
Each operator advertises `(input_kind, output_kind, training_signal)`:

| operator | input | output | training_signal |
|---|---|---|---|
| `FeedforwardLearner` | single item | item distribution | `supervised_pairs` |
| *(future RL operator)* | state | action values | `reward_td` |

`shape_check` covers a mechanism only if **all three** match. A Q-network
is architecturally a feed-forward net, but its `training_signal = reward_td`
≠ `supervised_pairs` → **no match → not covered.** The training-signal
dimension is what stops RL flattening; the LLM only *extracts* the triple
(closed enum, cross-checked by a deterministic keyword backstop:
`reward/return/TD/Q-value`), the deterministic **triple-match is the
verdict**. Adding an operator = adding one contract row.

**(b) Faithfulness rating** (LLM self-flag `full|partial|none`) is a cheap
first filter; `partial`/`none` halts. The deterministic shape-check is the
backstop that holds even if the rating is gamed.

### 4. Coverage is a 4-tier ladder; the fuzzy middle is resolved by VERIFIABILITY

Not `{operator | uncovered}` — four tiers by build risk:

1. **operator** — a verified library operator (contract matches). Lowest risk.
2. **ordinary** — rules / arithmetic / sampling the CoderAgent writes safely.
3. **stdlib-standard** — a named standard algorithm with a numpy/scipy path
   (Kalman filter, a simple LP, finite-difference diffusion). The fuzzy middle.
4. **uncovered** — deep / custom / no clean reference (a GAN, a bespoke solver).

The tier-3 boundary is NOT judged by a smarter classifier. It is resolved by
**verifiability**: a tier-3 mechanism passes only if codegen can emit a
mechanism-level **self-test with a known-answer oracle** (Kalman tracks a
known linear-Gaussian signal; tabular Q-learning solves a known MDP; an LP
matches a known optimum). **Pass iff that self-test passes; no oracle or a
failing test → drop to `uncovered` → HALT.** This converts "is it buildable?"
(a fuzzy prediction) into "can we verify this build?" (an empirical check) —
the anti-fabrication move of ADR-013, now applied to coverage.

This is strictly finer than any classifier: it splits same-named mechanisms
by verifiability — **tabular Q-learning (PASS, build+verify) from deep RL
(HALT)**, **Kalman (PASS) from a particle filter with no test (HALT)**.

### 5. The unifying principle

Both hard problems — flattening, and the binary/fuzzy boundary — dissolve
under one rule: **judge coverage by a deterministic CONTRACT and empirical
VERIFIABILITY, never by architectural resemblance or the LLM's word.**

## Test surface (the Gate's self-test spec)

The interface is the test surface. The Coverage Gate is a real seam only if
its fixtures span the **failure modes**, not two GAN-shaped cases:

| fixture | mechanism class | expected | why |
|---|---|---|---|
| Yaman spec | learner + turnover + rule-table | **PASS** | every mechanism contract-matches an operator |
| Conditional GAN | adversarial multi-network | **HALT** | no contract match; no verifiable build |
| Deep RL agent | reward-driven deep net | **HALT** | `reward_td` ≠ any operator; no clean oracle |
| Tabular Q-learning | reward-driven tabular | **PASS** (build+verify) | tier-3 with a known-MDP self-test |
| Kalman-filter agent | Bayesian linear update | **PASS** (build+verify) | tier-3 with a known-signal self-test |
| Custom MILP solver | bespoke optimization | **HALT** | tier-3 with no generatable oracle |

A corpus run (the 63 example models) yields a single **coverage %** — the
empirical generalization metric, replacing "vibes" about what the system can
express.

## Consequences

- **Locality**: one module owns "what can we build". **Leverage**: honest
  halt + demand-driven operator expansion (the halt names the next operator)
  + a coverage metric.
- Operator-vocabulary growth becomes demand-driven and measurable, not an
  open-ended chase.
- A small, honest **ceiling** is made explicit: mechanisms whose complexity
  is irreducible to a small interface (a GAN) are out of scope BY DESIGN —
  handled by detection + halt, not forced into a shallow mega-operator.

## Honest residual / open questions

- The remaining judgment is "**does this tier-3 mechanism have a clean
  self-test oracle?**" — more tractable than "is it buildable?" (you can
  either write a known-answer check or you cannot), and **conservative:
  halt when unsure**. A false-halt costs a human review; a false-pass costs
  a broken model — for a gate, that asymmetry favours halting.
- Per-operator contract triples + tier-3 oracle templates are the
  implementation surface to build first, alongside the six fixtures above.

## Status note

Design only, no code — same discipline as ADR-013. Build order: the
deterministic half (contract registry + shape-check + tier/verifiability
logic) and the six-fixture self-test first; the LLM extraction half second
(it is evidence, gated by the deterministic verdict).
