# Gray-Scott reaction-diffusion (Pearson 1993) — review

**tier: minimal** (all-REPRO 3/3, comfortable margins; no MISS). Reaction-diffusion CA.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (spots 112, stripes max_aspect 7.62, peak_spots 320, homog std 0.000) matches bundle/results.
- fair-control: **pass** — all four regimes run the SAME equations/numerics; only (F,k) differs (the pattern-selection contrast).
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; the runner + tests were authored centrally (the builder wrote a sound module but stalled before test/runner); L3 gate fingerprints FINDINGS.
- mechanism-aliveness: **pass** — the reaction-diffusion mechanism is alive: distinct morphologies emerge (spots/stripes/self-replication) and the homogeneous regime collapses flat.
- framing-disclosure: **pass** — reaction-diffusion PDE on a grid (CA), disclosed, not agent-stepping.

## Verdict: SOUND. 3/3 REPRO.
P1 pattern selection (compact spots vs elongated stripes by (F,k)); P2 self-replication (peak 320 spots);
P3 homogeneous regime (std 0.000). Faithful 5-point periodic Laplacian + explicit Euler within the
stability limit; 10 faithfulness tests. Distinctness: a continuum reaction-diffusion phase diagram no
built CA (game_of_life, forest_fire) produces. No tuning.

REVIEW COMPLETE
