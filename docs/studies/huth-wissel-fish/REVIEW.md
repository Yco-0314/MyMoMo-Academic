# Huth & Wissel fish schooling (1992) — review

**tier: deep (adversarially verified)** — 1/3 REPRO + 2 honest MISSes. genuine-agent, zonal SPP (disclosed).

## Cheap checks + adversarial verification
- numeric-provenance: **pass** — bundle (averaging gap 0.73, CV 0.603 vs 0.483, p_dec 0.176) matches results.
- fair-control: **pass** — averaging-vs-decision is a clean integration-rule A/B with identical zonal forces.
- no-post-lock-drift: **pass** — graded vs lock ed6fe16 BEFORE run; L3 gate fingerprints FINDINGS+lock+spec.
- mechanism-aliveness / adversarial: **pass, with a substantive honest finding** — verifier re-ran the locked config and probed for bugs (see below). No tuning; 21 tests pass; tiers=refutation.
- framing-disclosure: **pass** — zonal self-propelled fish, disclosed.

## Honest findings (the two MISSes are real, and one is scientifically important)
- **P1 REPRO (load-bearing claim holds):** averaging beats decision by gap=0.730 (avg p=0.906 vs dec p=0.176),
  zero per-seed overlap, ~5x the 0.15 bar. Averaging many-neighbour headings builds real global consensus.
- **P2 MISS (my metric was scale-confounded):** CV(NND)_avg=0.603 is NOT < CV(NND)_dec=0.483. Cause (verifier-
  confirmed): the decision school is LOOSER (mean NND 2.15 vs 1.07 for averaging), and a looser, more
  Poisson-uniform cloud has LOWER coefficient-of-variation despite WORSE absolute cohesion. Averaging IS tighter
  in absolute mean NND; my CV-of-NND proxy inverts under the scale difference. A miscalibrated metric choice, not a bug.
- **P3 MISS (the decision rule genuinely does not school):** p_dec=0.176 < 0.5. The verifier probed for a
  structural bug: the decision rule aligns correctly at n=2 (p~1.0) but NEVER schools at n=60 across Dzoo in
  {6,15,30} and noise in {0,0.05} (p stays ~0.06-0.17). This is the real emergent behaviour of
  follow-single-nearest (each fish chases a different, changing nearest neighbour). So in this zonal
  implementation the contrast is averaging-vs-near-disorder, not the "both school, averaging better" of the paper.

## Verdict: SOUND but a PARTIAL reproduction (1/3). Honest MISSes, no tuning.
The averaging advantage (P1) reproduces strongly. Huth-Wissel's fuller claim — that BOTH rules school and
averaging is merely quantitatively better — did NOT reproduce here: the follow-one-nearest decision rule
collapses to near-disorder at n=60 (P3), and the CV-of-NND cohesion proxy is scale-confounded (P2). Reported
plainly rather than tuned. This is a legitimate honest-MISS entry, not a pass. 21 tests.
REVIEW COMPLETE (deep tier, adversarially verified)
