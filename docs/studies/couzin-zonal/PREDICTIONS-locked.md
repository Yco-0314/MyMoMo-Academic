# Couzin et al. zonal collective motion (2002) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Couzin, Krause, James, Ruxton & Franks 2002 (J Theor Biol
218:1), not tuned. **Genuine-agent (disclosed): 3-zone self-propelled particles in 2D.** Verified; gate-checked.

**Model:** N self-propelled agents in continuous 2D. Each has position + heading, moves at fixed speed, and
turns each step by three nested zones: (1) a hard-core repulsion zone (avoid collisions), (2) an ORIENTATION
zone of width Δzoo (align heading with neighbours), (3) an attraction zone (steer toward distant neighbours).
Bounded turning rate + heading noise. Control parameter = orientation-zone width Δzoo. Two order parameters:
group polarization p (mean heading alignment, 0..1) and normalized angular momentum m (rotation about the group
centroid, 0..1).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Mill / torus regime exists. | for a NARROW orientation zone (small Δzoo) the group settles to a torus: polarization p < 0.35 while angular momentum m > 0.65 — a milling state distinct from a polarized flock. |
| P2 | Parallel / polarized regime. | for a WIDE orientation zone (large Δzoo) polarization is high (p > 0.9) and angular momentum collapses (m < 0.2) — a coherent moving flock. |
| P3 | Hysteresis between states. | sweeping Δzoo up vs down, the Δzoo at the swarm→polarized switch differs from the polarized→swarm switch by a finite gap (≥ 1 model length-unit) — the collective state is history-dependent (bistable). |

**Discipline:** N, speed, zone radii, Δzoo sweep grid, turning-rate, noise, seeds, run length FIXED; metrics
locked; no tuning. Falsified → MISS. gate_design_check: P1 (mill) and P3 (hysteresis) are the honest MISS-risk
clauses — the mill needs the narrow-orientation / strong-attraction regime and hysteresis needs a slow up/down
Δzoo ramp with equilibration at each step; P2 (parallel flock) is the robust wide-zone limit.
**Distinctness (keep):** the (polarization, angular-momentum) phase portrait — a milling/torus state and
bistable HYSTERESIS as a single zone-width parameter varies — cannot appear in vicsek_flocking (one alignment
rule, one order/disorder threshold, no mill, no hysteresis) or boids (no zone-width control parameter).
