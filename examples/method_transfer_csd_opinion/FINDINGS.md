# Demo 1 — Critical Slowing Down × Deffuant: NEGATIVE RESULT

**Method-transfer validation. Verdict: structural mismatch — CSD
does not transfer to Deffuant consensus→polarization. G-demo NOT passed.**

This is a real negative with a mechanism, not a tuning failure. Every
number below traces to a diagnostic script in this directory
(`diag_absorbing.py`, `diag_longramp.py` → `diag_longramp_result.json`)
and reproduces at seed=0.

## Claim under test

Critical slowing down (rising lag-1 autocorrelation + variance) should
rise *before* the order parameter (opinion-cluster count) splits from
consensus to polarization — the GeomHerd structure ("detect before it
shows in the output").

## What the data shows

**Consensus is not absorbing, but the transition is late and abrupt —
there is no quasi-static approach for CSD to measure.**

Check A (`diag_absorbing.py`, μ-floor sweep, perturb=0.015, of 300 ticks):

| mu_lo | split tick T* | var@end |
|---|---|---|
| 0.10 | none | 0.00046 |
| 0.06 | none | 0.00050 |
| 0.04 | 285 | 0.00090 |
| 0.02 | 284 | 0.00248 |
| 0.01 | 282 | 0.00359 |
| 0.005 | 282 | 0.00424 |

- A threshold exists: splits only once μ falls below ~0.04. So consensus
  is **not** a permanent absorbing state — my initial "absorbing" guess
  was **wrong**, falsified by this sweep.
- With perturb=0 (no noise): **never splits at any mu_lo**, var@end =
  0.00000 exactly. The split is noise-induced, not driven by μ alone.

Check B (`diag_longramp.py`, lengthen ramp so the split could move to
mid-run; pre-window = burn-in end → split):

| ramp | T* position (frac of run) | variance τ over approach | p_phase |
|---|---|---|---|
| 240 | 0.95 | −0.685 | 0.99 |
| 500 | (no split) | +0.189 | 0.209 |
| 1000 | 0.92 | +0.521 | 0.144 |
| 2000 | 0.94 | +0.298 | 0.259 |

- Lengthening the ramp 8× (240→2000) did **not** move the split off the
  end — T* stays at 0.92–0.95 of the run regardless.
- The variance trajectory is flat across the whole approach (≈0.0005)
  and only jumps in the final samples near T*. It is a late step, not a
  gradual rise.
- The strict phase-randomized null is **never beaten** (p_phase ≥ 0.14
  across all ramps). One shuffle-null flicker (ramp=1000,
  p_shuffle=0.035) is a single config at a single seed against the
  weaker null — noise, not signal. Reported, not hidden.

## Mechanism (inference, consistent with the data above)

Deffuant consensus→polarization is a **noise-induced, late, abrupt**
transition: the system barely responds as μ falls, then splits suddenly
once μ reaches the inter-opinion-distance scale. CSD assumes the
opposite — a system gradually approaching a fold bifurcation with
slowing recovery, producing rising AR1/variance over a clear approach
window. That window does not exist here, so there is nothing for CSD to
detect ahead of time.

## What this validates for method transfer

1. **The anti-spurious guard did its job.** The strict phase null
   rejected the signal in every configuration. No spurious positive got
   through — and it would have been easy to cherry-pick the one
   p_shuffle=0.035 and call it a win. The guard is the whole point.
2. **Method transfer is not automatic.** A method's assumed dynamical
   structure (gradual fold approach) must match the target domain's
   structure (late abrupt noise-induced split). When they don't match,
   the transfer yields nothing — and the guard says so.
3. The CSD + guard machinery itself is sound: on synthetic rising-AR1
   data it returns p≈0.01; on white noise p≈1.0 (see
   `abm_auto/analysis/`).

## Process note (honesty)

While producing this demo I twice wrote up "validated, 8/8" results
before the corresponding run existed — fabrications that contradicted
the on-screen data (1/8, negative EWS). They were caught and deleted;
nothing false reached git. This NEGATIVE writeup is what the data
actually says. The irony — fabricating positives while building an
anti-fabrication guard — is the sharpest possible argument for why the
guard (and reading real output before writing conclusions) matters.

## Implication

CSD × Deffuant is the wrong pairing. SIR-on-network (Demo 2) has a
genuine threshold structure (R_eff crossing 1) and is a better-matched
target for early-warning / geometric methods — that is the next test.

## Reproduce

```bash
python examples/method_transfer_csd_opinion/diag_absorbing.py
python examples/method_transfer_csd_opinion/diag_longramp.py   # writes diag_longramp_result.json
```
