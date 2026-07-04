# Classic ABM Reproductions — Batch 2 (design)

**Date:** 2026-06-29
**Goal:** Reproduce five more canonical ABMs with the full discipline (lock the paper's
claim BEFORE running → honest REPRO/MISS → adversarial review), as genuine agent-based
models on `abm_auto._platform`, mirroring batch 1 (Watts/Centola/Granovetter). Targets
chosen for mechanism diversity: **Schelling 1971** (segregation), **Axelrod 1997**
(culture), **Bass 1969** (diffusion), **Nowak & May 1992** (spatial cooperation),
**Deffuant 2000** (bounded-confidence opinion).

**Sources (verified via web search, not memory):**
- Schelling, T. (1971) "Dynamic Models of Segregation", J. Math. Sociol. 1:143–186.
- Axelrod, R. (1997) "The Dissemination of Culture", J. Conflict Resolution 41(2):203–226.
- Bass, F. (1969) "A New Product Growth for Model Consumer Durables", Mgmt Sci 15(5):215–227.
- Nowak, M. & May, R. (1992) "Evolutionary games and spatial chaos", Nature 359:826–829.
- Deffuant, Neau, Amblard, Weisbuch (2000) "Mixing beliefs among interacting agents",
  Adv. Complex Syst. 3:87–98.

## Shared architecture (same as batch 1)
Each model is genuine agent-based on `abm_auto._platform` (autonomous `Agent.step` +
`AgentSet`/`AgentModel`/`StagedAgentModel` + `DataCollector`). Spatial models (Schelling,
Axelrod, Nowak-May) hold a grid on the model; agents query their Moore neighborhood
locally. Code in `abm_auto/classics/`; runners in `examples/repro_<name>/run.py`; locked
predictions + findings + results + L3 bundles in `docs/studies/<name>/`; tests in
`tests/classics/`. Reuse `abm_auto.verification.gate.Verdict` (refutation tier) +
`abm_auto.repro_bundle`. **Discipline:** predictions = the paper's published claims,
locked + committed BEFORE running; no parameter tuned to pass; a falsified clause is a
valid MISS.

## Model 1 — Schelling 1971 segregation
Square grid (e.g. 50×50), two equal types, ~25–30% empty cells. An agent is unhappy if
the fraction of its (occupied) Moore-8 neighbors that share its type is < tolerance F
(F=1/3); unhappy agents move to a random empty cell. Iterate to a (near-)stable state.
Outcome = mean same-type-neighbor fraction (segregation index). **Claim:** a mild
preference (F=1/3) yields strong global segregation (segregation index ≫ F, ≫ the random
baseline ≈0.5). Lock: P1 final mean same-fraction ≥ 0.70; P2 final ≫ initial-random
baseline (≥ +0.15); P3 emergence — segregation far exceeds what any agent demands (final
≥ 2×F).

## Model 2 — Axelrod 1997 culture
L×L grid (e.g. 10×10). Each agent has F features, each taking one of q traits. Per step:
pick a random agent + a random neighbor; interact with probability = their cultural
similarity (fraction of shared features); on interaction, copy one differing feature's
trait. Run to an absorbing state (no further possible interactions). Outcome = number of
distinct stable cultural regions. **Claim:** #stable regions **increases with q**
(traits) and **decreases with F** (features). Lock: P1 #regions(q large, e.g. 15) >
#regions(q small, e.g. 5) at fixed F=5 (more traits → more polarization); P2 #regions(F
large) < #regions(F small) at fixed q; P3 monoculture limit — small q (e.g. q=2–5) → ~1
dominant region.

## Model 3 — Bass 1969 diffusion
N agents (e.g. 10,000), each non-adopter adopts each tick with probability p + q·F(t)
(F = current adopter fraction; p innovation, q imitation). **Claim:** cumulative
adoption is S-shaped; for q>p the per-tick adoption RATE is bell-shaped with an interior
peak at t* = ln(q/p)/(p+q). Lock (p=0.03, q=0.38, the meta-analytic defaults): P1
cumulative S-curve reaches ~full adoption; P2 the measured peak-adoption tick matches the
analytic t* = ln(q/p)/(p+q) within ±15%; P3 with q>p the rate curve has an interior peak
(bell), whereas with q=0 (pure innovation) adoption rate is monotonically decreasing (no
interior peak).

## Model 4 — Nowak & May 1992 spatial PD
Square lattice (e.g. 99×99), agents are AllC or AllD. Payoff vs each Moore-8 neighbor:
T=b (temptation, 1<b<2), R=1, P=0, S=0; each agent sums payoff over neighbors (self-play
convention per Nowak-May), then copies the strategy of the highest-scoring agent in its
neighborhood (incl. itself). Synchronous update. **Claim:** cooperation PERSISTS via
clusters on the lattice (1<b<2), whereas a well-mixed population of the same b collapses
to all-defect. Lock (b=1.85): P1 spatial stable cooperator fraction > 0.1 (persists, not
extinct); P2 well-mixed control (neighbors re-randomized each step) → cooperator fraction
→ ~0 (< 0.02); P3 the contrast — spatial cooperator fraction ≫ well-mixed.

## Model 5 — Deffuant 2000 bounded confidence
N agents (e.g. 1000), opinions ~ Uniform[0,1]. Per step: random pair; if |xi−xj| < ε,
each moves toward the other by μ·(difference) (μ=0.5). Run to convergence; count final
opinion clusters (groups within a small tolerance). **Claim:** #clusters ≈ ⌊1/(2ε)⌋;
consensus (1 cluster) for ε > 0.5; μ changes only convergence speed, not #clusters. Lock:
P1 #clusters(ε) ≈ ⌊1/(2ε)⌋ for ε ∈ {0.1, 0.15, 0.2, 0.3} (within ±1); P2 ε=0.5+ → 1
cluster (consensus); P3 μ ∈ {0.1, 0.5} gives the SAME #clusters at fixed ε (μ affects
time only).

## Testing & scope
`tests/classics/`: faithful-rule unit tests + determinism (seeded). Each reproduction
reports measured vs the paper's claim honestly; analytic anchors (Bass t*, Deffuant
1/(2ε), Nowak-May persistence) are the pass/fail clauses; qualitative claims
(Schelling/Axelrod direction) are the others. Faithful reproductions of published
synthetic models; no real-world data. Contribution: does the harness + discipline
reproduce these landmarks and would it flag an artifact.
