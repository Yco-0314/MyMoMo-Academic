# Dynamic Social Impact (Nowak-Szamrej-Latané 1990) — adversarial review

**tier: deep** (trigger: 2 honest MISSes). Reviewed against the verified canonical claim +
the committed lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (minority 0.045, bond 0.998, survival 0.10) matches the bundle/results.
- fair-control: **n/a** — single-arm frozen-state study (no two-arm contrast).
- no-post-lock-drift: **pass** — graded verbatim against the committed lock; L3 bundle integrity gate green (verdicts=3, doc hashes verified).
- mechanism-aliveness: **pass** — the impact functional is algebraically EXACT (the vectorized weight-matrix path verified bit-for-bit against an O(N²) double loop on hand-built lattices). The mechanism is alive; it simply drives the lattice to consensus.
- framing-disclosure: **pass** — genuine fixed agents, deterministic sweep-to-freeze, disclosed.

## Verdict: model FAITHFUL; P1/P3 are HONEST MISSes (a regime issue, NOT a bug).
- **P1 MISS (mean minority 0.045 vs band [0.08,0.45]) + P3 MISS (survival 0.10 vs 0.80).** 45/50 seeds collapse to full consensus. **Cause:** α=2 (inverse-square) on a 2D lattice makes influence too GLOBAL — the per-agent incoming weight ≈ 15.7 is dominated by the long-range tail (shell count ~d × weight ~1/d² ⇒ ~log-divergent reach), so the marginally-larger majority's persuasive field overwhelms local minority support everywhere and no minority enclave anchors. The builder verified the functional bit-for-bit, checked the synchronous update (same collapse, plus 2-cycle artifacts), and did NOT retune α or the traits to rescue it. The lock PRE-REGISTERED exactly this risk ("minority survival is a ZERO-NOISE, finite-size phenomenon").
- **P2 REPRO (bond fraction 0.998 ≥ 0.75).** Spatial self-organisation is strong and clear.

## Discipline check: PASS. Diagnosis + recommendation.
1/3 REPRO reported honestly; no tuning. The MISS is a mis-calibrated REGIME in the lock, not a
model defect: α=2 inverse-square is the marginal/too-global case; the canonical minority-survival
+ stable-cluster result needs MORE LOCAL influence (a faster decay α>2, or a bounded interaction
radius). A principled v2 re-lock at α>2 (or a finite range) would test the regime where the
phenomenon lives and is NOT tuning-to-pass (the correction follows from the lattice-sum reach
analysis, independent of the observed numbers). This is the same lesson as q-voter's sub-critical
ε: the gate-design (pre-lock) check "does the locked parameter put the system in the claimed
regime?" should be run before locking a distance/threshold parameter.

REVIEW COMPLETE
