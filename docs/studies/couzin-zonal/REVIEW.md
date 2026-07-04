# Couzin et al. zonal collective motion (2002) — review

**tier: deep (adversarially verified)** — 2/3 REPRO + 1 honest MISS (mill bar too aggressive). genuine-agent (disclosed).

## Cheap checks + adversarial verification
- numeric-provenance: **pass** — bundle (mill combined 0.493, parallel p=0.998, hysteresis gap 1.75) matches results.
- fair-control: **pass** — the orientation-zone width Dzoo is the single swept control on one 3-zone rule.
- no-post-lock-drift: **pass** — graded vs lock ed6fe16 BEFORE run; L3 gate fingerprints FINDINGS+lock+spec.
- mechanism-aliveness / adversarial: **pass** — verifier's independent Dzoo sweep [2,3,4,5,6] confirms the (polarization, angular-momentum) phase portrait is alive: parallel flock p=0.998/m=0.017 at wide Dzoo (P2, 6/6 seeds), and genuine bistable HYSTERESIS (up-switch ~5.5-6.0, down-switch ~3.5-4.0, gap 1.75, 6/6 seeds switch on BOTH branches — a real history-dependent loop, not trivially true).
- framing-disclosure: **pass** — 3-zone self-propelled particles, disclosed.

## The honest MISS (P1 mill)
P1 required a torus/mill: p<0.35 AND m>0.65 at narrow Dzoo. Narrow-zone polarization p=0.201 passes (<0.35),
but angular momentum m=0.493 (max 0.546 over 6 seeds) FAILS the m>0.65 bar. The verifier's sweep shows m PEAKS
at ~0.49 at Dzoo=4 and never reaches 0.65 before the system flips to polarized at Dzoo=5. The qualitative mill
is real (it is the max-rotation, lowest-polarization regime in the whole sweep) — but the specific 0.65 bar was
slightly too aggressive for this zone geometry. Honest falsification / over-tight locked bar; NOT a model bug,
NOT tuned.

## Verdict: SOUND. 2/3 REPRO + 1 honest (over-aggressive mill bar) MISS.
P2 parallel flock and P3 hysteresis — the defining bistability Vicsek cannot show — reproduce cleanly; the mill
exists qualitatively but its angular momentum (~0.49) falls under the locked 0.65. 26 tests. No tuning.
REVIEW COMPLETE (deep tier, adversarially verified)
