# Evolution of Fairness in the Ultimatum Game — review

**tier: light** (all-REPRO 3/3, but P1's p̄ is a near-threshold continuous pass — margin ~5%).
Genuine agent-based. Reviewed vs the verified claim + lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (q̄: 0.064/0.142/0.470/0.967; contrast 0.903) matches bundle/results.
- fair-control: **pass** — reputation weight w is the SOLE treatment knob; P3 isolates it across {0,0.2,0.5,1.0}.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; L3 integrity gate ok (FINDINGS fingerprinted).
- mechanism-aliveness: **pass** — the reputation mechanism is decisively alive: q̄ climbs monotonically 0.064→0.967 as w rises; the contrast 0.903 is far from the 0.20 bar.
- framing-disclosure: **pass** — genuine (p,q)-genotype PlayerAgents with fitness-proportional replication, disclosed.

## Light-tier check: the thin margin is honest, not tuned.
P1's p̄=0.190 clears its <0.20 bar by only 0.01. This is a MEASURED value (reported as-is, not tuned) and
the P1 verdict does not hinge on it alone: the load-bearing P1 quantity is q̄=0.064 (bar <0.15, comfortable),
and the whole-treatment signal (q̄ contrast 0.903 across w) is unambiguous. The thin p̄ margin is seed-noise
near the rational-collapse floor, not a biased pass.

## Verdict: SOUND. 3/3 REPRO.
Without reputation (w=0) evolution collapses to the rational near-0 offer (q̄=0.064, p̄=0.190); with
reputation (w=1) fair offers evolve (q̄=0.967, p̄=0.570); q̄ is monotone in w (contrast 0.903). Distinctness:
a (p,q)-genotype responder-rejection game where REPUTATION about acceptance thresholds drives fairness — a
channel the built public_goods model has no representation of. 18 tests. No tuning.

REVIEW COMPLETE
