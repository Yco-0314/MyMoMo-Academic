# Keller-Segel chemotaxis / aggregation (1970) — review

**tier: minimal** (all-REPRO 3/3, huge margins; no MISS). Reaction-diffusion (chemotaxis) CA.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (peak 869×, CV growth 2406×, low-q 5/5 vs 0/5) matches bundle/results.
- fair-control: **pass** — P1 (S=5, super-critical) vs P2 (S=0.3, sub-critical) is a clean single-knob A/B (only the dimensionless sensitivity S is dialled; χ derived from S).
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; L3 gate fingerprints FINDINGS+lock+spec.
- mechanism-aliveness: **pass (with a caught numerical trap)** — the chemotactic-collapse instability is alive AND physical: mass conserved (drift 3e-15), advective CFL 0.83 < 1. The builder caught + EXCLUDED a genuine numerical trap: at dt=2e-3 the super-critical run diverges to NaN (the KS finite-time singularity) — it used dt=5e-4 so the aggregation is real piling-up, not a blow-up.
- framing-disclosure: **pass** — two-field chemotaxis PDE on a grid (CA), disclosed.

## Verdict: SOUND. 3/3 REPRO.
P1 aggregation above threshold (S=5: peak ρ/ρ₀ 869×, CV growth 2406×); P2 uniform below threshold (S=0.3:
peak 1.0002×, CV shrinks to 0.008×); P3 long-wavelength instability sign check (low-q mode grows in 5/5
super-critical vs 0/5 sub-critical seeds). Keller & Segel's central claim — above a critical chemotactic
sensitivity a uniform lawn spontaneously collapses into dense peaks — reproduces, with a mass-conserving
upwind scheme that distinguishes physical aggregation from numerical blow-up. 18 tests. No tuning.

REVIEW COMPLETE
