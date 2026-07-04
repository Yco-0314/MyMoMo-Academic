# Anshuka 2026 — Paper-Extent Rerun (candidate #10b) — Locked Predictions (BEFORE any run)

**Locked:** 2026-06-28, BEFORE clipping the DEM or running. Anti-fabrication discipline:
write the expected outcome, commit, THEN run, THEN report match/miss honestly. This file
is the contract; any verdict must point back here.

## Why this rerun

Candidate #10 (`../anshuka-2026-real-dem/`) reproduced 3/5 magnitudes but H3 was PARTIAL
(slow-onset high-belief incap **57** vs the paper's **~30**; Δ(rapid−slow)=**18 < 20**).
Reading the paper (Anshuka et al. 2026, §2.3.3) showed candidate #10 used a bbox of
**~19 × 15.5 km (~190 m cells)** — about **10× larger / coarser** than the paper's STATED
study area: **~2.0 × 2.0 km at 20 m resolution** (lon 177.67358–177.69252°E, lat
−17.57415…−17.55598°S; 100×100 grid). Hypothesis: the harsh slow-onset baseline is largely
an **extent/resolution artifact** (agents walk ~10× farther on candidate #10's grid).

This rerun clips the SAME Copernicus/SRTM DEM (`data/anshuka_ba/ba_dem_utm.tif`, EPSG:32760,
which fully covers the paper bbox) to the paper's ~2 km window and resamples to 100×100
(≈20 m cells, matching the paper). **Mechanism byte-identical** to candidate #10 — only the
world extent changes. This is a paper-sourced parameter correction, NOT a threshold change.

## The LOCKED test (primary, H3′)

On the paper's ~2 km / 20 m extent:
- **PRIMARY:** slow-onset high-belief incap lands in the paper's band **[20, 40]** AND
  Δ(rapid−slow) at high belief **≥ 20** → **H3 → REPRO**.

Honest pre-registered failure modes (either ⇒ H3 NOT cleanly REPRO, reported as such):
- **(a) still harsh:** slow incap **> 40** → the extent was NOT the dominant confound;
  H3 stays geometry/mechanism-bound (the #10b hypothesis is falsified).
- **(b) over-corrected:** slow incap **< 20** (the small grid lets nearly everyone escape)
  → magnitude now too forgiving; the paper band is missed from the other side.

I genuinely do not know which of REPRO / (a) / (b) will occur. My weak prior: slow incap
drops substantially from 57 (≈10× shorter distances), most likely into [20,40] or below.

## Secondary (observed, NOT gating)

These will shift with the extent; recorded for honesty, not locked as pass/fail:
- **H1** low-belief evac: direction (low<med<high) holds; magnitude may rise toward the
  paper's mid/high (which candidate #10 over-corrected LOW at 19 km).
- **H2** earlier-alarm: expect the monotone high-belief recovery to persist (shorter
  distances still make a 30-tick delay costly, though the effect may shrink on a small grid).
- **H4** mobility gap: direction holds; magnitude may shrink (less distance to differentiate).
- **H5** collaboration: expect a **small** Δevac at all belief levels (≈null), **consistent
  with the paper** (Fig 9, prior-experience-gated). Not a pass/fail here.

## Scope / caveats (same honesty as candidate #10)

- Homes/shelters/river are still derived **heuristically** from the DEM (not real OSM
  locations); on a 2 km window the heuristic placement differs from the 19 km one.
- Elevation is normalized to the synthetic flood-vs-level regime, per the mechanism.
- n_iter=10 (paper 30); central tendency + direction only.
- Onset rapid/slow uses candidate #10's assumed `onset_steps` (rapid=3, slow=10) — the
  paper gives no numeric onset definition; unchanged here so #10b isolates the EXTENT.

## Decision rule

If PRIMARY holds → H3 promotes to REPRO at the paper's extent (the flagship reproduction
becomes 4/5), and candidate #10's H3 PARTIAL is explained as an extent artifact. If (a) →
the extent hypothesis is falsified, H3 is genuinely bound (honest). If (b) → record the
over-correction; H3 remains not-cleanly-REPRO. In all cases the candidate #10 (19 km)
bundle is left untouched; this is a separate artifact.
