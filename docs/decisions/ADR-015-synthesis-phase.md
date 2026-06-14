# ADR-015: The Synthesis Phase — bounded self-extension of the operator vocabulary

**Status**: Accepted (design; reasoned 2026-06-04 as the layer above the Coverage Gate). No code yet.
**Date**: 2026-06-04
**Deciders**: yco + Claude (Opus 4.8)
**Related**: [ADR-014](ADR-014-coverage-gate.md) (the Coverage Gate detects gaps + halts — this closes them), [ADR-013](ADR-013-gate-harness.md) (the human-audited self-test *paradigm library* is the trust frontier here; a generator cannot certify its own correctness)

---

## Context

ADR-014's Coverage Gate is a DETECTOR: on a gap (a mechanism with no
operator) it halts and names what's missing. Detection is passive. The
natural question: can the system CLOSE its own gaps — read the paper,
understand the missing mechanism, synthesize a new operator, and
**internalize** it as a first-class abm-auto artifact, the same shape as the
hand-harvested W2/W3/W4 operators?

The tempting framing is "the agent lacks adaptive learning." That framing is
wrong. An LLM CAN read a mechanism and draft an operator — the generative
ability is there. The real constraint is **trust**: can the synthesized
operator be internalized WITHOUT a human, or would that be the architecture-
level version of the fabrication ADR-013 exists to prevent (the system
confidently internalizing a mechanism that is silently wrong)?

So the boundary of safe self-extension is not intelligence. It is the same
**verifiability** line ADR-014 draws — now applied to the birth of an operator.

## Decision

Add a **Synthesis Phase** that runs only when the Coverage Gate halts with an
uncovered mechanism. It is gated by ADR-013's human-audited self-test
*paradigm library* — the same finite, audited set of known-answer oracles.

### The loop

```
Coverage Gate HALT(uncovered: M)
      │
      ▼
Is there a known-answer ORACLE PARADIGM for M's mechanism class
in the human-audited paradigm library?   (a deterministic registry lookup)
      │
  ┌───┴────────────────────────────────────────────┐
  │ yes (verifiable)                                │ no (unverifiable)
  ▼                                                 ▼
agent synthesizes the operator                  agent emits a PROPOSAL:
  (runtime library module +                       draft operator + draft
   contract triple + schema slot)                 candidate oracle.
      │                                            The Coverage Gate HALT
bind the LIBRARY oracle (NOT a                     STANDS. A human audits the
generated one) as its self_test                    oracle; if sound it enters
      │                                            the paradigm library, and
run self_test                                      FUTURE runs self-extend.
  ┌───┴───┐
  │ pass  │ fail
  ▼       ▼
INTERNALIZE   discard;
(register     halt stands
operator +
contract +
slot) →
re-gate →
covered
```

### The trust law (why the oracle must be independent)

If the agent writes BOTH the operator AND its self-test, the generator is
certifying itself — exactly the laundering ADR-013 forbid (a Gate's
`judge` may not be produced by the thing it judges). So the self-test's
ORACLE must come from the **human-audited paradigm library**, not be freely
generated to match the operator. Within validated paradigms the agent extends
autonomously; a NEW paradigm requires human audit before it confers trust.

### The two regimes, concretely

- **Verifiable gap** (a standard algorithm with a known-answer oracle —
  Kalman, tabular-Q, a simple LP; ADR-014 tier-3): safe AUTONOMOUS
  self-extension. The new operator earns trust the way W2/W3/W4 did — by
  passing a self-test it did not author. Result: the gap mechanism becomes a
  declarable operator, identical in shape to the hand-built ones. This is
  "internalize as abm output," made safe.
- **Unverifiable gap** (deep GAN, bespoke solver — no clean oracle): NO
  autonomous internalization. The agent proposes (operator + candidate
  oracle); a human audits the oracle. Not an agent deficiency — a trust law:
  without an independent oracle, no amount of "understanding" makes the output
  trustworthy.

## Test surface

The Synthesis Phase is itself harness-gated, so its own self-test is:

| fixture | gap mechanism | oracle paradigm in library? | expected |
|---|---|---|---|
| Kalman gap | bayesian_filter (kalman) | yes (track known signal) | **synthesize → self-test → internalize → re-gate PASS** |
| Tabular-Q gap | reinforcement_learning (tabular) | yes (solve known MDP) | **internalize → re-gate PASS** |
| Synthesized-but-buggy | (operator that fails the library oracle) | yes | **discard; halt stands** (proves the oracle actually gates) |
| GAN gap | generative_model | no | **proposal emitted; halt stands** (no autonomous internalization) |
| Self-certifying attempt | agent supplies its OWN oracle | — | **rejected** (oracle must come from the audited library) |

The buggy-synthesis and self-certifying fixtures are load-bearing: they prove
internalization turns on an INDEPENDENT oracle passing, not on the generator's
word.

## Consequences

- The system **grows its own operator vocabulary** autonomously — but only
  within verifiable paradigms. New paradigms gate on human audit.
- **The frontier of safe self-extension = the frontier of strong known-answer
  oracles = the human-audited paradigm library.** Growing the system means
  growing that library (audited), not just making the agent cleverer.
- Detection-then-halt (ADR-014) stays the safe FLOOR; Synthesis is an
  oracle-bounded addition on top, never a replacement.

## Honest residual / open questions

- **Ungated synthesis would be architecture-level fabrication** — the system
  "understands" a mechanism it cannot build, synthesizes an unverified
  operator, and internalizes it as if correct. That is strictly WORSE than
  halting (it disguises "I can't" as "I did"). The oracle gate is the only
  thing separating self-extension from self-deception.
- **Verification proves presence, not absence, of bugs.** A weak oracle
  passes a subtly-wrong operator. Strong oracles correlate with well-
  understood, standard algorithms — exactly tier-3. So self-extension is
  strongest where mechanisms are standard and forbidden where they are novel/
  deep. This is a feature, not a flaw: the system is most autonomous exactly
  where autonomy is safe.
- Build order: the deterministic registry lookup ("is there an oracle
  paradigm for class M?") + the internalize/re-gate plumbing first (self-
  testable); the LLM synthesis step second (a proposal, gated by the oracle).

## Prior art: synthesis should be a SEARCH, not single-shot (cf. DataMaster)

DataMaster (arXiv:2605.10906, SJTU) does autonomous data-engineering as a
**tree-structured search**: a DataTree (explore branches / exploit-refine), a
shared Data Pool (reusable candidates), and Global Memory (outcomes across
rounds). That machinery is the right shape for the LLM synthesis step here,
which is currently single-shot (draft ONE candidate operator → gate it).
Adopt it: **explore candidate operator implementations, refine the promising
ones, prune by the oracle, pool partial successes, carry findings across
attempts.**

But adopt the SEARCH only, not its oracle. DataMaster's validator is downstream
**benchmark performance — the very metric it optimizes**, which is gameable
(optimize-against-your-own-judge — the self-certification this ADR forbids).
Our pruning signal stays the **independent known-answer oracle**: search for
efficiency, independent oracle for honesty. A bonus our discipline buys:
DataMaster suffers DELAYED, noisy validation (you learn a data choice's value
only after downstream training); our oracles are immediate + deterministic, so
the search can prune far harder.

## Status note

Design only, no code — same discipline as ADR-013/014. This ADR exists so
"adaptive learning" has a defined, SAFE, buildable place in the architecture:
self-extension bounded by independent oracles, consistent with the through-
line — ADR-013 (don't trust the generator) → ADR-014 (judge coverage by
verifiability) → ADR-015 (judge a new operator's birth by the same ruler).
