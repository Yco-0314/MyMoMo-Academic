# Win-Stay-Lose-Shift (Pavlov) — adversarial review

**tier: deep** (trigger: 1 honest MISS). Reviewed vs the verified claim + lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (WSLS self 2.951, WSLS-vs-ALLC 3.965, late WSLS freq 0.977) matches bundle/results; exact Markov payoffs cross-checked vs agent-based sim (~0.01).
- fair-control: **pass** — P3's invasion asymmetry (5% ALLC under a WSLS resident vs a TFT resident) is a clean single-variable A/B.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; L3 integrity gate ok.
- mechanism-aliveness: **pass** — the two load-bearing mechanisms are vividly alive: error-correction (WSLS self-play ~96% CC under noise) and ALLC-exploitation asymmetry (ALLC → 0 under WSLS resident, → 1.0 under TFT resident).
- framing-disclosure: **pass** — noisy EVOLVING population (not the deterministic Axelrod tournament); the distinctness gate is honored.

## Verdict: model FAITHFUL; P2 is an HONEST MISS from an OPTIMISTIC LOCKED BAR (not a bug).
- **P1 REPRO** — WSLS restores cooperation under noise (self 2.951 ≥ 2.7; gap over TFT 0.701 ≥ 0.5).
- **P2 MISS** — WSLS-vs-ALLC = 3.965/round (locked bar ≥ 4.5) and margin over TFT 0.956 (bar ≥ 1.0).
  This is CORRECT physics, not a bug: faithful memory-one WSLS=(1,0,0,1) vs ALLC locks into EITHER CC
  (R=3) OR DC (T=5) — both absorbing under its own outcome-indexed policy — so symmetric noise gives
  π≈{CC:0.495, DC:0.495} and mean ≈ (R+T)/2 = 4.0, strictly between cooperation and exploitation.
  **The locked ≥4.5 bar was over-optimistic; the true faithful value is ~4.0.** The DIRECTIONAL claim
  (WSLS out-earns TFT vs a cooperator) holds; only the specific threshold misses. Not tuned.
- **P3 REPRO** — WSLS dominates the co-evolving noisy population (late freq 0.977 ≫ TFT 0.016); the
  invasion asymmetry is decisive. The ALLD-inclusive world is disclosed (WSLS plurality 0.428 > TFT 0.210,
  held under 0.5 by perpetual ALLD mutation + finite-N drift).

## Discipline check: PASS. Gate-design lesson (recurring).
2/3 REPRO reported honestly; no tuning. The WSLS-beats-TFT thesis REPRO via P1 (error-correction) + P3
(evolution/invasion). Same lesson as q-voter/social-impact/PSV: a locked NUMERIC bar (≥4.5) was optimistic;
the faithful value is a computable constant ((R+T)/2). 32 tests. Distinctness gate honored.

REVIEW COMPLETE
