# Erdős–Rényi giant component — FINDINGS

**Status: 3/3 locked clauses REPRO.** Authored BEFORE the L3 bundle (the bundle
fingerprints this file).

## What this is — and what it is NOT (read first)

This is a **network-GENERATION reproduction, not an agent-stepping ABM.** There are no
agents, no scheduler, no ticks, and no platform `step` loop. We draw an Erdős–Rényi
random graph G(n, p) and measure a single **static structural property** — the fraction
of nodes in the largest connected component — then compare it to the classic
self-consistent prediction. It is reproduced faithfully as a network-science result; it
does not exercise the agent-stepping machinery the way SIS, Voter, or Watts cascades do.
The lock-first → honest-verdict → L3-bundle discipline still applies in full.

## Model and metric (FIXED before the run; no tuning)

- **Graph:** G(n, p) with **n = 10,000**. Mean degree z = p(n−1) is swept. We build with
  networkx `gnm_random_graph` (the G(n, m) ensemble with m = round(z·n/2)) so the
  realised mean degree z = 2m/n is **exact** rather than in-expectation; the two
  ensembles are asymptotically equivalent and gnm removes one source of seed-to-seed
  degree noise.
- **Outcome metric (LOCKED):** fraction of nodes in the largest connected component,
  **mean over 10 seeds** (variance reported).
- **z-grid (LOCKED):** 0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0.
- **Theory:** giant fraction S is the surviving root of **S = 1 − e^(−zS)**, obtained by
  fixed-point iteration from S = 1 to convergence (S = 0 for z ≤ 1).
- **Determinism:** trial i uses graph seed `seed_base + i`; same seed → identical graph →
  identical fraction.

## Results — largest-component fraction vs z (mean over 10 seeds)

| z   | mean fraction | stdev  | min    | max    | S = 1−e^(−zS) | \|mean − S\| |
|-----|--------------|--------|--------|--------|---------------|-------------|
| 0.5 | 0.0018       | 0.0004 | 0.0013 | 0.0026 | 0.0000        | 0.0018      |
| 0.8 | 0.0067       | 0.0025 | 0.0042 | 0.0124 | 0.0000        | 0.0067      |
| 1.0 | 0.0427       | 0.0227 | 0.0128 | 0.0922 | 0.0000        | 0.0427      |
| 1.2 | 0.3094       | 0.0130 | 0.2802 | 0.3311 | 0.3137        | 0.0043      |
| 1.5 | 0.5832       | 0.0065 | 0.5713 | 0.5959 | 0.5828        | 0.0004      |
| 2.0 | 0.7991       | 0.0036 | 0.7924 | 0.8040 | 0.7968        | 0.0023      |
| 3.0 | 0.9400       | 0.0018 | 0.9370 | 0.9427 | 0.9405        | 0.0005      |

The transition is sharp: the largest component is sub-percent for z < 1, jumps through a
high-variance critical region at z ≈ 1 (stdev 0.0227 — the largest in the sweep, exactly
where finite-size critical fluctuations are expected), and tracks the theoretical S
closely from z = 1.2 upward.

## Verdicts on the LOCKED metric (refutation tier; falsified would be MISS)

- **P1 — REPRO.** Giant component absent below z=1, present above:
  frac(z=0.5) = **0.0018 < 0.05** AND frac(z=2.0) = **0.7991 > 0.40**.
- **P2 — REPRO.** Sharp transition near z=1: the mean fraction rises monotonically
  (non-decreasing across the whole grid) from 0.0018 at z=0.5 to 0.7991 at z=2.0,
  crossing z=1 (where it is still only 0.0427, with the high critical-region variance).
  Total rise = **0.7973**.
- **P3 — REPRO.** Measured fraction matches the self-consistent S = 1−e^(−zS) within
  ±0.05 at all three locked points: z=1.5 dev **0.0004**, z=2.0 dev **0.0023**, z=3.0 dev
  **0.0005**. Worst deviation **0.0023** ≪ 0.05.

## Caveats / honest scope

- **Network-generation, not agent-based** (restated): no agents/scheduler/ticks. Do not
  cite this as evidence the agent-stepping platform reproduces a dynamical process — it
  does not test that path.
- **Finite-size effects at the critical point.** At exactly z=1 the measured fraction
  (0.0427) is non-zero and high-variance, while the asymptotic theory gives S=0. This is
  the expected n=10,000 finite-size critical scaling (largest component ~ n^(2/3) at
  z=1), not a deviation from theory; P1/P2 are graded at z=0.5 and z=2.0 precisely to
  avoid grading on this knife-edge.
- **Synthetic model, no real-world data.** The contribution is whether the lock-first
  harness + discipline reproduce the classic phase transition and would catch an
  artifact, not a novel empirical finding.
- **gnm vs gnp.** Using exact-m gnm rather than independent-edge gnp is a deliberate
  variance-reduction choice, faithful to the asymptotically-equivalent ensemble; results
  are not sensitive to this at n=10,000.

## Reproduce

```
PYTHONPATH=. .venv/bin/python examples/repro_erdos_renyi/run.py
PYTHONPATH=. .venv/bin/python -m pytest tests/classics/test_erdos_renyi.py -q
```

Source: Erdős, P. & Rényi, A. (1960). *On the evolution of random graphs.* Publ. Math.
Inst. Hungar. Acad. Sci. 5:17–61.
