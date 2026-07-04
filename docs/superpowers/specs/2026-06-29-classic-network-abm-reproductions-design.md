# Classic Network/Coordination ABM Reproductions (design)

**Date:** 2026-06-29
**Goal:** Reproduce three canonical "structure → collective outcome" ABMs with the
full coord-response discipline (lock predictions from the paper BEFORE running →
honest REPRO/MISS verdicts → adversarial review), as genuine agent-based models on
the neutral platform (`abm_auto._platform`). Targets: **Watts 2002** (global
cascades / cascade window), **Centola & Macy 2007** (complex contagion / weakness of
long ties), **Granovetter 1978** (threshold model / distribution sensitivity).

**Why these:** each makes a sharp, falsifiable claim that *network or distribution
structure governs a collective process* — the same question coord-response asked of
DOC A. They are fully specified in their papers (no proprietary data), so they are
honestly reproducible, and their counterintuitive claims (cascade window; clustering
beats randomness; mean-invariant outcome swing) are exactly where the discipline can
catch an artifact.

**Sources (verified, not from memory):**
- Watts, D.J. (2002) "A simple model of global cascades on random networks", PNAS
  99(9):5766–5771. Open: https://pmc.ncbi.nlm.nih.gov/articles/PMC122850/
- Centola, D. & Macy, M. (2007) "Complex Contagions and the Weakness of Long Ties",
  AJS 113(3):702–734. Model corroborated via Centola, Eguíluz & Macy (2007),
  Physica A 374:449–456 (https://ndg.asc.upenn.edu/wp-content/uploads/2016/04/Centola-et-al-2007-PA.pdf).
- Granovetter, M. (1978) "Threshold Models of Collective Behavior", AJS 83(6):1420–1443.

---

## Shared architecture

Each model is a genuine agent-based model on `abm_auto._platform` (`Agent`,
`AgentSet`, `StagedAgentModel`/`AgentModel`, `DataCollector`) — autonomous agents with
local threshold rules, a scheduler, a collector — mirroring the coord-response v3
pattern. Code lives in a small package `abm_auto/classics/` (one module per model);
runnable experiments in `examples/repro_<name>/run.py`; locked predictions, findings,
results, and L3 verdict bundles in `docs/studies/<name>/`; tests in `tests/classics/`.

Each study reuses the trust seam: `abm_auto.verification.gate.Verdict` (refutation
tier — "not refuted", never "verified") and `abm_auto.gis._repro_bundle` for the L3
provenanced bundle (hashes the locked-predictions + findings docs).

**Discipline (binding, identical to coord):** predictions are the PAPER's published
claims, locked + committed BEFORE running any reproduction. No parameter is tuned to
make a claim pass; a falsified claim is a valid result reported as MISS. Each model is
calibrated only to faithfulness to the paper's stated rules.

---

## Model 1 — Watts 2002 global cascades

**Rules (verified):** Erdős–Rényi random graph, n=10,000, mean degree z. Every node has
a uniform fixed threshold φ=0.18. A node adopts state 1 iff the **fraction** of its
neighbors in state 1 is ≥ φ (isolated/degree-0 nodes are vulnerable by convention).
One random node is seeded active; the system runs deterministically to a fixed point.
A **global cascade** = a final active set occupying a macroscopic fraction of the
network (the size distribution is bimodal — tiny local vs system-spanning — so a fixed
cutoff cleanly separates them; we use final active fraction ≥ 0.10). Analytic
**vulnerable vertex**: degree k ≤ K = ⌊1/φ⌋ = 5.

## Model 2 — Centola & Macy 2007 complex contagion

**Rules (verified):** Watts–Strogatz ring lattice, degree z=8, rewiring fraction
p∈[0,1] (p=0 clustered regular, p=1 randomized). As built, this uses standard networkx
WS rewiring (edge count / mean degree exactly preserved; individual node degrees
fluctuate — approximately, not strictly, degree-preserving). The strict degree-preserving
double-edge-swap variant was not used; the approximation does not affect the result. A node
adopts iff the **NUMBER** of active neighbors ≥ R (R=1 simple, R≥2 complex). Because a
complex contagion (R≥2) cannot start from a single node, seed a small contiguous
neighborhood (a seed node + enough of its lattice neighbors so propagation can begin).
Run to fixed point; measure final adoption fraction (and whether it spreads at all).

## Model 3 — Granovetter 1978 threshold model

**Rules (verified):** N=100 agents, fully mixed (each reads the GLOBAL count already
acting). Agent i acts iff (number already acting) ≥ its integer threshold. People with
lower thresholds act first, possibly cascading. Deterministic iteration to a fixed
point. (Faithful to the 1978 fully-mixed formulation; a network variant is out of
scope.)

---

## Per-study locked predictions

Written in full in each `docs/studies/<name>/PREDICTIONS-locked.md` (committed before
running). Summary of the falsifiable claims:

- **Watts:** (P1) cascade frequency over random seeds is **non-monotonic** in z — ~0 at
  low z, an interior peak, ~0 at high z (an interior cascade window); (P2) the lower
  boundary sits near the ER connectivity onset (z≈1); (P3) the upper boundary is a
  finite z (canonical ≈5.8 for φ=0.18) beyond which cascades vanish because vulnerable
  vertices (k≤5) stop percolating; (P4) cascade-size distribution is bimodal
  (local vs global).
- **Centola:** (P1, simple R=1) final adoption is ≥ on randomized (high p) than
  clustered (p=0); (P2, complex R=2) final adoption is **higher on clustered** (low p)
  than randomized — randomization impedes; (P3) the **sign** of the rewiring effect
  flips between R=1 and R=2.
- **Granovetter:** (P1) uniform thresholds {0,…,99} → equilibrium = **100** (all act);
  (P2) perturbed (remove the threshold-1 agent, add a second at threshold 2 → gap at 1)
  → equilibrium = **1**; (P3) the two distributions' **means are nearly identical**
  (49.5 vs 49.51) yet outcomes differ ~100× (the distribution-not-mean claim).

## Testing & scope

- Tests in `tests/classics/`: faithful-rule unit tests + a determinism test per model;
  a mechanism-functionality check per model before locking is unnecessary (the claims
  ARE the predictions — but the reproduction must not be tuned).
- Each reproduction reports what it measured vs the paper's claim, honestly. Exact
  numeric boundaries (e.g. Watts' upper z) are reported as measured and compared to the
  canonical value; the *qualitative* claim is the pass/fail clause.
- Scope: faithful reproductions of published synthetic models; no real-world data; the
  contribution is "does mymomo's harness + the discipline reproduce these landmark
  results, and would it catch an artifact if one appeared."
