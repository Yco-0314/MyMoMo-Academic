# Burridge-Knopoff earthquake fault (Carlson & Langer 1989) — review

**tier: deep (adversarially verified)** — 3/3 REPRO on the high-difficulty mechanical model. genuine-agent (disclosed).

## Cheap checks + adversarial verification
- numeric-provenance: **pass** — bundle (ell=3.0 MLE exponent 1.724, tail 3.79 decades, stiffness ratio 2.72) matches results.
- fair-control: **pass** — the ell (stiffness) sweep is a clean single-parameter control; P3 uses the same integrator across ell.
- no-post-lock-drift: **pass** — graded vs lock d7599ab BEFORE run; L3 gate fingerprints FINDINGS+lock+spec.
- mechanism-aliveness / adversarial: **pass** — this is a genuine Newtonian spring-block chain (continuous position/velocity, velocity-weakening friction, inertia), NOT a CA. Verifier probed the concern that 77% of events sit at the single-block quantum (a delta-spike at xmin): but the percentile-window fit [p50,p97.5] is locked methodology, the exponent rises MONOTONICALLY with stiffness (1.47 at ell=2.0 -> 1.72 -> 2.33 at ell=4.0, with ell=2.0 BELOW the band), and the heavy tail survives dropping the top-5 events (3.71 decades / 5165x). Mean event moment strictly decreases with stiffness (1.63>1.25>0.60). Genuine, not a delta-spike artifact.
- framing-disclosure: **pass** — mechanical agent model with Newtonian integration, disclosed.

## Verdict: SOUND. 3/3 REPRO (adversarially verified).
P1 Gutenberg-Richter power law (MLE exponent 1.72 in [1.5,2.5]); P2 heavy-tailed moments (3.79 decades, robust to
outlier removal); P3 stiffness sharpens the distribution (mean moment falls 2.72x as ell rises). Inertia +
velocity-weakening friction produce genuine scale-free slip statistics — the mechanical result OFC's CA
caricature only approximates. 21 tests. No tuning.
REVIEW COMPLETE (deep tier, adversarially verified)
