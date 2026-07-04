# Anshuka 2026 — Paper-Extent Rerun (candidate #10b) — FINDINGS

**Run:** 2026-06-28, AFTER locking [PREDICTIONS-locked.md](PREDICTIONS-locked.md).
**World:** the SAME `data/anshuka_ba/ba_dem_utm.tif` clipped to the paper's STATED study
window (UTM 60S `(571477, 8056801, 573495, 8058804)` ≈ 2.0 × 2.0 km, lon 177.674–177.693°E,
lat −17.574…−17.556°S → `data/anshuka_ba/ba_dem_2km_utm.tif`, 67×67 @ 30 m, elev 1.0–72.7 m),
resampled to **100×100** (≈20 m cells, matching the paper). n=100 agents, n_iter=10.
**Mechanism byte-identical** to candidate #10; only the world extent changed. Runner:
`examples/reproduce_anshuka_real/run.py data/anshuka_ba/ba_dem_2km_utm.tif docs/reproduce/anshuka-2026-real-dem-2km`.

## Headline — LOCKED HYPOTHESIS FALSIFIED (the extent is NOT the H3 confound)

The pre-registered PRIMARY test was: on the paper's ~2 km / 20 m extent, slow-onset
high-belief incap should drop into the paper's band **[20, 40]**. **It did not.** Slow-onset
high-belief incap = **57.8** — essentially identical to candidate #10's **57.0** at the
~19 km extent. Pre-registered **failure mode (a)** occurred: slow incap stayed **> 40**, so
the ~10× extent/resolution difference was NOT the dominant driver of H3's miss.

**Why (mechanistic):** the `_simulate` mechanism is **cell-based and scale-invariant** —
mobility is in *cells/tick* and flood onset in *ticks*, so the walk-vs-flood race depends on
cell-distances and tick-timing, NOT on whether a cell is 20 m or 190 m. Both worlds resample
to 100×100, so the cell-geometry (and thus the outcome) is nearly unchanged by the real
extent. H3's harsh slow baseline is a property of the **cell-mechanism + heuristic
world-derivation**, robust to the metric extent.

## Verdicts vs the locked predictions (and vs candidate #10 @ 19 km)

| Hyp | #10b (2 km) | candidate #10 (19 km) | Verdict @ paper extent |
|---|---|---|---|
| **H1** low-belief evac | 15.4 (paper ~17) | 15.2 | **REPRO** (unchanged) |
| **H2** alarm-timing gap (hi) | 10.7 (monotone) | 24.4 | **REPRO but marginal** (effect shrank on the small grid) |
| **H3** slow=57.8, rapid=77.5, Δ=**19.7** | Δ=18.0, slow=57.0 | **FAIL** — slow unchanged; extent hypothesis FALSIFIED |
| **H4** mobility Δincap(hi)=**5.7** | 10.4 | **FAIL** (was REPRO @19 km; gap compressed below 6 on the small grid) |
| **H5** Δevac(low)=2.1 (med 6.2/high 4.8) | 1.8 (7.2/7.5) | ≈null — consistent with the paper (unchanged conclusion) |

**Net:** the paper's actual extent does NOT improve the reproduction — it is *no better* and
on H4 *worse* (H4 fell from REPRO to a marginal FAIL because the smaller grid compresses the
mobility differentiation). So candidate #10's 19 km extent was not "wrong"; the larger grid
actually surfaced more of the paper's qualitative magnitude movements.

## What this means

1. **The extent/resolution divergence is a real fidelity caveat but NOT the cause of H3.**
   This falsifies the hypothesis in [PREDICTIONS-locked.md](PREDICTIONS-locked.md) **and** the
   over-strong claim in candidate #10's earlier caveat (now corrected there) that H3's miss is
   "largely an extent/resolution artifact." Tested honestly; disproved.
2. **H3's real gap is mechanism/world-derivation, not geometry-scale.** The slow-onset
   baseline (~58% high-belief incapacitation vs the paper's ~30%) is ~2× too lethal and is
   robust across extent (here), onset_steps and shelter-count (earlier ladder-#5 sweeps). A
   legitimate future fix would target the flood-timing-vs-walk-speed calibration or real OSM
   shelter/road placement (cutting cell-distances), with predictions locked first — but it is
   not worth a solo chase; H3 stays PARTIAL, honestly.
3. **H5 unchanged:** small collaboration effect at all belief levels (≈null), consistent with
   the paper (Fig 9, prior-experience-gated).

## Honest bottom line

Candidate #10b is a **clean negative result**: re-running at the paper's stated ~2 km / 20 m
extent did **not** flip H3, because the cell-based mechanism is scale-invariant. The flagship
reproduction stays as candidate #10 reported it (3/5 magnitudes REPRO at 19 km). The value
here is epistemic — a locked hypothesis was tested and disproved, and an over-claim in the
candidate #10 caveat was caught and corrected. The candidate #10 (19 km) artifact is left
untouched; this is a separate, self-contained bundle.
