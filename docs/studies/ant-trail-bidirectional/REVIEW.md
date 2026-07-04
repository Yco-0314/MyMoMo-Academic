# Ant-trail flow CA (Chowdhury et al. 2002) — review

**tier: deep** — 2/3 REPRO + 1 honest MISS on the anomalous-plateau clause. CA (disclosed).

## Cheap checks + verification
- numeric-provenance: **pass** — bundle (f=0.005: rho*=0.55, band-variation 0.338; f=0.95 recovery) matches results.
- fair-control: **pass** — same NaSch+pheromone rule; the ONLY change across P1..P3 is the evaporation rate f (the pheromone knob), a clean single-parameter contrast.
- no-post-lock-drift: **pass** — graded vs lock e6f4f29 BEFORE run; L3 gate fingerprints FINDINGS+lock+spec.
- mechanism-aliveness: **pass** — the pheromone coupling is alive: the flow peak IS right-shifted to rho*=0.55>0.5 (P2), and raising f to 0.95 recovers NaSch (rho*->0.5, P3) — the anomaly is real and pheromone-controlled.
- framing-disclosure: **pass** — 1D exclusion CA + pheromone field, disclosed.

## The honest MISS (P1)
P1 required the mean-velocity to be roughly FLAT (<20% variation) across rho in [0.2,0.5] at small f. Measured
variation = 0.338 (34%) > 0.20 -> MISS. This was flagged as a MISS-risk clause in the lock: in this Q/q
parametrization the "plateau" is a gentle shoulder, not flat to within 20%. The two robust anomaly signatures
(right-shifted peak P2, evaporation-recovery P3) DO reproduce, so the pheromone anomaly is present; only the
strict flatness bar was too tight. Builder reported MISS rather than widen the band -- anti-fabrication held.

## Verdict: SOUND. 2/3 REPRO + 1 honest MISS (over-strict plateau-flatness bar).
The qualitative anomalous fundamental diagram (right-shifted peak + pheromone control) reproduces; the strict
20%-flatness plateau does not. 18 tests. No tuning.
REVIEW COMPLETE (deep tier)
