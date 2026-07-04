# Abrams-Strogatz language competition — review

**tier: minimal** (all-REPRO 3/3; every margin comfortable; no load-bearing dead-mechanism
risk). Reviewed against the verified canonical claim (Abrams & Strogatz 2003, Nature 424:900).

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (interior=0.000, boundary error 0.0232, equal-status
  symmetry error 0.037) matches verdict-bundle.json + results.json.
- fair-control: **n/a** — no two-arm contrast; P2 compares the measured basin boundary to the
  analytic mean-field unstable fixed point (a derivation, not a tuned second arm).
- no-post-lock-drift: **pass** — the three graded metrics match PREDICTIONS-locked.md.
- mechanism-aliveness: **pass** — the dynamics actually drive interior→{0,1} (interior fraction
  0.000, no stable coexistence) and the measured boundary 0.2361 sits near the analytic FP 0.2128.
- framing-disclosure: **pass** — docstring + FINDINGS disclose this is the "well-mixed stochastic
  form" reproducing the mean-field ODE, a "synthetic model reproduction, not empirical validation",
  with the "practical no-coexistence signature rather than literal all-agent monolinguality".

## Verdict: SOUND. Faithful stochastic agentization of the canonical mean-field ODE.
3/3 REPRO with comfortable margins (P2 error 0.0232 vs 0.08 bar; P3 symmetry 0.037 vs 0.10). The
analytic unstable fixed point is computed correctly (`basin_boundary`), and a≈1.31 is used as a
representative >1 exponent (not over-claimed as universal — consistent with the verified subtlety).
Faithfulness test present (tests/classics/test_abrams_strogatz.py, 10 passing). No tuning, no
fabrication, framing honest.

REVIEW COMPLETE
