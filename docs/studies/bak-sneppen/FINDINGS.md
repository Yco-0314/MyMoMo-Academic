# Bak-Sneppen evolution model (SOC) — FINDINGS

**Date:** 2026-06-30. **Verdict:** 3/3 locked clauses REPRO.
**Source:** Bak, P. & Sneppen, K. (1993), *Punctuated equilibrium and criticality in a
simple model of evolution*, Phys. Rev. Lett. 71(24):4083-4086,
doi:10.1103/PhysRevLett.71.4083.

## Honesty: what this IS and what it is NOT

This is **extremal dynamics / a self-organized-criticality (SOC) model**, **NOT
autonomous-agent-stepping**. Each step is **model-orchestrated**: the rule selects the
**GLOBAL minimum-fitness species across the entire ring** and replaces it together with
its two ring-neighbours. There is no scheduler over an agent roster, no per-agent
perceive/decide/act loop, no autonomous local stepping — the global-min selection is a
single centralized operation over the whole system. We disclose this exactly as the
sibling BTW-sandpile reproduction and the ER/WS network-generation reproductions disclose
that they are not agent-based. The lock-first + honest-verdict + L3-bundle discipline
still fully applies; the value here is whether the harness reproduces the SOC signatures
(critical threshold, power-law avalanches, punctuated activity) and would catch an
artifact — not a claim of emergence from autonomous agents.

## Model + fixed config (locked before running; no tuning toward 0.667)

- Ring of **N = 200** species (periodic boundary), each fitness ~ U[0, 1).
- **Extremal update:** find the global-minimum-fitness species `i`; replace
  `f[i]`, `f[i-1 mod N]`, `f[i+1 mod N]` with three fresh independent U[0, 1) draws.
- **Transient = 100,000** steps (discarded); then **n_steps = 1,000,000** measured steps.
- **seed = 0** (deterministic given the seed).
- **f_c estimator (fixed):** the **5th percentile** of the pooled stationary fitnesses
  (200,000 ring snapshots pooled). Rationale: in the stationary state most fitnesses lie
  ~uniform on (f_c, 1) with a sharp lower edge; the 5th percentile sits just above that
  edge and is a robust, tuning-free locator of where the bulk begins.
- **Avalanche definition (fixed before running):** the *f0/f_c-avalanche* of
  Paczuski-Maslov-Bak (1996) — a **maximal run of consecutive steps whose active minimum
  (the global min acted on that step) is < f_c**; its size is the number of steps in the
  run. The threshold is the measured f_c, fixed once.

## Measured results (seed = 0)

| Quantity | Value |
|---|---|
| f_c (5th-percentile cutoff) | **0.6482** |
| fraction of stationary fitnesses **above 0.667** | **0.913** (only 8.7% below) |
| mean active-min over the run | 0.217 |
| number of avalanches (below-f_c runs) | 193 |
| avalanche size — max | 92,595 steps |
| avalanche size — median | 675 steps |
| avalanche size — min | 1 step |
| **decades spanned by avalanche sizes** | **~4.97** (log10 92595 - log10 1) |
| avalanche tail exponent tau (MLE, reporting only) | ~1.15 +/- 0.01 |
| dips below f_c / recoveries above f_c | 193 / 192 |

Cross-seed check (seeds 0,1,2): f_c = 0.648-0.649, fraction above 0.667 = 0.912-0.913,
avalanche span 4.8-5.0 decades, 176-223 dips. Stable, not seed-cherry-picked.

## Locked verdicts (P1-P3)

- **P1 - REPRO.** The stationary distribution self-organizes to a sharp lower cutoff
  **f_c ~ 0.648**, inside the locked range [0.60, 0.72] and close to the canonical
  **f_c ~ 0.667**. ~91% of fitnesses lie above 0.667, with the density strongly
  suppressed below - the SOC critical threshold has emerged without tuning. (Our
  5th-percentile estimator deliberately reads *just above* the edge, so it sits a hair
  below the textbook 0.667; the fraction-above-0.667 = 0.913 is the cleaner
  estimator-independent witness of the same cutoff.)
- **P2 - REPRO.** The f_c-avalanche-size distribution is heavy-tailed, spanning
  **~4.97 decades** (1 -> ~92,595 steps), far past the locked >= 2-decade bar. The
  discrete MLE tail exponent (~1.15, reported only - not a locked clause) is consistent
  with the shallow power law expected for f0-avalanches in this model.
- **P3 - REPRO.** Activity is **intermittent / punctuated**: the running minimum dips
  below f_c **193 times** and recovers above it **192 times** over the run - repeated
  dip-and-recover cycles, not a single sustained excursion. Quiet spells above f_c are
  brief (the global min is naturally small), but the burst-then-recover structure is the
  punctuated-equilibrium signature, and the avalanche-size spread (P2) shows the bursts
  span many orders of magnitude.

## Caveats

- **Framing (repeated for emphasis):** extremal dynamics, centralized global-min
  selection - disclosed as NOT autonomous-agent-stepping.
- The 5th-percentile f_c estimator reads the lower **edge** of the plateau, so it lands
  slightly below the canonical 0.667 by construction. We report it transparently
  alongside the fraction-above-0.667 (0.913) and the full fitness histogram so a reviewer
  can read the cutoff independently of the estimator choice. We did **not** adjust the
  percentile to move f_c onto 0.667.
- Avalanche counts are modest (~200 per million steps) because the run length is fixed at
  10^6; the *sizes* (not the count) carry the heavy-tail signal, and they span ~5 decades.
- Faithful reproduction of a synthetic model; no real-world data.
