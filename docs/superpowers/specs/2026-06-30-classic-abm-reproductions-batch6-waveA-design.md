# Classic Reproductions — Batch 6 / Wave A (evolution / complexity / swarm)

**Date:** 2026-06-30. Same discipline (lock claim + GRADING METRIC before run → genuine
agent-based on `abm_auto._platform` → honest REPRO/MISS → adversarial review). Targets:
**Wright-Fisher drift**, **Kauffman NK**, **Bak-Sneppen**, **Daisyworld**, **ant
double-bridge foraging**, **Boids**.

**Honesty on framing:** Wright-Fisher, Daisyworld (grid), ant foraging, Boids → genuine
agent-stepping. NK → adaptive-walker agents on a landscape (the #optima count is a
landscape-property measurement). **Bak-Sneppen → extremal dynamics (each step selects the
GLOBAL minimum) = model-orchestrated, not autonomous-agent-stepping** — disclosed.

**Sources (verified via web, not memory):**
- Wright (1931) / Fisher (1930): neutral fixation prob = initial freq; heterozygosity decays
  by factor (1−1/2N) per generation; Var(Δf)=f(1−f)/(2N).
- Kauffman & Levin (1987): #local optima grows with K; K=0 → single peak; K=N−1 → ~2^N/(N+1)
  optima; adaptive walk length N/2 (K=0) → ~log₂N (K=N−1).
- Bak & Sneppen (1993): SOC; stationary fitness ~uniform on (f_c, 1), f_c ≈ 0.667; power-law
  avalanches.
- Watson & Lovelock (1983): Daisyworld — temperature homeostasis over a solar-luminosity range.
- Deneubourg / Goss (1989): ant double-bridge — colony self-organizes onto the shorter path.
- Reynolds (1987): Boids — flocking from separation/alignment/cohesion; emergent polarization.

## Shared architecture / discipline
Code `abm_auto/classics/`, runners `examples/repro_<name>/`, studies `docs/studies/<name>/`,
tests `tests/classics/`. Reuse `Verdict` + `abm_auto.repro_bundle`. Lock metric; seed-average +
variance; no tuning; falsified=MISS.

## Model 1 — Wright-Fisher neutral drift (genuine agent-based)
Population of N=100 haploid `AlleleAgent`s, two alleles (A/a), initial A-fraction p0. Each
generation: form the next generation by sampling N parents WITH replacement uniformly (neutral
— no fitness). Run to fixation (A=0 or N). Outcome = fixation probability of A over ≥2000 runs
+ heterozygosity H=2p(1−p) decay. **Claim:** neutral fixation prob = p0; H decays ~(1−1/2N)/gen.
Lock: P1 fixation prob of A at p0∈{0.2,0.5,0.8} within ±0.05 of p0 (≥2000 runs each); P2
mean heterozygosity decays geometrically with per-generation factor in [1−2/N, 1−1/(4N)]
(bracketing the 1−1/(2N) law for haploid N≈2N_diploid — report the measured rate vs 1/N); P3
neutral — E[Δp]≈0 (mean A-fraction across runs stays ≈ p0 until absorption).

## Model 2 — Kauffman NK landscape (adaptive-walker agents)
N=15 binary loci, fitness = mean of N per-locus contributions, each depending on its locus +
K others (random tables). Sweep K∈{0,2,4,8,14}. Count local optima (a genotype fitter than all
N single-bit-flip neighbours; enumerate the 2^15 space) + adaptive-walk length (greedy hill-climb
from random starts). **Claim:** ruggedness grows with K. Lock: P1 #local optima increases
monotonically with K; P2 K=0 → exactly 1 optimum (single-peaked); P3 mean adaptive-walk length
decreases with K. Mean over ≥5 random landscapes per K.

## Model 3 — Bak-Sneppen (extremal dynamics; SOC — disclosed, not autonomous-agent-stepping)
Ring of N=200 species, each a fitness ~U[0,1]. Each step: find the GLOBAL-minimum-fitness
species; replace its fitness AND its two ring-neighbours' fitnesses with fresh U[0,1]. Run long;
outcome = stationary fitness distribution + avalanche sizes (an avalanche = consecutive steps
where the min stays below a threshold). **Claim:** SOC — stationary fitnesses become ~uniform
above f_c≈0.667; power-law avalanches. Lock: P1 the stationary distribution's lower edge
(e.g. the 5th percentile, or the fraction below 0.667) shows most fitnesses lie ABOVE f_c≈0.667
(measured threshold in [0.60, 0.72]); P2 avalanche sizes are power-law/heavy-tailed (≥2 decades);
P3 punctuated — the activity is intermittent (the minimum repeatedly dips and recovers).

## Model 4 — Daisyworld (genuine agent-based, grid)
L×L grid (L=50) of cells: bare / black daisy / white daisy. Local temperature from solar
luminosity L_sol × (1 − local albedo) (black low albedo → warmer, white high → cooler). Daisies
reproduce into empty neighbours with a growth rate that is a parabolic function of local
temperature (peaked ~22.5°C), and die at a fixed rate. Sweep solar luminosity L_sol over a range.
Outcome = global mean temperature vs L_sol, with vs without daisies. **Claim:** daisies regulate
temperature (homeostasis) over a luminosity range. Lock: P1 WITH daisies, mean planetary
temperature stays within a narrow band (range < 10°C) over L_sol∈[0.7,1.3]; P2 WITHOUT daisies
(bare control) temperature rises monotonically with L_sol (range ≫ the daisy band, ≥ 30°C); P3
the daisy mix shifts (black-dominated at low L_sol → white-dominated at high L_sol). ≥3 seeds.

## Model 5 — Ant double-bridge foraging (genuine agent-based)
Nest + food connected by TWO paths (short length Ls, long Ll=2·Ls). Ant agents leave the nest,
choose a branch at the fork with prob ∝ (pheromone+k)^α, walk the branch (time ∝ length), deposit
pheromone, return. Pheromone evaporates each tick. Outcome = fraction of traffic on the short
path over time. **Claim:** the colony self-organizes onto the shorter path. Lock: P1 asymmetric
bridges (Ll=2Ls) → short-path traffic fraction > 0.8 at steady state (≥80% of seeds); P2
symmetric bridges (Ll=Ls) → symmetry breaking: one path wins (final fraction >0.8 on one,
randomly which, across seeds — NOT a stable 50/50); P3 the short-path fraction rises over time
(self-reinforcement). ≥5 seeds.

## Model 6 — Boids (genuine agent-based)
N=200 boid agents in a 2D periodic box, each position+velocity. Each tick apply
separation + alignment + cohesion (steer from neighbours within a radius), capped speed.
Order parameter φ = |mean normalized velocity|. **Claim:** flocking emerges (alignment) — and
the alignment rule is what causes it. Lock: P1 with all 3 rules → φ rises to > 0.7 (coherent
flock heading) after a transient; P2 WITHOUT the alignment rule (separation+cohesion only) → φ
stays low (< 0.3, no common heading); P3 cohesion holds — mean nearest-neighbour distance stays
bounded (the flock doesn't disperse). ≥5 seeds.

## Testing & scope
`tests/classics/`: faithful-rule + determinism. Analytic anchors (WF fixation=p0 + H decay,
NK #optima vs K, Bak-Sneppen f_c≈0.667, Daisyworld homeostasis, ant shorter-path, Boids
alignment-causes-flock) are the clauses. Faithful reproductions of synthetic models; no
real-world data. Bak-Sneppen disclosed as extremal-dynamics (not autonomous-agent-stepping).
