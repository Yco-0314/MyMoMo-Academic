# Classic ABM Reproductions — Batch 3 (design)

**Date:** 2026-06-29
**Goal:** Five more canonical social-simulation ABMs, same discipline (lock the paper's
claim BEFORE running → genuine agent-based on `abm_auto._platform` → honest REPRO/MISS →
adversarial review). Targets chosen for mechanism diversity beyond batches 1–2:
**Sugarscape** (emergent inequality), **Axelrod 1984** (IPD tournament / cooperation),
**Epstein 2002** (civil violence / deterrence), **Sznajd 2000** (opinion validation),
**SIR** (epidemic threshold).

**Sources (verified via web search, not memory):**
- Epstein, J. & Axtell, R. (1996) *Growing Artificial Societies* (Sugarscape).
- Axelrod, R. (1984) *The Evolution of Cooperation* (IPD computer tournament).
- Epstein, J. (2002) "Modeling civil violence", PNAS 99(suppl 3):7243–7250.
- Sznajd-Weron, K. & Sznajd, J. (2000) "Opinion evolution in closed community",
  Int. J. Mod. Phys. C 11(6):1157–1165.
- Kermack & McKendrick (1927) SIR; R0=β/γ, threshold + final-size (Brauer, standard).

## Shared architecture (same as batches 1–2)
Genuine agent-based on `abm_auto._platform` (Agent.step + AgentSet/AgentModel +
DataCollector). Code in `abm_auto/classics/`, runners in `examples/repro_<name>/`, locked
predictions + findings + results + L3 bundles in `docs/studies/<name>/`, tests in
`tests/classics/`. Reuse `Verdict` + `abm_auto.repro_bundle`. **Discipline:** predictions
= the paper's claims, locked + committed BEFORE running; **lock the GRADING METRIC too**
(batch-2 Deffuant lesson); no parameter/control tuned to pass; falsified clause = MISS;
controls must be FAIR (batch-2 Nowak-May lesson); guard against RNG-noise effects (coord
lesson — average over seeds, report variance).

## Model 1 — Sugarscape (Epstein-Axtell 1996), wealth inequality
50×50 toroidal grid; each cell has a sugar capacity (two sugar "mountains", classic
landscape) and regrows (rule G∞: instant regrow to capacity, or +1/tick — document). N
agents, each with vision v~U{1..6}, metabolism m~U{1..4}, initial sugar w0~U{5..25}.
Movement rule M: survey the 4 von-Neumann directions out to v, move to the nearest
unoccupied cell with the most sugar, harvest it, subtract metabolism; die if sugar<0.
Outcome = Gini coefficient of agent wealth over time. **Claim:** from a near-uniform
start, wealth becomes strongly right-skewed → Gini rises to a high steady value. Lock:
P1 final Gini ≥ 0.40 (strong inequality emerges); P2 final Gini ≫ initial Gini (Δ ≥ 0.15);
P3 wealth distribution is right-skewed (mean > median; top decile share ≫ 10%).

## Model 2 — Axelrod 1984 IPD tournament
Round-robin: every strategy plays every strategy (incl. itself) over 200 rounds; payoffs
T=5, R=3, P=1, S=0 (Axelrod's). Strategy pool ≥ 8 standard strategies (TitForTat, AllD,
AllC, Random, Grudger/Grim, TitForTwoTats, Joss/suspicious-TFT, Pavlov/win-stay-lose-shift).
Each `StrategyAgent` decides each round from local game history. Score = total (or mean)
points across all opponents. **Claim:** TIT-FOR-TAT wins (ranks #1) or is in the top
bracket; nice strategies (never defect first) out-score the rest on average. Lock (the
operative thresholds are in `docs/studies/axelrod-ipd-tournament/PREDICTIONS-locked.md`):
P1 TitForTat ranks #1 by total score (or tied-1 within <1% of the top — the binding
clause); P2 the top half of the ranking
is dominated by NICE strategies (mean rank of nice < mean rank of non-nice); P3 AllD does
NOT win (greedy defection is not the top strategy).

## Model 3 — Epstein 2002 civil violence
40×40 grid; populace agents (grievance G=H·(1−L), H~U[0,1], legitimacy L a global
parameter; risk-aversion Ri~U[0,1]) + cop agents. Each populace agent estimates arrest
prob P=1−exp(−k·(C/A)_local) (cops C and actives A in vision; k=2.3 so one cop in view of
one active gives P≈0.9) and goes ACTIVE iff G − Ri·P > threshold (0.1). Cops move to a
random site in vision and arrest a random active there (jail term J~U{1..Jmax}). Agents
move to a random empty site in vision. **Claim:** rebellion is PUNCTUATED (bursts), and
LEGITIMACY governs the regime. Lock: P1 high legitimacy (L=0.9) → low/calm active fraction
(mean active < 0.05); P2 low legitimacy (L=0.5) → large rebellion bursts (peak active ≫
mean, burstiness: max active / mean active ≥ 5, OR mean active ≥ 0.1); P3 increasing cop
density monotonically lowers the steady active fraction (deterrence).

## Model 4 — Sznajd 2000 opinion ("united we stand")
2D L×L lattice (periodic), opinions ∈ {−1,+1}, initial up-density d. Rule (2D Sznajd):
pick a random 2×2 plaquette; if all four agree, they set all their (8) outer neighbours to
that opinion; else no change (or the standard "disagree → no convince"). Run to a frozen
state. **Claim:** the system reaches COMPLETE CONSENSUS, and there is a phase transition
at d=1/2. Lock: P1 from d=0.5 (±) the final state is (near-)complete consensus on one
opinion (|final magnetization| ≥ 0.95) in the vast majority of runs; P2 phase transition
at d=1/2 — fraction of runs ending all-UP is a steep function of d: ≈0 for d≤0.4, ≈1 for
d≥0.6; P3 d>0.5 → all-up dominates (P(all-up | d=0.7) > 0.8), d<0.5 → all-down dominates.

## Model 5 — SIR epidemic threshold
Well-mixed (mass-action) population, N=10,000. Each tick, each infected (I) infects each
susceptible (S) with effective rate giving R0=β/γ; I→R at rate γ. Seed a few infected.
R0 = β/γ swept across 1. **Claim:** epidemic threshold — a large outbreak occurs iff
R0>1; for R0<1 the infection fades with negligible final size; and the final size obeys
ln(S0/S∞)=R0(1−S∞/N). Lock: P1 final attack rate (1−S∞/N) is negligible (< 0.05) for
R0=0.8 and substantial (> 0.3) for R0=2.0 (threshold behaviour); P2 the measured final
size at R0=2.0 matches the analytic final-size relation within ±10%; P3 monotonic — final
attack rate increases with R0 across {0.8, 1.0, 1.5, 2.0, 3.0}, near-zero below 1.

## Testing & scope
`tests/classics/`: faithful-rule unit tests + determinism (seeded). Analytic anchors (SIR
final-size, Sznajd transition at 0.5) are pass/fail clauses; qualitative claims
(Sugarscape inequality, Axelrod TFT, Epstein punctuation) are the others. Faithful
reproductions of published synthetic models; no real-world data. **Apply the batch-2
lessons:** lock the metric, use fair controls, average over seeds + report variance so an
RNG-noise effect cannot masquerade as a result.
