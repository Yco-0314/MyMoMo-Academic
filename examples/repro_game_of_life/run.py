"""Conway's Game of Life (B3/S23) — reproduction experiment + tier-honest verdicts.

Places each canonical seed pattern (glider, blinker, block, beacon) on a large toroidal
grid (large enough that wrap interference cannot reach the pattern over the measured
window), evolves it under the FIXED B3/S23 rule, and measures the EXACT shape period, the
net per-period translation, and the live-cell-count series. It then evaluates the LOCKED
clauses P1-P3 (docs/studies/game-of-life/PREDICTIONS-locked.md) into refutation-tier
``Verdict``s and writes results.json + the L3 verdict bundle.

HONESTY (binds the FINDINGS): this is a DETERMINISTIC CELLULAR AUTOMATON, NOT an
agent-stepping ABM. There are no agents that perceive/decide/act, no scheduler, no
per-agent step — only a single synchronous B3/S23 transition applied to the whole grid at
once. We disclose this exactly as the BTW sandpile / forest-fire reproductions disclose
they are cellular automata. The lock-first + honest-verdict + L3-bundle discipline still
fully applies.

Discipline (binding): the rule (B3/S23), the four starting patterns, and the grading
metric (EXACT pattern periods + the glider's exact net translation) are FIXED here BEFORE
the run; nothing is tuned. Because the CA is fully deterministic there is NO seeding and
NO averaging — the measured periods/translation are exact, not statistical. A falsified
clause is reported MISS. FINDINGS.md is authored BEFORE the bundle (the bundle
fingerprints it). Mirrors examples/repro_btw_sandpile/run.py for the Verdict + bundle usage.

Usage:  PYTHONPATH=. .venv/bin/python examples/repro_game_of_life/run.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from abm_auto.classics.game_of_life import (
    PATTERNS,
    detect_period,
    live_count_series,
    place_pattern,
)
from abm_auto.repro_bundle import build_bundle, write_bundle
from abm_auto.verification.gate import Verdict

REPO = Path(__file__).resolve().parents[2]
STUDY = REPO / "docs" / "studies" / "game-of-life"

# --- FIXED config (locked before running; the rule + patterns + metric are NOT tuned) ---
# A large toroidal grid so a pattern cannot wrap into itself over the measured window.
# The glider moves 1 cell/gen diagonally; over MAX_PERIOD gens it travels at most
# MAX_PERIOD cells, far inside a 64-cell torus, so its centroid translation is wrap-free.
L = 64
OFFSET = (3, 3)            # stamp away from (0,0); irrelevant on a torus but tidy
MAX_PERIOD = 16           # search horizon for the period detector (all targets are <= 4)
RULE = "B3/S23 (born on exactly 3 live Moore-8 neighbours; survive on 2 or 3), " \
       "synchronous update, toroidal grid"

# Locked expected behaviours (from PREDICTIONS-locked.md / Conway-Gardner 1970). These are
# the GRADING anchors, fixed before the run.
EXPECTED = {
    "glider":  {"period": 4, "translation": (1, 1)},   # period-4 diagonal spaceship
    "blinker": {"period": 2, "translation": (0, 0)},   # period-2 oscillator
    "block":   {"period": 1, "translation": (0, 0)},   # still life
    "beacon":  {"period": 2, "translation": (0, 0)},   # period-2 oscillator
}

PREDICTIONS_DOC = STUDY / "PREDICTIONS-locked.md"
FINDINGS_PATH = STUDY / "FINDINGS.md"
RESULTS_PATH = STUDY / "results.json"
BUNDLE_PATH = STUDY / "verdict-bundle.json"
DESIGN_SPEC = REPO / "docs" / "superpowers" / "specs" / \
    "2026-06-30-classic-abm-reproductions-batch5-waveA-design.md"


def measure() -> dict:
    """Measure each pattern's exact period, net per-period translation, and the
    live-cell-count series over one full period. Deterministic — no seeding."""
    out = {}
    for name, cells in PATTERNS.items():
        g = place_pattern(cells, L, offset=OFFSET)
        res = detect_period(g, max_period=MAX_PERIOD)
        period = res["period"] if res else None
        # live-cell series over exactly one full period (length period+1).
        series = live_count_series(g, period) if period else [int(g.sum())]
        out[name] = {
            "period": period,
            "translation": list(res["translation"]) if res else None,
            "live_count_initial": int(g.sum()),
            "live_count_series_one_period": series,
            "count_conserved": (len(set(series)) == 1),
        }
    return out


def verdicts_for(m: dict) -> list:
    g = m["glider"]
    bl = m["blinker"]
    bk = m["block"]
    bc = m["beacon"]

    # P1: the glider is a period-4 diagonal spaceship returning to its shape translated by
    # exactly (+1, +1) after 4 generations.
    p1_pass = (g["period"] == 4 and g["translation"] == [1, 1])
    p1 = Verdict(
        passed=p1_pass, tier="refutation",
        gate_name="P1 glider is a period-4 diagonal spaceship (returns to its shape "
                  "translated by exactly (+1,+1) after 4 generations)",
        salient_number=(float(g["period"]) if g["period"] is not None else -1.0, 4.0),
        reasons=[] if p1_pass else [
            f"measured glider period={g['period']}, translation={g['translation']} "
            f"(need period=4 and translation=(+1,+1))"])

    # P2: blinker period 2; block unchanged every generation (still life, period 1).
    p2_pass = (bl["period"] == 2 and bk["period"] == 1 and bk["translation"] == [0, 0])
    p2 = Verdict(
        passed=p2_pass, tier="refutation",
        gate_name="P2 blinker period 2 AND block is a still life (period 1, unchanged)",
        salient_number=(float(bl["period"]) if bl["period"] is not None else -1.0, 2.0),
        reasons=[] if p2_pass else [
            f"measured blinker period={bl['period']}, block period={bk['period']} "
            f"translation={bk['translation']} (need blinker=2, block=1, block "
            f"translation=(0,0))"])

    # P3: the locked text asks for live-cell count oscillation with period 2 for both
    # blinker and beacon. The canonical blinker has shape period 2 but its live count is
    # constant at 3, so this clause must be allowed to MISS honestly.
    block_conserved = bk["count_conserved"]
    blinker_series = bl["live_count_series_one_period"]
    beacon_series = bc["live_count_series_one_period"]
    blinker_oscillates_p2 = (
        bl["period"] == 2
        and len(blinker_series) >= 3
        and blinker_series[0] == blinker_series[2]
        and blinker_series[0] != blinker_series[1]
    )
    beacon_oscillates_p2 = (
        bc["period"] == 2
        and len(beacon_series) >= 3
        and beacon_series[0] == beacon_series[2]   # same after one full period
        and beacon_series[0] != beacon_series[1]   # genuinely changes within the period
    )
    p3_pass = (
        bc["period"] == 2
        and block_conserved
        and blinker_oscillates_p2
        and beacon_oscillates_p2
    )
    p3 = Verdict(
        passed=p3_pass, tier="refutation",
        gate_name="P3 beacon period 2; live-cell count conserved for the block and "
                  "oscillates with period 2 for blinker/beacon",
        salient_number=(
            float(
                int(bc["period"] == 2)
                + int(block_conserved)
                + int(blinker_oscillates_p2)
                + int(beacon_oscillates_p2)
            ),
            4.0,
        ),
        reasons=[] if p3_pass else [
            f"measured blinker period={bl['period']}, blinker count series={blinker_series}; "
            f"beacon period={bc['period']}, beacon count series={beacon_series}; "
            f"block count conserved={block_conserved} (need beacon period=2, block count "
            f"conserved, and live-count period-2 oscillation for both blinker and beacon)"])

    return [p1, p2, p3]


def main() -> None:
    print("\n=== Conway's Game of Life (B3/S23) — DETERMINISTIC CELLULAR AUTOMATON, "
          "NOT agent-stepping — verdicts (honest; falsified is valid) ===")
    print(f"config: L={L} (toroidal), rule={RULE}")
    print(f"grading metric: EXACT pattern periods + glider net translation "
          f"(deterministic; no seeding/averaging)")

    m = measure()
    verdicts = verdicts_for(m)
    labels = ["P1", "P2", "P3"]

    # --- print honest summary ---
    print("\nmeasured pattern behaviours (exact):")
    for name in ("glider", "blinker", "block", "beacon"):
        d = m[name]
        exp = EXPECTED[name]
        print(f"  {name:8s} period={d['period']} translation={d['translation']} "
              f"(expected period={exp['period']}, translation={list(exp['translation'])})"
              f"  live-count series/period={d['live_count_series_one_period']}")
    print()
    for lab, v in zip(labels, verdicts):
        word = "REPRO" if v.passed else "MISS"
        sn = v.salient_number
        print(f"{lab}: {word:5s} score={sn[0]} threshold={sn[1]}  | {v.gate_name}")
        for reason in v.reasons:
            print(f"      reason: {reason}")

    # --- write results.json ---
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps({
        "model": "conway-game-of-life (deterministic cellular automaton, NOT agent-stepping)",
        "config": {
            "L": L, "grid": "toroidal (periodic, wrap-around)",
            "neighbourhood": "Moore-8", "rule": "B3/S23", "update": "synchronous",
            "offset": list(OFFSET), "max_period_search": MAX_PERIOD,
            "deterministic": True, "seeds": None, "averaging": None,
            "metric": "exact pattern shape-period + net per-period translation + "
                      "live-cell-count series",
            "expected": {k: {"period": v["period"], "translation": list(v["translation"])}
                         for k, v in EXPECTED.items()},
        },
        "patterns": m,
        "verdicts": [{"label": lab, "passed": v.passed, "gate": v.gate_name,
                      "salient_number": list(v.salient_number), "reasons": v.reasons}
                     for lab, v in zip(labels, verdicts)],
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- L3 bundle (FINDINGS.md must already exist; the bundle fingerprints it) ---
    paper = {
        "title": "Mathematical Games: The fantastic combinations of John Conway's new "
                 "solitaire game 'life'",
        "authors": ["Martin Gardner", "John H. Conway"], "year": 1970,
        "journal": "Scientific American 223(4):120-123",
        "doi": "10.1038/scientificamerican1070-120",
    }
    n_repro = sum(1 for v in verdicts if v.passed)
    headline = (f"Conway Game of Life (deterministic cellular automaton): {n_repro}/3 "
                f"locked clauses REPRO; glider period={m['glider']['period']} "
                f"translation={m['glider']['translation']}, blinker/beacon period 2, "
                f"block still life (period 1)")
    bundle = build_bundle(
        paper=paper, headline=headline, verdicts=verdicts,
        data_artifacts={"life_results": RESULTS_PATH},
        doc_artifacts={"predictions_locked": PREDICTIONS_DOC, "findings": FINDINGS_PATH,
                       "design_spec": DESIGN_SPEC},
        repo=REPO,
        extra={
            "model": "conway-game-of-life", "L": L, "rule": "B3/S23",
            "deterministic": True,
            "model_class": "deterministic cellular automaton (NOT agent-stepping ABM): a "
                           "single synchronous B3/S23 transition is applied to the whole "
                           "grid at once; there are no agents, no scheduler, no per-agent "
                           "decisions and no randomness",
            "measured": {k: {"period": m[k]["period"], "translation": m[k]["translation"]}
                         for k in ("glider", "blinker", "block", "beacon")},
            "scope": "faithful reproduction of a published synthetic CA result; no "
                     "real-world data; the contribution is whether the harness + "
                     "discipline reproduce the catalogued EXACT periods/translation and "
                     "would catch an artifact (e.g. a wrong rule giving the wrong period)",
        },
        citations=[
            "Gardner, M. (1970). Mathematical Games: The fantastic combinations of John "
            "Conway's new solitaire game 'life'. Scientific American 223(4):120-123. "
            "doi:10.1038/scientificamerican1070-120.",
            "Conway, J.H. (the B3/S23 rule and the glider/blinker/block/beacon catalogue, "
            "as popularized by Gardner 1970).",
        ],
        benchmark={"cross_tool": None,
                   "note": "no cross-tool baseline; faithful single-implementation "
                           "reproduction. The catalogued Conway/Gardner pattern periods "
                           "(glider 4, blinker 2, block 1, beacon 2) and the glider's "
                           "(+1,+1) net translation are the literature anchors."},
    )
    write_bundle(bundle, BUNDLE_PATH)
    print(f"\nWrote: {RESULTS_PATH}\nWrote: {BUNDLE_PATH}")
    print("(FINDINGS.md is authored before the bundle so the bundle fingerprints it.)")


if __name__ == "__main__":
    main()
