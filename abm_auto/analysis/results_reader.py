"""
ResultsReader — single seam for reading and analysing simulation output CSVs.

Previously the logic for locating CSVs, filtering metadata columns, and computing
statistics was duplicated across Executor.get_results_summary(), SanityChecker.check_run(),
and Pipeline._has_converged(). All three now delegate here.

Public surface
--------------
METADATA_COLS   — canonical set of columns to exclude from metric analysis
load_run()      — returns list[DataFrame] for one run
numeric_metrics() — filters a DataFrame down to meaningful numeric metric columns
describe()      — text summary suitable for LLM consumption
convergence_cv()  — coefficient-of-variation convergence check across N runs
"""
from __future__ import annotations

import logging
import pandas as pd
from pathlib import Path

from abm_auto.runner.workspace import Workspace

logger = logging.getLogger(__name__)

# Single canonical skip-list used by every caller.
# Previously each caller maintained its own slightly different copy.
METADATA_COLS: frozenset[str] = frozenset({
    "id", "id_scenario", "id_run", "run_num",
    "agent_id", "period", "step", "t", "time", "tick",
    "x", "y",
})


def load_run(workspace: Workspace, run_id: int) -> list[pd.DataFrame]:
    """Load all result CSVs for *run_id* and return them as DataFrames.

    Uses the canonical Workspace.list_result_csvs() seam so callers never
    touch the directory structure directly.
    """
    dfs = []
    for csv_path in workspace.list_result_csvs(run_id):
        try:
            dfs.append(pd.read_csv(csv_path))
        except Exception as exc:
            logger.warning("skipping unreadable CSV %s: %s", csv_path, exc)
            continue
    return dfs


def numeric_metrics(df: pd.DataFrame) -> list[str]:
    """Return column names that are numeric and not metadata.

    This is the single definition of "a meaningful metric column".
    """
    return [
        c for c in df.columns
        if c.lower() not in METADATA_COLS
        and pd.api.types.is_numeric_dtype(df[c])
    ]


def describe(workspace: Workspace, run_id: int) -> str:
    """Return a text description of all CSVs for *run_id*, suitable for LLM prompts.

    Replaces Executor.get_results_summary() — that method now delegates here.
    """
    csvs = workspace.list_result_csvs(run_id)
    if not csvs:
        return "No CSV output files found."

    parts = []
    for csv_path in sorted(csvs):
        try:
            df = pd.read_csv(csv_path)
            desc = df.describe().to_string()
            parts.append(f"### {csv_path.name}\nShape: {df.shape}\n```\n{desc}\n```")
        except Exception as e:
            parts.append(f"### {csv_path.name}\nError reading: {e}")

    return "\n\n".join(parts)


def convergence_cv(
    workspace: Workspace,
    run_ids: list[int],
    cv_threshold: float = 0.05,
) -> tuple[bool, dict[str, float]]:
    """Check whether metric means have converged across *run_ids*.

    A metric is considered converged when its coefficient of variation
    (σ / |μ|) across the final values of each run is below *cv_threshold*.

    Returns
    -------
    converged : bool
        True when ALL metrics satisfy the CV threshold.
    cv_by_metric : dict[str, float]
        CV value per metric (useful for diagnostics).
    """
    if len(run_ids) < 2:
        return False, {}

    metric_finals: dict[str, list[float]] = {}

    for run_id in run_ids:
        csvs = workspace.list_result_csvs(run_id)
        if not csvs:
            continue

        # Prefer environment / aggregated CSV; fall back to first one
        target: Path | None = None
        for p in sorted(csvs):
            if "env" in p.name.lower() or "environment" in p.name.lower():
                target = p
                break
        if target is None:
            target = sorted(csvs)[0]

        try:
            df = pd.read_csv(target)
        except Exception as exc:
            logger.warning("skipping unreadable CSV %s: %s", target, exc)
            continue

        metrics = [c for c in numeric_metrics(df) if df[c].nunique() > 1]
        for col in metrics:
            metric_finals.setdefault(col, []).append(float(df[col].iloc[-1]))

    if not metric_finals:
        return False, {}

    cv_by_metric: dict[str, float] = {}
    for col, values in metric_finals.items():
        if len(values) < 2:
            continue
        s = pd.Series(values)
        mean = s.mean()
        # 1e-10 guards div-by-zero when a metric's mean is ~0; below it the ratio
        # is meaningless (would blow up), so report CV 0.0 rather than a huge value.
        cv = (s.std() / abs(mean)) if abs(mean) > 1e-10 else 0.0
        cv_by_metric[col] = round(cv, 4)

    if not cv_by_metric:
        return False, {}

    converged = all(cv <= cv_threshold for cv in cv_by_metric.values())
    return converged, cv_by_metric
