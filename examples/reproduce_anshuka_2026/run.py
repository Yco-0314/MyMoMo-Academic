"""Anshuka et al. 2026 — scoped reproduction runner.

Five locked levers P1-P5 from PREDICTIONS-locked.md, run end-to-end.
Outputs are read straight from real simulation runs and compared to the locked
predictions. Verdicts (REPRO / PARTIAL / MISS) are computed deterministically;
the FINDINGS.md is written by hand from these numbers.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from abm_auto.gis._anshuka_2026 import mean_outcome


# Base scenario shared across levers
BASE = dict(
    alarm_t=0,
    onset_steps=10,          # slow-onset default
    mobility_good_frac=0.70,
    collaboration=False,
    n_agents=100,
    max_steps=200,
)

N_ITER = 10                  # paper uses 30; we use 10 for repeatability


def fmt(label: str, r: dict) -> str:
    return (f"{label:>22s}: evac={r['evac']:5.1f}±{r['evac_std']:.1f}  "
            f"incap={r['incap']:5.1f}±{r['incap_std']:.1f}")


print("=" * 72)
print("Anshuka et al. 2026 — scoped reproduction")
print("=" * 72)

# ── P1: belief sweep ────────────────────────────────────────────────────────
print("\n--- P1: belief in alarm sweep (Fig 4; locked: low~17, med~55, high~72) ---")
P1 = {}
for label, belief in (("low",   0.10), ("med",  0.40), ("high", 0.70)):
    P1[label] = mean_outcome(belief=belief, n_iter=N_ITER, **BASE)
    print(fmt(f"P1 {label} belief={belief}", P1[label]))

# ── P2: alarm release time × belief level ───────────────────────────────────
print("\n--- P2: alarm release time × belief (Fig 5) ---")
P2 = {}
for blabel, belief in (("low", 0.10), ("med", 0.40), ("high", 0.70)):
    for tlabel, alarm_t in (("t=1 immediate", 1), ("t=10 delayed", 10),
                             ("t=30 very delayed", 30)):
        kw = {**BASE, "alarm_t": alarm_t}
        P2[(blabel, tlabel)] = mean_outcome(belief=belief, n_iter=N_ITER, **kw)
        print(fmt(f"P2 {blabel} {tlabel}", P2[(blabel, tlabel)]))

# ── P3: rapid vs slow onset × belief ────────────────────────────────────────
print("\n--- P3: rapid vs slow onset × belief (Fig 6) ---")
P3 = {}
for blabel, belief in (("low", 0.10), ("med", 0.40), ("high", 0.70)):
    for olabel, onset in (("slow-onset", 10), ("rapid-onset", 3)):
        kw = {**BASE, "onset_steps": onset}
        P3[(blabel, olabel)] = mean_outcome(belief=belief, n_iter=N_ITER, **kw)
        print(fmt(f"P3 {blabel} {olabel}", P3[(blabel, olabel)]))

# ── P4: good vs reduced mobility × belief ───────────────────────────────────
print("\n--- P4: mobility × belief (Fig 8) ---")
P4 = {}
for blabel, belief in (("low", 0.10), ("med", 0.40), ("high", 0.70)):
    for mlabel, good_frac in (("good 70%", 0.70), ("reduced 30%", 0.30)):
        kw = {**BASE, "mobility_good_frac": good_frac}
        P4[(blabel, mlabel)] = mean_outcome(belief=belief, n_iter=N_ITER, **kw)
        print(fmt(f"P4 {blabel} {mlabel}", P4[(blabel, mlabel)]))

# ── P5: collaboration on vs off × belief ────────────────────────────────────
print("\n--- P5: collaboration × belief (Fig 9) ---")
P5 = {}
for blabel, belief in (("low", 0.10), ("med", 0.40), ("high", 0.70)):
    for clabel, collab in (("collab OFF", False), ("collab ON", True)):
        kw = {**BASE, "collaboration": collab}
        P5[(blabel, clabel)] = mean_outcome(belief=belief, n_iter=N_ITER, **kw)
        print(fmt(f"P5 {blabel} {clabel}", P5[(blabel, clabel)]))


# ── Verdicts ───────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("Verdicts vs PREDICTIONS-locked.md")
print("=" * 72)

# P1 direction
e_low, e_med, e_hi = P1["low"]["evac"], P1["med"]["evac"], P1["high"]["evac"]
i_low, i_med, i_hi = P1["low"]["incap"], P1["med"]["incap"], P1["high"]["incap"]
p1_dir = (e_hi > e_med > e_low) and (i_low > i_med > i_hi)
print(f"P1 direction (evac↑ with belief, incap↓): {'REPRO' if p1_dir else 'MISS'}")
print(f"   evac low={e_low:.1f} med={e_med:.1f} hi={e_hi:.1f} "
      f"| paper ~17 / ~55 / ~72")

# P2 medium/high direction
def evac(*key):
    return P2[key]["evac"]
p2_mid = evac("med", "t=1 immediate") > evac("med", "t=10 delayed") > evac("med", "t=30 very delayed")
p2_hi = evac("high", "t=1 immediate") > evac("high", "t=10 delayed") > evac("high", "t=30 very delayed")
print(f"P2 medium belief earlier-better: {'REPRO' if p2_mid else 'MISS'}")
print(f"P2 high belief earlier-better:   {'REPRO' if p2_hi else 'MISS'}")

# P3 rapid vs slow at high belief
i_slow_hi = P3[("high", "slow-onset")]["incap"]
i_rapid_hi = P3[("high", "rapid-onset")]["incap"]
p3_dir = i_rapid_hi > i_slow_hi
print(f"P3 rapid-onset incap > slow-onset incap at high belief: "
      f"{'REPRO' if p3_dir else 'MISS'}  ({i_rapid_hi:.1f} vs {i_slow_hi:.1f}; "
      f"paper ~65 vs ~30)")

# P4 mobility direction at medium/high belief
i_good_med = P4[("med", "good 70%")]["incap"]
i_red_med  = P4[("med", "reduced 30%")]["incap"]
i_good_hi  = P4[("high", "good 70%")]["incap"]
i_red_hi   = P4[("high", "reduced 30%")]["incap"]
p4_med = i_red_med > i_good_med
p4_hi  = i_red_hi > i_good_hi
print(f"P4 reduced mobility incap > good at medium belief: "
      f"{'REPRO' if p4_med else 'MISS'}  ({i_red_med:.1f} vs {i_good_med:.1f})")
print(f"P4 reduced mobility incap > good at high belief:   "
      f"{'REPRO' if p4_hi else 'MISS'}  ({i_red_hi:.1f} vs {i_good_hi:.1f})")

# P5 collaboration null
for blabel, _ in (("low", 0.10), ("med", 0.40), ("high", 0.70)):
    de = abs(P5[(blabel, "collab OFF")]["evac"] - P5[(blabel, "collab ON")]["evac"])
    di = abs(P5[(blabel, "collab OFF")]["incap"] - P5[(blabel, "collab ON")]["incap"])
    null = de < 5 and di < 5
    print(f"P5 collaboration null at {blabel} belief: "
          f"{'REPRO' if null else 'MISS'}  (Δevac={de:.1f}, Δincap={di:.1f})")
