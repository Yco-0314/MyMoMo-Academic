# Independent Cascade + Influence Maximization — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Goldenberg-Libai-Muller 2001 / Kempe-Kleinberg-
Tardos 2003, not tuned. **Hybrid (agent activation states + edge-probability cascade + a
combinatorial optimization gate) — disclosed.** Verified.

**Model:** Independent Cascade — in the step right after a node becomes active it gets exactly ONE
independent attempt to activate each still-inactive out-neighbour, succeeding with edge probability
p (memoryless, single-shot per directed edge); runs synchronously until no new activations. On a
random graph G(n, ⟨k⟩=z) the control parameter is λ = p·z. ≥ many seeds/sims.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Percolation phase transition in single-seed cascade size. | uniform-p IC on G(n=1e4, z): mean reached fraction < 0.05 at λ=p·z=0.5; > 0.40 at λ=2.0; the transition crossing falls in λ ∈ [0.8, 1.3]. |
| P2 | Influence spread is SUBMODULAR (the discriminating gate). | for ≥200 random nested pairs A⊂B and v∉B (n=2000, z=8, p=0.1, ≥1e4 sims each), σ(A∪v)−σ(A) ≥ σ(B∪v)−σ(B) holds in ≥95% of pairs (diminishing returns). |
| P3 | Greedy attains the 1−1/e guarantee. | on a small instance (n≤200) with brute-force/CELF OPT for k=3 seeds, σ(greedy) ≥ 0.632·σ(OPT) (in practice ≥0.95·OPT), and σ(greedy) clearly exceeds a random k-set. |

**Discipline:** graph family, p/z grid, seed-set sizes, sim count FIXED + metrics (transition window,
submodularity fraction, 1−1/e ratio) locked; no tuning. Falsified → MISS. **Distinctness
(keep-with-gate):** nearest built are watts-cascade / granovetter-threshold / complex-contagion —
those are node-THRESHOLD (a node activates when a FRACTION of neighbours are active). IC is
edge-probability, memoryless single-shot per edge; submodularity + the 1−1/e greedy guarantee are
properties of IC that the deterministic threshold models do not have.
