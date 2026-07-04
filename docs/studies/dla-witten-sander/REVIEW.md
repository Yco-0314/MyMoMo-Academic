# DLA (Witten-Sander 1981) — adversarial review

**tier: deep** (trigger: 1 honest MISS + a corrected implementation bug). Reviewed vs the lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (mean D=1.660, outer-shell 0.098) matches bundle/results.
- fair-control: **n/a** — single-mechanism growth study; the compact-disk test (D≈2) is the negative control for the D estimator.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; the D band [1.55,1.90] was NOT tightened; P3 was NOT re-defined post-hoc to force a pass.
- mechanism-aliveness: **pass** — D=1.660 (canonical on-lattice value), clean power law (R²>0.99), density decreasing (screened interior).
- framing-disclosure: **pass** — on-lattice random-walk particles (agent-based), square-lattice anisotropy disclosed.

## Verdict: SOUND core reproduction (fractal D≈1.66); P3 is an honest metric-design MISS.
- **P1 REPRO** — mass dimension D=1.660 ∈ [1.55,1.90] — Witten-Sander's central kinetic-critical claim.
- **P2 REPRO** — fractal not compact (D≤1.85 + interior density decreasing).
- **P3 MISS** — tip-screening outer-shell fraction 0.098 vs 0.60. The MECHANISM is present (P2's decreasing
  density is its signature); the locked metric compares attachment radius to the FINAL R_max, which
  understates it (particles stick at the tip of the CURRENT, smaller cluster). Honest metric miss, not tuned.

## Bug caught + fixed (the strongest part of this review).
The off-lattice draft (from a builder that died on a process restart) had a genuine OVERLAP bug: tangent
placement relative to one touched particle left ~0.42-gap overlaps with others (its own no-overlap test
failed). Rewritten ON-LATTICE (lock-permitted), where non-overlap is structural — 8/8 tests pass and the
overlap that would have biased D upward is eliminated. D landed at the correct 1.66. No tuning.

REVIEW COMPLETE
