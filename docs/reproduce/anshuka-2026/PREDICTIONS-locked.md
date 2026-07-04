# Anshuka et al. 2026 — Locked Predictions (BEFORE any run)

**Paper:** Anshuka, A. et al. (2026). "A Holistic Approach to Early Warning
Systems Using an Agent-Based Model." *International Journal of Disaster Risk
Science* 17:439–455. https://doi.org/10.1007/s13753-026-00729-7
(Open Access, CC-BY 4.0; PDF: `~/Downloads/s13753-026-00729-7.pdf`)

**Locked:** 2026-06-23, BEFORE any run. The anti-fabrication discipline of this
project: write the expected outcomes, commit, then implement, then read REAL
output and report match/miss honestly. This file is the contract — any verdict
must point back here.

---

## Scope of the reproduction

This is a **scoped** reproduction. Faithful to:

- the **mechanism** (BDI human agent with belief / vision / mobility /
  collaboration; forecaster agent; bathtub flood inundation Kasmalkar 2024
  style with Moore radius 1)
- the **5 levers** + 1 **sensitivity** ordering (Figs 4–10)
- a **synthetic grid world**, n=100 agents

NOT faithful to:

- the actual Ba catchment GIS layers (real SRTM elevation, OSM road/buildings,
  Ba River shapefile) — those are not bundled with the paper; we use a
  synthetic 20×20m discretised grid that follows the paper's "R/B/W/P/_/S"
  symbolic scheme but with parameterised geometry
- exact 30-iteration variance bars — we lock the **central tendency** (mean)
  and the **direction** of variation across belief levels

This scoping is recorded honestly (per the Ge & Polhill 2016 pattern).

---

## P1 — belief in alarm ↑ → evacuation ↑ (Fig 4)

**Locked numbers** (paper Fig 4, n=100 agents, t=0 alarm, 30 iterations):

| Belief | Evacuated (mean) | Incapacitated (mean) |
|---|---|---|
| Low (10%)    | ~17  | ~83 |
| Medium (40%) | ~55  | ~45 |
| High (70%)   | ~72  | ~28 |

**Direction prediction (what must REPRODUCE):**

1. `evac(high) > evac(medium) > evac(low)` strictly
2. `incap(low) > incap(medium) > incap(high)` strictly
3. `evac(b) + incap(b) ≈ 100` at every belief b
4. evacuation share at high belief ≥ 60%
5. evacuation share at low belief ≤ 25%

---

## P2 — earlier alarm release → evacuation ↑ under medium/high belief (Fig 5)

**Locked direction** (alarm release t=1 immediate, t=10 delayed,
t=30 very-delayed):

1. At **medium and high belief**: `evac(t=1) > evac(t=10) > evac(t=30)` in
   mean human count by simulation end.
2. At **low belief**: counterintuitive — `evac(t=30) ≥ evac(t=1)`
   (under low trust, immediate alarm is disregarded; later, environmental cues
   drive self-evacuation).
3. Earliest alarm + highest belief produces the highest evacuation count overall.

---

## P3 — rapid-onset flood weakens the benefit of belief (Fig 6)

**Locked direction:**

1. In **slow-onset**, `evac(high belief) >> evac(low belief)` (gain large).
2. In **rapid-onset**, `evac(high belief) > evac(low belief)` but smaller gain;
   `incap(high, rapid) ≈ 2 × incap(high, slow)` (paper text: ~65 vs ~30).
3. Rapid-onset high-belief incapacitated count in the 50–70 range.
4. Slow-onset high-belief incapacitated count in the 20–40 range.

---

## P4 — reduced mobility → incapacitated ↑ (Fig 8)

**Locked direction** (good-mobility population vs reduced-mobility population,
30% good in the reduced case):

1. At **low belief**: minimal difference between the mobility populations.
2. At **medium and high belief**: `incap(reduced mobility) > incap(good mobility)`
   visibly.
3. The good-mobility high-belief case has the lowest overall incap count.

---

## P5 — collaboration shows ≈ NO significant effect (Fig 9)

**Locked direction (counterintuitive — this is the paper's stated finding):**

1. `|evac(collab on) − evac(collab off)| < 5` at each belief level.
2. `|incap(collab on) − incap(collab off)| < 5` at each level.

This prediction is unusual to lock — the paper's *finding* is null. We must
report a match honestly even when the effect is small, and we must not
"discover" an effect that the paper says is absent.

---

## P6 — second-order sensitivity ranking (Fig 10)

**Locked S2 magnitudes** (interaction sensitivity indices):

1. `|S2(Human Count, X)|` is the largest in magnitude (~0.49) and **negative**
   for X in {Collaboration %, Flood Probability, Believes Alarm,
   Mobility Good %}.
2. All other off-diagonal `|S2|` are **< 0.04** (Collaboration × Flood ≈ 0.008,
   Collaboration × Belief ≈ 0.008, Collaboration × Mobility ≈ 0.009,
   Flood × Belief ≈ 0.025, Flood × Mobility ≈ 0.025, Belief × Mobility ≈ 0.033).
3. The **dominant** interaction is Human-Count × every other parameter; all
   other interactions are 1–2 orders of magnitude smaller.

---

## Verdict rules

For each P1–P6, the reproduction reports one of:

- **REPRO**: locked direction(s) and ranges all hold on our simulated run.
- **PARTIAL**: direction holds but a specific magnitude band fails.
- **MISS**: direction does not hold.

A miss is reported as a miss — no glossing, per project anti-fabrication.

If a band requires variance / number-of-iterations that we did not simulate to
the paper's 30, we explicitly say so and downgrade to "partial".

## Implementation note (read after this file is locked)

The reproduction will use:

- **bathtub flood mechanic** built from our existing `_focal.py`
  (`convolve` with a Moore-neighbourhood kernel) — fits the spec's
  "1 cell wet → adjacent lower cell wets next step" rule;
  spread rate ≈ 0.0008/step parameter.
- **BDI agent decision**: belief-in-alarm probability gates the "evacuate
  toward nearest shelter via shortest path on the road graph" action.
- **Shortest-path routing** to shelters via our `_geo_network.py`.
- **Vision sensing** of flood when belief is low: at each step, agent checks
  Moore radius=vision; if a wet cell appears, agent self-warns.
- A small synthetic 20×20m grid (~20×20 cells) playground rather than the real
  Ba grid; positions of buildings (agent starts), road, river, and shelters
  are parameterised.

`docs/reproduce/anshuka-2026/FINDINGS.md` will be written AFTER runs, citing
actual outputs.
