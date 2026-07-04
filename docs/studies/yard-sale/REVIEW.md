# Yard-Sale wealth exchange — adversarial review

**tier: deep** (trigger: 1 honest MISS). Reviewed vs the verified claim + lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (Gini 0.9929, top-1 0.274, bottom-50% 3.6e-46) matches bundle/results.
- fair-control: **pass** — P3's contrast is vs the DY exponential fixed point (Gini 0.5); total wealth conserved (verified in tests on both agent + numpy paths).
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; the sweep budget was NOT extended to force P2 (discipline held); L3 gate ok.
- mechanism-aliveness: **pass** — condensation is vividly alive: Gini climbs 0→0.993, bottom-50% collapses to ~1e-46.
- framing-disclosure: **pass** — genuine WealthAgent.step + a bit-equivalent numpy fast path, disclosed.

## Verdict: model FAITHFUL; P2 is an HONEST MISS from an over-strict finite-time bar (not a bug).
- **P1 REPRO** — condensation: final Gini = 0.9929 (all seeds ≥ 0.95); Gini(t) near-monotone (max dip 4.9e-4, a finite-N noise floor 3 orders below the 0→0.99 rise, within the locked 1e-3 tolerance).
- **P2 MISS** — bottom-50% share 3.6e-46 (≤ 0.01, passes overwhelmingly) but the richest agent holds only 0.274 vs the locked ≥ 0.90. At the fixed 2×10⁴-sweep budget wealth condenses onto an OLIGARCHY (top-10 ≈ 91%), not a single winner. **Single-agent takeover ≥ 0.90 is the asymptotic t→∞ limit and needs ≫ 2×10⁴ sweeps for N=1000** — the locked top-1 bar was over-strict for the finite budget. The builder did NOT extend the budget to force a pass.
- **P3 REPRO** — final Gini ≈ 0.99 ≫ the exponential's 0.5: multiplicative stake-the-poorer exchange condenses (breaks ergodicity), the opposite of additive conserved exchange — the load-bearing distinctness contrast vs Dragulescu-Yakovenko.

## Discipline check: PASS. Finite-time bar-calibration lesson.
2/3 REPRO honestly; no budget-extension to force a pass. The condensation + distinctness (vs DY exponential)
reproduce; only the single-winner absolute-share bar, a t→∞ limit, misses at the locked budget. 20 tests.

REVIEW COMPLETE
