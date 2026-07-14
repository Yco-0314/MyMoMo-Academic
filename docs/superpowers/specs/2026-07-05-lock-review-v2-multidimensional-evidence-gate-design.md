# Lock Review v2 Multidimensional Evidence Gate Design

**Status:** Ready for review.
**Date:** 2026-07-05
**Scope:** Upgrade the lock construct-validity gate from a three-label
classification into a multidimensional evidence profile while preserving the
anti-fabrication discipline from ADR-025.

## Summary

Lock Review v1 proved the missing invariant: a locked prediction must be reviewed
for construct validity before run results are interpreted. The v1 labels
`sound`, `uncertain`, and `mis_specified` are useful as a high-level rollup, but
they are too coarse for scientific narration.

This v2 design keeps the three-label rollup for registry counts, but moves the
real explanation into explicit dimensions:

- whether the metric operationalizes the paper claim;
- whether the metric direction is correct;
- whether the locked parameter/data regime fits the paper mechanism;
- whether the metric is robust to thresholds, noise, censoring, and sample size;
- whether the control or baseline isolates the mechanism;
- whether the finding is load-bearing for the model;
- whether a pass is emergent, generic, or trivial by construction;
- whether the clause discriminates the model from simple alternatives;
- whether the run actually executed the locked test.

The first dry-run against Wave-21 force-model results adds one architectural
distinction: **pre-run construct review** and **post-run realization review**
must be separate. A clause can be construct-sound while the run is underpowered,
right-sized, censored, or numerically limited. That case should not be collapsed
into either `lock_miss` or a clean theory-level `model_miss`.

The completed Helbing-Molnar run adds two more distinctions that v1 cannot
express: a clause can be **not run** because the required test geometry was out
of scope, and a clause can reproduce the qualitative relationship while missing
a fragile absolute endpoint. These must be first-class interpretations, not
after-the-fact prose exceptions.

The goal is not to make the gate more permissive. The goal is to make each PASS
or MISS carry a clearer scientific meaning.

## Problem With v1

The v1 rollup answers one question:

```text
Is this locked metric a sound proxy for the paper claim?
```

That is necessary but not sufficient. It conflates several different situations:

- a metric points in the wrong direction;
- a metric is plausible but locked to the wrong parameter regime;
- a pass is true but trivial because the allocator enforces the result by
  construction;
- a miss is a genuine model failure under a sound clause;
- a clause is a sanity check, not evidence of the model's distinctive mechanism.

In Wave-21, this made some results hard to read:

- White-Engelen P2 passed, but it was a weak finding because demand satisfaction
  was constructed into the allocator.
- Kirchner P1 missed, but the risk was identified prospectively as a regime
  mismatch.
- Kirchner P2 missed under a prospective `sound` review, so it must remain a
  model miss rather than being downgraded after the fact.

The v2 gate needs to preserve that discipline while making those distinctions
machine-readable.

## Goals

1. Keep ADR-025's anti-escape constraints:
   - bad locks do not become PASS;
   - original findings are not overwritten;
   - prospective reviews must not see results;
   - lock review must precede implementation/run interpretation.
2. Replace the single review label with a multidimensional clause profile.
3. Keep `construct_validity` as a derived registry rollup for compatibility.
4. Make PASS quality explicit, not only MISS classification.
5. Support scientific narration: "what does this clause actually prove?"
6. Keep the schema discrete and auditable; do not introduce free-form scoring.

## Non-Goals

- No numeric confidence scores in Phase 1.
- No automatic scientific truth certification.
- No retroactive rewriting of v1 findings.
- No change to the deterministic run gate semantics.
- No public projection until v2 has validator and bundle/report integration.

## v2 Schema Shape

The artifact remains:

```text
LOCK-REVIEW.json
```

The schema becomes:

```text
abm-auto/lock-review/v2
```

Each clause item carries a pre-run `construct_dimensions` object. Example:

```json
{
  "clause_id": "P2",
  "paper_claim": "Demand constraints are satisfied by the land-use allocator.",
  "locked_metric": "max relative class-demand residual <= 0.01",
  "validity": "uncertain",
  "construct_dimensions": {
    "operationalization": "direct",
    "directionality": "correct",
    "regime_fit": "in_regime",
    "metric_robustness": "robust",
    "control_quality": "weak_control",
    "mechanism_specificity": "trivial_by_construction",
    "load_bearing_role": "sanity_check",
    "emergence_level": "accounting_identity",
    "counterfactual_discrimination": "non_discriminating"
  },
  "issue_kinds": ["weak_control"],
  "requires_relock": false,
  "review_rationale": "The metric directly checks demand satisfaction, but the allocator enforces this accounting constraint by construction, so a PASS is weak evidence for the spatial mechanism."
}
```

## Dimensions

### operationalization

Does the locked metric measure the paper claim?

Allowed values:

- `direct`
- `proxy`
- `wrong_proxy`
- `ambiguous`

### directionality

Is the pass/fail inequality or trend direction correct?

Allowed values:

- `correct`
- `reversed`
- `ambiguous`
- `not_directional`

### regime_fit

Does the locked parameter/data regime match the paper mechanism's expected
operating regime?

Allowed values:

- `in_regime`
- `risky_regime`
- `extrapolated`
- `wrong_regime`
- `unknown`

### metric_robustness

Is the metric stable under reasonable sampling, thresholds, censoring, and
measurement noise?

Allowed values:

- `robust`
- `threshold_fragile`
- `noise_sensitive`
- `censored`
- `sample_size_sensitive`
- `unknown`

### control_quality

Does the baseline/control isolate the mechanism?

Allowed values:

- `causal_control`
- `weak_control`
- `confounded`
- `no_control_needed`
- `unknown`

### mechanism_specificity

Does the finding identify the model's distinctive mechanism, or could a simpler
model produce it?

Allowed values:

- `distinctive`
- `generic`
- `trivial_by_construction`
- `unknown`

### load_bearing_role

How important is this clause for the paper's core mechanism?

Allowed values:

- `core`
- `supporting`
- `sanity_check`

### emergence_level

Is the finding emergent from the mechanism, directly implied by parameters, or
an accounting identity?

Allowed values:

- `emergent`
- `parameter_implied`
- `accounting_identity`
- `diagnostic_only`
- `unknown`

### counterfactual_discrimination

Would this clause distinguish the claimed model from simple alternatives?

Allowed values:

- `discriminating`
- `weakly_discriminating`
- `non_discriminating`
- `unknown`

## Derived Rollups

The v2 validator derives the v1-compatible `validity` rollup, but authors may
also provide it explicitly. If explicit and derived values disagree, validation
fails.

Suggested derivation:

```text
mis_specified if:
  operationalization == wrong_proxy
  or directionality == reversed
  or regime_fit == wrong_regime
  or control_quality == confounded

uncertain if:
  any dimension is ambiguous, unknown, threshold_fragile, noise_sensitive,
  censored, sample_size_sensitive, weak_control, risky_regime, extrapolated,
  generic, trivial_by_construction, parameter_implied,
  accounting_identity, diagnostic_only, weakly_discriminating,
  non_discriminating

sound otherwise
```

This is intentionally conservative. A clause can be direct and directionally
correct but still `uncertain` if it is trivial by construction or
non-discriminating.

## Verdict Interpretation

Run verdicts still have:

```text
passed: true | false
```

v2 adds interpretation fields to the bundle output, derived from verdict,
pre-run construct dimensions, and optional post-run realization dimensions:

```text
evidence_strength: strong | moderate | weak
failure_kind: none | model_miss | lock_miss | uncertain_lock | implementation_miss | scale_regime_miss | threshold_endpoint_miss | censored | not_run
finding_role: core | supporting | sanity_check
```

Rules:

- `passed=true` with `trivial_by_construction`, `accounting_identity`, or
  `non_discriminating` becomes weak evidence, not a strong reproduction claim.
- `passed=false` with derived `sound` becomes `model_miss`.
- `passed=false` with derived `mis_specified` becomes `lock_miss`.
- `passed=false` with derived `uncertain` becomes `uncertain_lock`.
- `passed=false` with derived `sound` plus underpowered scale, missing
  load-bearing mechanism terms, unstable numerics, or disclosed right-sizing
  becomes `implementation_miss` or `scale_regime_miss`, not a clean
  theory-level `model_miss`.
- `passed=false` with `test_execution_status=not_run` becomes `not_run`, not
  `model_miss`.
- `passed=false` with qualitative core present, stable numerics, and only a
  fragile absolute endpoint missed may become `threshold_endpoint_miss`.
- `passed=true` with derived `mis_specified` remains invalid, as in v1.
- `passed=true` with derived `uncertain` is allowed, but the evidence strength
  must not be `strong`.

## Post-Run Realization Dimensions

These dimensions are not part of the prospective lock review. They are added
after execution, in the verdict bundle or a v2 interpretation addendum, to
describe whether the implementation/run faithfully realized the locked test.

### test_execution_status

Was the locked clause actually executed?

Allowed values:

- `executed`
- `partial_run`
- `not_run`
- `failed_to_run`
- `unknown`

### scale_fidelity

Was the run executed at the locked or scientifically required scale?

Allowed values:

- `faithful_scale`
- `right_sized_proxy`
- `underpowered`
- `not_scale_sensitive`
- `unknown`

### mechanism_fidelity

Were the mechanism terms needed for the paper claim implemented?

Allowed values:

- `complete`
- `approximate`
- `missing_load_bearing_terms`
- `unknown`

### numerical_fidelity

Were the numerical method and time step stable enough for the claim?

Allowed values:

- `stable`
- `integration_limited`
- `unstable`
- `unknown`

### censoring_status

Did caps, early stopping, or non-completion affect the measured number?

Allowed values:

- `uncensored`
- `right_censored`
- `left_censored`
- `cap_hit`
- `unknown`

### qualitative_core_status

Did the qualitative mechanism appear even if the quantitative locked bar
missed?

Allowed values:

- `qualitative_core_present`
- `qualitative_core_absent`
- `not_applicable`
- `unknown`

## Examples

### White-Engelen P2

```text
passed: true
validity: uncertain
operationalization: direct
directionality: correct
regime_fit: in_regime
metric_robustness: robust
control_quality: weak_control
mechanism_specificity: trivial_by_construction
load_bearing_role: sanity_check
emergence_level: accounting_identity
counterfactual_discrimination: non_discriminating
evidence_strength: weak
failure_kind: none
```

Meaning: the clause passes, but it is not strong evidence for the land-use
mechanism's distinctive spatial behavior.

### Kirchner P1

```text
passed: false
validity: uncertain
operationalization: proxy
directionality: correct
regime_fit: risky_regime
metric_robustness: robust
control_quality: causal_control
mechanism_specificity: distinctive
load_bearing_role: supporting
emergence_level: emergent
counterfactual_discrimination: discriminating
evidence_strength: weak
failure_kind: uncertain_lock
```

Meaning: the miss was prospectively flagged as a regime-risk clause. It should
not be read as the same kind of failure as a sound core miss.

### Kirchner P2

```text
passed: false
validity: sound
operationalization: direct
directionality: correct
regime_fit: in_regime
metric_robustness: robust
control_quality: causal_control
mechanism_specificity: distinctive
load_bearing_role: core
emergence_level: emergent
counterfactual_discrimination: discriminating
evidence_strength: strong
failure_kind: model_miss
```

Meaning: this is a genuine model miss under the locked regime. The system must
not downgrade it after seeing the result.

### Helbing-Molnar P2

```text
passed: false
validity: sound
operationalization: direct
directionality: correct
regime_fit: in_regime
metric_robustness: sample_size_sensitive
control_quality: causal_control
mechanism_specificity: distinctive
load_bearing_role: core
emergence_level: emergent
counterfactual_discrimination: discriminating
test_execution_status: not_run
mechanism_fidelity: missing_load_bearing_terms
evidence_strength: weak
failure_kind: not_run
```

Meaning: the locked doorway-alternation test was not executed because the
two-chamber doorway geometry was not part of the run. It is a coverage gap, not
evidence that the social-force model failed doorway alternation.

### Helbing-Molnar P3

```text
passed: false
validity: uncertain
operationalization: direct
directionality: correct
regime_fit: in_regime
metric_robustness: threshold_fragile
control_quality: no_control_needed
mechanism_specificity: generic
load_bearing_role: supporting
emergence_level: emergent
counterfactual_discrimination: weakly_discriminating
test_execution_status: executed
scale_fidelity: right_sized_proxy
mechanism_fidelity: complete
numerical_fidelity: stable
censoring_status: uncensored
qualitative_core_status: qualitative_core_present
evidence_strength: moderate
failure_kind: threshold_endpoint_miss
```

Meaning: the fundamental diagram's shape is reproduced, but the high-density
absolute endpoint misses. This is not a PASS, but it also should not be narrated
as absence of the qualitative crowd-speed relation.

## Architecture

### Module

Keep the existing seam:

```text
abm_auto/lock_review.py
```

Add v2 support without deleting v1:

```python
validate_lock_review(review, expected_clause_ids=None) -> dict
derive_construct_validity(dimensions: dict) -> str
derive_evidence_interpretation(
    verdict: dict,
    review_item: dict,
    realization: dict | None = None,
) -> dict
```

The module remains a review-artifact validator, not a model-run gate.

### Bundle Integration

`abm_auto/repro_bundle.py` should:

- accept either v1 or v2 lock review artifacts;
- require v2 `construct_dimensions` when schema is v2;
- reject explicit `validity` when it disagrees with the derived rollup;
- attach derived `evidence_strength`, `failure_kind`, and `finding_role` to
  bundle validation output;
- classify non-sound failed clauses as `miss_lock` or `uncertain_lock` only
  when the lock review is prospective and `lock_provenance` git ancestry proves
  `lock_commit <= lock_review_commit <= implementation_commit <=
  first_run_commit`;
- count failed non-sound clauses with retrospective, missing, or unverifiable
  provenance as `unclassified_miss_count`;
- keep old bundles valid.

### Study Corpus Integration

`abm_auto/study_corpus.py` should add optional v2 counts only when a bundle has a
valid lock review:

```text
weak_pass_count
strong_pass_count
miss_model_count
miss_lock_count
uncertain_lock_count
unclassified_miss_count
trivial_pass_count
core_clause_count
```

Existing `miss_lock_count`, `miss_model_count`, and `uncertain_lock_count`
remain for compatibility; `unclassified_miss_count` records failed clauses whose
non-sound lock interpretation is not provenance-admissible.

## Validation Rules

1. All construct dimension keys are required in v2.
2. All dimension values must be from fixed enums.
3. `validity` must equal the derived rollup.
4. `mis_specified` clauses require at least one hard issue:
   - `wrong_proxy`
   - `reversed`
   - `wrong_regime`
   - `confounded`
5. `requires_relock=true` is required for `mis_specified`.
6. Prospective reviews still require `result_visibility=no_results_seen`.
7. Clause ids must cover verdict gate ids.
8. A passed mis-specified clause is invalid.
9. A passed uncertain clause cannot claim `evidence_strength=strong`.
10. A `trivial_by_construction` or `accounting_identity` clause cannot be
    load-bearing `core` unless the rationale explicitly says the paper's core
    claim is itself an accounting identity.
11. A sound construct miss with `scale_fidelity=underpowered` must not be
    counted as a clean theory-level model miss without also reporting the scale
    limitation.
12. A `not_run` clause must have `test_execution_status=not_run` or
    `failed_to_run`, and must not count as `model_miss`.
13. A `threshold_endpoint_miss` requires `qualitative_core_status` to be
    `qualitative_core_present` and the missed bar to be documented as an
    absolute endpoint or fragile threshold.
14. `MISS-lock` and `uncertain-lock` counts require prospective review timing
    plus verified git ancestry for the lock-review provenance chain. Otherwise
    the original failed verdict remains an unclassified MISS.

## Test Plan

Add v2 coverage in:

```text
tests/test_lock_review.py
tests/test_repro_bundle_lock_review.py
tests/test_repro_bundle_lock_provenance.py
tests/test_study_corpus.py
```

Required tests:

- valid v2 lock review validates;
- missing dimension fails;
- invalid dimension enum fails;
- explicit validity disagreeing with derived validity fails;
- mis-specified clause without a hard issue fails;
- prospective review with results visible fails;
- passed mis-specified verdict fails;
- passed uncertain verdict validates but derives weak or moderate evidence;
- White-Engelen P2 fixture derives weak pass/trivial finding;
- Kirchner P1 fixture derives uncertain lock miss;
- Kirchner P2 fixture derives model miss;
- Helbing escape-panic fixture derives `scale_regime_miss` where the
  qualitative faster-is-slower core appears but quantitative bars miss under
  underpowered N=80;
- Helbing-Molnar P2 fixture derives `not_run`;
- Helbing-Molnar P3 fixture derives `threshold_endpoint_miss`;
- v1 lock reviews still validate;
- legacy bundles without lock review keep old registry shape.

## Rollout

### Phase 1: Spec-only dry run

Manually encode v2 profiles for White-Engelen, Kirchner, and both Helbing
force-model cases without changing their v1 bundles. Confirm the dimensions
explain the scientific narrative better than the three-label rollup, especially
for weak passes, prospectively risky misses, underpowered physical
realizations, not-run clauses, and threshold endpoint misses.

### Phase 2: Validator support

Add v2 schema validation and derivation helpers while keeping v1 support.

### Phase 3: Bundle/report integration

Attach derived evidence interpretation to bundle validation and corpus registry
counts.

### Phase 4: Wave-21 re-report

Do not rewrite old verdicts. Add a separate v2 interpretation addendum for
Wave-21 now that the Helbing force-model runs are complete.

### Phase 5: Public projection

Only after the v2 schema has validator and bundle/report support, project the
stabilized infrastructure to public v3/v4.

## Scientific Boundary

This gate improves finding interpretation. It does not prove the model is true,
and it does not make an uncertain lock into a pass. It is a structured way to say
what a finding means:

```text
PASS/MISS
plus
what construct was measured
plus
how distinctive the evidence is
plus
whether the failure belongs to the model, the lock, the regime, or censoring
```

The intended public narrative is:

```text
MyMoMo does not only report reproduction rates. It audits the scientific meaning
of each finding.
```
