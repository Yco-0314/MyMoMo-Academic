# ADR-013: The `Gate` seam — unifying validators into the research harness

**Status**: Accepted (design; grilled 2026-06-02 via improve-codebase-architecture). No code yet — this records the interface decisions so implementation and future reviews share one shape.
**Date**: 2026-06-02
**Deciders**: yco + Claude (Opus 4.8)
**Related**: [ADR-012](ADR-012-method-transfer-engine.md) (anti-fabrication: verification must be structural, independent of the generator), [ADR-011](ADR-011-six-wedge-benchmark-thesis.md) (wedges + benchmark gates), [terminology.md](../context/terminology.md#research-harness-gate-vocabulary)

---

## Context

abm-auto has accumulated scattered validators, each with a different
return type and a different "pass" convention:

| Validator | Returns | "pass" = | polarity |
|---|---|---|---|
| `codegen/anti_patterns.scan` | `list[str]` | empty | hits = bad |
| `verification/execution_verifier.verify_execution` | `VerificationResult` | `.is_valid` | mismatch = bad |
| `analysis/method_transfer_guard.test_against_null` | `GuardResult` | `.significant` | significant = **good** |
| `calibration/posterior.maybe_halt_on_diagnostics` | `tuple[bool,str]` | `False` | True = **halt/bad** |
| `pipeline/phases/codegen` structural_fidelity closure | `list[str]` | empty | issues = bad |

Five validators, five "pass" shapes, **inconsistent polarity**. Any
caller composing them must memorize each one's quirk. The GVR loop, the
diagnostics-HALT, and the (planned) method-transfer harness each
re-implement their own pass/fail glue. The complexity is already smeared
across callers — the **deletion test** says concentrating it into one
seam is a real deepening, not a pass-through.

This matters most because of ADR-012's lesson (the author fabricated
"validated" results twice): **trust must move to a small, auditable core
of deterministic checks + unforgeable artifacts.** A unified `Gate` seam
*is* that core, if designed so a generator cannot self-certify.

## Decision

Introduce one deep seam, `Gate`, that every validator satisfies. Shape
(Protocol, generic over the intermediate-state family it consumes):

```python
class Gate(Protocol[T]):
    family: str                                   # intermediate-state family it consumes
    self_test_paradigm: str                       # human-audited verification pattern it binds to
    tier: Literal["verification", "refutation"]   # DERIVED from paradigm, never hand-written
    def judge(self, x: T) -> Verdict: ...          # deterministic — no LLM inside
    def self_test(self) -> bool: ...               # runs the paradigm's synthetic ground truth

@dataclass
class Verdict:
    passed: bool
    tier: str
    evidence: object                               # Gate-specific blob; harness does not interpret
    salient_number: tuple[float, float] | None = None   # (score, threshold), optional
```

Three grilled sub-decisions:

### D1 — Input: generic `Gate[T]` + dynamic family routing (chose 1B, not 1A)

Validators consume genuinely different inputs (source dict, trajectory
array, sim CSV, workspace path). Unification happens on the **output**
(Verdict), not the input.

- **Rejected 1A — single `Artifact` envelope** (`judge(artifact)` where
  the artifact carries every possible accessor). Reason it's load-bearing
  to reject: the envelope's interface grows linearly with Gate variety
  (add Ricci → `.interaction_graph()`, add TDA → `.point_cloud()`),
  becoming a shallow god-object; and Gate↔artifact compatibility becomes
  a runtime `KeyError` instead of a wiring-time fact — the exact
  "thought it was there, it wasn't" failure mode this project keeps
  hitting.
- **Chosen 1B** — each Gate declares its type; the harness holds a
  routing table keyed by **intermediate-state family** (a finite set:
  source code / scalar trajectory / interaction graph / point cloud /
  workspace-signal), not one entry per Gate. Families are *discovered* at
  runtime; **new family *types* are not generated** (see D-dynamic).
- 1B's cost, recorded honestly: routing complexity moves into the harness,
  and the type protection leans on mypy strictness (W3). If routing
  degrades into `if has_csv: feed NullGate`, it has just relocated 1A's
  runtime coupling — so the routing table must be organized by family,
  reviewed as its own object.

### D2 — Output: thin Verdict + optional `salient_number` (chose 2C)

- **Rejected 2A** (bool-only Verdict): collapses `test_against_null`'s
  p=0.144 to `passed=False`, discarding margin — and margin was the most
  informative thing in the Demo-1 negative (p_phase ≥ 0.14 across all
  configs says far more than "didn't pass").
- **Chosen 2C** — `Verdict` carries `passed + tier + evidence-blob`; the
  harness reads only `passed + tier` for flow control (stays thin/deep);
  the Gate-specific evidence sinks into a blob the harness does not
  interpret. A **optional `salient_number = (score, threshold)`** lets
  Gates that have a continuous quantity (null p, calibration MSE,
  curvature) surface it to provenance + rendering without forcing Gates
  that don't (anti_patterns) to fake one.
- Consequence accepted: the harness deliberately does **not** make
  margin-based flow decisions (e.g. "p near threshold → resample"). If we
  later want that, it requires retreating toward 2B (harness reads score).
  Logged as a known limitation, not an oversight.

### D3 — tier derived from self-test paradigm (chose 3C)

- **Rejected 3A** (tier = static author label): nothing stops a Gate
  author tagging a refutation-only check as `verification` — label
  decoupled from what the check can actually prove. That is precisely the
  laundering of ADR-012 (the author crowning their own output "validated").
- **Rejected 3B** (tier returned by `judge` at runtime): makes tier a
  generation-time self-assessment — the red line again.
- **Chosen 3C** — tier is a **function of the self-test paradigm** the
  Gate binds to. Bind to a completeness-proving paradigm (byte-equal
  invariance; exhaustive known-bad detection) → `verification`. Bind to a
  rejection-only paradigm (synthetic signal-vs-noise; degree-preserving
  rewire null) → `refutation`. Tier becomes a *consequence*, not a
  *claim*.

### D-LLM — deterministic `judge` forces ε to split (consequence of 3C)

3C requires `judge` to be self-testable, hence deterministic, hence
**no LLM inside judge**. `verify_execution` currently calls an LLM to
extract qualitative claims. Therefore ε splits:
- claim extraction (LLM) → a **generator**, not a Gate;
- `diff_claims_vs_actuals` (already deterministic) → the actual Gate
  (`refutation` tier).

This is the harness's generate/judge separation reproduced in miniature:
the LLM generates claims; deterministic code judges them.

### D-dynamic — families/judges may be generated; self-tests may NOT

Discussed and explicitly bounded. A generated Gate (new representation +
new judge for an unseen method×domain) is allowed and is the source of
the harness's flexibility. But its **self-test cannot be generated** —
that would let the generator write its own always-pass exam (ADR-012 red
line via the back door). A generated Gate must *bind to an existing
human-audited self-test paradigm* to earn a verification/refutation tier;
if it cannot, its Verdict is tagged `unverified` and may never claim
verification. The paradigm library is finite and human-audited.

## Consequences

### Positive
- One seam consumed by GVR, diagnostics-HALT, and the method-transfer
  harness; a new method×domain adds a `Gate` (or reuses one), not new glue.
- **Locality**: "what a check means + what it proves" lives in one type.
- **The interface is the test surface**: every Gate ships a `self_test`
  on synthetic ground truth (generalizing the CSD guard's
  rising-AR1→p≈0.01 / white-noise→p≈1.0).
- tier makes the verification/refutation honesty boundary structural, not
  a writing convention an author (or LLM) can violate.
- Sets up the provenance credential (next candidate, C3): a Verdict stream
  with tiers + salient numbers + artifact hashes is replayable by a third
  party; a fabricated claim points to no artifact and is structurally
  visible.

### Negative / costs
- Routing complexity moves into the harness; the routing table must itself
  be kept deep (organized by family) or it relocates 1A's coupling.
- Real protection depends on mypy strictness (W3 wedge) actually landing.
- Harness cannot do margin-based flow control under 2C (accepted).
- The self-test paradigm library is finite: a genuinely novel method whose
  validity needs a new paradigm (e.g. GeomHerd's CSAD mean-field bridge,
  validated by mathematics not synthetic data) will be tagged `unverified`
  rather than auto-certified. This is the harness's honest ceiling — it
  rejects/flags rather than fakes, and cannot manufacture new verification
  paradigms (that needs a human/theory).

### Neutral
- No code in this ADR. Implementation will refactor the five validators
  behind `Gate` incrementally; each must keep its current behavior
  (byte-equal/test-equal) while gaining the uniform Verdict + a self_test.

## Open questions
- **OQ1**: exact family taxonomy — is "workspace-signal" one family or
  several? Settle when the 2nd graph-consuming Gate (Ricci) lands and
  forces the interaction-graph family to exist.
- **OQ2**: where does the routing table live — harness config, or each
  Gate self-registering to a family? Self-registration keeps Gates
  autonomous but makes the full routing set non-local.
- **OQ3**: does `evidence` need any minimal common shape for the renderer,
  or is `salient_number` + a `summary() -> str` enough? Defer to first
  provenance implementation (C3).
