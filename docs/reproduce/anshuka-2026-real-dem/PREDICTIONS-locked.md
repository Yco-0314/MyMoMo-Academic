# Anshuka 2026 — Real-DEM Reproduction (candidate #10) — LOCKED Predictions

**Paper:** Anshuka et al. (2026), *IJDRS* 17:439–455 (Ba River EWS ABM).
**This is the fidelity test-stone** (ADR-023 candidate #10 / [ADR-024](../../decisions/ADR-024-strategic-sequencing-and-domain-migration.md) D3 step 1):
replace the synthetic 20×20 grid of the [first reproduction](../anshuka-2026/FINDINGS.md)
with the **real Ba catchment SRTM DEM + OSM** road/building/shelter layers, and test
whether real agent-to-shelter geometry closes the magnitude gaps and recovers the P2 MISS.

**Locked:** BEFORE any real-DEM run. This commit IS the lock — every #10 verdict must
point back here. (Anti-fabrication 命门: predict first, then run, then report match/miss
honestly — even when the prediction is wrong.)

---

## The hypothesis under test (from the first reproduction's documented root cause)

[FINDINGS.md](../anshuka-2026/FINDINGS.md) attributes EVERY magnitude miss to one cause:
*"our 20×20 synthetic grid has small agent-to-shelter distances; the paper's 100×100 grid
(10,000 cells) makes hesitation more costly."* Candidate #10 tests that cause directly. The
real Ba DEM (~100×100 at the paper's geometry, real distances, real flood-vs-distance budget)
should move magnitudes toward the paper AND expose the alarm-timing lever — UNLESS the gap is
mechanistic, not geometric, in which case #10 falsifies the root-cause claim (a valuable result
either way).

Baseline = the synthetic-grid numbers already on record in FINDINGS.md.

## H1 — P1 magnitude CONVERGES (direction already REPRO)

- **Locked:** on the real DEM, low-belief evacuation **drops from 54.8 → ≤ 35**, and
  incap(low) **rises from 45.2 → ≥ 60**, moving toward the paper's ~17 / ~83. High-belief
  evac stays **≥ 60**. All three monotonic directions still hold.
- **REPRO** if low-belief evac enters ≤ 35 (the ~3× gap closes to < 1.5×). **PARTIAL** if it
  drops materially (≤ 45) but not into band. **MISS** if it stays > 45 (root cause refuted — see H6).

## H2 — P2 MISS → RECOVERY (the single most decisive test)

- **Locked:** with real distances, the earlier-alarm benefit **recovers at high belief**:
  `evac(t=1) > evac(t=10) > evac(t=30)` with `evac(t=1) − evac(t=30) ≥ 10` (vs the synthetic
  near-flat ≤ 5). Low belief stays counterintuitive (`evac(t=30) ≥ evac(t=1)`, per the paper).
- **REPRO** if the high-belief monotone holds with gap ≥ 10. **PARTIAL** if a weak monotone
  (gap 5–10). **MISS** (still) if flat. *This is the prediction that most directly proves the
  test-stone: a MISS→REPRO here is the magnitude-fidelity win the whole strategy is gated on.*

## H3 — P3 rapid-onset magnitude WIDENS

- **Locked:** high-belief rapid-onset incap **rises from 12.9 → ≥ 30** (toward the paper's
  50–70 band), and `Δincap(high) = rapid − slow ≥ 20` (from 10.3). Direction holds at every belief.
- **REPRO** if incap(high,rapid) ≥ 30 and Δ ≥ 20. **PARTIAL** if it rises but below band.

## H4 — P4 mobility-gap magnitude WIDENS

- **Locked:** mid/high-belief mobility gap widens: `Δincap(high, reduced − good) ≥ 6`
  (from the synthetic 1.6). Direction (reduced hurts more at mid/high belief) holds.
- **REPRO** if Δincap(high) ≥ 6. **PARTIAL** if it widens but < 6.

## H5 — P5 low-belief deviation PERSISTS (honest negative prediction)

- **Locked:** the low-belief P5 deviation (synthetic Δevac = 11.4, where the paper says null)
  is a **mechanism omission** — the missing prior-experience gate (paper §3.1.5) — **NOT a
  geometry artefact**. So it should **persist** on the real DEM: `Δevac(low) > 5` still.
- **REPRO of the prediction** = the deviation persists (Δevac(low) > 5), confirming it is
  mechanistic and belongs to ladder step #5 (calibration / prior-experience gate), not #10.
- **Surprise to investigate** = it disappears purely from the grid change. We must NOT credit
  the DEM for fixing P5 without understanding why. (This guards against motivated attribution.)

## H6 — Falsification condition (the test-stone cuts both ways)

- **If** real-DEM magnitudes do NOT move materially toward the paper — P1 low-belief evac stays
  > 45 AND P2 stays flat — **then the FINDINGS root-cause (grid geometry) is REFUTED**, and the
  magnitude gap is mechanistic/calibration, not geometric. That is a real, publishable finding
  that redirects work to ladder step #5, and #10 is reported as **root-cause MISS**, honestly.
- This makes #10 falsifiable and valuable in both outcomes: geometry-was-the-cause (moat earned)
  OR geometry-was-not (the gap is mechanistic — equally citable, and it saves months of wrong work).

---

## Verdict rules

Per H1–H6: **REPRO** (locked band holds), **PARTIAL** (direction/movement holds, band fails),
**MISS** (direction fails). A miss is a miss — no glossing. The headline #10 success criterion
(ADR-023 / ADR-024): **at least one of {H1, H2} reaches REPRO on magnitudes** — that converts the
honest scaffold into an earned scientific claim. H2 (P2 recovery) is the strongest single proof.

## What #10 does NOT change (kept identical to the first reproduction, to isolate the grid variable)

- The BDI agent mechanism, the belief/vision/mobility/collaboration rules, the bathtub flood
  mechanic, the 5-lever sweep structure, n=100 agents, the seed protocol. **Only the world geometry
  (elevation, roads, buildings, shelters) becomes real.** This is a controlled single-variable test:
  any magnitude movement is attributable to geometry, not to a mechanism change.
- n_iter stays at the first pass's value; P6 Sobol' sensitivity remains out of scope here.
