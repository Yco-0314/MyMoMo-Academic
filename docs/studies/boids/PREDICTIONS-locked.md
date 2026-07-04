# Boids Flocking — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Reynolds (1987), not tuned. Genuine
agent-based.

**Model:** N=200 boid agents in a 2D periodic box, each position+velocity. Each tick apply
separation + alignment + cohesion (steer from neighbours within a radius), capped speed. Order
parameter φ = |mean of normalized velocities|. Compare full (3 rules) vs an alignment-OFF
control (separation+cohesion only). ≥5 seeds, measure after transient.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Flocking emerges (3 rules). | φ > 0.7 after transient (coherent common heading) |
| P2 | Alignment causes the common heading. | alignment-OFF control: φ < 0.3 (no coherent heading) |
| P3 | Cohesion holds (no dispersal). | mean nearest-neighbour distance stays bounded (does not grow without bound) |

**Discipline:** N, box, radius, rule weights, speed, seeds FIXED + metric locked; the control
differs ONLY by removing the alignment rule (FAIR). No tuning. Falsified → MISS.
