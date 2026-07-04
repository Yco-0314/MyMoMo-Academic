# Classic Reproductions — Batch 5 / Wave A (phase transitions / sync / SOC)

**Date:** 2026-06-30. Same discipline (lock claim + GRADING METRIC before run → genuine
agent-based on `abm_auto._platform` → honest REPRO/MISS → adversarial review). Apply all
prior lessons (lock the metric, fair controls, seed-averaging, no tuning; disclose CA
framing). Targets: **Ising 2D**, **Kuramoto**, **Majority-vote**, **Drossel–Schwabl forest
fire**, **Conway Game of Life**.

**Honesty on framing:** Ising, Kuramoto, Majority-vote → genuine agent-stepping (spin /
oscillator agents update). **Forest fire + Game of Life → cellular automata** (disclosed,
like BTW/NaSch — central synchronous update, no autonomous agent decision).

**Sources (verified via web, not memory):**
- Onsager (1944): 2D Ising T_c = 2/ln(1+√2) ≈ 2.269; spontaneous magnetization below T_c.
- Kuramoto (1975): order parameter r→0 below critical coupling K_c, >0 above; mean-field
  K_c = 2/(π g(0)); for ω~N(0,1), g(0)=1/√(2π) → K_c ≈ 1.60.
- de Oliveira (1992): 2-state majority-vote on the square lattice, order–disorder at a
  critical noise q_c (Ising universality); canonical q_c ≈ 0.075 (von-Neumann-4) — reported
  vs measured.
- Drossel & Schwabl (1992): forest-fire SOC; cluster/fire-size power law (cluster exponent
  τ≈2), reached in the f/p→0 (double-separation) limit.
- Conway / Gardner (1970): Life B3/S23; glider period 4 translating (1,1); blinker period 2;
  block still life.

## Shared architecture / discipline
Code `abm_auto/classics/`, runners `examples/repro_<name>/`, studies `docs/studies/<name>/`,
tests `tests/classics/`. Reuse `Verdict` + `abm_auto.repro_bundle`. Lock metric; seed-average
+ variance; no tuning; falsified=MISS.

## Model 1 — Ising 2D (genuine agent-based, Glauber)
L×L periodic lattice (L=32), spins ±1. Glauber single-spin dynamics: each tick pick spins
and flip with prob 1/(1+exp(ΔE/T)) (ΔE from the 4 NN). Measure |magnetization| after
equilibration. Sweep T∈{1.5,2.0,2.27,2.5,3.0,3.5}. **Claim:** ferromagnetic transition at
T_c≈2.269. Lock: P1 |m| > 0.7 at T=1.5 AND |m| < 0.2 at T=3.5; P2 |m| drops sharply across
T_c (the measured half-magnetization crossing is in [2.0,2.6]); P3 |m| monotonically
non-increasing in T. Mean over ≥5 seeds.

## Model 2 — Kuramoto (genuine agent-based)
N=500 phase oscillators, natural frequencies ω_i~N(0,1). Each tick (dt=0.05):
θ_i += (ω_i + (K/N)Σ_j sin(θ_j−θ_i))·dt. Order parameter r = |Σ e^{iθ}|/N, after transient.
Sweep K∈{0,0.5,1.0,1.6,2.0,3.0,4.0}. **Claim:** synchronization transition at K_c≈1.60. Lock:
P1 r < 0.3 at K=0.5 (incoherent) AND r > 0.6 at K=3.0 (synchronized); P2 r rises sharply near
K_c≈1.6 (onset — first K with r>0.3 is in [1.0,2.2]); P3 r monotonically non-decreasing in K.
Mean over ≥5 seeds.

## Model 3 — Majority-vote (genuine agent-based)
L×L periodic lattice (L=50), spins ±1. Each tick (random sequential or synchronous — doc):
each spin takes the sign of its 4-NN majority with prob (1−q), or the minority with prob q
(noise). Measure |magnetization| after equilibration. Sweep q∈{0.02,0.05,0.075,0.10,0.15}.
**Claim:** order–disorder transition at a critical noise q_c (Ising universality). Lock:
P1 |m| > 0.7 at q=0.02 AND |m| < 0.3 at q=0.15; P2 |m| drops across q_c — measured
half-magnetization crossing reported vs canonical ~0.075 (pass if crossing in [0.04,0.12]);
P3 |m| monotonically non-increasing in q. Mean over ≥5 seeds.

## Model 4 — Drossel–Schwabl forest fire (cellular automaton; SOC — disclosed)
L×L grid (L=128), cells empty/tree/burning. Each tick: a burning cell → empty; a tree with a
burning neighbour → burning; an empty cell → tree with prob p; a tree → burning (lightning)
with prob f. Use p=0.05, f/p small (f=p/1000) for scale separation. Record fire sizes (number
burnt per lightning-triggered fire) in the stationary state. **Claim:** SOC — fire-size
distribution is power-law/heavy-tailed (cluster exponent ≈2). Lock: P1 fitted fire-size tail
exponent τ ∈ [1.0, 2.5]; P2 heavy-tailed (spans ≥2 decades; max fire ≥ 100× median); P3
self-organizes to a stationary tree density independent of initial condition. Honest caveat
in FINDINGS: forest-fire SOC is only approximately scale-free (known deviations at large
sizes) — report the fit range.

## Model 5 — Conway Game of Life (cellular automaton; disclosed)
L×L grid (toroidal), B3/S23. **Claim:** the catalogued pattern behaviours. Lock (exact,
deterministic): P1 the **glider** returns to its own shape translated by (+1,+1) after exactly
4 generations (a period-4 diagonal spaceship); P2 the **blinker** has period 2 and the
**block** is a still life (period 1); P3 a **5×5 random-free census** — total live cells is
conserved for the block (still life) and oscillates with period 2 for the blinker/beacon
(verify periods exactly). No seeds/averaging (deterministic).

## Testing & scope
`tests/classics/`: faithful-rule + determinism. Analytic anchors (Ising T_c, Kuramoto K_c,
majority-vote q_c, forest-fire τ, GoL exact periods) are the clauses. Faithful reproductions
of synthetic models; no real-world data. Forest-fire + GoL disclosed as CA.
