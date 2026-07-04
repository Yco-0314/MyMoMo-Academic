# Classic Reproductions — Batch 5 / Wave B (ecology / cooperation / coordination / genetics)

**Date:** 2026-06-30. Same discipline (lock claim + GRADING METRIC before run → genuine
agent-based on `abm_auto._platform` → honest REPRO/MISS → adversarial review). Apply all
prior lessons (lock metric, fair controls, seed-averaging, no tuning). Targets: **spatial
rock-paper-scissors**, **agent Lotka-Volterra predator-prey**, **El Farol bar**,
**Axelrod-Hammond ethnocentrism**, **Moran process with selection**. All 5 are genuine
agent-stepping (no CA in this wave).

**Sources (verified via web, not memory):**
- Reichenbach, Mobilia & Frey (2007 Nature / 2008 JTB 254:368): spatial cyclic dominance —
  coexistence (spiral waves) only with LOCAL interaction; well-mixed/high-mobility → biodiversity loss.
- Lotka (1925) / Volterra (1926); agent-based predator-prey: oscillations, predator lags prey.
- Arthur (1994): El Farol bar, capacity 60/100 — attendance self-organizes near 60 (~56–60).
- Hammond & Axelrod (2006) J. Conflict Resolution: ethnocentric strategy dominates; humanitarian 2nd.
- Moran (1958): fixation prob ρ=(1−1/r)/(1−1/rᴺ); neutral r=1 → 1/N; large-N → 1−1/r.

## Shared architecture / discipline
Code `abm_auto/classics/`, runners `examples/repro_<name>/`, studies `docs/studies/<name>/`,
tests `tests/classics/`. Reuse `Verdict` + `abm_auto.repro_bundle`. Lock metric; seed-average +
variance; no tuning; falsified=MISS.

## Model 1 — Spatial rock-paper-scissors (genuine agent-based)
L×L periodic lattice (L=100), each cell empty or one of 3 species (R,P,S). Each tick (random
events): a random site interacts with a random neighbour — predation (R beats S beats P beats
R: the predator converts the prey site / prey→empty), reproduction (a species fills an empty
neighbour), and pair-exchange/mobility (swap with a neighbour) at rate ε. **Claim:** local
spatial structure preserves coexistence; well-mixed (or high mobility) loses it. Lock: P1
SPATIAL (low/zero mobility) → all 3 species coexist (each fraction > 0.05 at the end of a long
run, in ≥80% of seeds); P2 WELL-MIXED (random global partners every interaction, structure
destroyed) → biodiversity lost (≥1 species extinct, typically down to 1); P3 the contrast —
spatial #surviving species > well-mixed #surviving species. ≥5 seeds.

## Model 2 — Agent Lotka-Volterra predator-prey (genuine agent-based)
L×L grid (L=100) with prey and predator agents. Prey reproduce (rate); predators move, eat a
prey on their cell (gain energy), reproduce when energy high, die when energy ≤0; prey have a
growth/carrying-capacity term so the system can sustain a limit cycle. Outcome = prey and
predator population time series. **Claim:** sustained oscillations with the predator lagging the
prey. Lock: P1 sustained oscillations — both populations show ≥2 peaks and neither goes extinct
over the run (in ≥60% of seeds; report the survival rate honestly); P2 predator LAGS prey — the
cross-correlation of the two series is maximized at a POSITIVE lag (predator peak after prey
peak); P3 persistence — the oscillation continues to the end of the run (not a single transient
spike). ≥5 seeds. (Agent LV is extinction-prone — report the survival fraction honestly.)

## Model 3 — El Farol bar (genuine agent-based)
N=100 `BarAgent`s, capacity = 60. Each holds a small set of predictors mapping recent
attendance history → a forecast; each week each agent uses its currently best predictor to
forecast next attendance and GOES iff forecast < 60; the realized attendance updates history and
each agent re-scores its predictors. **Claim:** attendance self-organizes near the capacity 60.
Lock: P1 mean attendance ≈ 60 (in [50, 65]) over a long run after transient; P2 attendance
FLUCTUATES (std > 2, not pinned); P3 self-organization — the long-run mean sits near 60
regardless of init (within [50,65]), i.e. the "efficient" level emerges without coordination.
≥5 seeds. (Arthur's original: long-run mean ~56–60.)

## Model 4 — Axelrod-Hammond ethnocentrism (genuine agent-based)
L×L grid (L=50) with empty sites. Each agent has a TAG (one of 4 colours) + a strategy = (coop
with same tag? yes/no, coop with diff tag? yes/no) → 4 phenotypes: ethnocentric (C-in,D-out),
humanitarian (C,C), egoist/selfish (D,D), traitorous (D-in,C-out). Each tick: immigration of a
random agent to an empty site; pairwise one-shot PD with the 4 NN (cost c=0.01 to give,
benefit b=0.03 to receive); reproduction with prob ∝ accumulated payoff (offspring inherits
tag+strategy with small mutation, placed in an empty neighbour); death at a fixed rate.
**Claim:** ethnocentric strategy dominates; humanitarian 2nd. Lock: P1 ethnocentric is the MOST
common strategy at steady state (largest share); P2 ethnocentric share > 0.40; P3 in-group
cooperation rate > out-group cooperation rate (the ethnocentrism signature). ≥5 seeds.

## Model 5 — Moran process with selection (genuine agent-based)
Well-mixed population N=100, one mutant (fitness r) vs N−1 residents (fitness 1). Each step:
choose one individual to REPRODUCE with prob ∝ fitness, and one (uniformly at random) to DIE;
the offspring replaces the dead. Run to fixation (all-mutant or all-resident). Outcome =
fixation probability of the mutant over many runs. **Claim:** ρ = (1−1/r)/(1−1/rᴺ) (exact
Moran); neutral r=1 → 1/N; large-N → 1−1/r. Lock: P1 measured fixation prob at r∈{1.05,1.1,1.2,
2.0} matches ρ=(1−1/r)/(1−1/rᴺ) within ±0.03 (over ≥2000 runs each); P2 neutral r=1.0 →
fixation prob ≈ 1/N = 0.01 (±0.01); P3 monotone — fixation prob increases with r. (NOTE: the
Moran large-N limit is 1−1/r≈s, NOT the Wright-Fisher 2s — we lock the exact Moran formula.)

## Testing & scope
`tests/classics/`: faithful-rule + determinism. Analytic anchors (Moran ρ formula, El Farol ~60,
RPS coexistence-vs-extinction) are the clauses. Faithful reproductions of synthetic models; no
real-world data.
