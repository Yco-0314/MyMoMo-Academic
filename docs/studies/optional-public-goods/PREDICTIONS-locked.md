# Optional Public Goods (Voluntary Participation / Loners) — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Hauert, De Monte, Hofbauer & Sigmund 2002
(Science 296:1129), not tuned. Genuine agent-based. Verified; bars set to what a FAITHFUL run
meets (gate-checked).

**Model:** public goods game with cost c=1, multiplication factor r, sample/group size N=5, plus a
LONER (abstain) third strategy earning fixed σ (0<σ<r−1). In a group of participants (n_c cooperators)
defector payoff P_d = r·n_c/S, cooperator P_c = P_d − 1; loner gets σ; a lone participant is forced to
σ. Cyclic dominance: D beats C, L beats D, C beats L (RPS). Well-mixed replicator OR a finite-population
imitation IBM (pop ≥ 5000). **PROTOCOL (gate-checked, to avoid a false MISS):** the interior fixed point
Q is only a neutrally-stable CENTER, so a finite IBM WITHOUT mutation drifts to the boundary and fixates
— use the DETERMINISTIC replicator arm, OR a bounded horizon, OR a tiny mutation μ≈1e-3; ≥5 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Three-strategy RPS cyclic coexistence (r>2). | at r=3, σ=1: time-avg frequency of EACH of C, D, L ∈ (0.05, 0.90) (none fixates) AND cooperator frequency has peak-to-trough amplitude > 0.10 (genuine cycling). *Loose floor 0.05, NOT 1/3.* |
| P2 | Voluntary participation prevents the all-D collapse (vs compulsory). | compulsory arm (loner removed): time-avg cooperator freq < 0.05 (collapse); voluntary arm: time-avg cooperator freq ≥ 0.15 AND exceeds compulsory by ≥ 0.10. *Loose voluntary floor — the cyclic C time-avg is only moderate.* |
| P3 | Regime flip across r=2 (loner is a release valve). | at r=1.8, σ=0.5 (r≤2): loner-dominated (loner time-avg > 0.5, cooperator < 0.15, brief bursts); at r=3, σ=1 (r>2): cooperation persists (cooperator time-avg ≥ 0.15). σ kept strictly inside (0, r−1). |

**Discipline:** r/σ grid, N=5, horizon, seeds, update FIXED + metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep):** public_goods (Fehr-Gächter) sustains cooperation by PEER PUNISHMENT with only
C/D/Punisher (no loner, no RPS cycle); rock_paper_scissors has hand-coded cyclic rates, no PGG r/σ. No
built model has an opt-out/loner strategy.
