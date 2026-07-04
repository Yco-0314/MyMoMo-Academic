# Olami-Feder-Christensen Earthquakes (SOC) — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Olami, Feder & Christensen (1992), not tuned.
**Driven-threshold cellular automaton (SOC), NOT autonomous-agent-stepping** — disclosed.

**Model:** L×L lattice (L=50), site forces ~U[0,1]. Drive all sites uniformly until max=1;
relax: over-threshold site → 0, adds α·force to each of 4 neighbours (open boundary); cascade.
Event size = #topplings/drive. Discard transient, collect ≥10⁴ events. Conservation α≤0.25.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Power-law event sizes (α=0.2). | event-size distribution heavy-tailed: ≥2 decades AND max ≥ 100× median nonzero |
| P2 | More conservative α → heavier tail. | mean event size at α=0.2 > at α=0.1 |
| P3 | Self-organizes to a stationary critical state. | event-size distribution stationary after transient + init-independent |

**Discipline:** L, α grid, threshold, drive, transient FIXED + metric locked; no tuning. Falsified → MISS.
