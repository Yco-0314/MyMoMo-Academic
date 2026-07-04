# Dynamic Social Impact Theory (Nowak, Szamrej & Latané 1990) — FINDINGS

**Status: 1/3 locked clauses REPRO. P2 (spatial self-organisation) REPRO; P1 (stable
nonzero minority) and P3 (minority survives in clusters) are honest MISSes — under the
EXACT locked specification the system collapses to consensus rather than preserving a
stable minority.** Genuine agent-based reproduction on `abm_auto._platform`. Predictions
were locked BEFORE running (`PREDICTIONS-locked.md`); the configuration below was fixed
before the run and was **NOT** tuned to rescue any clause. The locked document explicitly
flagged this as the honest-MISS risk; the risk materialised, and it is reported plainly.

## What was built

A 41×41 square lattice (N = 1681), one agent per site, **fixed in space** — clustering
happens by OPINION FLIPS, never by relocation (the contrast with Schelling, where agents
move and opinions are fixed). Each agent carries a binary opinion σ = ±1 and two i.i.d.
personal traits drawn once ~U[0,1] and **held fixed for the whole run**: persuasiveness
`p` (power to convert opponents) and supportiveness `s` (power to reinforce allies). The
total social impact on agent *i* is the persuasive impact from the OPPOSITE camp MINUS
the supportive impact from its OWN camp (Latané's distance-discounted social-impact law):

  I_i = Σ_j p_j/g(d_ij)·(1 − σ_iσ_j) − Σ_j s_j/g(d_ij)·(1 + σ_iσ_j),

with Euclidean distance d_ij, decay g(d) = 1 + d^α, **α = 2 (inverse-square)**, and the
self term excluded. Dynamics are **deterministic** (zero social temperature, external
field h = 0): agent *i* flips iff the opposing persuasive impact strictly exceeds the
supporting impact (I_i > 0). Sweeps run to a **fixed point** (a sweep with no flips). The
start is f₀ ≈ 0.5 (each opinion i.i.d. ±1).

**Efficiency / exactness.** The impact is all-pairs. The N×N weight matrix
`W_ij = 1/(1 + d_ij²)` (diagonal zeroed) is precomputed **once** (~22 MB) and every
sweep's impacts are exact vectorised products — **no cutoff radius, no truncation**. The
faithfulness tests check the vectorised functional against a from-scratch O(N²) double
loop on hand-built tiny lattices (exact match).

**Update rule (disclosed).** The locked spec permits *synchronous or sequential* sweeps
to a fixed point. We use **sequential** (asynchronous, fixed row-major visiting order),
maintained with an O(N) incremental field update that is verified bit-exact against a
from-scratch recompute. Sequential is the faithful choice: deterministic asynchronous
dynamics provably reach a **true** fixed point, whereas the synchronous (parallel) update
can leave a 2-cycle that never freezes (the classic parallel-update artifact — we
confirmed seed 3 oscillates forever under synchronous update). The two schemes give the
**same scientific verdict** here (see below); sequential just removes the 2-cycle
artifact.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| lattice L | 41 (N = 1681), hard edges |
| decay exponent α | 2.0 (inverse-square) |
| start f₀ | 0.5 (i.i.d. ±1) |
| traits p, s | i.i.d. ~U[0,1], fixed |
| update | sequential (asynchronous), exact all-pairs |
| seeds | 0…49 (50 seeds) |
| max sweeps | 200 |
| minority-cluster threshold | 5 sites |

## Results (50 seeds, sequential)

| Quantity | Value |
|---|---|
| mean final minority fraction | **0.045** (range [0.000, 0.488]) |
| seeds reaching FULL consensus (minority → 0) | **45 / 50** |
| mean same-opinion bond fraction at freeze | **0.998** |
| mean largest-majority-cluster fraction | 0.951 (min 0.341) |
| minority-cluster (≥5) survival fraction | **0.10** (5 / 50 seeds) |

The dynamics show two regimes and **neither** is the predicted stable small minority:

1. **Consensus (45/50 seeds).** Starting from a near-balanced split, the slightly larger
   majority's persuasive field sweeps the whole lattice; the minority is fully eliminated
   (minority fraction → 0, bond fraction → 1.0) within ≈3–20 sweeps. Full consensus is
   always a fixed point: with all opinions equal there is zero persuasion and pure
   support, so every impact is ≤ 0 and nobody flips (proved in the tests).

2. **Two-domain non-freezing split (5/50 seeds).** The remaining seeds (16, 18, 21, 25,
   49) partition the lattice into **two large contiguous halves** (a single minority
   cluster of ~700–820 sites, minority fraction ~0.42–0.49) whose domain wall keeps
   slowly migrating — these states do **not** freeze even after 2000 sweeps. They are
   near-balanced boundary-drift states, not the paper's stable small minority enclaves.

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Stable nonzero minority | mean f_min ∈ [0.08, 0.45] | **0.045** | **MISS** |
| **P2** | Spatial self-organisation | mean bond fraction ≥ 0.75 | **0.998** | **REPRO** |
| **P3** | Minority survives in clusters | maj cluster ≥ 0.55·N AND minority ≥5 survives in ≥80% of seeds | maj 0.951 ✓ but survival **0.10** | **MISS** |

## Honest interpretation

- **P2 REPRO, but read it carefully.** The same-opinion bond fraction does rise from
  ≈0.49 (random start) to ≈0.998 — opinions are emphatically *not* left scattered; they
  self-organise into contiguous regions. The mechanistic claim "social impact produces
  spatial coherence" reproduces. The caveat is that the coherence here is the *trivial*
  high-bond state of a (near-)consensus or two-big-domains lattice, not coherence wrapped
  around a *surviving* minority. P2 passes on its own terms; it does not rescue P1/P3.

- **P1 MISS (mean minority 0.045 vs the [0.08, 0.45] band).** This is the central
  prediction and it is falsified under the exact locked functional. The reproduction does
  **not** preserve a stable minority — 45 of 50 seeds reach full consensus. The cause is
  mechanistic and was disclosed as the honest-MISS risk: with **α = 2 (inverse-square)**
  on a 41×41 lattice the influence is too **global**. Each agent feels a total incoming
  weight ≈ 15.7, dominated by the long-range tail, so it responds to the *global* opinion
  balance rather than only its neighbourhood. A globally-felt field lets the
  marginally-larger majority overwhelm local minority support everywhere, and minority
  domains cannot anchor. Minority survival in this model is a phenomenon of
  *sufficiently local* influence (stronger distance decay / shorter range) so that the
  interior support of a cluster beats the persuasion crossing its boundary; the locked
  α = 2 sits on the wrong side of that line. The locked PREDICTIONS doc named exactly
  this — "minority survival is a ZERO-NOISE, finite-size phenomenon … the locked run is
  h = 0 on a finite lattice" — and we report the falsification rather than retune α or
  the traits to pass.

- **P3 MISS.** The majority-cluster half of P3 passes on average (the majority is a single
  giant cluster, 0.951·N), but the load-bearing half — a minority cluster of ≥5 sites
  surviving in ≥80% of seeds — fails decisively: only **10%** of seeds retain any minority
  cluster of size ≥5, and those are the two-domain non-freezing states (one ~700-site
  half-lattice), not the small persistent enclaves the clause describes. P3 is a MISS.

- **Not a synchronous-update artifact.** We checked the synchronous (parallel) scheme too:
  mean minority 0.057, bond 0.998, survival 0.14 — the same scientific picture (consensus
  dominates). The synchronous scheme additionally leaves some seeds in a perpetual 2-cycle;
  sequential avoids that, which is why it is the reported run. Either way P1/P3 MISS.

**Bottom line:** the harness + locked-prediction discipline did its job — it reproduced
the *spatial self-organisation* claim (P2) and **honestly falsified** the *minority
survival* claim (P1, P3) under the exact locked inverse-square, U[0,1]-trait, h = 0
specification, reporting full consensus rather than a tuned minority. The MISS is
mechanistically understood (influence too global at α = 2 on this lattice) and was the
pre-registered honest-MISS risk; no parameter was changed to manufacture a pass.

## Source

Nowak, A., Szamrej, J. & Latané, B. (1990). *From private attitudes to public opinion:
A dynamic theory of social impact.* Psychological Review 97(3):362–376.
doi:10.1037/0033-295X.97.3.362. Impact functional as in Castellano, Fortunato & Loreto
(2009), *Statistical physics of social dynamics*, Rev. Mod. Phys. 81:591–646, Eq. 16.
doi:10.1103/RevModPhys.81.591.

Scope: a faithful reproduction of a published synthetic model; no real-world data. The
contribution is whether the harness reproduces minority survival + spatial
self-organisation under the EXACT locked specification, and would honestly report a
falsified clause — which is what happened.
