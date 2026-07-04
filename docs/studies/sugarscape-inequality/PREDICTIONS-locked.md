# Sugarscape (Epstein-Axtell 1996) — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claim is Epstein & Axtell's, not tuned. Source:
*Growing Artificial Societies* (1996).

**Model (faithful):** 50×50 toroidal grid, two sugar peaks, regrow rule (G∞ instant or
+1/tick — documented). N agents: vision v~U{1..6}, metabolism m~U{1..4}, initial sugar
w0~U{5..25}. Rule M: look v cells in the 4 directions, move to nearest unoccupied
max-sugar cell, harvest, subtract metabolism, die if sugar<0. Outcome = Gini of wealth.
Average over ≥10 seeds; report variance.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Strong wealth inequality emerges. | final mean Gini ≥ 0.40 |
| P2 | Inequality rises far above the initial. | final Gini − initial Gini ≥ 0.15 |
| P3 | Wealth distribution is right-skewed. | mean wealth > median wealth AND top-decile share ≥ 0.30 |

**Discipline:** grid, agent-attribute ranges, regrow rule, N, seeds FIXED + the metric
(Gini) locked before the run; no tuning. Falsified clause → MISS.
