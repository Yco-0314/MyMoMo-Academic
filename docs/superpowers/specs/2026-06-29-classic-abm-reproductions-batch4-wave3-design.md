# Classic Reproductions — Batch 4 / Wave 3 (collective motion / SOC / markets / language / traffic)

**Date:** 2026-06-30. Same discipline (lock claim + GRADING METRIC before run → genuine
agent-based on `abm_auto._platform` → honest REPRO/MISS → adversarial review). Apply
batch-2/3 lessons. Targets: **Vicsek flocking**, **BTW sandpile**, **Nagel–Schreckenberg
traffic**, **Gode–Sunder zero-intelligence traders**, **Naming Game**.

**Honesty on framing:** Vicsek, NaSch (cars), ZI-traders, Naming Game → genuine
agent-stepping. **BTW sandpile → cellular automaton (SOC), not agent-decision** — disclosed
in its FINDINGS (like ER/WS in wave 1).

**Sources (verified via web, not memory):**
- Vicsek et al. (1995) PRL 75:1226; noise-driven order–disorder transition of self-propelled particles.
- Bak, Tang & Wiesenfeld (1987); 2D sandpile avalanche power law, exponent τ≈1.2, topple at height≥4.
- Nagel & Schreckenberg (1992) J. Physique I 2:2221; fundamental diagram + spontaneous jams.
- Gode & Sunder (1993) JPE 101:119; ZI-C (budget-constrained) → ~100% allocative efficiency.
- Baronchelli et al. (2006) / Steels; minimal Naming Game → global lexicon consensus, vocabulary peak.

## Shared architecture / discipline
Code in `abm_auto/classics/`, runners `examples/repro_<name>/`, studies `docs/studies/<name>/`,
tests `tests/classics/`. Reuse `Verdict` + `abm_auto.repro_bundle`. Lock the metric;
seed-average + report variance; no tuning; falsified = MISS.

## Model 1 — Vicsek flocking (genuine agent-based)
N particles in an L×L periodic box, constant speed v=0.03, interaction radius r=1. Each
tick: each `ParticleAgent` sets heading = average heading of all particles within r
(including self) + uniform noise in [−η/2, η/2]; then moves. Order parameter
φ = |Σ e^{iθ}| / N. Density ρ=N/L². **Claim:** noise-driven order–disorder transition —
φ≈1 (ordered flock) at low noise, φ≈0 (disordered) at high noise. Lock (N=300, ρ≈2, so
L≈12): P1 φ > 0.5 at low noise (η=0.5) AND φ < 0.2 at high noise (η=5.0, near 2π); P2 φ
monotonically non-increasing as η rises across {0.5,1,2,3,4,5}; P3 ordered phase reaches
strong alignment (φ > 0.8 at η=0.1). Average over ≥10 seeds, measure after transient.

## Model 2 — BTW sandpile (cellular automaton; SOC — disclosed, NOT agent-decision)
L×L grid (L=50), each cell a height. Drive: add 1 grain at a random cell; while any cell
height ≥ 4, topple (cell −4, each of 4 neighbours +1; grains leaving the boundary are
lost). Avalanche size s = number of topplings per added grain. Drive to the critical steady
state (discard transient), then collect ≥10⁵ avalanches. **Claim:** SOC — avalanche sizes
are power-law distributed P(s)~s^{−τ}, τ≈1.2 (2D). Lock: P1 fitted tail exponent τ ∈
[0.9, 1.6] (MLE/CCDF, kmin fixed before run); P2 the size distribution is heavy-tailed
spanning ≥2 decades (NOT exponential — e.g. max avalanche ≥ 100× the median); P3 the system
self-organizes to a stationary critical mean height in [2.0, 2.2].

## Model 3 — Nagel–Schreckenberg traffic (genuine agent-based)
1D ring of Lcells (1000), `CarAgent`s with integer velocity 0..vmax=5, slowdown prob p=0.3.
Each tick (parallel): (1) v←min(v+1,vmax); (2) v←min(v, gap-to-next-car); (3) with prob p,
v←max(v−1,0); (4) move x←x+v. Outcome = flow (mean cars passing a point per tick = ρ·⟨v⟩)
and mean velocity vs density ρ. Sweep ρ. **Claim:** fundamental diagram (flow rises then
falls; interior max) + free-flow→jam transition + spontaneous jams. Lock: P1 flow(ρ) is
non-monotonic with an interior maximum (peak at ρ_c≈0.1, not at the density endpoints); P2
mean velocity high (≥3) at low density (ρ=0.05) and low (≤2) at high density (ρ=0.5); P3
spontaneous jams emerge at intermediate-high density (p>0) — a stopped-car fraction (v=0)
that is ≫0 even though no obstacle exists. Average over ≥10 seeds, measure after transient.

## Model 4 — Gode–Sunder zero-intelligence traders (genuine agent-based)
Continuous double auction. M buyers with private values, M sellers with private costs
(drawn to define a known competitive-equilibrium surplus). ZI-C traders: each submits a
random bid/ask uniformly in [budget bound] — buyer bids U(0, value), seller asks
U(cost, max) — so trades never violate the budget constraint; a trade clears when a bid ≥
ask. ZI-U traders: random bid/ask over the full price range ignoring value/cost. Outcome =
allocative efficiency = realized surplus / max competitive surplus. **Claim:** ZI-C →
near-100% efficiency; ZI-U much lower (the institution, not rationality, drives efficiency).
Lock: P1 ZI-C efficiency > 0.95; P2 ZI-U efficiency < ZI-C by a large margin (ZI-U < 0.90 or
≥0.10 below ZI-C); P3 the budget constraint is the cause (ZI-C − ZI-U ≥ 0.10). Average over
≥20 seeds.

## Model 5 — Naming Game (genuine agent-based)
N=1000 `NamerAgent`s, each with a vocabulary (set of names) for one object, initially empty.
Each step: pick a random speaker + hearer; speaker utters a name (random from its inventory,
or invents a fresh one if empty); if the hearer HAS that name → success: both collapse their
inventory to just that name; else failure: hearer ADDS the name. Run to global consensus
(all agents share exactly one common name). Outcome = consensus reached + total #words and
#distinct names over time. **Claim:** local pairwise interactions → global lexicon
consensus, via a characteristic vocabulary peak. Lock: P1 reaches global consensus (a single
name held by all N) within the step cap, in 100% of runs; P2 #distinct names rises then
collapses to exactly 1 (the peak-then-consensus signature; peak distinct names > 1); P3 total
vocabulary size peaks (> N) then collapses to N (each agent ends with exactly 1 name).
Average over ≥10 seeds.

## Testing & scope
`tests/classics/`: faithful-rule + determinism. Analytic/qualitative anchors (Vicsek
transition, BTW τ≈1.2, NaSch fundamental diagram, ZI-C ~100%, Naming consensus) are the
clauses. Faithful reproductions of synthetic models; no real-world data. BTW disclosed as CA.
