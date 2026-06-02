# Reproduction Spec — GeomHerd: Ricci-curvature herding detection (arXiv 2605.11645v1)

**Source**: GeomHerd PDF (Yang et al., arXiv 2605.11645v1, 20pp).
Extracted 2026-06-01 via printable-ASCII island extraction from
`docs/reproduce/_extract_pdf.py` output (the CID decoder returned 0 chars
on this PDF; the plain extractor's prose islands → /tmp/geomherd_prose.txt).
Equations are partly garbled by extraction; symbols marked ⚠️ need a
clean re-read or the HTML version (https://arxiv.org/html/2605.11645v1).
Nothing below is from memory.

## CRITICAL CORRECTION to Track 1's earlier framing

Earlier I assumed "Ricci × SIR". **GeomHerd does NOT use SIR.** Its
substrate is the **Cividino–Sornette continuous-spin agent-based model**
(a financial-market herding model), with an out-of-domain transfer to
the **Vicsek self-driven-particle model**. The herding signal lives on a
**behavioral-agreement agent graph**, not an epidemic transmission graph.

This matters for our Track 1: reproducing GeomHerd faithfully means
building the Cividino–Sornette substrate, not instrumenting our SIR
model. Applying Ricci curvature to our SIR transmission graph would be a
*method-transfer probe* (W7), NOT a reproduction of this paper. Two
different things — keep them distinct (this is exactly the W3
"interpretation" discipline).

## What GeomHerd does (confirmed from abstract + method islands)

1. **Substrate**: a heterogeneous LLM-driven multi-agent simulator —
   each trader is a persona-conditioned LLM call (varying risk appetite,
   momentum horizon, herding tendency) — treated as a "forecastable
   world". Headline testbed = Cividino–Sornette continuous-spin ABM.
   Only population-level behavioral sweeps are controlled.
2. **Dynamic agent graph G_t**: nodes = agents; **edges encode recent
   behavioral agreement** (a weight w_t(i,j) = how much agents i,j have
   recently agreed in action).
3. **Discrete Ollivier–Ricci curvature** on each edge (i,j) ∈ E_t:

   ```
   κ_OR(i,j,t) = 1 − W₁(μ_t^i, μ_t^j) / d_t(i,j)
   ```

   where W₁ = 1-Wasserstein distance solved exactly by linear
   programming (POT library), and the edge length **d_t(i,j) = w_t(i,j)**
   — agreement weight used **directly as similarity-as-distance** (higher
   agreement → shorter edge). The paper explicitly does NOT use 1/w or
   −log w (those would invert the herding-signal sign by mapping a
   herding clique to long distances). ⚠️ μ_t^i = the probability measure
   on i's neighborhood (standard OR construction) — exact mass
   definition needs clean re-read.
4. **Two curvature signals**: κ⁺_OR(t) (mean positive OR curvature) and a
   contagion-side signal (⚠️ the "Δ⁻"/second series — garbled glyph).
5. **Detector**: one-sided **CUSUM** on each signal, fired when dynamics
   deviate from a **pre-stress baseline**; contagion side augmented with
   a **Kendall-τ slope test** as a trend channel.

   ```
   S⁺_t = max(0, S⁺_{t−1} + (κ⁺_OR(t) − base⁺) − k⁺);  A⁺_t = 1[S⁺_t > h⁺]
   S⁻_t = max(0, S⁻_{t−1} + (... − base⁻) − k⁻);        A⁻_t = 1[S⁻_t > h⁻]
   contagion alarm also requires Kendall-τ over window [t−W, t] > thresh
   ```
6. **Theory bridge**: a **mean-field bridge mapping κ_OR → CSAD** (Cross-
   Sectional Absolute Deviation), the classical macroscopic herding
   statistic — this is the GeomHerd analogue of a "theory bridge"
   (exactly the rigor ADR-012 demands of method transfer).
7. **Event definition**: order parameter Va(t) crosses herding threshold
   **φ_event = 0.50**; curvature crosses geometric threshold
   **κ_geom = 0.30** *before* that. Lead time Δ = (event time) − (alarm
   time).

## Headline results (confirmed numbers from abstract)

- Primary detector fires a **median 272 steps before** order-parameter
  onset (continuous-spin substrate).
- Contagion detector recalls **65% of critical trajectories 318 steps
  early**.
- On co-firing trajectories, agent-graph signal precedes
  price-correlation-graph baselines by **40 steps**.
- Complementary indicator: **effective vocabulary of agent actions
  contracts** during cascades.
- Geometric signature **transfers out-of-domain to Vicsek**.
- Curvature-conditioned forecasting head reduces cascade-window
  log-return MAE vs detector-conditioned + price-only baselines.

## Dependencies (heavier than CSD)

- **POT** (Python Optimal Transport) for exact W₁ via linear programming.
- A graph library for the dynamic agent graph + neighborhoods.
- The Cividino–Sornette continuous-spin ABM as substrate (we do not have
  this model; it must be built or sourced).
- (Their full pipeline also uses persona-conditioned LLM agents; the
  *headline geometric result* is on the continuous-spin substrate, which
  is a classical ABM — reproducible without LLM calls.)

## Two distinct things we could build (DO NOT conflate)

| | What | Faithful to GeomHerd? | abm-auto wedge |
|---|---|---|---|
| **R-repro** | Build Cividino–Sornette substrate + OR-curvature + CUSUM + CSAD bridge | YES — reproduces the paper | reproduce mode + W7 analysis |
| **R-probe** | Apply OR-curvature to our existing SIR transmission graph | NO — new method×domain | W7 method-transfer probe |

R-probe is cheaper (reuses SIR + the event-stream prerequisite) but is
NOT a reproduction. R-repro is the real thing but needs a new substrate.
Decide explicitly before building.

## ⚠️ Gaps needing the HTML version or clean re-read

- Exact OR neighborhood measure μ_t^i (idleness/mass-on-self parameter α).
- The contagion-side second curvature series definition (garbled glyph).
- CUSUM constants k±, h±, baseline window length, Kendall window W.
- The agreement-weight w_t(i,j) update rule (decay? lookback window?).
- Cividino–Sornette substrate equations + parameters.

Next: pull the HTML version for the garbled equations before any
R-repro implementation. No implementation in this artifact.
