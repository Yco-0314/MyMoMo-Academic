# Public Goods + Punishment — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claim is Fehr & Gächter (2000/2002), not tuned.
Genuine agent-based (strategy agents, payoff-proportional imitation).

**Model:** well-mixed population, groups of n=5/round play a PGG (contribution c=1,
multiplier r=3, equal split). Strategies: Cooperator, Defector, and (with-punishment only)
Punisher (cooperates + pays β=1 per defector in group; each punished defector loses γ=3).
Strategy update = payoff-proportional imitation. Two FAIR treatments differing only in
whether Punisher is available. Outcome = mean cooperation (fraction contributing) at steady
state. Mean over ≥10 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Without punishment, cooperation collapses. | no-punishment final mean cooperation < 0.20 |
| P2 | With punishment, cooperation is sustained. | with-punishment final mean cooperation > 0.50 |
| P3 | Punishment makes the difference. | with-punishment − no-punishment cooperation ≥ 0.30 |

**Discipline:** PGG params (n,c,r,β,γ), update rule, seeds FIXED + metric locked before run;
the two treatments differ ONLY in the punishment option (fair). No tuning. Falsified → MISS.
