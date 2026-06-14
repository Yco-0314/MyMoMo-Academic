"""NetLogo headless as a verification oracle for ABM Auto ports.

When a topology adapter or mechanism is supposed to mirror NetLogo's
behavior (e.g. `netlogo_spatially_clustered`, the virus-on-a-network
SIR mechanism), this module is how we check: drive NetLogo via headless,
capture trajectories or network stats, compare statistically to our
Python output.

Setup (one-time, per dev machine):
  1. Install NetLogo 6.4 (any platform)
  2. Install OpenJDK 17 — `brew install openjdk@17` on macOS
  3. Set env vars (or rely on defaults below):
       export NETLOGO_DIR="/path/to/NetLogo 6.4.0"
       export JAVA_HOME="/opt/homebrew/opt/openjdk@17"

The defaults match the development setup; CI / other devs should set the
env vars explicitly. `is_available()` returns False if either is missing,
which lets tests skip cleanly instead of erroring.
"""
from __future__ import annotations

import os
import subprocess
from io import StringIO
from pathlib import Path
from typing import Optional

import pandas as pd

DEFAULT_NETLOGO_DIR = "/Applications/NetLogo 6.4.0"
DEFAULT_JAVA_HOME = "/opt/homebrew/opt/openjdk@17"


def netlogo_dir() -> Path:
    """Resolve NetLogo install directory from $NETLOGO_DIR or default."""
    return Path(os.environ.get("NETLOGO_DIR", DEFAULT_NETLOGO_DIR))


def java_home() -> str:
    """Resolve JAVA_HOME from env or default."""
    return os.environ.get("JAVA_HOME", DEFAULT_JAVA_HOME)


def is_available() -> bool:
    """True iff netlogo-headless.sh and a Java install are both present."""
    headless = netlogo_dir() / "netlogo-headless.sh"
    return headless.exists() and Path(java_home()).exists()


def run_experiment(
    model_path: Path | str,
    experiment_name: str,
    output_path: Path | str,
    timeout: int = 600,
) -> subprocess.CompletedProcess:
    """Run a BehaviorSpace experiment via netlogo-headless.sh.

    The experiment must already exist in the .nlogo file's BehaviorSpace
    section. Output table is written to `output_path` (NetLogo's
    table-version-2.0 format).

    Args:
        model_path: Path to the .nlogo file containing the experiment.
        experiment_name: Name attribute of the experiment in the BehaviorSpace XML.
        output_path: Where to write the table CSV.
        timeout: Subprocess timeout in seconds.
    """
    if not is_available():
        raise RuntimeError(
            f"NetLogo oracle unavailable. Set NETLOGO_DIR (currently {netlogo_dir()}) "
            f"and JAVA_HOME (currently {java_home()}). See module docstring."
        )

    headless = netlogo_dir() / "netlogo-headless.sh"
    env = {**os.environ, "JAVA_HOME": java_home()}
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [
            str(headless),
            "--model", str(model_path),
            "--experiment", experiment_name,
            "--table", str(output_path),
        ],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def parse_table(csv_path: Path | str) -> pd.DataFrame:
    """Parse a NetLogo BehaviorSpace table output (version 2.0 format).

    Skips the 6-line preamble (version banner, model path, experiment name,
    timestamp, world dimensions header, world dimensions values).
    """
    with open(csv_path, encoding="utf-8") as f:
        lines = f.readlines()
    header_idx = next(
        i for i, l in enumerate(lines) if l.startswith('"[run number]"')
    )
    return pd.read_csv(StringIO("".join(lines[header_idx:])))


def trajectory_summary(
    df: pd.DataFrame,
    target_cols: Optional[list[str]] = None,
    tick_col: str = "[step]",
    run_col: str = "[run number]",
    max_tick: Optional[int] = None,
) -> pd.DataFrame:
    """Aggregate per-tick mean/std across runs for trajectory comparison.

    Args:
        df: Output of parse_table (per-run, per-tick rows).
        target_cols: Columns to aggregate (defaults to all numeric except
                     params + step + run number).
        tick_col: Name of the tick/step column.
        run_col: Name of the run-number column.
        max_tick: Truncate trajectories at this tick. NetLogo stops simulations
                  when the epidemic dies out; without truncation, late ticks
                  have fewer than n_runs samples and biased statistics.

    Returns DataFrame indexed by tick with columns `<col>_mean`, `<col>_std`,
    `n_samples`.
    """
    if target_cols is None:
        skip = {tick_col, run_col, "number-of-nodes", "average-node-degree",
                "initial-outbreak-size", "virus-check-frequency",
                "virus-spread-chance", "recovery-chance",
                "gain-resistance-chance"}
        target_cols = [c for c in df.columns if c not in skip
                       and pd.api.types.is_numeric_dtype(df[c])]
    if max_tick is not None:
        df = df[df[tick_col] <= max_tick]

    out: dict[str, list] = {tick_col: []}
    for col in target_cols:
        out[f"{col}_mean"] = []
        out[f"{col}_std"] = []
    out["n_samples"] = []

    for tick, group in df.groupby(tick_col):
        out[tick_col].append(tick)
        out["n_samples"].append(len(group))
        for col in target_cols:
            out[f"{col}_mean"].append(group[col].mean())
            out[f"{col}_std"].append(group[col].std(ddof=0))
    return pd.DataFrame(out).set_index(tick_col)
