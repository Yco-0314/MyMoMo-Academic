# Heider Social Balance / Antal-Krapivsky-Redner (2005) CTD — FINDINGS

**Status: 3/3 locked clauses REPRO.** Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the config below was fixed before the run and was NOT tuned to
make a clause pass.

## Framing disclosure (binding)

This is **signed-network dynamics (model-orchestrated triad/edge updates), NOT autonomous
agent-stepping.** The dynamical object is the *signed edge matrix* of a complete graph; the
model repeatedly picks an imbalanced triangle and flips one edge. The nodes are not platform
`Agent`s and there is no per-agent `step`. We ride the neutral platform
(`abm_auto._platform.AgentModel`) only for its seeded-RNG + deterministic run-loop floor. We
disclose this exactly as the Erdős–Rényi / Watts–Strogatz network-generation and the BTW
sandpile reproductions disclose that they are not agent-stepping ABMs. The lock-first +
honest-verdict + L3-bundle discipline applies in full.

## What was built

A complete signed graph on **N = 30** nodes. Every unordered pair `(i, j)` carries a sign
`s_ij ∈ {+1, −1}`, initialised independently `±1` with probability `1/2` (the only randomness
besides the triangle/tie-break draws). A triangle `(i, j, k)` is **balanced** iff the product
of its three edge signs is `+1` (0 or 2 negative edges), **imbalanced / frustrated** iff the
product is `−1` (1 or 3 negative edges). **Frustration (energy)** = the number of imbalanced
triangles (out of `C(30,3) = 4060`).

**Constrained triad dynamics (Antal–Krapivsky–Redner 2005), exactly:**

1. Pick a uniformly random **imbalanced** triangle `(i, j, k)`.
2. Flipping any one of its three edges balances *that* triangle, but each edge is shared with
   the other `N−2` triangles through it, so each candidate flip changes the **global**
   imbalanced-triangle count by some `Δ`. Compute `Δ` for each of the three edges (the
   incremental inner loop scans only the `N−2` triangles through the flipped edge).
3. Flip the edge whose `Δ` is **most negative** (greatest reduction in global frustration),
   breaking ties uniformly at random.
4. **AKR constraint:** accept the flip **only if `Δ ≤ 0`** (energy non-increasing). If all
   three candidate flips would *raise* global frustration, reject the move and draw another
   imbalanced triangle.

Run to absorption (no imbalanced triangle remains) or a generous step cap. Deterministic given
a seed. The incremental `Δ` is pinned equal to a brute-force whole-graph recount in the tests,
and the per-step energy is checked consistent with a fresh recount.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| N | 30 (complete signed graph) |
| edge init | each `±1` independently, prob 1/2 |
| update rule | CTD: most-negative-`Δ` flip of a random imbalanced triangle, accept iff `Δ ≤ 0` |
| seeds | 0…9 (10 seeds) |
| max steps | 200 000 (never approached; absorption hit in ~200 flips) |
| triangles | C(30,3) = 4060 |

## Results (10 seeds)

| Quantity | Value |
|---|---|
| seeds reaching a balanced absorbing state (energy 0) | **10 / 10** |
| seeds with a valid ≤2-faction partition | **10 / 10** |
| seeds with monotone non-increasing frustration | **10 / 10** |
| paradise (all +) vs two-faction | **0 paradise, 10 two-faction** |
| initial energy (imbalanced triangles) | 1980–2068 (≈ half of 4060, as expected for 50/50 random init) |
| final energy | 0 (all seeds) |
| accepted flips to absorption | 177–265 (median ≈ 217) |
| recovered faction sizes | (14,16) (17,13) (19,11) (17,13) (18,12) (17,13) (16,14) (15,15) (16,14) (21,9) |

**Energy-decrease curve (seed 0, 224 accepted flips):** 2068 → 1808 (25%) → 1580 (50%) →
1084 (75%) → 0 (100%). Frustration falls monotonically (never rises on any accepted flip) from
~2068 imbalanced triangles to exactly 0, accelerating toward the end as the graph collapses
into two factions and the last frustrated triangles are removed in cascades (the seed-0 tail
runs … 182, 158, 132, 110, 84, 56, 28, 0).

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Reaches a balanced state | ≥ 90% of seeds reach energy 0 (absorbing) | **100% (10/10)** | **REPRO** |
| **P2** | Final state is a valid ≤2-faction balance | every final state = paradise OR two factions (+ intra / − inter), verified | **100% (10/10)** | **REPRO** |
| **P3** | Frustration is non-increasing | imbalanced-triangle count never rises | **100% (10/10)** | **REPRO** |

## Honest interpretation

- **CTD drives the complete signed graph to structural balance every time.** From a random
  50/50 sign assignment (≈ 2000 of 4060 triangles frustrated), the AKR most-negative-`Δ`,
  accept-iff-`Δ ≤ 0` rule removes frustration monotonically and reaches a fully balanced
  absorbing state (energy 0) in all 10 seeds, in only ~200 accepted edge flips. This is the
  AKR result: on a complete graph the constrained dynamics cannot get stuck above balance.

- **The absorbing state is always the two-faction structure, never paradise.** All 10 seeds
  landed on a valid two-faction split — every within-faction edge `+`, every between-faction
  edge `−` — verified by recovering a globally consistent 2-colouring (P2). Faction sizes are
  near-even (the most lopsided was 21/9), and **no seed reached the all-positive "paradise."**
  This matches AKR: from an unbiased `ρ = 1/2` initial condition the complete-graph CTD
  overwhelmingly settles into two mutually-hostile cliques rather than universal friendship.
  P2 is satisfied (paradise is the allowed degenerate one-faction case; it simply never
  occurred here), so we report the two-faction outcome honestly rather than claiming paradise.

- **Frustration is monotonically non-increasing by construction, and we verified it.** The
  `Δ ≤ 0` acceptance guard makes every accepted flip non-increasing in the global
  imbalanced-triangle count; P3 checks the recorded energy series of every seed and finds it
  monotone non-increasing with zero exceptions. We did *not* observe a single rejection-trap in
  any seed (the energy reached 0 before any `max_rejections` cutoff mattered).

**Bottom line:** the reproduction cleanly demonstrates all three locked claims — the
constrained triad dynamics reach structural balance, the absorbing state is a valid ≤2-faction
balance (here always two factions, never paradise), and the frustration energy decreases
monotonically to zero — on a model-orchestrated signed network, disclosed as such.

## Source

Antal, T., Krapivsky, P. L. & Redner, S. (2005). *Dynamics of social balance on networks.*
Physical Review E 72(3):036121. doi:10.1103/PhysRevE.72.036121. Structural balance originates
with Heider, F. (1946). *Attitudes and cognitive organization.* J. Psychology 21:107–112.

Scope: a faithful reproduction of a published synthetic model; no real-world data. The
contribution is whether the harness + locked-prediction discipline reproduce the AKR drive to
structural balance (absorbing ≤2-faction state, monotone-decreasing frustration) and would
catch an artifact.
