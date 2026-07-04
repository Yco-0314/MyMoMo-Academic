# Conway's Game of Life (B3/S23) - FINDINGS

**Run 2026-06-30, verdict refreshed during reconciliation. Status: 2/3 locked clauses REPRO.**
The rule and starting patterns were locked in `PREDICTIONS-locked.md` before the run.

## Honesty

This is a deterministic cellular automaton, not an agent-decision ABM. A single synchronous
B3/S23 transition is applied to the whole grid at once. There are no agents, no scheduler,
no per-agent decisions, no seeding, and no averaging.

## Configuration

- Grid: L = 64, toroidal.
- Rule: B3/S23, Moore-8 neighbours, synchronous update.
- Patterns: glider, blinker, block, beacon, stamped at offset (3, 3).
- Period search horizon: 16 generations.
- Metric: exact shape period, exact net translation, and live-cell-count series.

## Observed Results

| Pattern | Shape period | Net translation / period | Live-cell count series over one period |
|---|---:|---:|---|
| Glider | 4 | (+1, +1) | 5, 5, 5, 5, 5 |
| Blinker | 2 | (0, 0) | 3, 3, 3 |
| Block | 1 | (0, 0) | 4, 4 |
| Beacon | 2 | (0, 0) | 8, 6, 8 |

## Verdicts

| # | Locked clause | Verdict | Notes |
|---|---|---|---|
| P1 | glider returns to its own shape translated by (+1,+1) after 4 generations | **REPRO** | exact |
| P2 | blinker period = 2; block period = 1 unchanged | **REPRO** | exact |
| P3 | beacon period = 2; live-cell count conserved for block and oscillates with period 2 for blinker/beacon | **MISS** | beacon count oscillates, but blinker count is constant at 3 |

The model is correct; the locked P3 wording was too strong. The blinker is a period-2
shape oscillator, but its population does not oscillate: a horizontal 3-cell row becomes a
vertical 3-cell column, so the count remains 3. The reconciled verdict reports this as a
MISS rather than silently weakening the locked clause.

## Artifacts

- `results.json` contains the exact measured periods, translations, count series, and
  verdict rows.
- `verdict-bundle.json` fingerprints this findings file, the locked predictions, the design
  spec, and the result artifact.
