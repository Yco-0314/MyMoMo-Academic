# Classic Reproductions — Batch 4 / Wave 1 (networks + epidemics)

**Date:** 2026-06-29
**Goal:** Five canonical complexity/network models, same discipline (lock the claim + the
GRADING METRIC BEFORE running → honest REPRO/MISS → adversarial review), on
`abm_auto._platform` where genuinely agent-based. Targets: **Erdős–Rényi giant
component**, **Barabási–Albert preferential attachment**, **Watts–Strogatz small-world**,
**SIS endemic threshold**, **Voter model fixation**.

**Honesty on "agent-based" (binds the FINDINGS):**
- SIS, Voter → genuine agent-stepping models (state agents step on the platform).
- Barabási–Albert → mildly agent-based (arriving NodeAgents make a preferential-attachment
  decision each tick).
- Erdős–Rényi, Watts–Strogatz → **network-GENERATION** models, NOT agent-stepping ABMs.
  Reproduced faithfully as network-science structural results; each FINDINGS must state
  this plainly (do not over-claim them as agent-based). The lock-first + honest-verdict +
  L3-bundle discipline still fully applies.

**Sources (verified via web search, not memory):**
- Erdős & Rényi (1960); giant component at mean degree ⟨k⟩=1, fraction S solves S=1−e^{−⟨k⟩S}.
- Barabási & Albert (1999) Science 286:509; P(k)~k^{−3}, exponent independent of m.
- Watts & Strogatz (1998) Nature 393:440; small-world window in rewiring p.
- SIS (Kermack-McKendrick / standard); R0=β/γ, endemic prevalence i*=1−1/R0 for R0>1.
- Voter model (Clifford-Sudbury 1973 / Holley-Liggett 1975); mean-field fixation prob =
  initial density.

## Shared architecture / discipline
Code in `abm_auto/classics/`, runners in `examples/repro_<name>/`, locked predictions +
findings + results + L3 bundles in `docs/studies/<name>/`, tests in `tests/classics/`.
Reuse `Verdict` + `abm_auto.repro_bundle`. Lock the metric; average over seeds + report
variance; no tuning; falsified clause = MISS.

## Model 1 — Erdős–Rényi giant component (network generation)
G(n,p), n=10,000, mean degree z=p(n−1) swept. Outcome = fraction of nodes in the largest
connected component. **Claim:** giant component emerges at z=1. Lock: P1 largest-component
fraction is small (< 0.05, O(log n / n)) for z=0.5 and large (> 0.4) for z=2.0; P2 sharp
rise across z=1 (transition); P3 measured giant fraction at z∈{1.5,2,3} matches the
self-consistent S=1−e^{−zS} within ±0.05.

## Model 2 — Barabási–Albert preferential attachment (mildly agent-based)
Start from a small connected seed; each tick a new NodeAgent arrives with m edges, each
attached to an existing node with probability ∝ its degree. Grow to N=10,000, m=3.
Outcome = degree distribution (CCDF / log-log slope). **Claim:** power-law P(k)~k^{−γ}
with γ≈3, independent of m. Lock: P1 the tail exponent fit γ ∈ [2.7, 3.3] (m=3); P2 γ is
~m-independent (γ at m=1,3,5 all in [2.5,3.5]); P3 heavy-tailed vs ER — BA max degree ≫ ER
max degree at the same mean degree.

## Model 3 — Watts–Strogatz small-world (network generation)
Ring lattice n=1000, each node degree k=10; rewire fraction p∈[0,1]. Outcome =
characteristic path length L(p) and clustering C(p), normalized to p=0. **Claim:** a
small-world window — at small p, L drops sharply toward random while C stays high. Lock:
P1 L(p=0) ≫ L(p=1) AND C(p=0) ≫ C(p=1) (the two endpoints); P2 at an intermediate p
(≈0.01–0.1) L/L0 < 0.5 WHILE C/C0 > 0.5 (the small-world regime exists); P3 L collapses
faster than C as p rises (L/L0 reaches half-drop at smaller p than C/C0).

## Model 4 — SIS endemic threshold (genuine agent-based)
Well-mixed N=10,000 state agents S/I. γ recovery prob/tick; β so R0=β/γ; each tick each S
infected w.p. 1−(1−β/N)^{I}, each I recovers w.p. γ but returns to S (no immunity). Seed a
few I. Run to a steady state; outcome = endemic prevalence (mean I/N over late ticks).
**Claim:** endemic threshold at R0=1; prevalence i*=1−1/R0 for R0>1. Lock: P1 prevalence
→0 (<0.02) for R0=0.8 and >0.3 for R0=2.0; P2 measured endemic prevalence at R0∈{1.5,2,3}
matches i*=1−1/R0 within ±0.05; P3 monotone in R0, ≈0 below 1.

## Model 5 — Voter model fixation (genuine agent-based)
Complete-graph / well-mixed N=1000 agents, binary opinion, initial up-fraction u. Each
step: a random agent copies a random other agent's opinion. Run to consensus (absorbing).
Outcome = which consensus + consensus time. **Claim:** fixation probability to the
all-up state = initial up-fraction u (mean-field). Lock: P1 every run reaches consensus
(absorbing, 100%); P2 P(fixation to all-up) ≈ u across u∈{0.2,0.5,0.8} (within ±0.07 over
≥200 runs each); P3 consensus is reached (no perpetual coexistence in finite well-mixed).

## Testing & scope
`tests/classics/`: faithful-rule unit tests + determinism. Analytic anchors (ER S
equation, SIS i*, Voter fixation=u, BA γ≈3) are pass/fail clauses. Faithful reproductions
of published synthetic models; no real-world data. ER/WS disclosed as network-generation
(not agent-stepping).
