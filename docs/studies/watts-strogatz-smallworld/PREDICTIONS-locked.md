# Watts–Strogatz Small-World — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claim is Watts & Strogatz (1998), not tuned.
**Network-GENERATION model, not agent-stepping** (disclosed in FINDINGS).

**Model:** ring lattice n=1000, each node degree k=10; rewire each edge with prob p∈[0,1].
Outcome = characteristic path length L(p) and clustering C(p), each normalized to the p=0
lattice values (L0, C0). Mean over ≥10 seeds (use the largest connected component for L).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Endpoints: lattice has long L + high C; random has short L + low C. | L(0) ≫ L(1) (ratio ≥ 5×) AND C(0) ≫ C(1) (ratio ≥ 5×) |
| P2 | Small-world window exists. | ∃ p∈[0.001,0.1] with L(p)/L0 < 0.5 AND C(p)/C0 > 0.5 |
| P3 | L collapses faster than C. | the p at which L/L0 first drops below 0.5 is < the p at which C/C0 first drops below 0.5 |

**Discipline:** n, k, p-grid, seeds, both metrics FIXED before run; no tuning. Falsified → MISS.
