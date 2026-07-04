# Ge & Polhill 2016 — Reproduction SUMMARY (all four levers)

Scoped faithful reproduction on the **real Aberdeen GIS data** (COMSES TiPaC
bundle), using the GeoNetwork foundation + a BPR congestion model. Predictions were
**locked to git before any run** ([PREDICTIONS-locked.md](PREDICTIONS-locked.md));
each lever's verdict is reported against its locked claim, honestly.

## Verdicts

| Lever | Locked prediction | Verdict | Evidence |
|---|---|---|---|
| **P1 flexitime** | ↓ time, ↓ variability, ↓ CO2; diminishing returns | ✅ **reproduced** + calibrated | strong; realistic 16/98 min ([details](FINDINGS-flexitime.md)) |
| **P2 urban concentration** | ↓ time, ↓ CO2; but ↓ reliability (trade-off) | 🟡 **2 of 3** | ↓time/↓CO2 ✅ (routes 13→9 km); reliability trade-off ❌ ([details](FINDINGS-urban-concentration.md)) |
| **P3 bypass (AWPR)** | small ↓ time, slight ↑ CO2 | 🟡 **signs only** | both signs ✅ + both small (as predicted), but magnitude near-zero / crude grafting ([details](FINDINGS-bypass.md)) |
| **P4 cyclists** | no significant ↑ in time/variability | ✅ **reproduced** | car time −0.9% across 0→50% cyclists; contingent on PCE<1 ([details](FINDINGS-cyclists.md)) |

## What reproduced, and what did not

**Reproduced** — the **first-order directional findings**, on real Aberdeen data:
flexitime lowers commute time/variability/CO2 (with diminishing returns); urban
concentration lowers commute time and CO2 (shorter homes-to-work); the bypass nudges
time down and CO2 up (both small); cyclists do not significantly slow car traffic.

**Did NOT reproduce / weak:**
- P2's **reliability trade-off** (the scoped BPR-on-A+B doesn't build urban
  congestion enough; cross-commuter std is dominated by route length, which shrinks).
- P3's **magnitude** (crude 2-link AWPR grafting → near-zero effect).
- All **absolute magnitudes** depend on a *fitted* BPR capacity, not the paper's
  calibration.

## Honesty / method

- Car-following micro-physics simplified to a BPR volume-delay model (stated up front).
- Minor roads (polygons) omitted → the A+B network concentrates traffic.
- Predictions locked **before** running; the claim that failed (P2 trade-off) is
  reported as a failure, not glossed; weak evidence (P3) and assumption-dependence
  (P4 PCE) are flagged.

## Conclusion

A **faithful partial reproduction**: the paper's qualitative, first-order policy
conclusions reproduce on the real Aberdeen network; second-order effects (P2
reliability), one weak magnitude (P3), and calibrated absolute values are **not**
claimed. To close the gaps would need the minor-road network, a fitted capacity,
day-to-day stochasticity, and the car-following micro-dynamics — i.e. converging
toward the original micro-simulation.
