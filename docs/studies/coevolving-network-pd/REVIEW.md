# Coevolving-network PD (Santos-Pacheco-Lenaerts 2006) — adversarial review

**tier: deep** (trigger: 2 honest MISSes). Reviewed vs the verified claim + lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (W=0→0.000, W=16→0.630) matches bundle/results.
- fair-control: **pass** — W=0 (static) vs W>0 (adaptive) differ ONLY in the rewiring rate; degree/edge-count conserved throughout.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; L3 gate ok; edge/degree conservation + defectors-never-initiate verified in tests.
- mechanism-aliveness: **pass** — the coevolution mechanism is vividly alive: cooperation is RESCUED from 0.000 (static) to 0.630 (W=16), monotone and threshold-gated in W.
- framing-disclosure: **pass** — network-generation + adaptive rewiring, disclosed.

## Verdict: model FAITHFUL; P2 + P3 are HONEST MISSes from a lock UNDER-SPECIFICATION (not a bug).
- **P1 REPRO** — static graph (W=0) collapses to all-D (coop 0.000 < 0.05). Decisive; 20/20 seeds.
- **P2 MISS** — W=16 cooperation 0.630 < the locked 0.80 (though the ENHANCEMENT sub-clause 0.630 > 0.6 passes).
- **P3 MISS** — the jump (0.630 > 0.5) ✓ and coop(W=0.5)=0.000 < 0.2 ✓, but coop(W=16)=0.630 is not > 0.7.
  **Cause (honest, disclosed):** the lock fixes rewiring to a RANDOM NEW NODE, whereas Santos-Pacheco-Lenaerts'
  ASSORTATIVE rule (rewire toward the imitated winner's neighbourhood) builds stronger cooperator clusters and
  a higher ceiling (>0.8). Reaching >0.8 would require changing the locked rewiring TARGET — which no-tuning
  forbids. The coevolution EFFECT (large, monotone, threshold-gated rescue) reproduces; only the absolute
  ceiling, which depends on the specific rewiring rule the lock under-specified, misses.

## Discipline check: PASS. Recurring lock-under-specification lesson.
1/3 REPRO reported honestly; no tuning (the builder identified that the assortative rule would reach the ceiling
but left the locked random-node rule intact). The qualitative coevolution result is REPRO; the quantitative
ceiling is sensitive to the rewiring rule the lock did not pin precisely — the same class of pre-lock
gate-design gap seen in Deffuant-Amblard's regime boundaries. 19 tests.

REVIEW COMPLETE
