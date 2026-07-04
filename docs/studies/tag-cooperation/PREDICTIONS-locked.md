# Tag-Based Cooperation (Riolo-Cohen-Axelrod 2001) — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Riolo, Cohen & Axelrod 2001 (Nature 414:441),
not tuned. Genuine agent-based. Verified; gate-checked.

**Model:** N=100 agents, each with a heritable continuous tag τ ∈ [0,1] and heritable tolerance T ≥ 0.
Each generation each agent is a potential DONOR to P=3 randomly-chosen partners (with replacement); it
donates (cost c=0.1 to donor, benefit b=1.0 to recipient) iff |τ_partner − τ_self| ≤ T_self. Fitness =
accumulated payoff; reproduce by tournament (compare to one random other, copy the fitter) with mutation
(τ Gaussian, T Gaussian, rate 0.1, σ=0.01, T truncated at 0). Initial τ, T ~ U[0,1]. 30,000 generations,
≥10 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Tag-similarity donation sustains substantial cooperation (no reciprocity). | at P=3: mean donation rate over gen 100–30,000 ∈ [0.55, 0.85] (paper 0.736). *WIDE band (large wave variance); MUST be at P=3 — at P≤2 the faithful rate is ~0.02–0.04.* |
| P2 | A dominant tag cluster forms. | time-averaged modal-tag-cluster share (agents with \|τ − modal τ\| ≤ 0.01, post-transient gen>100) ≥ 0.60 (paper 0.79 onset → 0.97 mid-life; averaging over birth/growth/collapse ⇒ 0.60 is the faithful bar). |
| P3 | Cooperation is INTERMITTENT (waves of tolerance), not a plateau. | over gen 100–30,000: within-run coefficient of variation (sd/mean) of the donation rate ≥ 0.10 AND ≥1 crash-and-recover event (series drops below 0.5×running-mean then returns above 0.9×running-mean) in a majority of seeds. *No fixed wave count/period.* |

**Discipline:** N, c, b, P, mutation, generations, seeds FIXED + metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep):** ethnocentrism (Hammond-Axelrod) is tag-based but SPATIAL (lattice, local
interaction, 4 tag-strategies); Riolo-Cohen-Axelrod is WELL-MIXED (random pairing, no space), continuous
tag + tolerance, and its signature is the WAVES of tolerance-drift-then-invasion — absent from the spatial
ethnocentrism model.
