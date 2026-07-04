# Granovetter 1978 Threshold Model — FINDINGS

**Reproduction run 2026-06-29, AFTER predictions were locked** (see
`PREDICTIONS-locked.md`). Genuine agent-based model on the neutral platform
(`abm_auto._platform`): N=100 autonomous `ThresholdAgent`s, fully mixed, each reading
the GLOBAL active count; synchronous round to a fixed point; **NO RNG** (fully
deterministic). Model: `abm_auto/classics/granovetter_threshold.py`. Runner:
`examples/repro_granovetter_threshold/run.py`.

Source: Granovetter, M. (1978) "Threshold Models of Collective Behavior",
AJS 83(6):1420-1443.

## The two locked distributions (FIXED before the run, not tuned)

| Distribution | Threshold multiset | Sum | Mean |
|---|---|---|---|
| A — uniform | {0, 1, 2, ..., 99} (one each) | 4950 | 49.50 |
| B — perturbed | {0, 2, 2, 3, 4, ..., 99} (remove the lone thr-1 agent, add a second thr-2) | 4951 | 49.51 |

The perturbation moves exactly one agent (from threshold 1 to threshold 2), leaving a
gap at threshold 1. The mean rises by exactly 1/100 = 0.01 (delta ~ 0.02%).

## Equilibria + per-round cascade series (deterministic)

- **A (uniform): equilibrium = 100.** Active-count series `[0, 1, 2, 3, ..., 99, 100, 100]`
  -- one new actor per round (the next-higher threshold flips because the count just
  reached it), marching from the lone instigator to everyone in 100 rounds, then a
  terminal no-change round confirming the fixed point. 102 entries (t=0 baseline + 101
  rounds).
- **B (perturbed): equilibrium = 1.** Active-count series `[0, 1, 1]` -- the threshold-0
  instigator acts (count -> 1), but the next-lowest threshold is now 2 (the gap at 1),
  and with only 1 acting nobody else can ever join. The cascade dies at the instigator;
  the trailing `1` is the terminal no-change round.

Comparison: |mean_A - mean_B| = **0.01**; equilibrium ratio A/B = **100.0**.

## Verdicts (honest REPRO / MISS per locked clause)

| # | Clause | Result | Salient number |
|---|---|---|---|
| P1 | uniform equilibrium = 100 | **REPRO** | equilibrium = 100 (= 100) |
| P2 | perturbed equilibrium = 1 | **REPRO** | equilibrium = 1 (= 1) |
| P3 | \|mean_A - mean_B\| < 0.1 AND eq ratio ~ 100 | **REPRO** | mean_diff = 0.01 (< 0.1); ratio = 100.0 (~ 100) |

**3/3 locked clauses REPRO — but only 2 are independent emergent facts.** No clause was
falsified; nothing was tuned to hit 100/1. The exact uniform set and the exact
single-agent perturbation are the ones fixed in `PREDICTIONS-locked.md`. **Honest
evidential weight (adversarial review 2026-06-29):** the *independent* simulated results
are P1 (uniform → 100) and P2 (perturbed → 1). **P3 is a derived restatement, not
independent run-dependent evidence**: its mean sub-clause is hand-computable from the
pre-fixed multisets (the sums differ by exactly 1 → Δmean = 0.01, no simulation needed),
and its ratio sub-clause simply reuses the P1 and P2 equilibrium values (100/1). The
"~100× swing" is **N = 100 by construction** (uniform always cascades to N; the broken
case stalls at 1), not an emergent magnitude. So read this as **2 independent emergent
facts + 1 derived identity**, not three independent confirmations.

## The headline (stated plainly)

The two distributions have **nearly identical means** (49.50 vs 49.51, a 0.02%
difference) yet their equilibria differ by **~100x** (100 vs 1). Moving a single agent
from threshold 1 to threshold 2 -- a mean-invariant change -- collapses the riot from
"everyone joins" to "only the instigator acts." This is Granovetter's central claim:
**collective behavior is a property of the threshold DISTRIBUTION, not of the population
mean** (collective outcomes != the aggregation of individual preferences). The
sensitivity is to the *gap at threshold 1*, not to the average.

## Honest caveats

- **This is a faithful reproduction of a published synthetic model**, not real-world
  prediction. The 1978 fully-mixed formulation is reproduced; a network/spatial variant
  is explicitly out of scope.
- **Fragility is the point, and it cuts both ways.** P2's equilibrium = 1 is exquisitely
  sensitive to the exact perturbation: it depends entirely on creating an *unbridgeable
  gap* in the threshold sequence. A different single-agent move (e.g. removing thr-1 and
  adding the agent at an already-present value below the contiguous run) would leave the
  cascade unbroken and yield a very different equilibrium. The ~100x swing is a
  demonstration of distribution-sensitivity, not a robust law -- it is precisely as
  fragile as Granovetter says collective behavior is.
- **The result is deterministic (no RNG)**, so "reproducible" here means exact, not
  statistical. Determinism, monotonicity, order-independence (synchronous commit), and
  the global-count rule are pinned by `tests/classics/test_granovetter_threshold.py`.
- The P3 clause is a conjunction the model satisfies exactly (ratio = 100.0, not merely
  ~ 100), because the perturbed equilibrium is exactly 1 and the uniform exactly 100.
- **Bundle `code_commit` provenance:** `verdict-bundle.json`'s `code_commit` is HEAD at
  run-time (the bundle is committed together with the code, so it points to the parent
  commit, not the one carrying the bundle). Reproduction integrity is anchored on the
  content-addressed **sha256** of the docs/data artifacts (all `replay: strong`, all
  verified MATCH by the integrity gate), not on the commit pointer.
