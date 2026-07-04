# Axelrod 1984 IPD Tournament — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claim is Axelrod's (1984), not tuned. Source:
*The Evolution of Cooperation* (1984).

**Model (faithful):** round-robin tournament — every strategy plays every strategy
(including itself) for 200 rounds; payoffs T=5, R=3, P=1, S=0. Strategy pool (≥8):
TitForTat, AllD, AllC, Random, Grudger (grim), TitForTwoTats, Suspicious-TFT (Joss-like),
Pavlov (win-stay-lose-shift). Score = total points across all matches. "Nice" = never the
first to defect (TitForTat, AllC, Grudger, TitForTwoTats, Pavlov-ish first move C).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | TIT-FOR-TAT wins (ranks #1 by total score). | TitForTat is rank 1 (or tied-1 within <1% of the top) |
| P2 | Nice strategies dominate the top. | mean rank of NICE strategies < mean rank of non-nice |
| P3 | Greedy defection does NOT win. | AllD is not rank 1 |

**Discipline:** the strategy pool, payoffs, round count, scoring metric FIXED before the
run; no strategy added/removed to engineer the ranking. Falsified clause → MISS.
