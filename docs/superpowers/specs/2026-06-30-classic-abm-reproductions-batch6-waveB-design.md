# Classic Reproductions — Batch 6 / Wave B (SOC / social) — reaches 50 total

**Date:** 2026-06-30. Same discipline (lock claim + GRADING METRIC before run → genuine
agent-based on `abm_auto._platform` → honest REPRO/MISS → adversarial review). Targets:
**Olami-Feder-Christensen earthquakes**, **Axelrod 1986 norms/metanorms**, **Heider social
balance**, **seceder model**, **Miller-Page standing ovation**. This wave brings the suite to
**50 reproductions**.

**Honesty on framing:** Axelrod-norms, seceder, standing-ovation → genuine agent-stepping.
**OFC → driven-threshold cellular automaton (SOC), NOT autonomous-agent-stepping** — disclosed.
Heider balance → a signed-network dynamics (nodes hold relations; link/triad updates are
model-orchestrated) — disclosed.

**Sources (verified via web, not memory):**
- Olami, Feder & Christensen (1992): non-conservative SOC earthquake model; conservation α;
  Gutenberg-Richter power-law event sizes; criticality strongest near-conservative.
- Axelrod (1986) APSR 80:1095: norms game; boldness/vengefulness; metanorms (punish non-punishers)
  help maintain the norm (norm collapses without; metanorms raise enforcement — but fragile).
- Heider / Antal, Krapivsky & Redner (2005 PRE 72:036121): signed-network balance dynamics →
  a balanced absorbing state (all-positive "paradise" or two mutually-hostile factions).
- Dittrich, Liljeros, Soulier & Banzhaf (2000): seceder model — "be different from the mean"
  → spontaneous multi-cluster (≈3) group formation.
- Miller & Page (2004): standing ovation — quality + spatial conformity → ovation spreads.

## Shared architecture / discipline
Code `abm_auto/classics/`, runners `examples/repro_<name>/`, studies `docs/studies/<name>/`,
tests `tests/classics/`. Reuse `Verdict` + `abm_auto.repro_bundle`. Lock metric; seed-average +
variance; no tuning; falsified=MISS.

## Model 1 — Olami-Feder-Christensen earthquakes (CA / SOC — disclosed)
L×L lattice (L=50), each site a real "force" ~U[0,1]. Drive: add the same increment to ALL sites
until the max reaches threshold 1. Relax: the over-threshold site resets to 0 and adds α·(its
force) to each of its 4 neighbours (α = conservation, ≤0.25); neighbours that cross 1 also topple
(avalanche); open boundary (edge dissipation). Event size = #topplings per drive. **Claim:** SOC
— event sizes power-law (Gutenberg-Richter), heavier near-conservative. Lock: P1 (α=0.2) event-size
distribution is heavy-tailed/power-law (≥2 decades; max ≥100× median nonzero); P2 the more
conservative α=0.2 produces a HEAVIER tail (larger mean event size) than α=0.1; P3 self-organizes
to a stationary critical state (event-size distribution stationary after transient, init-independent).

## Model 2 — Axelrod 1986 norms / metanorms (genuine agent-based)
N=20 player agents, each (boldness B, vengefulness V) ∈ {0..7}². A round: each agent defects with
prob (1 − B/7) deterrence... use Axelrod's payoffs — defecting gives temptation T=3 to the
defector and hurt H=−1 to each other; if seen (prob ∝ S), a witness punishes with prob V/7 at
cost E=−2 to the defector and P=−1 to the punisher. METANORM variant: a witness who saw a
defection but did NOT punish is itself punished (prob ∝ another's V). Evolutionary update each
generation (reproduce ∝ payoff + mutation). **Claim:** without metanorms the norm collapses;
metanorms RAISE enforcement. Lock (≥20 seeds, the result is stochastic): P1 no-metanorm →
collapses (final mean vengefulness < 2.5 / boldness rises) in the majority of seeds; P2
with-metanorm → mean final vengefulness is HIGHER than no-metanorm (metanorms raise enforcement);
P3 the contrast holds on the seed-averaged final (vengefulness_meta > vengefulness_nometa). (Lock
the COMPARATIVE claim — Axelrod's own result is that metanorms HELP but do not guarantee the norm.)

## Model 3 — Heider social balance (signed-network dynamics — disclosed)
Complete signed graph on N=30 nodes, each edge ±1 (random init). Dynamics (Antal-Krapivsky-Redner
local triad update): repeatedly pick a random imbalanced triad (product of its 3 edges < 0) and
flip one of its edges to make it balanced (reduce frustration). Run to an absorbing state. **Claim:**
the network reaches a BALANCED state — partitionable into ≤2 factions (every + within, every −
between). Lock: P1 the fraction of balanced triads rises to 1.0 (system reaches a balanced state)
in ≥90% of seeds; P2 the final state is a valid balance: either all-positive ("paradise") OR a
2-faction split (every + intra-faction, every − inter-faction) — verify the partition; P3 the
frustration (count of imbalanced triads) is non-increasing under the dynamics. ≥10 seeds.

## Model 4 — Seceder model (genuine agent-based)
Population of N=200 `EntityAgent`s, each a real value (1D trait), init ~N(0,1). Reproduction event:
pick 3 random entities, the one with the LARGEST distance to their 3-mean reproduces a mutated
offspring (value + N(0,σ)); the offspring replaces a random entity. Many events. **Claim:** "be
different" → spontaneous multi-cluster (≈3) formation. Lock: P1 the population forms ≥2 clusters
(typically 3) at steady state (cluster on the trait line with a gap tolerance); P2 the clusters
persist — population variance stays high (≫ the σ_mut floor), not collapsing to a single point; P3
the cluster structure is stable over time (cluster count ≈ constant in the late run). ≥5 seeds.

## Model 5 — Miller-Page standing ovation (genuine agent-based)
L×L auditorium (L=40) of `AudienceAgent`s. Each perceives quality q_i = signal s + noise ε_i
(ε~N(0,σ)); STANDS initially iff q_i > threshold T=0.5. Then iterate: each agent conforms — stands
iff ≥ half of the agents in its viewing neighbourhood (e.g. those in front within a cone, or Moore-8)
are standing (and stays standing once up, or re-evaluates — document). Run to a fixed point.
**Claim:** quality + spatial conformity drive whether an ovation forms. Lock: P1 high signal
(s=0.8 > T) → ovation: final standing fraction > 0.8; P2 low signal (s=0.2 < T) → no ovation:
final standing fraction < 0.2; P3 spatial conformity AMPLIFIES — at an intermediate signal the
final standing fraction (after conformity) differs from the initial pre-conformity fraction
(spreads up if seeded above ~half, or a no-conformity control gives a less-complete ovation). ≥5 seeds.

## Testing & scope
`tests/classics/`: faithful-rule + determinism. Anchors (OFC power-law + α-dependence, norms
metanorm-enforcement, Heider balanced absorbing state, seceder ≈3 clusters, ovation quality
threshold) are the clauses. Faithful reproductions of synthetic models; no real-world data. OFC
disclosed as CA/SOC; Heider as signed-network dynamics.
