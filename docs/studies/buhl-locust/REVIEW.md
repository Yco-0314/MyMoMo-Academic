# Buhl et al. marching locusts (2006) — review

**tier: minimal+ (adversarially verified)** — 3/3 REPRO. genuine-agent, 1D SPP (disclosed).

## Cheap checks
- numeric-provenance: **pass** — bundle (density crossover 0.642, 4 reversals near-critical, monotone tol 0.08) matches results.
- fair-control: **pass** — DENSITY is the single swept control on one 1D alignment rule.
- no-post-lock-drift: **pass** — graded vs lock ed6fe16 BEFORE run; L3 gate fingerprints FINDINGS+lock+spec.
- mechanism-aliveness: **pass** — verifier confirmed the density-driven order/disorder crossover (|<v>|<0.3 low, >0.7 high) AND the near-critical intermittent direction reversals (the empirical locust signature), with |<v>| monotone in density. 18 tests pass.
- framing-disclosure: **pass** — 1D ring self-propelled particles (Czirok variant), disclosed.

## Verdict: SOUND. 3/3 REPRO.
P1 density-driven marching onset; P2 spontaneous global-direction reversals near threshold; P3 monotone ordering.
The 1D density-controlled transition + intermittent switching (distinct from Vicsek's noise transition) reproduce. 18 tests. No tuning.
REVIEW COMPLETE (minimal+)
