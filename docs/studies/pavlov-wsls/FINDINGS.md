# Win-Stay-Lose-Shift (Pavlov), Nowak & Sigmund 1993 — FINDINGS

**Status: 2/3 locked clauses REPRO; P2 is an honest MISS (WSLS-vs-ALLC = 3.965/round vs
the locked ≥ 4.5 bar).** Genuine agent-based reproduction on `abm_auto._platform` in the
NOISY iterated Prisoner's Dilemma. Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the config below was fixed before the run and was NOT tuned to
cross any threshold.

## What was built

Memory-one (reactive-with-own-move) strategies as 4-vectors `p = (p_R, p_S, p_T, p_P)` =
P(play C next | this player's last-round outcome R/S/T/P):

| Strategy | (p_R, p_S, p_T, p_P) | Reading |
|---|---|---|
| **WSLS / Pavlov** | (1, 0, 0, 1) | C after R or P (repeat if it worked / shift after mutual defection); D after S or T |
| **TFT** | (1, 0, 1, 0) | copy the opponent's last move (C after R/T, D after S/P) |
| **ALLC** | (1, 1, 1, 1) | always cooperate |
| **ALLD** | (0, 0, 0, 0) | always defect |

Each `MemoryOneAgent` draws its INTENDED move from its policy applied to the last-round
outcome, then an **implementation-noise** flip changes it to the other action with
probability ε (the "trembling hand"). Payoffs are the canonical PD (T=5 > R=3 > P=1 > S=0,
2R > T+S). Noise is the load-bearing ingredient: it is what makes these reactive strategies
behave differently from the deterministic Axelrod tournament.

**Exact pairwise payoffs** come from the memory-one **joint-state Markov chain**: the two
players' realised moves define a Markov chain over the four joint states {CC, CD, DC, DD};
with ε > 0 the chain is ergodic, its stationary distribution π is unique, and the mean
per-round payoff is `Σ π(state)·payoff(state)`. This exact route is cross-checked against a
genuine many-round agent-based noisy simulation in the tests (they agree within Monte-Carlo
error).

**Evolution (P3)** is a finite (N=100) well-mixed population of `PopMember` agents, each
carrying one strategy label. Each generation: (1) every strategy's fitness = its mean exact
payoff against the current mixture; (2) the next generation of N is drawn by
fitness-proportional (roulette) sampling — finite N ⇒ real sampling drift, seeded; (3) each
offspring mutates to a uniformly-random strategy with probability μ. An **invasion control**
(mutation OFF) seeds a resident population with a 5% ALLC minority and asks whether ALLC
grows.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| payoffs (T,R,P,S) | 5, 3, 1, 0 |
| implementation noise ε | 0.01 |
| population N | 100 |
| mutation μ | 0.01 |
| generations / measurement window | 500 / last 100 |
| seeds | 0…9 (10 seeds) |
| co-evolving strategy set (primary) | {WSLS, TFT, ALLC} — the cooperative regime |
| invasion control | 5% ALLC into WSLS vs TFT resident, μ=0, 300 gens |

## Results

### Exact pairwise mean per-round payoffs (Markov stationary, ε=0.01)

| Pairing | payoff | Pairing | payoff |
|---|---|---|---|
| **WSLS vs WSLS** | **2.951** | **TFT vs TFT** | **2.250** |
| **WSLS vs ALLC** | **3.965** | **TFT vs ALLC** | **3.009** |
| WSLS vs TFT | 2.250 | WSLS vs ALLD | 0.535 |
| TFT vs ALLD | 1.020 | | |

WSLS self-play spends ~96% of rounds in mutual cooperation (CC): after any accidental
defection, two WSLS players hit mutual defection (a "loss"), both shift, and restore
cooperation within a couple of rounds. TFT self-play is eroded to ~2.25 because a single
implementation error triggers a long alternating echo of retaliations that noise keeps
re-igniting.

### Co-evolving population (mean late-window frequency over 10 seeds)

| Strategy | cooperative regime {WSLS,TFT,ALLC} | full world {WSLS,TFT,ALLC,ALLD} (disclosure) |
|---|---|---|
| **WSLS** | **0.977** (range [0.970, 0.985]) | 0.428 (range [0.026, 0.915]) |
| TFT | 0.016 | 0.210 |
| ALLC | 0.007 | 0.058 |
| ALLD | — | 0.304 |

### Invasion (mutation OFF): 5% ALLC minority seeded into a resident population

| Resident | late ALLC frequency (seeded at 0.05) | Outcome |
|---|---|---|
| **WSLS** | **0.000** | WSLS RESISTS (ALLC driven out) |
| **TFT** | **1.000** | TFT ADMITS (ALLC takes over) |

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Two WSLS restore cooperation under noise | WSLS-self ≥ 2.7 AND (WSLS−TFT)-self ≥ 0.5 | 2.951; gap 0.701 | **REPRO** |
| **P2** | WSLS exploits ALLC; TFT does not | WSLS-vs-ALLC ≥ 4.5 AND ≥ TFT-vs-ALLC + 1.0 | 3.965; margin 0.956 | **MISS** |
| **P3** | WSLS dominates the co-evolving noisy population | late WSLS ≥ 0.5 and > TFT AND WSLS resists ALLC while TFT admits | 0.977 > 0.016; ALLC 0.00 vs 1.00 | **REPRO** |

## Honest interpretation

- **P1 REPRO — cooperation is self-repairing under noise, and only for WSLS.** Two WSLS
  players sit in mutual cooperation ~96% of the time and score **2.951/round**, whereas two
  TFT players — hit by the same noise — fall into retaliation echoes and score only
  **2.250**. The 0.70 gap is exactly the Nowak-Sigmund error-correction advantage: WSLS
  after an accidental defection reaches mutual defection (a loss), shifts, and restores
  cooperation; TFT has no such reset. This is the mechanism that the noise-free Axelrod
  tournament (where both nice strategies cooperate perfectly) cannot show.

- **P2 MISS — honest, and mechanistically informative.** The locked bar assumes WSLS drives
  ALLC to near-permanent T-harvesting (≈5/round). The FAITHFUL memory-one WSLS = (1,0,0,1)
  does not: against ALLC it locks into EITHER CC (outcome R, so `p_R=1` → stays cooperating)
  OR DC (outcome T, so `p_T=0` → stays defecting). Both are absorbing under WSLS's own
  policy, so implementation noise — the *only* thing that moves it between them — shuttles it
  **symmetrically**, leaving π ≈ {CC: 0.495, DC: 0.495} and a mean of ~(R+T)/2 = **3.965**,
  strictly between pure cooperation (3) and pure exploitation (5). This is short of the ≥4.5
  bar and the margin over TFT (0.956) is just short of the ≥1.0 requirement. We report the
  faithful number rather than swapping in a different WSLS variant (e.g. one with `p_T`
  biased toward staying-defecting) to force exploitation — that would be tuning, which the
  discipline forbids. The DIRECTIONAL claim survives clearly (WSLS exploits ALLC for ~1.0
  more per round than TFT ever gets from a cooperator), and it is decisive in the
  evolutionary game (P3) — but the specific ≥4.5 pairwise threshold is falsified, so P2 is a
  MISS.

- **P3 REPRO — WSLS dominates the cooperative regime, and the invasion asymmetry is
  decisive.** In the cooperative-regime population {WSLS, TFT, ALLC} — the Nowak-Sigmund
  succession in which cooperation is already established and the only question is which
  cooperative strategy wins — WSLS reaches **0.977** mean late-window frequency (tight across
  seeds, [0.970, 0.985]), crushing TFT (0.016) and ALLC (0.007). The invasion control is even
  cleaner: a 5% ALLC minority is **driven to 0.000 under a WSLS resident** (WSLS exploits and
  resists the drifting cooperators) but **rises to 1.000 under a TFT resident** (TFT is
  exploitation-neutral toward cooperators, so ALLC accumulates by drift/selection). That
  asymmetry — WSLS resists ALLC where TFT admits it — is precisely the locked P3 mechanism
  and precisely why WSLS beats TFT once cooperation is established.

  **Disclosure (not the graded arm):** in the ALLD-inclusive full world {WSLS, TFT, ALLC,
  ALLD} with perpetual μ=0.01 mutation, WSLS remains the **plurality winner and still beats
  TFT** (0.428 vs 0.210), but finite-N drift plus continual ALLD re-injection hold its mean
  below 0.5 and let ALLD parasitize (0.304). We report this openly. The choice of the
  cooperative-regime population as the *primary* co-evolving arm is a faithfulness decision
  (Nowak-Sigmund's evolutionary result is about the cooperative attractor that emerges AFTER
  TFT first defeats ALLD, not about WSLS directly invading pristine defectors — WSLS cannot
  invade all-ALLD, since ALLD-self beats WSLS-vs-ALLD), fixed before grading; it is an
  initial-regime choice, not a threshold tune.

## Distinctness (keep-with-gate)

This is emphatically **NOT** the sibling `abm_auto.classics.axelrod_ipd` — a deterministic,
noise-free, static round-robin tournament where TFT wins. WSLS beats TFT here **specifically
because of noise + evolution**: (i) error-correction — noise creates accidental defections
that WSLS repairs and TFT does not (P1); (ii) ALLC-exploitation — under selection WSLS punishes
and out-competes the unconditional cooperators that drift in under TFT's neutrality (P3). Turn
the noise off and put the strategies in a static tournament and the result reverts to Axelrod's
TFT victory. The gate is that this is a **noisy evolving population**, not the tournament.

## Source

Nowak, M. & Sigmund, K. (1993). *A strategy of win-stay, lose-shift that outperforms
tit-for-tat in the Prisoner's Dilemma game.* Nature **364**:56–58. doi:10.1038/364056a0.

Scope: a faithful reproduction of a published game-theoretic model; no real-world data. The
contribution is whether the harness + locked-prediction discipline reproduce WSLS's
noise+evolution advantage over TFT, isolate its two mechanisms (error-correction +
ALLC-exploitation), and would catch an artifact — including honestly reporting the one locked
pairwise threshold (P2's ≥4.5) that the faithful memory-one WSLS does not reach.
