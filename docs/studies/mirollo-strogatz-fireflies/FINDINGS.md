# Mirollo-Strogatz Pulse-Coupled Oscillators (1990) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Genuine-agent reproduction (**disclosed**:
integrate-and-fire oscillators — each of the N agents carries its own phase; the firing
oscillator pulls every other agent up). Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the config below was fixed before the run and only `eps` (the P2
coupling control) and the curve shape `b>0` vs `b=0` (the P3 concavity control) were dialled.
Nothing was tuned to make a clause pass.

## What was built

N = 100 integrate-and-fire oscillators, event-driven. Each agent carries a phase `phi` in
[0, 1] rising at unit rate; its "voltage" is a smooth, monotone, **concave-down** charging
curve

    x = f(phi) = (1/b) * ln(1 + (e^b - 1) * phi),   b > 0

with `f(0)=0`, `f(1)=1`, `f' > 0`, `f'' < 0`, and its **exact** inverse
`f_inv(x) = (e^{b x} - 1)/(e^b - 1)`. The LINEAR control curve `f(phi) = phi` (`b = 0`,
`f_inv(x) = x`) has no concavity — the same monotone charging, but a straight line.

**The event-driven dynamics (the Mirollo-Strogatz rules).** Advance every phase uniformly by
`dt = 1 - max_i phi_i` so the leading oscillator(s) reach `phi = 1` and FIRE. A firing group:

  1. **resets** to `phi = 0`;
  2. delivers **one collective pulse of size `eps`** to every other oscillator, in VOLTAGE:
     `x_j -> min(1, x_j + eps)`, i.e. `phi_j -> f_inv(min(1, f(phi_j) + eps))`;
  3. **ABSORPTION**: any oscillator driven to/over threshold by *that single pulse* fires in
     the same instant and **coalesces** into the firing group — reset to 0 together, sharing
     one group label, phase-locked forever after (identical phase => identical future kicks).

**Full synchrony** = all N oscillators collapse into ONE firing group (equivalently, one
distinct group label remains). The only randomness is the seeded initial-phase draw
(`phi_i ~ U(0,1)`, distinct); every event afterwards is deterministic.

**The one faithfulness subtlety that mattered — a firing is ONE pulse, not a domino.** A
phase-locked firing group behaves as a single oscillator and therefore emits **one** `eps`
pulse. An earlier build let each newly-absorbed member re-kick the survivors within the same
event (a `queue` of re-firings), so an oscillator sitting at voltage 0.03 was dragged over
threshold by ~99 successive `eps` kicks — the whole population collapsed in a **single**
cycle regardless of `eps`. That is not the Mirollo-Strogatz model: it destroys the
coupling-strength dependence (P2) and inflates absorption. The fix — apply exactly one
collective `eps` pulse per firing event, absorbing only those the *single* pulse reaches —
is pinned by a dedicated faithfulness test (`test_single_pulse_not_a_domino`) and by the
absorption / phase-lock tests. With the correct single-pulse rule, cycles-to-sync becomes a
real, `eps`-dependent quantity (median 17 at `eps=0.1`), which is exactly what P2 measures.

## Per-clause results (from the actual run: N=100, 20 seeds, max_cycles=20000)

### P1 — Universal synchronization (measure-1): **REPRO**
Concave curve (`b=3`), `eps=0.1`: **sync fraction = 1.000 (20/20 seeds)** reach FULL sync
(all 100 oscillators in one firing group; worst-case final group count = 1). Locked bar was
`>= 0.95`. Median cycles-to-sync = 17 (per-seed range 11-31). Every seed, from independent
random initial phases, synchronizes with NO finite coupling threshold — the measure-1
synchrony result. **REPRO** (1.000 >= 0.95).

### P2 — Coupling speeds synchronization (monotone in eps): **REPRO**
Same concave curve, coupling dialled:

| eps  | median cycles-to-sync | mean | sync fraction |
|------|-----------------------|------|---------------|
| 0.05 | **31.5**              | 33.7 | 1.00          |
| 0.20 | **8.0**               | 8.45 | 1.00          |

Stronger pulse coupling synchronizes strictly faster: median 8.0 at `eps=0.2` vs 31.5 at
`eps=0.05`, and the per-seed distributions do not overlap (strong arm's slowest seed = 13
cycles < weak arm's fastest = 24). **REPRO** (8.0 < 31.5).

### P3 — Concavity is necessary: **REPRO**
LINEAR curve (`b=0`, `f(phi)=phi`), SAME protocol (`N=100`, `eps=0.1`, same 20 seeds):
**sync fraction = 0.000 (0/20 seeds)** reach full sync. The final state stalls at 9-10
distinct firing groups for every seed. Locked bar was `< 0.50`. With a linear charging curve
a `+eps` voltage kick is a `+eps` phase kick for every oscillator, so it preserves phase
*differences* between un-absorbed oscillators — the group structure freezes and never
collapses to one. Flipping ONLY the curve shape (concave -> linear), with the identical pulse
coupling, takes sync from 100% to 0%: it is the curve's **CONCAVITY**, not the pulse coupling
alone, that drives the universal result. **REPRO** (0.000 < 0.50).

## Honest accounting

All three locked clauses REPRO. No clause was falsified; no threshold, metric, or parameter
was moved to make a clause pass. The single-pulse-vs-domino distinction was resolved as a
faithfulness **bug fix** in the firing rule (caught before locking any verdict), not a knob:
the correct Mirollo-Strogatz rule (one `eps` pulse per firing group, absorbing only those it
reaches) is what makes cycles-to-sync a meaningful, `eps`-graded quantity and is required for
faithfulness regardless of the outcome.

## Distinctness (why this is not Kuramoto)

Discrete integrate-and-fire **pulse** coupling with hard state resets and **absorption**
(firings coalescing into phase-locked groups), synchronizing for almost-every initial
condition with **no finite coupling threshold**, and depending on the charging curve's
**concavity** (P3: linear -> no sync). This is absent from Kuramoto (continuous sinusoidal
mean-field coupling, a finite critical `K_c`, no firing / reset / absorption, no concavity
dependence).

## Reproduce

    .venv/bin/python -m pytest tests/classics/test_mirollo_strogatz_fireflies.py -q
    PYTHONPATH=. .venv/bin/python examples/repro_mirollo_strogatz_fireflies/run.py

Model + experiment helpers: `abm_auto/classics/mirollo_strogatz_fireflies.py`.
Paper: Mirollo, R.E. & Strogatz, S.H. (1990). Synchronization of pulse-coupled biological
oscillators. *SIAM Journal on Applied Mathematics* 50(6):1645-1662. doi:10.1137/0150098.
