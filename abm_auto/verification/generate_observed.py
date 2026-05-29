"""Generate a multi-seed observed.csv from the NetLogo oracle fixture.

Single-seed observed.csv has noise floor ~100-200 (variance of one random
realization). Averaging across N=30 NetLogo runs at ground-truth params
gives a per-tick mean that converges to the model's expected trajectory,
dropping noise floor to ~20 (sqrt(30) ≈ 5.5× tighter).

Use this script when you want the lean benchmark's calibration MSE to
sit at the algorithm's true noise floor (~20 in our case) rather than
the single-realization floor (~100). The trade-off is that we're now
calibrating against an "expected trajectory" — calibration target shifts
from "match this specific run" to "match the model's mean behavior".

Default source: tests/fixtures/netlogo/output/sir_trajectories.csv
                (30 reps × 251 ticks × {S, I, R} from the NetLogo oracle)

Default destination: examples/calibration_challenge_virus/observed.csv
                     (replaces the existing single-seed file in-place)

Usage:
    python -m abm_auto.verification.generate_observed
    python -m abm_auto.verification.generate_observed \\
        --fixture tests/fixtures/netlogo/output/sir_trajectories.csv \\
        --out examples/calibration_challenge_virus/observed.csv \\
        --mode mean  # or median
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from abm_auto.verification.netlogo_oracle import parse_table

REPO = Path(__file__).parent.parent.parent
DEFAULT_FIXTURE = REPO / "tests" / "fixtures" / "netlogo" / "output" / "sir_trajectories.csv"
DEFAULT_OUT = REPO / "examples" / "calibration_challenge_virus" / "observed_multi_seed.csv"


def generate_multi_seed_observed(
    fixture_path: Path,
    out_path: Path,
    mode: str = "mean",
) -> dict[str, float]:
    """Read NetLogo 30-rep fixture, aggregate per-tick across runs, write observed.csv.

    Returns a small summary dict (rows, runs, aggregation mode) for caller
    logging.
    """
    df = parse_table(fixture_path)

    # NetLogo's BehaviorSpace table columns (verbose NetLogo expressions)
    s_col = "count turtles with [not infected? and not resistant?]"
    i_col = "count turtles with [infected?]"
    r_col = "count turtles with [resistant?]"
    tick_col = "[step]"
    run_col = "[run number]"

    missing = [c for c in (s_col, i_col, r_col, tick_col, run_col) if c not in df.columns]
    if missing:
        raise ValueError(
            f"Fixture missing required columns: {missing}. "
            f"Available: {list(df.columns)}"
        )

    n_runs = df[run_col].nunique()

    # Group by tick, aggregate across runs
    if mode == "mean":
        agg = df.groupby(tick_col)[[s_col, i_col, r_col]].mean()
    elif mode == "median":
        agg = df.groupby(tick_col)[[s_col, i_col, r_col]].median()
    else:
        raise ValueError(f"mode must be 'mean' or 'median', got {mode!r}")

    # Round to integers — agent counts are discrete, the calibrator's
    # distance metric stays cleaner against integer-valued observations.
    # Drop the trailing tick if it's one beyond what the Python sim records:
    # NetLogo's BehaviorSpace captures the initial state + each post-tick
    # state (so a 250-tick experiment yields 251 rows). The Python runtime's
    # `iterator(periods)` runs `periods` iterations and records once per
    # iteration (so 250 rows). Aligning lengths prevents
    # `np.linalg.norm(sim - obs)` shape mismatch in the calibrator distance.
    if len(agg) == 251:
        agg = agg.iloc[:250]
    out = pd.DataFrame({
        "tick": agg.index,
        "susceptible": agg[s_col].round().astype(int),
        "infected": agg[i_col].round().astype(int),
        "resistant": agg[r_col].round().astype(int),
    })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)

    return {
        "rows": len(out),
        "n_runs": n_runs,
        "mode": mode,
        "fixture": str(fixture_path),
        "out": str(out_path),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--mode", choices=("mean", "median"), default="mean",
        help="Aggregation across runs per tick. Default: mean.",
    )
    args = ap.parse_args()

    if not args.fixture.exists():
        print(f"ERROR: fixture not found: {args.fixture}")
        print("To regenerate the fixture, run NetLogo headless with the")
        print("oracle_BEHAVE2025_GT experiment in tests/fixtures/netlogo/.")
        return 1

    summary = generate_multi_seed_observed(args.fixture, args.out, args.mode)
    print(f"✓ Multi-seed observed.csv written:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
