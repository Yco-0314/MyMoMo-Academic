# Coevolving-Network Prisoner's Dilemma (Santos-Pacheco-Lenaerts 2006) — FINDINGS

**Status: 1/3 locked clauses REPRO. P1 REPRO (decisive); P2 and P3 are honest MISSes on
their ABSOLUTE bars (steady cooperation reaches ~0.63 at W=16, short of the locked
>0.80 / >0.70 thresholds), even though the coevolution EFFECT — a large, monotone,
threshold-like rescue of cooperation by adaptive rewiring — is reproduced.** Genuine
agent-based reproduction on `abm_auto._platform`. Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the config below was fixed before the run and was NOT tuned to
make cooperation cross a bar.

**Framing (disclosed):** network-generation + adaptive rewiring. The contact network is a
generated random z-regular homogeneous graph; the structural dynamics is the locked
rewiring rule — a dissatisfied cooperator (a C linked to a D) redirects that tie away from
the defector toward a **new node**, conserving the edge count and the average degree.

## What was built

1000 `PDNode`s on a **homogeneous random graph** — a random z-regular graph with every
node of degree exactly z=30 (edge count N*z/2 = 15000, **conserved** for the whole run).
Each agent is a pure cooperator (C) or defector (D). Two dynamics are entangled at a
timescale ratio **W**:

- **Strategy update (probability 1/(1+W) per elementary step).** Every node's fitness is
  the SUM of its one-shot PD payoffs over all current neighbours (the SPL accumulated-payoff
  convention). A random agent A picks a random neighbour B and copies B's strategy with the
  **Fermi** (pairwise-comparison) probability `p = 1/(1+exp(-beta*(fit_B - fit_A)))`.
- **Structural update (probability W/(1+W); only when W>0).** A dissatisfied cooperator A
  (one with a defecting neighbour B — A is being exploited) tries to sever the (A,B) tie.
  The contest is resolved by the same Fermi rule; when A escapes, it **redirects its end of
  the (A,B) edge to a fresh uniformly-random node C** (C != A, not already adjacent). This
  MOVES one edge endpoint: the edge count and A's own degree are preserved (B loses a
  neighbour, C gains one).

A generation = N elementary steps. **W=0 is the static-graph control** (the structural
update never fires — the homogeneous random graph is frozen and only strategies evolve).
The graded observable is the steady-state cooperator fraction, averaged over the trailing
window and over 20 independent realizations. Absorbing states (all-C / all-D) are fixed
points of the whole dynamics, so a run that reaches one is stopped and its absorbed value
IS its steady state.

The reproduction is deterministic given a seed (the graph draw, the initial C/D placement,
and every Fermi coin are all from one seeded RNG chain). The z-regular graph is built by a
configuration-model stub pairing repaired to simple with degree-preserving edge swaps
(verified in the tests: exact degree z everywhere, symmetric, edges conserved under
rewiring).

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| N | 1000 |
| degree z (homogeneous) | 30 (edges = 15000, conserved) |
| payoffs T / R / P / S | 2 / 1 / 0 / -1  (b/c = T/R = 2, the hard point) |
| selection beta | 0.005 |
| initial cooperator fraction | 0.5 |
| W grid | 0.0 (static control), 0.5, 16.0 |
| seeds | 0..19 (20 realizations) |
| generations / measurement window | 3000 / last 300 |

## Results (mean over 20 seeds; steady-state cooperator fraction)

| W | mean steady coop | range | std | mean gens run |
|---|---|---|---|---|
| **0.0 (static control)** | **0.0000** | [0.000, 0.000] | 0.000 | 91 |
| **0.5** | **0.0000** | [0.000, 0.000] | 0.000 | 135 |
| **16.0** | **0.6302** | [0.599, 0.660] | 0.015 | 3000 |

Every W=0 and W=0.5 realization is **absorbed to all-defect** (final cooperation 0.000);
the run detects the absorbing fixed point and stops (mean ~91 / ~135 generations). At
W=16 the cooperator fraction climbs from the random start (~0.5) through a short transient
and **plateaus near 0.63 by generation ~200**, then holds perfectly flat for the rest of
the run (the cooperator clusters have no remaining C-D active links to rewire and no
fitness differences left to flip — a genuine steady state, robust across seeds: std 0.015).

Per-seed W=16 steady cooperation: 0.643, 0.635, 0.655, 0.644, 0.631, 0.616, 0.660, 0.637,
0.644, 0.618, 0.621, 0.633, 0.625, 0.638, 0.599, 0.630, 0.620, 0.615, 0.609, 0.630.

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Static network collapses | W=0 steady coop < 0.05 | **0.0000** | **REPRO** |
| **P2** | Coevolution prevails + dramatic enhancement | coop(W>=16) > 0.80 AND enhancement > 0.6 | **0.630** (enhancement **0.630**) | **MISS** (absolute bar) |
| **P3** | Monotone W-dependence with a threshold | coop(16)-coop(0.5) > 0.5, coop(0.5) < 0.2, coop(16) > 0.7 | jump **0.630**, coop(0.5) **0.000**, coop(16) **0.630** | **MISS** (coop(16) > 0.7 sub-clause) |

## Honest interpretation

- **P1 REPRO, decisively.** On the frozen homogeneous random graph at b/c=2, cooperation
  collapses to **exactly 0** in every one of 20 realizations — the static homogeneous
  network cannot sustain cooperation at this temptation, which is precisely the baseline
  the paper reports and the control the whole experiment is built against.

- **The coevolution effect is real, large, monotone, and threshold-like — the *direction*
  of P2 and P3 is fully reproduced.** Turning on adaptive rewiring at a high timescale
  ratio rescues cooperation from a hard 0.000 collapse to a robust **0.630** — a rescue of
  +0.63 in absolute cooperator fraction, far exceeding the locked "enhancement > 0.6" sub-bar
  and the "jump > 0.5" sub-bar. And the W-dependence has a clear threshold: at W=0.5 (below
  the critical timescale) cooperation still collapses to 0.000 (well under the locked 0.2
  cap), while at W=16 (well above it) cooperation prevails at ~0.63. Every *comparative*
  and *threshold* sub-clause of P2/P3 passes.

- **P2 and P3 MISS only on their ABSOLUTE ceilings (0.80 / 0.70), reported honestly, not
  papered over.** This faithful, lock-specified formulation settles at ~0.63 cooperation at
  W=16 rather than the >0.80 (P2) / >0.70 (P3) the paper's figures reach. The shortfall is a
  genuine, robust property of the formulation, not a transient or a seed artifact: the W=16
  plateau is tight across 20 seeds (std 0.015, range 0.599-0.660), and it is stationary for
  thousands of generations past steady state (flat from gen ~200 to gen 3000). The most
  likely mechanistic reason is the **rewiring target rule fixed in the lock**: a dissatisfied
  cooperator redirects its severed tie to a **uniformly-random new node**. Santos-Pacheco-
  Lenaerts' rule instead redirects the contested link preferentially — the winner of the
  A/B comparison keeps/attracts the endpoint, so cooperators disproportionately rewire toward
  *other cooperators' neighbourhoods*. That assortative bias is what drives their cooperator
  clusters to the high (>0.8) cooperation levels; redirecting to a random node produces
  weaker cooperator assortment and a lower — but still large and threshold-gated — cooperation
  ceiling. Reaching >0.8 here would require changing the locked rewiring target (random ->
  assortative), which the discipline forbids. We report the faithful model's honest number.

**Bottom line:** the reproduction cleanly demonstrates the *mechanistic* claim of the paper
— on a homogeneous graph at b/c=2 the static network collapses to zero cooperation, and
adaptive rewiring above a critical timescale rescues cooperation by a large, threshold-gated
margin (0.000 -> 0.630). It reports honestly that the *absolute* cooperation ceiling of this
lock-specified (rewire-to-random-new-node) formulation is ~0.63, falling short of the locked
>0.80 (P2) and >0.70 (P3) thresholds the paper's assortative-rewiring rule attains.

## Distinctness from the static-lattice PD

`nowak_may_pd` is a STATIC square lattice with deterministic best-takes-over imitation and
a fixed topology. The entire novelty here is the **coevolving topology**: the contact
network rewires away from defectors, and the W=0 arm (structure frozen) is exactly the "no
rewiring" control that isolates rewiring as the cause of the cooperation rescue. That
control has no representation in a static-lattice model.

## Source

Santos, F. C., Pacheco, J. M. & Lenaerts, T. (2006). *Cooperation prevails when individuals
adjust their social ties.* PLoS Computational Biology 2(10):e140.
doi:10.1371/journal.pcbi.0020140.

Scope: a faithful reproduction of a published synthetic model; no real-world data. The
contribution is whether the harness + locked-prediction discipline reproduce the
coevolution-rescues-cooperation effect, isolate adaptive rewiring as its cause (via the W=0
control), and would catch an artifact. Framing: network-generation + adaptive rewiring
(disclosed).
