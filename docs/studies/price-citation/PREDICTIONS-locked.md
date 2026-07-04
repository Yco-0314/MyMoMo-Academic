# Price Cumulative-Advantage Citation Model — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is de Solla Price 1965/1976 (Newman derivation), not
tuned. **Network-generation (disclosed).** Verified; gate-checked (bars use finite-size-ROBUST
structural quantities, not brittle exponent fits).

**Model:** growing DIRECTED graph. Nodes (papers) added one at a time; each new node emits m out-edges
(citations) to EXISTING nodes only, choosing target j with probability ∝ (in-degree k_j + a). a = 1
(Price's additive constant), m = 3 ⇒ target exponent γ = 2 + a/m = 2.33. Grow N ≥ 50,000 (N ≥ 100,000
for the tail). ≥20 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Directed DAG with constant out-degree (structural signature). | at N≥50k, m=3, a=1: every non-seed node has out-degree exactly 3 (out-degree variance ≈ 0); in-degree max k_max ∈ [40, 400] (>20·m); Var(in-degree)/Var(out-degree) > 50. |
| P2 | Large never-cited mass (finite-size-robust, BA gives 0). | fraction of zero-in-degree nodes ∈ [0.52, 0.62] (analytic p_0=(m+1)/(2m+1)=4/7≈0.571). |
| P3 | Heavy-tailed TUNABLE power-law tail γ < 3. | Clauset-MLE tail exponent γ̂ (KS-selected k_min) ∈ [2.1, 2.9] (target 2.33, wide band absorbs finite-size upward bias) — significantly below 3; a contrast run m=1,a=1 gives γ̂ noticeably higher (≈2.6–3.4), showing a/m tunability. |

**Discipline:** N, m, a, seeds FIXED + metrics locked; no tuning. Use m≥2 (m=1,a=1 ⇒ γ=3 degenerate with
BA — excluded as the discriminating run). Falsified → MISS. **Distinctness (keep-with-gate):** BA is the
UNDIRECTED version with p_0=0, γ=3, no additive-constant knob; the built config-model samples a FIXED
degree sequence (no growth/cumulative-advantage). A BA rerun fails P1 (undirected), P2 (p_0=0), and the
γ<3 half of P3.
