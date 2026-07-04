# Centola & Macy 2007 Complex Contagion — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running any reproduction.** Predictions are Centola &
Macy's (2007) published claims, not tuned. Source: AJS 113(3):702–734; model
corroborated via Centola, Eguíluz & Macy (2007) Physica A 374:449–456
(https://ndg.asc.upenn.edu/wp-content/uploads/2016/04/Centola-et-al-2007-PA.pdf).

**Model (faithful):** Watts–Strogatz ring lattice, degree z=8, rewiring fraction
p∈[0,1] in degree-preserving pairs (p=0 clustered, p=1 randomized). Node adopts iff
**number** of active neighbors ≥ R (R=1 simple, R=2 complex). Seed a small contiguous
neighborhood (a node + its immediate lattice neighbors) so a complex contagion can
start. Run to fixed point; outcome = final adoption fraction, averaged over seeds/graphs.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | **Simple contagion (R=1):** randomization helps — final adoption (or spread speed) on randomized (high p) ≥ clustered (p=0). | adoption(p=1) ≥ adoption(p=0) for R=1 |
| P2 | **Complex contagion (R=2):** clustering helps — final adoption on clustered (low p) **>** randomized (high p); randomization **impedes** ("weakness of long ties"). | adoption(p=0) > adoption(p=1) for R=2 |
| P3 | **Crossover:** the SIGN of the rewiring effect on adoption flips between R=1 and R=2. | sign[adoption(p=1)−adoption(p=0)]_{R=1} ≠ sign[...]_{R=2} |

**Discipline:** z=8, R∈{1,2}, seeding scheme, p grid fixed BEFORE the run; no tuning to
force the crossover. A falsified clause is reported MISS. The headline is P2/P3 (the
counterintuitive "clustering beats randomness" claim).
