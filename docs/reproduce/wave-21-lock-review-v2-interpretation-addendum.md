# Wave-21 Lock Review v2 Interpretation Addendum

**Date:** 2026-07-05
**Status:** Additive interpretation addendum. This file does not rewrite any
locked prediction, verdict bundle, findings document, or original PASS/MISS
grade.

## Boundary

This addendum applies the Lock Review v2 interpretation vocabulary to Wave-21
P0 after the force-model runs completed.

It is not a rerun, not a re-lock, and not a scoring upgrade. It is a
reader-facing explanation layer over already committed findings:

```text
original verdict
plus construct meaning
plus realization status
plus what the finding is actually evidence for
```

The distinction matters because Wave-21 exposed several cases that a single
PASS/MISS or `sound | uncertain | mis_specified` label compresses too much:

- a PASS can be weak because it is an accounting identity;
- a MISS can be a prospectively known regime-risk clause;
- a MISS can be a quantitative scale/realization miss even when the qualitative
  mechanism appears;
- a clause can be not run, which is a coverage gap rather than tested model
  failure;
- a relation can reproduce in shape while missing a fragile endpoint.

## Scope

Wave-21 P0 has seven completed studies.

Four studies have prospective lock reviews and therefore enter the v2
interpretation layer:

- `white-engelen-constrained-landuse`
- `kirchner-schadschneider-bionics-ca`
- `helbing-farkas-vicsek-escape-panic`
- `helbing-molnar-social-force`

Three earlier studies predate the prospective construct-validity gate:

- `wilson-entropy-gravity`
- `radiation-model-mobility`
- `clarke-sleuth-urban-growth`

Those three remain useful diagnostics, but they are not counted as prospective
v2 evidence because their lock-quality judgment was made after or alongside the
run. This is intentional: v2 should not create a new retrospective escape hatch.

## Prospective v2 Summary

The prospective v2 set contains 12 clauses: 3 passes and 9 misses under the
original locked verdicts. v2 does not change those verdicts. It changes the
meaning attached to them.

| Interpretation | Count | Meaning |
|---|---:|---|
| weak pass | 1 | PASS is true but weak evidence for the distinctive mechanism. |
| moderate pass | 1 | PASS is real but partly generic, proxied, or censored. |
| strong pass | 1 | PASS is discriminating, core or clearly mechanism-specific. |
| uncertain lock miss | 2 | MISS was tied to a prospectively identified regime/proxy/threshold risk. |
| model miss | 1 | MISS under a sound core clause; do not downgrade after seeing the result. |
| scale/regime miss | 4 | Qualitative mechanism or implementation exists, but the run scale/regime does not realize the quantitative bar. |
| threshold endpoint miss | 1 | Qualitative relation appears, but a fragile absolute endpoint misses. |
| not run | 1 | Clause was not executed; report as coverage gap, not tested failure. |

## Clause Table

| Study | Clause | Original verdict | v2 evidence strength | v2 failure kind | Interpretation |
|---|---|---:|---|---|---|
| White-Engelen | P1 type-distinct fractal morphology | MISS | moderate | uncertain_lock | Morphology is present, but the locked between-type gap is threshold-fragile. |
| White-Engelen | P2 demand constraint satisfaction | PASS | weak | none | Demand is satisfied by construction; useful sanity check, weak mechanism evidence. |
| White-Engelen | P3 interaction sign controls segregation | PASS | strong | none | Single-variable counterfactual isolates the spatial interaction mechanism. |
| Kirchner-Schadschneider | P1 interior herding optimum at `k_S=4.0` | MISS | weak | uncertain_lock | The clause targets a risky visibility regime identified before the run. |
| Kirchner-Schadschneider | P2 herding helps more when visibility is poor | MISS | strong | model_miss | Sound core clause missed; this remains a real model miss. |
| Kirchner-Schadschneider | P3 bottleneck saturation and over-herding jam | PASS | moderate | none | Over-herding jam appears, but censoring and generic single-exit saturation weaken the evidence. |
| Helbing-Farkas-Vicsek | P1 faster-is-slower interior minimum | MISS | moderate | scale_regime_miss | Faster-is-slower qualitative time signature appears, but N=80 shifts the quantitative optimum. |
| Helbing-Farkas-Vicsek | P2 bursty exit gaps at high desired speed | MISS | weak | scale_regime_miss | High-speed burstiness appears, but low-speed queuing does not settle at the locked crowd scale. |
| Helbing-Farkas-Vicsek | P3 exit-zone density builds with desired speed | MISS | weak | scale_regime_miss | The right-sized run does not reach the compression needed for the locked density bar. |
| Helbing-Molnar | P1 lane formation | MISS | moderate | scale_regime_miss | Lane ordering is present but weak; corridor/scale/calibration do not realize stable stripes. |
| Helbing-Molnar | P2 doorway alternation | MISS | weak | not_run | Two-chamber doorway geometry was not executed; this is coverage, not tested failure. |
| Helbing-Molnar | P3 fundamental diagram | MISS | moderate | threshold_endpoint_miss | Speed falls monotonically with density, but the high-density endpoint misses by 0.06. |

## Historical Diagnostics, Not Prospective v2 Evidence

The first three Wave-21 studies are still scientifically useful because they
show why v2 was needed. They should be narrated as retrospective diagnostics,
not prospective lock-review evidence.

| Study | Original result | Diagnostic lesson |
|---|---:|---|
| Wilson entropy gravity | 2/3 REPRO | P3 lock compares against the wrong entropy reference set. The Wilson mechanism is reproduced, but the locked entropy inequality is backwards. |
| Radiation mobility | 1/3 REPRO | P1 is depressed by small-count log noise; P2 uses a uniform-square geometry for an empirical-cluster exponent. The radiation law itself is verified by linear and well-sampled checks. |
| Clarke SLEUTH urban growth | 1/3 REPRO | P1 is clean; P2 mixes a real self-modification effect with a capped coefficient proxy; P3's Moran sub-clause is directionally suspect for road-linear growth. |

These diagnostics are exactly why future waves should use v2 prospectively:
construct validity must be reviewed before run interpretation, not repaired
after a clause misses.

## Scientific Narrative

The public narrative should not be that v2 improves the original scores.

```text
Wave-21 has better reproduction outcomes after v2.
```

The correct narrative is:

```text
Wave-21 keeps the original PASS/MISS discipline, but adds a second layer that
audits what each finding is evidence for.
```

That is the architectural improvement:

- weak passes remain weak;
- sound model misses remain model misses;
- lock-risk misses are not over-read;
- physical scale limitations are not mistaken for theory failure;
- not-run clauses are disclosed as coverage gaps;
- qualitative mechanism recovery is not rounded into quantitative PASS.

## Next Step

Phase 5 should project this stabilized interpretation layer into the public
v3/v4 split only after the intended public history is chosen. The safe route is
to publish the infrastructure and addendum first, then decide whether any Wave-21
re-locks deserve a separate future branch. Re-locking should remain prospective:
new locks first, then new runs.
