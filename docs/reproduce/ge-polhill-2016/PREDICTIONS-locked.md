# Ge & Polhill 2016 — Locked Predictions (before reproduction)

**Locked:** 2026-06-16, BEFORE building or running any reproduction. Anti-fabrication
discipline: lock the falsifiable claims to git first; read the real source; only
report "reproduced" / "not reproduced" against these after a real run.

**Source (provided by the user):**
- Paper: Ge, J. & Polhill, G. (2016). *Exploring the Combined Effect of Factors
  Influencing Commuting Patterns and CO2 Emissions in Aberdeen Using an
  Agent-Based Model.* JASSS 19(3), 11. (`local paper PDF (not committed)`)
- Model: COMSES "Transport simulation in a real road network" v1.1.0 —
  `code/TiPaC_roadNetwork10.nlogo` + `docs/TiPaC ODD.pdf` + real Aberdeen GIS data.

---

## Mechanism (read from the NetLogo source)

A multi-day, real-GIS traffic micro-simulation:

- **Environment:** Aberdeen A-roads / B-roads / minor-roads loaded from shapefiles
  onto NetLogo patches; a junction graph (`junctions` + directed `junction-links`)
  is built from the road patches. Also: coastline, urban/eight-fold zones, the AWPR
  bypass route, stations, home `address_point`s and `firm_address` workplaces.
- **Agents:** `persons` (commuters) with a home `live-patch` + an `employer` firm;
  each may `drive` (a `car`), `ride-a-bike`, or `walk`. `firms` are workplaces.
- **Movement:** car-following — `speed-up-car` / `slow-down-car` by the car ahead,
  `braking-distance`, `max-speed`, `zero-to-sixty-seconds`; speed limits per road
  class.
- **Route choice + learning:** shortest path weighted by travel time
  (`get-drive-map-to-work/home`, `update-best-paths`); persons learn better paths
  across days (`run-n-days`).
- **Departure timing:** `leave-home-minute` / `leave-work-minute`; `flexi-time-start-at`
  spreads departures (the flexitime lever).
- **Outputs:** `average-commute-time`, commute-time variability, and `co2` =
  Σ over moving cars of `co2-emissions[speed, acceleration]` (idle CO2 when stopped;
  speed/acceleration-based otherwise).

## The four policy levers

1. **Flexitime** — spread of allowed start times (`flexi-time-start-at`).
2. **Urban concentration** — fraction of people living in the urban core (`eight-fold` / urban zones).
3. **Bypass** — the AWPR peripheral route added to the network.
4. **Cyclists** — cyclists sharing roads with cars.

---

## LOCKED predictions (directional — the paper's findings)

A faithful reproduction must reproduce the **signs / directions** of these effects.

| # | Lever | Predicted effect (to reproduce) |
|---|---|---|
| P1 | **Flexitime ↑** | **↓ total CO2** (significant) and **↓ peak CO2**; CO2 declines with *diminishing returns* as more flexitime is added; **↓ mean commute time** and **↓ commute-time variability** (more reliable) |
| P2 | **Urban concentration ↑** | **↓ mean commute time** and **↓ total CO2** (people live closer); but **↑ urban congestion** and **↓ reliability** (a length-vs-reliability trade-off) |
| P3 | **Bypass (AWPR)** | **↓ mean commute time by only a small amount**, while **slightly ↑ total CO2** (higher speeds / longer distances) |
| P4 | **Cyclists on roads** | **NO significant ↑** in mean commute time or commute-time variability (cyclists do not necessarily slow traffic overall) |

## Falsification conditions

The reproduction **fails to reproduce** a claim if its run shows the **opposite sign**
(e.g. flexitime *raising* CO2, or the bypass *reducing* total CO2, or cyclists
*significantly* slowing traffic). Magnitudes will differ; the **signs and the
trade-off structure** (esp. P2's length-vs-reliability) are what is being tested.

## Scope note (honest)

This is a large micro-simulation. A bit-identical port of the car-following physics
is out of scope for a first reproduction. The plan is a **faithful reproduction of
the aggregate findings** (commuters routing on the real Aberdeen network, departure
timing, an explicit CO2 proxy from speed/acceleration), with any simplification of
the micro-dynamics **stated explicitly** — a *partial faithful reproduction*, not a
claimed full port. Whether to attempt the full micro-physics port is a separate
decision.
