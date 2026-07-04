# Ge & Polhill 2016 — Flexitime reproduction FINDINGS

**Run:** 2026-06-16, AFTER locking predictions ([PREDICTIONS-locked.md](PREDICTIONS-locked.md)).
Scoped faithful reproduction; real Aberdeen GIS data (COMSES TiPaC bundle).

## What was run

- **Network:** real Aberdeen **A-roads + B-roads** → GeoNetwork (1,111 nodes,
  1,159 edges, largest connected component), EPSG:27700.
- **Commuters:** 2,000 sampled real home `address_point`s → random real `firm_address`
  workplaces; 1,993 routable home→work shortest paths.
- **Mechanism:** BPR volume-delay congestion per (edge, departure slot); CO2 proxy
  from congestion (stop-go surcharge). **Flexitime = spread of departure slots.**

## Result (calibrated, capacity = 100)

Capacity calibrated on this network so full-flexitime is free-flow and
no-flexitime is realistically (not degenerately) congested — see calibration note.

| flexitime (spread) | mean time | std time | total CO2 (proxy) |
|---|---|---|---|
| 0.00 (none) | 97.5 min | 118.9 min | 22,592,860 |
| 0.25 | 17.4 min | 14.5 min | 4,059,380 |
| 0.50 | 16.4 min | 13.7 min | 3,824,527 |
| 0.75 | 16.4 min | 13.7 min | 3,819,429 |
| 1.00 (full) | 16.4 min | 13.6 min | 3,817,092 |

**Calibration note:** per-(edge,slot) BPR capacity = 100. At full flexitime the
mean route (~12.8 km) runs at free-flow (~16 min); at no flexitime the morning
peak is ~6× congested (~98 min). The earlier uncalibrated run (capacity 20) gave a
degenerate 845-hour no-flex extreme; capacity ≥ 300 over-smooths (no congestion).
This is a *fitted* capacity — not the paper's specific calibration.

## Verdict vs locked P1

**Directional claims (the locked prediction) — REPRODUCED:**
- ✅ mean commute time **decreases** with flexitime
- ✅ commute-time variability (std) **decreases** with flexitime
- ✅ total CO2 **decreases** with flexitime
- ✅ **diminishing returns** (steep drop then leveling) — matches the paper's
  "emissions decline more slowly as more flexitime is introduced"

**The signs and the trade-off structure of P1 reproduce on real Aberdeen data.**

## Honest caveats (what did NOT reproduce / is not from the paper)

1. **Magnitudes are *fitted*, not from the paper.** Capacity=100 was tuned to
   give realistic commute times (16 min free-flow / 98 min congested), not taken
   from Ge & Polhill's calibration. The *shape* (steep drop + diminishing returns)
   is the reproduced result; the absolute minutes depend on the fitted capacity.
2. **Car-following simplified** to a BPR volume-delay function (stated up front).
3. **Minor roads omitted** — they are polygons (road *areas*) in the data; only
   A+B line roads were used, so traffic concentrates on fewer edges (inflating the
   no-flex congestion).
4. **Only lever P1 (flexitime)** is done. P2 (urban concentration), P3 (bypass),
   P4 (cyclists) are not yet reproduced.

## Conclusion

A **partial faithful reproduction**: P1's *directional* findings reproduce on the
real Aberdeen network. **Not claimed:** calibrated magnitudes, the car-following
micro-dynamics, or the other three levers. Magnitude calibration would need the
minor-road network and a fitted BPR capacity; the remaining levers are future work.
