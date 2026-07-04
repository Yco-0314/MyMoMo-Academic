# Ge & Polhill 2016 — Urban-concentration reproduction FINDINGS (P2)

**Run:** 2026-06-16, after locking predictions. Scoped reproduction; real Aberdeen
A+B network, 2,000 commuters, BPR congestion (capacity 100, fixed flexitime 0.5).

Concentration `c` biases homes toward the firm-centroid city centre (c=0 city-wide,
c=1 nearest ~15%).

## Result

| concentration | mean time | std time | mean route | total CO2 |
|---|---|---|---|---|
| 0.00 | 16.9 min | 14.3 min | 13.16 km | 3,941,069 |
| 0.25 | 12.9 min | 11.3 min | 10.02 km | 3,004,709 |
| 0.50 | 11.6 min | 11.0 min | 9.00 km | 2,699,820 |
| 0.75 | 11.2 min | 10.8 min | 8.72 km | 2,621,526 |
| 1.00 | 11.5 min | 11.0 min | 8.97 km | 2,694,873 |

## Verdict vs locked P2

**Reproduced:**
- ✅ **mean commute time decreases** with urban concentration (16.9 → 11.5 min)
- ✅ **total CO2 decreases** with urban concentration (3.94M → 2.69M)
- ✅ mechanism is the predicted one: people live closer → **routes shorten**
  (13.2 → 9.0 km)

**NOT reproduced:**
- ❌ the **length-vs-reliability trade-off**. The paper finds higher concentration
  makes travel time *less reliable* (↑ variability / ↑ urban congestion). Here the
  std time *decreases* (14.3 → 11.0 min) — reliability *improves*, the opposite
  sign. The shorter routes dominate, and the scoped BPR-on-A+B model does not build
  up urban-core congestion strongly enough to worsen reliability. The original
  car-following micro-sim on the full (incl. minor) road network captures that
  congestion build-up; this scoped model does not.

## Conclusion

A **partial reproduction of P2**: the two first-order claims (↓ time, ↓ CO2 via
shorter homes-to-work distance) reproduce on real Aberdeen data; the **second-order
reliability trade-off does not** — an honest limitation of the scoped congestion
model (BPR on the A+B network only). Capturing it would need the minor-road network
and a congestion model that loads urban edges as concentration rises.
