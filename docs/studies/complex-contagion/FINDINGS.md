# Centola & Macy 2007 Complex Contagion — FINDINGS (agent-based reproduction)

**Status:** Run complete against the pre-registered `PREDICTIONS-locked.md` (locked
2026-06-29 BEFORE this run). Verdicts are reported against their LITERAL locked clauses,
honestly (REPRO / MISS). No model parameter, the p-grid, n, the seed count, or the
seeding scheme was changed after seeing outcomes. The model is a genuine agent-based
model on `abm_auto._platform` (autonomous `ContagionAgent` with a local NUMBER-threshold
`step`, an `AgentSet` scheduler, a `DataCollector`) — not a god-loop.

**Source:** Centola, D. & Macy, M. (2007) "Complex Contagions and the Weakness of Long
Ties", AJS 113(3):702–734 (doi:10.1086/521848); model corroborated via Centola, Eguíluz
& Macy (2007), Physica A 374:449–456.

**Config (FIXED before the run):** Watts–Strogatz ring lattice, n=1000, degree z=8,
rewiring grid p∈{0, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0}, R∈{1, 2}, 20 independent graphs/seeds
per (R,p) (seeds 0–19, the SAME seed sequence for every cell so comparisons are paired).
Seeding scheme = **contiguous neighborhood**: node 0 plus its ±2 nearest ring-neighbors
(= 5 seed nodes), IDENTICAL for R=1 and R=2, never enlarged to force spread. Adoption is
synchronous (every agent reads the tick-start activation snapshot, so the fixed point is
order-independent) and irreversible. Run to a fixed point (no new adoptions in a tick);
outcome = final adoption fraction.

## TL;DR

The counterintuitive headline reproduces cleanly. **A complex contagion (R=2) spreads
fully on the clustered ring (p=0) and dies on the randomized graph (p=1)**, while a
simple contagion (R=1) saturates everywhere regardless of randomization. The sign of the
rewiring effect on **final adoption** flips between R=1 and R=2 — satisfying the locked
crossover clause. **Honest nuance (adversarial review 2026-06-29):** the measured flip is
**null(0) vs negative(−1)**, not Centola & Macy's *positive*-vs-negative crossover —
because R=1 saturates to 1.0 at every p, the "randomization helps simple contagion" effect
shows up here in **speed** (≈126 → 5 steps from p=0 → 1), not in final adoption fraction.
The decisive, faithful part of the result is **P2** (complex contagion: clustering beats
randomness, margin 0.99). **All three locked clauses REPRO (3/3).**

## Adoption(R, p) — mean final adoption fraction (n=1000, 20 seeds)

| R \ p | 0.0 | 0.1 | 0.2 | 0.4 | 0.6 | 0.8 | 1.0 |
|---|---|---|---|---|---|---|---|
| **R=1 (simple)**  | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **R=2 (complex)** | 1.0000 | 1.0000 | 1.0000 | 0.8515 | 0.1578 | 0.0069 | 0.0065 |

- **R=1 curve:** flat at 1.0 across all p. A simple contagion needs only ONE active
  neighbor, so it percolates the ring lattice to saturation whether clustered or
  randomized. (It spreads *faster* as p rises — mean steps-to-fixed-point fall from 126
  at p=0 to 5 at p=1 — but the final fraction is invariant at this n/z.)
- **R=2 curve:** flat at 1.0 for p≤0.2, then a sharp collapse — 0.85 at p=0.4, 0.16 at
  p=0.6, ≈0.006 at p≥0.8. Randomization destroys the redundant local ties a complex
  contagion needs to reach the R=2 threshold. The "weakness of long ties."
- **Crossover** between R=1 (flat) and R=2 (collapsing) is unmistakable around p≈0.4–0.6.

## Verdict table (literal locked clauses)

| Prediction | Verdict | salient | honest reading |
|---|---|---|---|
| **P1** — simple R=1: adoption(p=1) ≥ adoption(p=0) | **REPRO** | Δ = 1.0000 − 1.0000 = 0.0 (≥0 ✓) | Holds, but by **saturation**, not by a strict gain — R=1 already reaches everyone at p=0, so randomization cannot *help* a fraction that is already 1.0 (see caveat 1). |
| **P2** — complex R=2: adoption(p=0) > adoption(p=1) | **REPRO** | 1.0000 > 0.0065, margin **0.9936** | The headline result. Clustering helps; randomization impedes, decisively. |
| **P3** — sign[adoption(p=1)−adoption(p=0)] flips R=1↔R=2 | **REPRO** | sign(R=1)=0 ≠ sign(R=2)=−1 | Crossover present: the rewiring effect is null/flat for R=1 and strongly negative for R=2. |

**3/3 testable clauses REPRO. The crossover appeared.**

## Honest caveats

1. **P1 holds by saturation, not by a strict improvement.** The locked clause is the
   inequality `adoption(p=1) ≥ adoption(p=0)`, which is satisfied (1.0 ≥ 1.0). But on
   this n=1000, z=8 ring a simple contagion already reaches 100% at p=0, so there is no
   headroom for randomization to *raise* final adoption. Centola & Macy's broader claim
   that "randomization helps simple contagion" shows up here in **speed**
   (steps-to-fixed-point fall ~25× from p=0 to p=1), not in the final fraction. The
   locked clause was deliberately written as "≥ (or spread speed)"; the final-fraction
   form passes trivially and the speed form is corroborated. This is reported, not
   hidden: P1 is the weakest of the three clauses on this substrate.

2. **The R=2 transition zone (p≈0.4) is bimodal across seeds, not a smooth mean.** At
   p=0.4 the mean 0.8515 is an average of full-spread runs (max 1.0) and near-total stall
   runs (min 0.009): the contagion either catches and fills the network or fizzles at the
   seed, depending on the random rewiring of that particular graph. The mean is a
   legitimate ensemble summary but should not be read as "85% of nodes typically adopt";
   per-seed values are in `results.json`. This bimodality is itself consistent with the
   complex-contagion picture (a percolation-like threshold in p).

3. **WS rewiring is only approximately degree-preserving.** We use networkx
   `watts_strogatz_graph(n, k=8, p, seed)`, the standard WS construction. Rewiring moves
   one endpoint of an edge, so individual node degrees fluctuate around 8 while the EDGE
   COUNT (hence mean degree z=8) is exactly preserved. The locked predictions and the
   design spec both explicitly accept this approximation; a strictly degree-preserving
   double-edge-swap rewiring was not used. The NUMBER-threshold rule (not fraction) makes
   the model mildly sensitive to the degree fluctuations a high-p graph introduces, which
   is part of why R=2 collapses — this is faithful to, not an artifact distinct from, the
   "long ties are weak" mechanism.

4. **Seeding is load-bearing and was held minimal + identical across p.** A complex
   contagion cannot ignite from a single node; the 5-node contiguous seed is the minimum
   that lets R=2 start on the clustered ring, and it is reused verbatim for R=1 and for
   every p. We did NOT enlarge the seed to rescue spread at high p — the collapse of R=2
   at p≥0.6 is a real finding about the substrate, not a seeding artifact. (Unit test
   `test_R2_complex_cannot_ignite_from_single_seed_on_ring` pins the single-seed failure
   mode; `test_R2_complex_ignites_from_contiguous_seed_on_z8_lattice` pins ignition.)

5. **Nothing failed to reproduce.** All three clauses passed. The only honest softening
   is caveat 1 (P1 is saturated, so its "≥" is trivially true on the final-fraction
   metric and meaningful only on the speed metric).

6. **Bundle `code_commit` provenance.** `verdict-bundle.json`'s `code_commit` is HEAD at
   run-time (the bundle is committed together with the code, so it points to the parent
   commit). Reproduction integrity is anchored on the content-addressed **sha256** of the
   docs/data artifacts (all `replay: strong`, verified MATCH), not the commit pointer.

## What this demonstrates

The harness + lock-before-run + no-tuning discipline reproduces the landmark
complex-contagion result and its counterintuitive crossover on a genuine agent-based
model. The decisive, falsifiable claim (P2: clustering beats randomness for a complex
contagion, margin 0.99) is unambiguous; the weaker claim (P1) is honestly flagged as
holding only by saturation on the final-fraction metric. Had the model been miswired
(e.g. a FRACTION threshold instead of a NUMBER threshold, which would make R=2 behave
like R=1), P2/P3 would have been MISS — the discipline would have caught it.
