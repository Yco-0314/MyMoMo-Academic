# Conway Game of Life — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Conway/Gardner (1970), not tuned.
**Cellular automaton (deterministic), NOT agent-decision** — disclosed in FINDINGS.

**Model:** L×L toroidal grid, rule **B3/S23** (a dead cell with exactly 3 live neighbours is
born; a live cell with 2 or 3 survives; else dies). Deterministic — no seeds/averaging.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | The glider is a period-4 diagonal spaceship. | the glider returns to its own shape translated by exactly (+1,+1) after 4 generations |
| P2 | Blinker period 2; block is a still life. | blinker period = 2; block unchanged every generation (period 1) |
| P3 | Catalogued periods are exact. | beacon period = 2; live-cell count is conserved for the block and oscillates with period 2 for blinker/beacon |

**Discipline:** rule B3/S23, the exact starting patterns FIXED before run; deterministic
(exact, not statistical). Falsified → MISS.
