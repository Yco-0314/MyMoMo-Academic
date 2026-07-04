# Win-Stay-Lose-Shift (Pavlov) — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Nowak & Sigmund 1993 (Nature 364:56), not tuned.
Genuine agent-based. Verified.

**Model:** noisy iterated Prisoner's Dilemma (T>R>P>S; canonical R=3,T=5,P=1,S=0). Memory-one
strategies as (p_R,p_S,p_T,p_P) = cooperation prob after each outcome; WSLS/Pavlov=(1,0,0,1), TFT=
(1,0,1,0), ALLC=(1,1,1,1), ALLD=(0,0,0,0). Implementation noise ε (each intended move flips w.p. ε;
ε≥0.01). Payoffs = mean per-round over many rounds. For P3, an evolutionary population (≥100 agents
or a replicator over the strategy set) with mutation, run to a late steady state, ≥10 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Two WSLS restore cooperation under noise. | WSLS-vs-WSLS mean payoff ≥ 2.7/round at ε=0.01, AND (WSLS_self − TFT_self) ≥ 0.5 (TFT self-play is eroded by noise). |
| P2 | WSLS EXPLOITS unconditional cooperators; TFT does not. | WSLS-vs-ALLC ≥ 4.5/round AND ≥ (TFT-vs-ALLC) + 1.0. |
| P3 | WSLS dominates the co-evolving noisy population. | late-run WSLS frequency ≥ 0.5 and > TFT; ALLC-vs-WSLS payoff < 0.1·(max) proxy: WSLS resists ALLC invasion (ALLC freq stays low) whereas a TFT population admits ALLC. |

**Discipline:** payoffs, noise ε, strategy set, rounds, population, mutation, seeds FIXED + metrics
locked; no tuning. Falsified → MISS. **Distinctness (keep-with-gate):** axelrod_ipd is a
deterministic noise-free static round-robin tournament where TFT wins; the WSLS result requires
NOISE + EVOLUTION (error-correction + ALLC-exploitation) — the gate is that this is a noisy
evolving population, not the tournament, and WSLS beats TFT specifically because of noise.
