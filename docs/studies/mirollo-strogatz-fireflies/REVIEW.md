# Mirollo-Strogatz pulse-coupled oscillators (1990) — review

**tier: minimal+ (adversarially verified)** — 3/3 REPRO. genuine-agent (disclosed).

## Cheap checks
- numeric-provenance: **pass** — bundle (concave sync fraction 1.0, median cycles 8 vs 31.5, linear sync 0.0) matches results.
- fair-control: **pass** — P1 vs P3 is a clean concave-vs-linear curve A/B; P2 varies only epsilon.
- no-post-lock-drift: **pass** — graded vs lock ed6fe16 BEFORE run; L3 gate fingerprints FINDINGS+lock+spec.
- mechanism-aliveness: **pass** — the integrate-and-fire absorption mechanism is alive: concave curve syncs 100% of seeds (measure-1), stronger coupling speeds sync (median 8 vs 31.5 cycles), and a LINEAR curve fails to sync (0.0 fraction) — confirming CONCAVITY, not mere pulse coupling, drives the result. 17 tests pass.
- framing-disclosure: **pass** — integrate-and-fire oscillators with pulse coupling + absorption, disclosed.

## Verdict: SOUND. 3/3 REPRO.
P1 universal (measure-1) synchronization; P2 coupling speeds sync; P3 concavity is necessary. The
Mirollo-Strogatz theorem — pulse-coupled IF oscillators with a concave curve sync from almost all IC with no
coupling threshold — reproduces exactly, and is distinct from kuramoto (continuous coupling, finite K_c). 17 tests. No tuning.
REVIEW COMPLETE (minimal+)
