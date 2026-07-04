# Axelrod 1986 Norms / Metanorms — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Axelrod (1986), not tuned. Genuine
agent-based. Axelrod's own result is that metanorms HELP but do not guarantee the norm, so the
locked clauses are COMPARATIVE (metanorms raise enforcement vs no-metanorm), not "always
establishes".

**Model:** N=20 player agents, (boldness B, vengefulness V) ∈ {0..7}². Defect prob ∝ (1−B/7);
defection: temptation T=3, hurt H=−1 to others; if seen (prob S), punished with prob V/7 (defector
−9? use Axelrod's E=−9 to defector, P=−2 to punisher). METANORM variant: a non-punishing witness is
itself punished (prob ∝ another's V, same costs). Evolutionary update each generation (reproduce ∝
payoff + mutation). ≥20 seeds, ~100 generations.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Without metanorms, the norm collapses. | no-metanorm: final mean vengefulness < 2.5 (norm not enforced) in the majority of seeds |
| P2 | Metanorms raise enforcement. | with-metanorm seed-mean final vengefulness > no-metanorm seed-mean final vengefulness |
| P3 | The contrast holds. | (vengefulness_meta − vengefulness_nometa) > 0 AND boldness_meta < boldness_nometa |

**Discipline:** N, payoffs, generations, seeds FIXED + metric locked; the only difference is the
metanorm; no tuning. Falsified → MISS. (Stochastic + init-sensitive — report seed spread.)
