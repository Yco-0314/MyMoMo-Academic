# Classic Reproductions — Batch 4 / Wave 2 (cooperation/games + opinion)

**Date:** 2026-06-29. Same discipline (lock claim + GRADING METRIC before run → genuine
agent-based on `abm_auto._platform` → honest REPRO/MISS → adversarial review). Apply
batch-2/3 lessons (lock the metric, fair controls, seed-averaging, no tuning). Targets:
**Hawk–Dove ESS**, **Public Goods + punishment**, **Hegselmann–Krause**, **Galam
majority rule**, **Minority Game**.

**Sources (verified via web, not memory):**
- Maynard Smith & Price (1973) Hawk-Dove; mixed ESS hawk fraction p*=V/C (cost model, V<C).
- Fehr & Gächter (2000/2002) public goods with punishment; cooperation collapses without
  punishment, sustained with peer punishment.
- Hegselmann & Krause (2002) JASSS 5(3); synchronous average-within-ε; consensus above ε≈0.2.
- Galam majority-rule model; reshuffled small-group majority → consensus, tipping at 0.5
  (odd groups); even-group tie-bias shifts the tipping point (minority spreading).
- Challet & Zhang (1997) Minority Game; volatility σ²/N minimum at αc≈0.337, α=2^m/N.

## Shared architecture / discipline
Code in `abm_auto/classics/`, runners `examples/repro_<name>/`, studies
`docs/studies/<name>/`, tests `tests/classics/`. Reuse `Verdict` + `abm_auto.repro_bundle`.
Lock the metric; seed-average + report variance; no tuning; falsified = MISS.

## Model 1 — Hawk–Dove ESS (replicator / evolutionary, agent-based)
Well-mixed population of `StrategyAgent`s, each Hawk or Dove. Payoffs: (H,H)=(V−C)/2,
(H,D)=V, (D,H)=0, (D,D)=V/2, with V<C. Each generation: random pairings, accumulate
payoff, then strategy update by replicator/imitation (reproduce ∝ fitness). V=2, C=4 (so
p*=V/C=0.5); also V=1,C=4 (p*=0.25). Outcome = steady-state hawk fraction. **Claim:** the
hawk fraction converges to the ESS p*=V/C from any interior start. Lock: P1 from x0=0.9 and
x0=0.1, steady hawk fraction → p*=V/C (within ±0.05) for V=2,C=4 (p*=0.5); P2 for V=1,C=4
the steady fraction → 0.25 (±0.05); P3 the equilibrium is an attractor (both starts converge
to the same p*).

## Model 2 — Public Goods Game + punishment (evolutionary, agent-based)
Well-mixed (or grouped) population; strategies Cooperator (C), Defector (D), and Punisher
(P = cooperates AND pays to punish defectors). Each round: groups of n=5 play a PGG
(contribution c=1, multiplier r=3, split among group); punishers pay β=1 per defector in
group, each punished defector loses γ=3. Strategy update by payoff-proportional imitation.
Two treatments: **no-punishment** (only C/D) vs **with-punishment** (C/D/P). Outcome = mean
cooperation (fraction contributing) at steady state. **Claim:** without punishment
cooperation collapses; with punishment it is sustained. Lock: P1 no-punishment → final mean
cooperation < 0.2 (collapse); P2 with-punishment → final mean cooperation > 0.5 (sustained);
P3 with-punishment cooperation ≫ no-punishment (difference ≥ 0.3). (FAIR comparison: same
PGG params, only the punishment option differs.)

## Model 3 — Hegselmann–Krause opinion (genuine agent-based)
N=1000 agents, opinions ~U[0,1]. Synchronous update: x_i ← mean of {x_j : |x_i−x_j| ≤ ε}
(including self). Run to a stationary state; count final opinion clusters (tol 0.01).
**Claim:** consensus above a confidence threshold ε≈0.2; fragmentation (more clusters)
below. Lock: P1 ε≥0.25 → consensus (1 cluster) in ≥90% of runs; P2 #clusters is
non-increasing as ε rises across {0.05,0.1,0.15,0.2,0.3}; P3 ε≤0.1 → fragmentation (≥2
clusters typical). Average over ≥20 seeds.

## Model 4 — Galam majority rule (genuine agent-based)
N=10001 agents, binary opinion, initial up-fraction p0. Each step: randomly partition into
groups of size g; apply local majority rule (all in a group adopt the group majority);
reshuffle. **Odd g=3:** ties impossible. **Even g=4:** ties broken toward a fixed opinion
(the "prejudice"/status-quo bias). Run to consensus. Outcome = which consensus vs p0.
**Claim:** majority rule drives consensus with a tipping point; odd groups → tipping at
p_c=0.5; even-group tie-bias shifts p_c (minority spreading). Lock: P1 (g=3) reaches
consensus AND the initial-majority opinion wins (p0>0.5 → all-up; p0<0.5 → all-down) — a
tipping point at 0.5; P2 (g=4, ties→up) the up-tipping point p_c < 0.5 (an initial up
MINORITY, e.g. p0=0.45, can still win) — minority spreading; P3 the flow moves away from
p_c toward 0 or 1 (no interior fixed point except the unstable p_c). Average over ≥20 seeds.

## Model 5 — Minority Game (genuine agent-based)
N=301 agents (odd), memory length m, each holds S=2 strategies (random lookup tables from
history→action); each round agents pick the action of their currently best-scoring
strategy; the MINORITY side wins; strategies are scored by whether they would have predicted
the minority. Control α=2^m/N (sweep m to vary α at fixed N, or N at fixed m). Outcome =
volatility σ²/N (variance of the attendance/excess demand). **Claim:** σ²/N has a minimum
near αc≈0.34; small α → σ²/N > 1 (worse than random, crowding); large α → σ²/N → ~1
(random-like). Lock: P1 σ²/N is U-shaped/asymmetric in α with a minimum near αc∈[0.1,0.6];
P2 at small α (≤0.1) σ²/N > 1 (worse than random); P3 at large α (≥2) σ²/N ≈ 1 (within
[0.7,1.5], random-like). Average over ≥10 seeds.

## Testing & scope
`tests/classics/`: faithful-rule + determinism. Analytic anchors (Hawk-Dove p*=V/C, MG
αc≈0.34, HK ε_c≈0.2, Galam tipping) are pass/fail clauses. Faithful reproductions of
synthetic models; no real-world data.
