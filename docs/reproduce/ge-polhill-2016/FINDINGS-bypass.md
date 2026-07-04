# Ge & Polhill 2016 — Bypass (AWPR) reproduction FINDINGS (P3)

**Run:** 2026-06-16, after locking predictions. Scoped reproduction; real Aberdeen
A+B network + the AWPR route, time-based routing (base 13 m/s, bypass 25 m/s).

## Result

| scenario | mean time | mean route | total CO2 |
|---|---|---|---|
| no bypass | 16.4 min | 12.76 km | 3,824,627 |
| with bypass (+2 links) | 16.4 min | 12.78 km | 3,828,561 |

## Verdict vs locked P3

**Reproduced (signs):**
- ✅ bypass **reduces mean commute time by a small amount** (−0.02 min) — matches
  "only reduce mean commute time by a small amount"
- ✅ bypass **slightly increases total CO2** (+0.1%, via slightly longer routes) —
  matches "slightly increasing total CO2 emissions"

Both effects are in the predicted directions **and both are small**, which is
itself the paper's claim ("small amount" / "slightly").

## Honest caveats

1. **Magnitude is near-negligible** (−1.2 s mean, +0.1% CO2). The signs are right,
   but the effect is so small it is barely above noise.
2. **Crude bypass grafting.** The AWPR's 15 segments were attached as fast links
   between the nearest existing A+B junctions; the peripheral endpoints collapsed
   to **only 2 distinct links**, so few commuters can benefit. A faithful bypass
   would be a properly connected peripheral road with multiple access junctions —
   that needs the minor-road network so the AWPR threads into real interchanges.
3. Higher-speed CO2 is modelled only via longer distance, not a speed-emission
   curve (stated).

## Conclusion

A **qualified reproduction of P3's signs**: the bypass nudges commute time down and
CO2 up, both small (as the paper states). The near-zero magnitude is partly a
modelling artifact (2-link grafting on an A+B-only network), so this is weaker
evidence than P1. Honestly: directionally consistent, magnitude not trustworthy.
