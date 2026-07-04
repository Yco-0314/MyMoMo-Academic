# Galam Majority Rule — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claim is the Galam majority-rule model, not tuned.
Genuine agent-based (opinion agents, reshuffled local-majority groups).

**Model:** N=10001 agents, binary opinion, initial up-fraction p0. Each step: randomly
partition into groups of size g; each group adopts its local majority; reshuffle. Odd g=3:
no ties. Even g=4: ties broken toward UP (fixed prejudice). Run to consensus. Outcome =
which consensus vs p0. Mean over ≥20 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | g=3: majority rule → consensus with tipping at p_c=0.5. | p0=0.45 → all-down AND p0=0.55 → all-up (initial majority wins, reaches consensus) |
| P2 | g=4 (ties→up): tipping point shifts below 0.5 (minority spreading). | the up-win threshold p_c < 0.5 — e.g. p0=0.45 → all-UP (an initial up minority wins) |
| P3 | Flow moves away from p_c (no interior stable fixed point). | trajectories of up-fraction move monotonically toward 0 or 1, not toward an interior value |

**Discipline:** N, group sizes, tie rule, p0 values, seeds FIXED + metric locked before run;
no tuning. Falsified → MISS.
