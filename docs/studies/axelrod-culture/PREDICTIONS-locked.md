# Axelrod 1997 Dissemination of Culture — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claims are Axelrod's (1997), not tuned. Source:
J. Conflict Resolution 41(2):203–226.

**Model (faithful):** L×L grid (10×10). Each agent has F features, each holding one of q
traits. Per step: pick a random agent + random Moore/von-Neumann neighbor; interact with
probability = cultural similarity (fraction of shared features); on interaction copy one
randomly chosen differing feature's trait. Run to an absorbing state (no possible
interactions remain). Outcome = number of distinct stable cultural regions (connected
same-culture components).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | #stable regions **increases with traits q** (at fixed F=5). | #regions(q=15) > #regions(q=5) |
| P2 | #stable regions **decreases with features F** (at fixed q). | #regions(F=10) < #regions(F=5) |
| P3 | Monoculture limit: small q → ~1 dominant region. | #regions(q=2–5, F=5) is small (≤ ~3; near-monoculture) |

**Discipline:** L=10, F/q grids, neighborhood, absorbing-state stop fixed before run.
Report mean #regions over seeds. A falsified clause → MISS.
