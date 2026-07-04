"""Candidate #10 — real Ba-DEM reproduction runner.

Same 5 levers as the synthetic reproduction, but on the REAL Ba SRTM DEM (only the
world geometry changes — the mechanism is the byte-identical _simulate). Compares each
lever to BOTH the paper AND the synthetic baseline, so the H1-H6 magnitude movement in
docs/reproduce/anshuka-2026-real-dem/PREDICTIONS-locked.md is visible.

Usage:
    .venv/bin/python examples/reproduce_anshuka_real/run.py [DEM_PATH]

DEM_PATH defaults to data/anshuka_ba/ba_dem_utm.tif (a pre-reprojected, metric-CRS
GeoTIFF — see docs/reproduce/anshuka-2026-real-dem/DATA-acquisition.md). If it is missing,
this script prints the acquisition instructions and exits (no synthetic fallback — the
real-data gate forbids one).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from abm_auto.gis._anshuka_real import build_world_from_dem, mean_outcome_real

DEM_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/anshuka_ba/ba_dem_utm.tif")
GRID_SIZE = 100           # ~ the paper's 100x100 / 10,000-cell geometry (H-series precondition)
N_ITER = 10

# Synthetic baseline (from docs/reproduce/anshuka-2026/FINDINGS.md) + paper, for side-by-side.
SYN = {  # (evac, incap)
    "P1": {"low": (54.8, 45.2), "med": (91.5, 8.5), "high": (97.4, 2.6)},
    "P3_high": {"slow": 2.6, "rapid": 12.9},
    "P4_high": {"good": 2.6, "reduced": 4.2},
}
PAPER = {"P1": {"low": (17, 83), "med": (55, 45), "high": (72, 28)}}

if not DEM_PATH.exists():
    print(f"[candidate #10] DEM not found: {DEM_PATH}\n")
    print("Download + prep (see docs/reproduce/anshuka-2026-real-dem/DATA-acquisition.md):")
    print("  1. SRTM tile S18E177 (OpenTopography SRTMGL1, public domain) for Ba 17.53S/177.67E")
    print("  2. reproject to UTM 60S (EPSG:32760), clip to the Ba floodplain bbox")
    print("  3. save as data/anshuka_ba/ba_dem_utm.tif, then re-run this script")
    sys.exit(2)

BASE = dict(alarm_t=0, onset_steps=10, mobility_good_frac=0.70,
            collaboration=False, n_agents=100, max_steps=600)

print("=" * 72)
print(f"Anshuka 2026 — REAL Ba-DEM reproduction (candidate #10)  grid={GRID_SIZE}x{GRID_SIZE}")
print(f"DEM: {DEM_PATH}")
print("=" * 72)

# Build the real world ONCE (the geometry is fixed; levers vary the mechanism params).
world = build_world_from_dem(DEM_PATH, grid_size=GRID_SIZE, source=f"SRTM:{DEM_PATH.name}")
print(f"world: {len(world.homes)} home cells, {len(world.shelters)} shelters, "
      f"{int(world.initial_water.sum())} initial water cells\n")


def run(**kw):
    return mean_outcome_real(world=world, n_iter=N_ITER, **{**BASE, **kw})


def fmt(label, r):
    return f"{label:>26s}: evac={r['evac']:5.1f}±{r['evac_std']:.1f}  incap={r['incap']:5.1f}±{r['incap_std']:.1f}"


# ── P1 belief sweep (H1: low-belief evac should DROP 54.8 -> <=35 toward paper ~17) ──
print("--- P1 belief sweep (H1: low-evac 54.8 -> <=35? toward paper ~17) ---")
P1 = {}
for lab, b in (("low", 0.10), ("med", 0.40), ("high", 0.70)):
    P1[lab] = run(belief=b)
    s, p = SYN["P1"][lab], PAPER["P1"][lab]
    print(fmt(f"P1 {lab} b={b}", P1[lab]) + f"   [syn {s[0]}/{s[1]} | paper {p[0]}/{p[1]}]")

# ── P2 alarm-release × belief (H2: high-belief earlier-better should RECOVER) ──
print("\n--- P2 alarm release time × belief (H2 DECISIVE: high-belief monotone, gap>=10?) ---")
P2 = {}
for blab, b in (("low", 0.10), ("med", 0.40), ("high", 0.70)):
    for tlab, t in (("t=1", 1), ("t=10", 10), ("t=30", 30)):
        P2[(blab, tlab)] = run(belief=b, alarm_t=t)
        print(fmt(f"P2 {blab} {tlab}", P2[(blab, tlab)]))

# ── P3 rapid vs slow × belief (H3: high-belief rapid incap 12.9 -> >=30) ──
print("\n--- P3 rapid vs slow onset × belief (H3: high rapid incap 12.9 -> >=30?) ---")
P3 = {}
for blab, b in (("low", 0.10), ("med", 0.40), ("high", 0.70)):
    for olab, o in (("slow", 10), ("rapid", 3)):
        P3[(blab, olab)] = run(belief=b, onset_steps=o)
        print(fmt(f"P3 {blab} {olab}", P3[(blab, olab)]))

# ── P4 mobility × belief (H4: high-belief reduced-good gap 1.6 -> >=6) ──
print("\n--- P4 mobility × belief (H4: high-belief Δincap 1.6 -> >=6?) ---")
P4 = {}
for blab, b in (("low", 0.10), ("med", 0.40), ("high", 0.70)):
    for mlab, m in (("good", 0.70), ("reduced", 0.30)):
        P4[(blab, mlab)] = run(belief=b, mobility_good_frac=m)
        print(fmt(f"P4 {blab} {mlab}", P4[(blab, mlab)]))

# ── P5 collaboration × belief (H5: low-belief deviation should PERSIST — it's mechanism) ──
print("\n--- P5 collaboration × belief (H5: low-belief Δevac should PERSIST >5) ---")
P5 = {}
for blab, b in (("low", 0.10), ("med", 0.40), ("high", 0.70)):
    for clab, c in (("OFF", False), ("ON", True)):
        P5[(blab, clab)] = run(belief=b, collaboration=c)
        print(fmt(f"P5 {blab} collab-{clab}", P5[(blab, clab)]))


# ── Verdicts vs the LOCKED hypotheses H1-H6 (as gate Verdicts -> L3 bundle) ──
from abm_auto.verification.gate import Verdict
from abm_auto.gis._repro_bundle import build_bundle, write_bundle

print("\n" + "=" * 72)
print("Verdicts vs PREDICTIONS-locked.md (H1-H6)")
print("=" * 72)

def ev(*k):
    return P2[k]["evac"]

e_low = P1["low"]["evac"]
gap_hi = ev("high", "t=1") - ev("high", "t=30")
mono_hi = ev("high", "t=1") > ev("high", "t=10") > ev("high", "t=30")
ir_hi = P3[("high", "rapid")]["incap"]; is_hi = P3[("high", "slow")]["incap"]
dg_hi = P4[("high", "reduced")]["incap"] - P4[("high", "good")]["incap"]
dlow = abs(P5[("low", "OFF")]["evac"] - P5[("low", "ON")]["evac"])

h1_pass = e_low <= 35
h2_pass = mono_hi and gap_hi >= 10
h3_pass = ir_hi >= 30 and (ir_hi - is_hi) >= 20
h4_pass = dg_hi >= 6
h5_pass = dlow > 5   # locked prediction: the deviation PERSISTS (mechanism, not geometry)

verdicts = [
    Verdict(passed=h1_pass, tier="refutation", gate_name="H1 P1 magnitude converges (low-belief evac)",
            salient_number=(round(e_low, 2), 35.0),
            reasons=[] if h1_pass else [f"evac(low)={e_low:.1f} did not drop <=35"]),
    Verdict(passed=h2_pass, tier="refutation", gate_name="H2 P2 recovery (DECISIVE: high-belief earlier-alarm)",
            salient_number=(round(gap_hi, 2), 10.0),
            reasons=[] if h2_pass else [f"gap(t1-t30)={gap_hi:.1f}, monotone={mono_hi}"]),
    Verdict(passed=h3_pass, tier="refutation", gate_name="H3 P3 rapid-onset magnitude widens",
            salient_number=(round(ir_hi - is_hi, 2), 20.0),
            reasons=[] if h3_pass else [f"high rapid incap={ir_hi:.1f} (>=30 {'ok' if ir_hi>=30 else 'no'}); Δ={ir_hi-is_hi:.1f} < 20"]),
    Verdict(passed=h4_pass, tier="refutation", gate_name="H4 P4 mobility-gap magnitude widens",
            salient_number=(round(dg_hi, 2), 6.0),
            reasons=[] if h4_pass else [f"Δincap(high)={dg_hi:.1f} < 6"]),
    Verdict(passed=h5_pass, tier="refutation", gate_name="H5 P5 low-belief deviation persists (predicted mechanism)",
            salient_number=(round(dlow, 2), 5.0),
            reasons=[] if h5_pass else [
                f"FALSIFIED: Δevac(low)={dlow:.1f} did NOT persist; deviation relocated to mid/high "
                f"(med {P5[('med','ON')]['evac']-P5[('med','OFF')]['evac']:.1f}, "
                f"high {P5[('high','ON')]['evac']-P5[('high','OFF')]['evac']:.1f}) — P5 partly geometric; ladder #5 target"]),
]
for v in verdicts:
    print(v.render())

success = h1_pass or h2_pass
headline = "EARNED" if success else "NOT YET"
print("\n" + "-" * 72)
print(f"#10 HEADLINE (>=1 of H1,H2 REPRO on magnitudes): {headline} {'✅' if success else ''}")

# ── Emit the L3 replayable bundle (ADR-023 L3 / ladder #6) ──
ROOT = Path(__file__).resolve().parent.parent.parent
# argv[2] optionally redirects the output dir (e.g. the paper-extent #10b rerun);
# no argv[2] => candidate #10's canonical dir, byte-identical to before.
REPRO = ROOT / (sys.argv[2] if len(sys.argv) > 2 else "docs/reproduce/anshuka-2026-real-dem")
bundle = build_bundle(
    paper={"title": "A Holistic Approach to Early Warning Systems Using an Agent-Based Model",
           "authors": "Anshuka et al.", "year": 2026, "journal": "IJDRS 17:439-455",
           "doi": "10.1007/s13753-026-00729-7"},
    headline=headline,
    verdicts=verdicts,
    data_artifacts={"ba_dem_utm": DEM_PATH},
    doc_artifacts={"predictions_locked": REPRO / "PREDICTIONS-locked.md",
                   "findings": REPRO / "FINDINGS.md",
                   "design_spec": ROOT / "docs/superpowers/specs/2026-06-24-anshuka-real-dem-design.md"},
    repo=ROOT,
    extra={"grid_size": GRID_SIZE, "n_iter": N_ITER,
           "data_source": "Copernicus DEM GLO-30 tile S18E177 (public domain), clipped to Ba floodplain, UTM 60S",
           "world": {"home_cells": len(world.homes), "shelters": len(world.shelters),
                     "initial_water_cells": int(world.initial_water.sum())},
           "fetch": "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_S18_00_E177_00_DEM/Copernicus_DSM_COG_10_S18_00_E177_00_DEM.tif"})
write_bundle(bundle, REPRO / "verdict-bundle.json")
print(f"wrote {REPRO / 'verdict-bundle.json'} (L3 replayable artifact)")
