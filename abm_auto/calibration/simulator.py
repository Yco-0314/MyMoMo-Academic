"""SimulatorWrapper — calibration's adapter over the workspace + executor.

Stateful (unlike priors/posterior helpers) because it owns:
  - the workspace path (to find scenario CSV + read result CSV)
  - the executor (to actually run a sim)
  - a monotonic run_id counter (every simulate() call gets a unique id)
  - a `summary_fn` (which dictates what the calibrator actually optimizes —
    see abm_auto.calibration.summary_stats)

Provides ONE public method, `simulate(params, targets) → np.ndarray | None`,
which the inference backends consume as a callable. Backends never touch
the executor or the workspace directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from abm_auto.calibration.summary_stats import (
    SummaryStats,
    full_trajectory,
    mean_std_last,
    normalize_columns,
)
from abm_auto.calibration.types import Fidelity


class SimulatorWrapper:
    """Adapts (workspace, executor) into a simulate(params, targets) callable.

    Usage:
        sim = SimulatorWrapper(workspace, executor)
        stats = sim.simulate({"virus_spread_chance": 5.0, ...}, ["susceptible", "infected"])
        # → np.array(flattened trajectory) or None on failure

    Pass `summary_fn=mean_std_last` to switch back to the previous summary
    behavior (3-D per column instead of full trajectory).

    Multi-fidelity: set `sim.fidelity = Fidelity.coarse()` between phases of
    the MF scheduler; subsequent `simulate()` calls inject a scaled
    `periods` into the params dict so the underlying sim runs shorter.
    Backends (RF / ABC / PyMC / NM) need no changes — they see the same
    callable surface.
    """

    def __init__(
        self,
        workspace,
        executor,
        base_run_id: int = 10000,
        summary_fn: SummaryStats = full_trajectory,
        expected_rows: Optional[int] = None,
        fidelity: Optional[Fidelity] = None,
    ):
        """
        Args:
            workspace: abm_auto.runner.workspace.Workspace
            executor:  abm_auto.runner.executor.Executor
            base_run_id: starting run_id for calibration sims. Defaults to 10000
                         to leave room for normal pipeline runs (1, 2, 3, ...).
            summary_fn: reduces sim DataFrame to fixed-length stats vector.
                        Default `full_trajectory` preserves all per-tick info,
                        which gives ABC/NM a sharp loss surface to descend.
            expected_rows: optional row count to TRUNCATE the simulator
                        output DataFrame to before summary_fn runs.
                        When the simulator writes more rows than the
                        observed CSV (e.g., 251 vs 250 due to off-by-one
                        in tick recording), `np.linalg.norm(sim - obs)`
                        raises ValueError on shape mismatch and sklearn's
                        RandomForestRegressor refuses to fit on
                        non-uniform feature lengths across samples. Set
                        this to `len(observed_df)` to align all sims to
                        the observed length. None = no truncation.
        """
        self.workspace = workspace
        self.executor = executor
        self._run_counter = base_run_id
        self.summary_fn = summary_fn
        self.expected_rows = expected_rows
        self.fidelity = fidelity
        # Lazily snapshot the base `periods` so MF scaling stays anchored
        # to the original CSV value, not whatever the previous fidelity
        # write left behind.
        self._base_periods: Optional[int] = None

    @property
    def scenario_csv_path(self) -> Path:
        return self.workspace.model_dir / "data" / "input" / "SimulatorScenarios.csv"

    def _ensure_base_periods(self) -> Optional[int]:
        """Read+cache the scenario CSV's `periods` column on first call.

        Returns None if the CSV doesn't exist or doesn't have a `periods`
        column — callers should treat that as "fidelity scaling is a
        no-op for this model" rather than an error.
        """
        if self._base_periods is not None:
            return self._base_periods
        csv_path = self.scenario_csv_path
        if not csv_path.exists():
            return None
        try:
            df = pd.read_csv(csv_path)
        except Exception:
            return None
        if "periods" not in df.columns or df.empty:
            return None
        self._base_periods = int(df.loc[df.index[0], "periods"])
        return self._base_periods

    def _apply_fidelity(self, params: dict) -> dict:
        """Inject a scaled `periods` into params when fidelity is set.

        Honors a `params['periods']` already set by the caller (rare —
        priors normally exclude `periods`) over the fidelity scaling.

        When fidelity is None or full, this is a no-op — the caller's
        params win and the CSV's current `periods` value persists.
        Callers that need to RESET periods to base (e.g., after a MF
        run wrote coarse periods) should use `restore_periods_to_base()`.
        """
        if self.fidelity is None or self.fidelity.periods_scale == 1.0:
            return params
        if "periods" in params:
            return params
        base = self._ensure_base_periods()
        if base is None:
            return params
        scaled = max(2, int(round(base * self.fidelity.periods_scale)))
        return {**params, "periods": scaled}

    def restore_periods_to_base(self) -> None:
        """Write the snapshotted base `periods` back to the scenario CSV.

        Multi-fidelity stages leave the CSV with whichever scaled
        `periods` the last coarse/medium sim wrote. `apply_best_params`
        and `run_final_validation_sim` (in posterior.py) bypass
        `simulate()` and would otherwise inherit the stale coarse
        value — producing a 50-row validation CSV that breaks MSE
        scoring against a 250-row observed.csv.

        Calibrator.fit() calls this once before returning. Safe no-op
        if base periods were never captured (no MF actually ran).
        """
        if self._base_periods is None:
            return
        csv_path = self.scenario_csv_path
        if not csv_path.exists():
            return
        try:
            df = pd.read_csv(csv_path)
        except Exception:
            return
        if "periods" not in df.columns or df.empty:
            return
        if int(df.loc[df.index[0], "periods"]) == self._base_periods:
            return  # already at base, nothing to write
        df.loc[df.index[0], "periods"] = self._base_periods
        df.to_csv(csv_path, index=False)

    def simulate(self, params: dict, targets: list[str]) -> Optional[np.ndarray]:
        """Run the simulator with `params`, return summary stats over `targets`.

        Returns None on any failure (CSV write fail, simulator crash, empty output).
        Callers use None to mark a sample as rejected.

        Failure observability — `_last_failure_kind` records WHY the most
        recent simulate() returned None (one of: "write_params", "executor",
        "no_csv", "summary_fn", "exception:<ClassName>"). Per-failure
        warnings go through `_log_failure` which dedupes by kind to avoid
        spamming the console when 100 sample sims all fail the same way.
        """
        self._run_counter += 1
        run_id = self._run_counter
        params = self._apply_fidelity(params)
        try:
            self.write_scenario_params(params)
        except Exception as e:
            self._log_failure(f"exception:{type(e).__name__}", f"write_scenario_params failed: {e}")
            return None
        try:
            success, output = self.executor.run(run_id)
        except Exception as e:
            self._log_failure(f"exception:{type(e).__name__}", f"executor.run raised: {e}")
            return None
        if not success:
            self._log_failure("executor", f"executor returned not-OK for run {run_id}: {output[:200]}")
            return None
        try:
            df = self.read_result_metrics(run_id)
        except Exception as e:
            self._log_failure(f"exception:{type(e).__name__}", f"read_result_metrics raised: {e}")
            return None
        if df is None or df.empty:
            self._log_failure("no_csv", f"no result CSV (or empty) for run {run_id}")
            return None
        try:
            df = normalize_columns(df, targets)
            if self.expected_rows is not None:
                df = _align_rows(df, self.expected_rows)
            return self.summary_fn(df, targets)
        except Exception as e:
            self._log_failure(f"exception:{type(e).__name__}", f"summary_fn failed: {e}")
            return None

    def _log_failure(self, kind: str, detail: str) -> None:
        """Record + emit at-most-once warning per failure kind."""
        self._last_failure_kind = kind
        seen = getattr(self, "_logged_failure_kinds", None)
        if seen is None:
            seen = set()
            self._logged_failure_kinds = seen
        if kind not in seen:
            seen.add(kind)
            from rich.console import Console
            Console().print(
                f"  [yellow]simulate() failure ({kind}): {detail}[/yellow]"
            )

    def write_scenario_params(self, params: dict) -> None:
        """Mutate row 0 of SimulatorScenarios.csv with the given params.

        Columns not in `params` are left untouched. Columns in `params` but
        not in the CSV are silently ignored (defensive — calibrator's
        allowlist should already prevent this).

        Dtype handling: if the column's pandas-inferred dtype is narrower
        than `value`'s actual type (typical case: column inferred as int64
        from an earlier integer-valued write, then calibrator writes a
        float from the prior), modern pandas raises a TypeError on the
        `df.loc[..., name] = value` assignment. We widen the column dtype
        first so the assignment succeeds. Without this, BayesianCalibrator
        produced "0 successful sims" — every sample failed silently before
        the subprocess could fire (root cause of the 2026-05-29 dogfood
        bug; see tests/e2e/diagnose_calibrator_zero_sims.py).
        """
        csv_path = self.scenario_csv_path
        if not csv_path.exists():
            return
        df = pd.read_csv(csv_path)
        for name, value in params.items():
            if name not in df.columns:
                continue
            col_dtype = df[name].dtype
            if isinstance(value, float) and not pd.api.types.is_float_dtype(col_dtype):
                df[name] = df[name].astype(float)
            elif isinstance(value, bool) and not pd.api.types.is_bool_dtype(col_dtype):
                df[name] = df[name].astype(bool)
            df.loc[df.index[0], name] = value
        df.to_csv(csv_path, index=False)

    def read_result_metrics(self, run_id: int) -> Optional[pd.DataFrame]:
        """Read the simulator's output CSV for a given run id."""
        csvs = self.workspace.list_result_csvs(run_id)
        if not csvs:
            return None
        try:
            return pd.read_csv(csvs[0])
        except Exception:
            return None


def _align_rows(df: pd.DataFrame, target_n: int) -> pd.DataFrame:
    """Truncate or pad the DataFrame to exactly target_n rows.

    Truncate (df longer than target): keep the first target_n rows.
    Pad (df shorter): repeat the LAST row to fill. Padding with last-row
    value is more honest than zeros — it represents "system reached
    steady state at this point, no further dynamics" rather than "values
    crashed to 0". Calibration distance metrics then reflect that
    steady-state difference rather than treating a stalled sim as a
    catastrophic mismatch.

    Why this exists: cross-domain dogfood revealed that when sim runs
    for N ticks but observed.csv has M ticks (N≠M), RF calibrator
    crashes with "X has K features, expected J" because feature vector
    length depends on row count. Forcing exact row alignment lets RF
    fit and ABC distance norms work consistently.

    Returns a NEW DataFrame; never mutates input.
    """
    n = len(df)
    if n == target_n:
        return df
    if n > target_n:
        return df.iloc[:target_n].reset_index(drop=True)
    # n < target_n: pad with repeated last row
    if n == 0:
        # Edge case: zero-row df, return as-is (caller's summary_fn will
        # produce a zero vector — handled by upstream `if df.empty` check)
        return df
    last_row = df.iloc[-1:]
    padding = pd.concat([last_row] * (target_n - n), ignore_index=True)
    return pd.concat([df.reset_index(drop=True), padding], ignore_index=True)


# Back-compat: external code may still import `summary_stats` from this
# module. Alias it to `mean_std_last` (the historical default). New code
# should import directly from `abm_auto.calibration.summary_stats`.
summary_stats = mean_std_last


def infer_targets(observed: pd.DataFrame) -> list[str]:
    """Default calibration targets: all numeric columns minus obvious id cols.

    Used by orchestrator when spec.calibration_targets is empty.
    """
    skip = {"id", "step", "period", "run_num", "scenario_id", "agent_id"}
    return [
        c for c in observed.columns
        if pd.api.types.is_numeric_dtype(observed[c]) and c.lower() not in skip
    ]
