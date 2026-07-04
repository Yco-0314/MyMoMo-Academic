# Ge & Polhill 2016 — Cyclists reproduction FINDINGS (P4)

**Run:** 2026-06-16, after locking predictions. Scoped reproduction; real Aberdeen
A+B network, 1,993 commuters, BPR congestion (capacity 100, fixed flexitime 0.5).

A fraction `f` of commuters cycle; a cyclist contributes PCE = 0.4 car-equivalents
of congestion but removes a full car. We measure CAR commute time vs f.

## Result

| cyclist fraction | car mean | car std | n cars |
|---|---|---|---|
| 0.0 | 16.40 min | 13.67 min | 1993 |
| 0.1 | 16.21 min | 13.63 min | 1796 |
| 0.2 | 16.15 min | 13.66 min | 1614 |
| 0.3 | 16.24 min | 13.62 min | 1419 |
| 0.4 | 16.30 min | 13.58 min | 1219 |
| 0.5 | 16.25 min | 13.57 min | 1045 |

## Verdict vs locked P4

**Reproduced:**
- ✅ car commute time does **NOT significantly increase** with cyclists
  (16.40 → 16.25 min across 0 → 50% cyclists, −0.9%; non-monotone within ~1% noise)
- ✅ commute-time variability also flat (13.67 → 13.57 min)

Matches "cyclists sharing roads with cars do not necessarily slow down the traffic
on the whole."

## Honest caveats

1. **Assumption-dependent.** The null result follows from **PCE < 1** (a bike
   congests less than the car it replaces; here 0.4). This is a defensible
   assumption, but the verdict is sensitive to it — PCE > 1 would flip the sign.
   The paper's micro-sim derives the effect from explicit car–bicycle interactions
   (`has-waited-for-bicycle?`); we encode it as a single PCE constant.
2. Cyclists' own (bike-speed) travel times are not modelled — only their effect on
   car congestion, which is what P4 is about.

## Conclusion

A **reproduction of P4's directional null result** (cyclists do not significantly
slow car traffic) on real Aberdeen data, contingent on a reasonable PCE < 1. Honest:
the *sign* reproduces; the mechanism is encoded as a constant rather than derived
from car–bicycle following.
