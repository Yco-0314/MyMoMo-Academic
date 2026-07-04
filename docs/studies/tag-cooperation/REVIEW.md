# Tag-based cooperation (Riolo-Cohen-Axelrod 2001) — review

**tier: minimal** (all-REPRO 3/3, comfortable margins; no MISS). Genuine agent-based.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (donation 0.6133, cluster 0.9104, CV 0.3232, crash-recover 10/10) matches bundle/results.
- fair-control: **n/a** — single-arm evolutionary run; the P-dependence (P=3 vs P≤2) is the distinctness gate, not an in-run control.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; FINDINGS authored + re-run so the bundle fingerprints it.
- mechanism-aliveness: **pass** — the tag-similarity donation + tolerance-wave mechanism is alive (donation 0.61, dominant cluster 0.91, crash-and-recover in every seed).
- framing-disclosure: **pass** — genuine well-mixed agent-based (random pairing, no space), disclosed.

## Verdict: SOUND. 3/3 REPRO.
P1 donation rate 0.6133 ∈ [0.55,0.85] (paper 0.736); P2 dominant tag cluster 0.9104 ≥ 0.6; P3 intermittent
waves (CV 0.3232 ≥ 0.1, crash-and-recover in 10/10 seeds). Distinctness: WELL-MIXED tag donation + waves of
tolerance — distinct from the built SPATIAL ethnocentrism (lattice, 4 tag-strategies). 22 tests. No tuning.
(Experiment authored + run centrally after the builder's process hit an API error before completing the run.)

REVIEW COMPLETE
