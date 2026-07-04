# TASEP with open boundaries (1993) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Derrida, Evans, Hakim & Pasquier 1993 (J Phys A 26:1493),
not tuned. **CA (disclosed).** Verified; gate-checked.

**Model:** totally asymmetric simple exclusion process on a 1D open chain of L sites. Random-sequential
update: a particle hops right into an empty site with rate 1; particles are injected at the left boundary
with rate α (if site 1 empty) and extracted at the right boundary with rate β (if site L occupied). Current
J = steady-state hopping rate across a bond; bulk density ρ = mean occupancy of the central region.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Maximal-current plateau J = 1/4. | for α, β > 0.5 (both large) the steady-state current J = 0.25 ± 0.02, independent of α and β (measured at several (α,β) points in that region). |
| P2 | Low-density phase. | for α < 0.5 and α < β the current J ≈ α(1−α) and the bulk density ρ ≈ α, each matched within ± 0.03 (α-controlled phase). |
| P3 | Coexistence line ⇒ density jump. | on α = β < 0.5 the chain shows a linear (shock) density profile; crossing the line by lowering β below α flips the bulk density from ≈ α toward ≈ 1−β (high-density phase), a finite density jump ≥ 0.2. |

**Discipline:** L, α/β grids, update scheme, warm-up + averaging windows, seeds FIXED; metrics locked; no
tuning. Falsified → MISS. gate_design_check: L ≥ 200 and long averaging so the exact mean-field values are
resolvable; bulk density read from the central third to avoid boundary layers.
**Distinctness (keep):** minimal hopping-exclusion process (vmax 1) with OPEN boundaries; its hallmark is a
boundary-induced three-phase diagram with an exactly known maximal current J = 1/4 — a distinct, analytically
exact target that nagel_schreckenberg (closed ring, vmax 5) never reaches.
