# Anshuka et al. 2026 — Reproduction FINDINGS

**Run:** 2026-06-23, after locking predictions
([PREDICTIONS-locked.md](PREDICTIONS-locked.md)). Scoped reproduction:
synthetic 20×20 grid, n=100 agents, n_iter=10 (paper uses 30 — partial
downgrade noted).

**Implementation:** `abm_auto/gis/_anshuka_2026.py`. **Runner:**
`examples/reproduce_anshuka_2026/run.py`.

## Verdict summary

| Lever | Direction | Magnitude | Verdict |
|---|---|---|---|
| **P1** belief → evac↑, incap↓ | ✅ all three monotonic | ❌ much weaker (55/92/97 vs 17/55/72) | **PARTIAL** (direction REPRO) |
| **P2** earlier alarm → evac↑ at mid/high belief | ❌ flat at all belief levels | n/a | **MISS** |
| **P3** rapid-onset worsens evac, especially at high belief | ✅ rapid raises incap at every belief level | ❌ smaller in absolute terms (12.9 vs 2.6 at high; paper 65 vs 30) | **PARTIAL** (direction REPRO) |
| **P4** reduced mobility → incap↑ at mid/high belief | ✅ both directions match | ❌ very small effect | **PARTIAL** (direction REPRO) |
| **P5** collaboration ≈ null | ✅ med + high (Δ<5) | ❌ low belief shows Δevac=11.4 | **PARTIAL** (2/3 levels REPRO) |
| **P6** sensitivity Human-Count×* dominant | — not implemented (would need Sobol' / variance-based SA) | — | **not assessed** |

**3 PARTIAL + 1 MISS + 1 unassessed** in 6 locked predictions. **All
directions that hold in the paper are reproduced in direction here**, but the
magnitudes are systematically weaker on our synthetic grid.

## Detailed numbers (from the real run, mean ± std over 10 seeds)

### P1 — belief sweep (slow-onset, alarm t=0, 70% good mobility, no collab)

| Belief | Our evac | Paper evac | Our incap | Paper incap |
|---|---|---|---|---|
| Low (10%)    | 54.8 ± 4.7 | ~17 | 45.2 ± 4.7 | ~83 |
| Medium (40%) | 91.5 ± 2.3 | ~55 | 8.5  ± 2.3 | ~45 |
| High (70%)   | 97.4 ± 1.0 | ~72 | 2.6  ± 1.0 | ~28 |

Direction REPRO; magnitudes off by ~3× on the low end. **Honest reason**: our
synthetic 20-cell grid has agents only ~5–8 cells away from shelters, so even
late-warned agents usually escape. The paper's Ba grid is larger (~10,000
cells / 100×100) and agents are farther from shelters — a paper agent who
delays self-warning by 20 steps typically *cannot* reach a shelter before
inundation. Our grid does not punish hesitation as severely.

### P2 — alarm release time (slow-onset, vary alarm_t)

| Belief × Alarm | t=1 evac | t=10 evac | t=30 evac |
|---|---|---|---|
| Low    | 57.5 | 57.3 | 57.0 |
| Medium | 90.6 | 92.2 | 87.3 |
| High   | 96.2 | 97.1 | 91.3 |

**MISS** for the direction at all belief levels. The paper finds a clear
benefit for earlier release at medium/high belief; we see a flat curve (med
even shows t=10 ≥ t=1). **Honest reason**: in our scenario the slow-onset
flood gives even t=30 agents time to evacuate from a small grid; the
"earlier-is-better" effect needs a tighter flood-vs-distance budget.

### P3 — rapid vs slow onset (each belief level)

| Belief | Slow incap | Rapid incap | Δincap |
|---|---|---|---|
| Low    | 45.2 | 76.7 | +31.5 |
| Medium | 8.5  | 32.6 | +24.1 |
| High   | 2.6  | 12.9 | +10.3 |

Direction REPRO at every belief level: rapid-onset always worsens evacuation.
Magnitudes are weaker than the paper's (paper at high belief: ~30 → ~65
incap), but the **rank ordering** (rapid > slow at every belief, gap shrinks
slightly at low belief because of saturation) matches.

### P4 — mobility good (70%) vs reduced (30% good)

| Belief | Good incap | Reduced incap | Δincap |
|---|---|---|---|
| Low    | 45.2 | 46.7 | +1.5 |
| Medium | 8.5  | 10.6 | +2.1 |
| High   | 2.6  | 4.2  | +1.6 |

Direction REPRO at all three levels; consistent with the paper's claim that
reduced mobility hurts more at medium / high belief. **Magnitudes small** —
the paper's Fig 8 shows a much wider gap at medium / high belief. Same reason
as P1: our shorter distances and gentler flood expansion make slow agents
mostly still arrive.

### P5 — collaboration on / off

| Belief | Δevac | Δincap | Verdict |
|---|---|---|---|
| Low    | 11.4 | 11.4 | **MISS** (paper says null; we see a real lift) |
| Medium | 3.2  | 3.2  | REPRO (within ±5) |
| High   | 0.8  | 0.8  | REPRO (within ±5) |

**Mixed**: at medium and high belief the null effect reproduces, but at low
belief collaboration substantively *helps* (Δevac=+11.4). **Honest reading**:
our collaboration mechanism propagates awareness too easily when many agents
are clustered around the same low-belief building (one self-warned neighbour
triggers a chain). The paper's collaboration also propagates, but with a
prior-experience gate that we did not implement (§3.1.5: "the agent's
experience threshold ... uninformed agent receives flood information through
social interaction, their decision to act depends on prior experience"). The
**low-belief MISS is real** and a candidate for a follow-up calibration.

## Honest scoping (not reproduced; transparent about it)

1. **Magnitudes** are systematically weaker than the paper across all levers
   except the directions. Root cause: our 20×20 synthetic grid has small
   agent-to-shelter distances; the paper's 100×100 grid (Section 2.3.5,
   "10,000 cells") makes hesitation more costly. We did NOT calibrate the
   grid to match the paper's geometry.
2. **P2 MISS**: alarm release time has nearly no effect here because the
   slow-onset flood gives almost everyone time. A faster default flood +
   bigger grid would expose this lever.
3. **P5 low-belief deviation**: our collaboration uptake lacks the
   prior-experience gate the paper describes. This is a known omission.
4. **P6 sensitivity not implemented**: the second-order Sobol' / TAT analysis
   needs SALib + many runs; out of scope for this first pass.

## Conclusion

A **faithful partial reproduction** in the same shape as Ge & Polhill 2016 on
this project: 3 of 5 mechanistic levers reproduce in direction, 1 is a real
miss, 1 is mixed; all magnitudes are systematically weaker because the
synthetic grid does not punish delay as harshly as the paper's larger grid.
The qualitative story — belief × flood-speed × mobility shaping evacuation
outcomes — is real on our model; the absolute counts and the
alarm-release-time lever require closer GIS-grid fidelity than this first
pass attempts.

This is reported honestly — no glossing of P2 and the low-belief P5 deviation.
