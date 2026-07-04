# Cyclic cellular automaton (1991) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Fisch, Gravner & Griffeath 1991 (cyclic cellular automata
in 2D), not tuned. **CA (disclosed).** Verified; gate-checked.

**Model:** n-colour cyclic cellular automaton on a 2D torus, Moore neighbourhood, threshold 1. Cell in
colour k advances to colour (k+1) mod n iff at least one Moore neighbour already holds colour (k+1) mod n;
otherwise it stays. Random uniform initial colours. Colours form a cyclic dominance ladder 0→1→…→n-1→0.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Spiral phase for small n. | for n = 8 on a 256×256 torus from random IC, the system self-organises into persistent rotating spirals: after a transient the fraction of cells changing colour per step settles to a nonzero plateau (> 0.2) rather than freezing. |
| P2 | Fixation (debris) for large n. | for n = 16 (above the critical colour count) the dynamics fixate: the fraction of cells changing colour per step decays to < 0.01 within the run — a sharp spiral→fixation transition as n crosses n_c. |
| P3 | Cycle period equals n in the spiral phase. | in the n = 8 spiral phase a cell that keeps cycling returns to its starting colour every n steps: the dominant temporal period of colour at persistently-active cells equals n (± 1). |

**Discipline:** n grid, neighbourhood, threshold, seeds FIXED; metrics (change-fraction plateau, colour-return
period) locked; no tuning. Falsified → MISS. gate_design_check: n=8 is inside the known spiral regime for
Moore/threshold-1 and n=16 inside the fixating regime; period graded as colour-return period (± 1), not by
tracking one hand-picked core.
**Distinctness (keep):** cells deterministically advance through n>3 cyclic colour states by neighbour-matching
(no payoff game); the lockable result is a spiral-vs-fixation transition in the number of colours n — absent
from rock_paper_scissors (3-species payoff ESS) and game_of_life.
