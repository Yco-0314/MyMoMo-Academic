"""Engine-equivalence oracle — the byte-diff gate for the ADR-009 Melodie
decommission (Phase 4 and beyond).

Runs each handcrafted reference model end-to-end and hashes its output CSV(s).
`--record` writes the golden hashes (captured while the CURRENT engine is in
place); `--check` re-runs and asserts byte-identical output. Every step of the
engine replacement (standalone Config / DataLoader / Simulator / Model / Agent)
must keep these hashes unchanged — same discipline that pinned Phase 3's
AgentList (Schelling md5 528d7d5b).

    python engine_oracle.py --record   # capture golden (run on current engine)
    python engine_oracle.py --check    # verify a replacement is byte-identical

Models are deterministic (scenario.seed fixed). Yaman is heavier; pass
`--fast` to skip it.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(ROOT, "engine_oracle_golden.json")

# (label, handcrafted_model dir) — covers Grid, Network, and multi-operator paths
MODELS = [
    ("schelling_grid", "examples/calibration_challenge_schelling/handcrafted_model"),
    ("virus_network", "examples/calibration_challenge_virus/handcrafted_model"),
    ("opinion_network", "examples/calibration_challenge_opinion/handcrafted_model"),
    ("yaman_operators", "examples/reproduce_yaman_semantic_innovation/handcrafted_model"),
]


def _md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def run_model(model_dir: str) -> dict[str, str]:
    """Run main.py in its dir; return {output_csv_basename: md5}."""
    abs_dir = os.path.join(ROOT, model_dir)
    out_dir = os.path.join(abs_dir, "data", "output")
    for f in glob.glob(os.path.join(out_dir, "*.csv")):
        os.remove(f)
    env = dict(os.environ, PYTHONPATH=f"{ROOT}:{abs_dir}")
    r = subprocess.run(
        [sys.executable, "main.py"], cwd=abs_dir, env=env,
        capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        raise RuntimeError(f"{model_dir} exited {r.returncode}\n{r.stderr[-1500:]}")
    csvs = sorted(glob.glob(os.path.join(out_dir, "*.csv")))
    if not csvs:
        raise RuntimeError(f"{model_dir} produced no output CSV")
    return {os.path.basename(c): _md5(c) for c in csvs}


def _read_rows(model_dir: str) -> list[dict]:
    """Run main.py and return the output CSV rows (for the science gate)."""
    import csv
    run_model(model_dir)
    out = sorted(glob.glob(os.path.join(ROOT, model_dir, "data", "output", "*.csv")))
    return list(csv.DictReader(open(out[0])))


def _col(rows, name):
    return [float(r[name]) for r in rows]


# Behavioral "science-correctness" gate — the post-redesign validation (ADR-009
# follow-up: when the engine is redesigned away from a Melodie-faithful copy,
# byte-diff vs Melodie no longer applies, but the models must still reproduce the
# right SCIENCE). Captured from the current engine; a redesigned engine must keep
# these qualitative outcomes even though exact (RNG/order-dependent) trajectories
# differ. Each entry returns (passed, description).
SCIENCE = {
    "schelling_grid": lambda r: (
        _col(r, "segregation_index")[-1] > 0.65
        and _col(r, "segregation_index")[-1] > _col(r, "segregation_index")[0]
        and _col(r, "n_unhappy")[-1] < 5,
        "segregates (index>0.65, rising) → near-zero unhappy"),
    "virus_network": lambda r: (
        max(_col(r, "count_i")) > 100 and _col(r, "count_s")[-1] < 20,
        "epidemic peaks (max infected>100), susceptibles deplete"),
    "opinion_network": lambda r: (
        _col(r, "opinion_variance")[-1] < _col(r, "opinion_variance")[0]
        and _col(r, "n_clusters")[-1] >= 2,
        "opinions converge (variance drops) into ≥2 clusters"),
    "yaman_operators": lambda r: (
        _col(r, "repertoire_size")[-1] >= 5 and _col(r, "max_level")[-1] > 0,
        "innovation grows (repertoire≥5, deeper recipes)"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true", help="capture golden hashes")
    ap.add_argument("--check", action="store_true", help="verify vs golden")
    ap.add_argument("--fast", action="store_true", help="skip the heavier Yaman model")
    ap.add_argument("--science", action="store_true",
                    help="behavioral gate (post-redesign): models reproduce the right science")
    args = ap.parse_args()
    if not (args.record or args.check or args.science):
        ap.error("pass --record, --check, or --science")

    models = [m for m in MODELS if not (args.fast and m[0] == "yaman_operators")]

    if args.science:
        ok = True
        for label, d in models:
            try:
                passed, desc = SCIENCE[label](_read_rows(d))
                print(f"  {'✓' if passed else '✗'} {label}: {desc}")
                ok = ok and passed
            except Exception as e:
                ok = False
                print(f"  ✗ {label} ERROR: {str(e)[:200]}")
        print("\nSCIENCE GATE: PASS" if ok else "\nSCIENCE GATE: FAIL")
        return 0 if ok else 1
    results: dict[str, dict[str, str]] = {}
    for label, d in models:
        try:
            results[label] = run_model(d)
            print(f"  ✓ ran {label}: {results[label]}")
        except Exception as e:
            print(f"  ✗ {label} FAILED: {e}")
            results[label] = {"__error__": str(e)[:200]}

    if args.record:
        with open(GOLDEN, "w") as f:
            json.dump(results, f, indent=2, sort_keys=True)
        print(f"\nGolden written: {GOLDEN}")
        return 0

    # --check
    if not os.path.exists(GOLDEN):
        print("No golden file — run --record first")
        return 2
    golden = json.load(open(GOLDEN))
    ok = True
    for label, _ in models:
        g, n = golden.get(label), results.get(label)
        if g == n:
            print(f"  ✓ {label}: byte-identical")
        else:
            ok = False
            print(f"  ✗ {label}: MISMATCH\n      golden={g}\n      now   ={n}")
    print("\nENGINE ORACLE: PASS" if ok else "\nENGINE ORACLE: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
