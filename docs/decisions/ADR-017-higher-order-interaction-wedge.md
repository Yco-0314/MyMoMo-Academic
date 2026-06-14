# ADR-017: Higher-order interaction wedge — group operators + a verifiable flatten-to-pairwise check

**Status**: Proposed (design draft — no code). Records the interface decisions so implementation and reviews share one shape, same discipline as [ADR-014](ADR-014-coverage-gate.md)/[ADR-015](ADR-015-synthesis-phase.md). Grounded in a 10-paper literature scan (below).
**Date**: 2026-06-09
**Deciders**: yco + Claude (Opus 4.8)
**Related**: [ADR-007](ADR-007-schema-driven-codegen.md) (`TopologySpec` + operators this extends), [ADR-014](ADR-014-coverage-gate.md) (coverage by contract + verifiability — the ΔΦ check is a new tier-3 oracle), [ADR-016](ADR-016-codegen-fidelity-wall.md) (the flatten is the fidelity wall on a new axis), [ADR-013](ADR-013-gate-harness.md) (anti-fabrication: the flatten verdict is an empirical measurement, not the generator's word).

---

## Context

The whole runtime is **pairwise**: `TopologySpec` builds a `Network` of two-node
edges; `PayoffGame` is a **two-player** game; contagion is node-to-node SIR. A real
and growing slice of the corpus is **higher-order** — interactions binding *groups*
of agents at once: public-goods / collective-risk games (n-player), simplicial /
complex contagion (a group threshold, not a sum of pairwise exposures), hypergraph
diffusion. These have a property pairwise *dynamics* cannot reproduce: **group
nonlinearity** — payoff / infection is a nonlinear function of how many group
members cooperate / are infected, producing discontinuous transitions, bistability,
and cooperation regimes absent pairwise.

When extraction meets such a paper it does the ADR-016 thing on a new axis: it
**flattens** the group mechanism onto the pairwise stack (a 2-player game, a
node-to-node SIR) and silently drops the group nonlinearity. The flattened model is
covered, buildable, and runs — the exact silent-false-pass shape ADR-016 is about,
one axis over (network *order*).

### What the literature scan settled (10 papers)

The decisive reframing comes from **Peixoto, Peel, Gross & De Domenico, "Graphs are
maximally expressive for higher-order interactions"** (arXiv:2602.16937, 2026):
a graph (with a factor / bipartite encoding — a node per hyperedge) can **faithfully
represent any higher-order interaction structure**. So the wedge is **not** "pairwise
can't express groups" (it can). The open question is purely **dynamical**: does the
*dynamics* on the naive pairwise projection reproduce the group dynamics? That is
exactly what **Xie et al., "Transformability…"** (Comm Phys 2026, arXiv:2501.16016)
measures: `ΔΦ* = ΔΦ₁ + ΔΦ₂` decomposes the dynamical gap between a higher-order
process and its pairwise projection into a **dynamical** part (group nonlinearity,
metric `Q`) and a **structural** part (multi-edges from the projection), via an
entropy order parameter `Φ(t) = −Σ pₓ log₂ pₓ`; the flatten is faithful iff
`ΔΦ* → 0` (`β_δ → 0`, `Q → Q*`).

The structural half (`ΔΦ₂`) now has rigorous footing: a cluster of papers gives
**metrics and stability/Lipschitz bounds for hypergraph→graph "graphification"** —
**Needham & Semrad, "Stability of Hypergraph Invariants and Transformations"**
(arXiv:2412.02020 = FoDS 2026 10.3934/fods.2026008), **Chowdhury et al., "Hypergraph
Co-Optimal Transport"** (arXiv:2112.03904), and **Green/Joslyn et al., "Topological
Structures of the Orders of Hypergraphs"** (arXiv:2504.11760, the
hypergraph ≅ formal-context ≅ Dowker-complex correspondence). Implementation
reference for the topology + any learned hyperedge structure: the open-access book
**Dai & Gao, *Hypergraph Computation*** (Springer 2023, 978-981-99-0185-2) and
**Zhou et al., "Totally Dynamic Hypergraph Neural Networks"** (IJCAI 2023). The two
foundational reviews (**Majhi/Perc/Ghosh** RSIF 2022 arXiv:2203.06601; **Battiston
et al.** Nat Rev Phys 2025 arXiv:2510.05253) are the menu of group dynamics and
their operators. *(Marginal/off-topic, recorded for honesty: Haynes "Program
Hypergraph" arXiv:2603.17627 — hypergraph compiler IR, only an analogy to our
codegen's invariant-preservation; engrXiv "SuperHypergraphs" #4769 — fringe;
Rossmann & Voll arXiv:1908.09589 — pure algebra (ask zeta functions), unrelated.)*

**Net**: structural representability is settled (Peixoto — a graph can hold it); the
gate's only real job on this axis is **dynamical faithfulness**, and there is a
measured criterion for it (Xie ΔΦ\*) plus rigorous structural-loss tooling
(Needham-Semrad / HyperCOT) for its `ΔΦ₂` term. This is ADR-014's move — "is it
buildable? → can we *verify* the build?" — applied to order: **"is the flatten
dynamically faithful? → can we *measure* ΔΦ\* and check it's ~0?"**

## Decision

Add a **higher-order interaction wedge**: a topology kind, two group operators, and
— the load-bearing part — **wire the ΔΦ\* criterion into the Coverage Gate as the
tier-3 verifiability oracle for "flatten-to-pairwise".** No operator trusts the
LLM's word; the flatten verdict is an empirical ΔΦ\* measurement (ADR-013 lineage).

### 1. Higher-order topology (extends `TopologySpec`)

- `TopologySpec.type ∈ {"hypergraph", "simplicial_complex"}` with params for the
  hyperedge-size distribution (or a clique-lift of a pairwise graph + a fraction ρ
  of triangles promoted to true 2-simplices, the standard construction).
- Runtime `HigherOrderTopology`: the **factor/bipartite encoding** Peixoto endorses
  — a group node per hyperedge, giving each agent its hyperedges and each hyperedge
  its members. The environment iterates **groups**, not pairs. (Because this is a
  graph encoding, it composes with the existing `Network` machinery and the ADR-016
  interaction-completeness gate unchanged.)

### 2. Group-interaction operators (extend the operator library)

Same library/strategy split as W2/W3/W4 — verified library + self_test + two
cross-domain adapters + a coverage contract + deterministic codegen emission. Both
consume a hyperedge (a group), not a pair:

- **`PublicGoodsGame`** — n-player. Cooperators pay cost `c` into a pot multiplied
  by synergy `r`, split among all members; defectors free-ride. Payoff is
  **nonlinear in the cooperator count** — the property a pairwise `PayoffGame`
  cannot reproduce. self_test: known group → known payoffs; cooperation rises with
  `r` (the reviews' signature result). Adapters: collective-risk dilemma,
  common-pool-resource harvest.
- **`SimplicialContagion`** — node S/I states spread through hyperedges with a
  pairwise rate `β₁` AND a group rate `β_δ` (the Iacopini model). self_test:
  reproduces the discontinuous transition + bistability a pairwise SIR cannot.
  Adapters: complex social contagion (adoption needs k peers in a group), rumor.

These compose with existing operators (a `PublicGoodsGame` under `MoranProcess`
turnover is the reviews' evolutionary-games-on-hypergraphs setting).

### 3. The ΔΦ\* flatten-faithfulness check (the new Coverage-Gate oracle)

When a mechanism is group-interaction but the design **projects it onto pairwise**,
the Coverage Gate decides whether that projection is dynamically faithful. A
**tier-3 verifiability oracle** (ADR-014 §4), the higher-order analogue of the
Kalman / tabular-Q self-tests:

- **Oracle (library-owned, not generated — the ADR-015 trust law)**: simulate (or
  mean-field) BOTH the declared higher-order mechanism and its pairwise projection
  on a small fixture, measure `Φ(t)`, compute `ΔΦ* = ΔΦ₁ + ΔΦ₂` (Xie). The `ΔΦ₂`
  structural term can be bounded with the graphification-stability results
  (Needham-Semrad / HyperCOT) rather than only simulated.
- **Verdict**: `ΔΦ* ≤ ε` → the flatten is faithful → **PASS as pairwise** (emit the
  cheaper pairwise model honestly). `ΔΦ* > ε` → **HALT**, naming the missing
  capability ("needs `PublicGoodsGame` / `SimplicialContagion`: group nonlinearity
  Q=… is not reducible") — demand-driven, like every Coverage-Gate halt.

### The unifying principle

**Network order is a coverage/fidelity dimension — and a purely DYNAMICAL one.**
Peixoto settles that a graph can always *represent* the group structure; the only
question is whether the projected *dynamics* survive, and Xie's ΔΦ\* is the measured
answer. Judge the flatten by a measured order parameter, never by the LLM's "pairwise
is close enough" — the same anti-fabrication law as ADR-013/014/016, now on order.

## Test surface (fixtures, ADR-014 style)

| fixture | mechanism | expected | why |
|---|---|---|---|
| 2-player Hawk-Dove | pairwise game | **PASS (pairwise)** | genuinely pairwise; no group term |
| public-goods game, high synergy r | strong group nonlinearity | **HALT → PublicGoodsGame** | ΔΦ\* ≫ ε; flatten drops cooperation regime |
| public-goods game, r→0 (additive) | ~linear in cooperators | **PASS (pairwise)** | ΔΦ\*→0; faithful (Xie β_δ→0, Q→Q*) |
| simplicial contagion, supralinear β_δ | group threshold | **HALT → SimplicialContagion** | discontinuous/bistable; pairwise SIR can't |
| simplicial contagion, β_δ→0 | ~pairwise exposure | **PASS (pairwise)** | reduces to SIR; ΔΦ\*→0 |

Plus each operator's own self_test (known group → known payoff/spread) and two
cross-domain adapters (W2/W3/W4 parity — "two adapters = a real seam").

## Consequences

- **A real new wedge**, demand-driven: operators are built only when the gate HALTs
  naming them (ADR-014), and the ΔΦ\* check is what generates that demand signal
  honestly instead of letting a flatten pass silently.
- **Leverage**: one library owns "is this group mechanism reducible to pairwise?",
  with a *measured* answer — locality for a question that currently lives nowhere.
- Composes with the existing stack (group games under Moran turnover; the
  factor-graph topology + the ADR-016 interaction-completeness gate, unchanged).

## Honest residual / open questions

- **Peixoto reframes the value proposition.** Because a graph is maximally
  expressive, a higher-order operator is a **faithfulness + ergonomics** choice (a
  verified, group-native primitive the LLM can't mis-flatten), NOT an expressiveness
  necessity. The wedge's worth rests on the ΔΦ\* check catching unfaithful flattens
  and on the operator being easier-to-get-right than a hand-rolled factor-graph
  encoding — both empirical, to be shown on real models, not assumed.
- **ΔΦ\* needs the design to expose the group structure** (β_δ, the projection) for
  the oracle. Extraction must field a higher-order slot; until it does, the gate can
  only catch flattens it can reconstruct. First implementation surface.
- **Xie validated ΔΦ\* on contagion + opinion dynamics.** Group GAMES and
  synchronization may need their own faithfulness metric (a payoff-distribution or
  order-parameter distance), not the SI/opinion entropy. The *principle* (measure
  the order-axis loss) generalizes; the *metric* may be per-dynamics-class.
- **Cost**: simulating both sides is heavier than a Kalman self-test; the mean-field
  ΔΦ\* (Xie's effective-degree approximation) + the graphification Lipschitz bounds
  (Needham-Semrad) are the tractable path.
- Build order (ADR-013 discipline): `HigherOrderTopology` + `PublicGoodsGame` +
  its self_test + the ΔΦ\* oracle on the two public-goods fixtures FIRST;
  `SimplicialContagion` + the extraction slot second.

## Status note

Design only, no code — same discipline as ADR-013/014/015. This ADR records the
shape; whether to BUILD it stays demand-driven (build when the Coverage Gate HALTs
on a real group-interaction paper and names the operator).
