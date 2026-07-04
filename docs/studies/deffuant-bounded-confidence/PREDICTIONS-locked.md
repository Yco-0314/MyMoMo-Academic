# Deffuant 2000 Bounded Confidence — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claims are Deffuant et al. (2000), not tuned.
Source: Adv. Complex Syst. 3:87–98.

**Model (faithful):** N agents (1000), opinions ~ Uniform[0,1]. Per step: pick a random
pair (i,j); if |x_i − x_j| < ε, update x_i += μ(x_j − x_i) and x_j += μ(x_i − x_j)
(μ=0.5). Run to convergence (no opinion moves beyond a tiny tolerance). Outcome = number
of final opinion clusters (groups within a small tolerance, e.g. 0.01).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | #clusters ≈ ⌊1/(2ε)⌋ across ε. | for ε ∈ {0.1,0.15,0.2,0.3}: \|#clusters − ⌊1/(2ε)⌋\| ≤ 1 each |
| P2 | Consensus (1 cluster) for large ε. | ε ≥ 0.5 → exactly 1 cluster |
| P3 | μ affects convergence TIME only, not #clusters. | #clusters(μ=0.1) == #clusters(μ=0.5) at fixed ε |

**Discipline:** N, ε-grid, μ values, cluster tolerance, seed-count fixed before run.
Report mean #clusters over seeds. A falsified clause → MISS.
