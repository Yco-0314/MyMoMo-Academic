"""Summary-statistics adapters for ABC distance computation.

A `SummaryStats` callable reduces a simulator's tick-by-tick DataFrame to a
fixed-length vector. The calibrator's distance metric is L2 over those
vectors, so the choice of summary determines what the calibrator actually
optimizes:

    SummaryStats = Callable[[pd.DataFrame, list[str]], np.ndarray]

Two built-in adapters cover the common cases:

  - `full_trajectory` — flatten the full table (n_ticks × n_targets dims).
    Default for trajectory-matching calibrations. Preserves all per-tick
    information; sharp loss surface; supports local search (Nelder-Mead).

  - `mean_std_last` — per-column [mean, std, last] (3 × n_targets dims).
    Was the original default. Severely loses information — multiple
    trajectories yield identical summaries, producing a flat loss surface
    where NM cannot descend. Kept for calibrations that genuinely care
    only about average/extreme behavior (e.g., "fit the steady-state
    price" not "fit the price curve").

Background: a 2026-05-28 benchmark of the BEHAVE 2025 virus challenge
revealed that mean_std_last was destroying signal — the calibrator's NM
refinement landed on absurd points (virus≈0, virus≈14) because the 9-D
summary had wide flat regions. Switching to full_trajectory restored the
informative loss surface NM needs.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

SummaryStats = Callable[[pd.DataFrame, list[str]], np.ndarray]


# Column aliases: simulator output frequently uses `count_s` / `count_i` etc.
# while observed.csv uses canonical SIR names. `normalize_columns` bridges
# the two so summary_fn sees consistent target names. Mirrors the alias map
# in benchmark_calibration_challenge._COLUMN_ALIASES (intentionally
# duplicated to keep abm_auto.calibration self-contained; if a third
# consumer appears, factor into a shared location).
COLUMN_ALIASES: dict[str, list[str]] = {
    "susceptible": ["susceptible", "count_s", "s", "count_susceptible", "n_susceptible"],
    "infected":    ["infected",    "count_i", "i", "count_infected",    "n_infected"],
    "resistant":   ["resistant",   "count_r", "r", "count_resistant",   "n_resistant",
                    "recovered",   "count_recovered"],
}


def normalize_columns(df: pd.DataFrame, targets: list[str]) -> pd.DataFrame:
    """Rename df columns to match `targets` via the alias map.

    Idempotent — if df already uses target names, returns df unchanged.
    Case-insensitive on the alias side.

    Without this step, a sim writing `count_s/i/r` and a calibrator asking
    for `susceptible/infected/resistant` would silently produce all-zero
    summary vectors, making the entire distance metric a constant.
    """
    df_cols_lower = {c.lower(): c for c in df.columns}
    rename_map: dict[str, str] = {}
    for target in targets:
        if target in df.columns:
            continue
        aliases = COLUMN_ALIASES.get(target.lower(), [target.lower()])
        for alias in aliases:
            if alias in df_cols_lower:
                rename_map[df_cols_lower[alias]] = target
                break
    if rename_map:
        return df.rename(columns=rename_map)
    return df


def full_trajectory(df: pd.DataFrame, targets: list[str]) -> np.ndarray:
    """Flatten the full per-tick trajectory across all target columns.

    Output shape: n_ticks × n_targets, row-major (per-tick blocks). Missing
    columns contribute zeros so the vector length is always consistent.
    """
    arrays: list[np.ndarray] = []
    for col in targets:
        if col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce").fillna(0.0).values
            arrays.append(series.astype(float))
        else:
            # Pad with a placeholder column of zeros matching the table length
            arrays.append(np.zeros(len(df), dtype=float))
    if not arrays:
        return np.zeros(0, dtype=float)
    # Stack as (n_targets, n_ticks) → transpose → flatten in per-tick blocks
    return np.vstack(arrays).T.flatten()


def mean_std_last(df: pd.DataFrame, targets: list[str]) -> np.ndarray:
    """Per-target [mean, std, last_value] — 3 × n_targets dims.

    Missing columns contribute zeros so the vector length is always
    3 × len(targets).
    """
    stats: list[float] = []
    for col in targets:
        if col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(series) > 0:
                stats.extend([
                    float(series.mean()),
                    float(series.std() or 0.0),
                    float(series.iloc[-1]),
                ])
                continue
        stats.extend([0.0, 0.0, 0.0])
    return np.array(stats, dtype=float)


__all__ = [
    "SummaryStats",
    "full_trajectory",
    "mean_std_last",
    "COLUMN_ALIASES",
    "normalize_columns",
]
