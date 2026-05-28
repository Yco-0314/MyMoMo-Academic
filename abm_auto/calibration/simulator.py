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


class SimulatorWrapper:
    """Adapts (workspace, executor) into a simulate(params, targets) callable.

    Usage:
        sim = SimulatorWrapper(workspace, executor)
        stats = sim.simulate({"virus_spread_chance": 5.0, ...}, ["susceptible", "infected"])
        # → np.array(flattened trajectory) or None on failure

    Pass `summary_fn=mean_std_last` to switch back to the previous summary
    behavior (3-D per column instead of full trajectory).
    """

    def __init__(
        self,
        workspace,
        executor,
        base_run_id: int = 10000,
        summary_fn: SummaryStats = full_trajectory,
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
        """
        self.workspace = workspace
        self.executor = executor
        self._run_counter = base_run_id
        self.summary_fn = summary_fn

    @property
    def scenario_csv_path(self) -> Path:
        return self.workspace.model_dir / "data" / "input" / "SimulatorScenarios.csv"

    def simulate(self, params: dict, targets: list[str]) -> Optional[np.ndarray]:
        """Run the simulator with `params`, return summary stats over `targets`.

        Returns None on any failure (CSV write fail, simulator crash, empty output).
        Callers use None to mark a sample as rejected.
        """
        try:
            self.write_scenario_params(params)
            self._run_counter += 1
            run_id = self._run_counter
            success, _ = self.executor.run(run_id)
            if not success:
                return None
            df = self.read_result_metrics(run_id)
            if df is None or df.empty:
                return None
            # Bridge sim's column-naming convention (e.g. `count_s`) to the
            # canonical target names (`susceptible`) before summarizing.
            # Without this step, summary_fn returns all zeros silently.
            df = normalize_columns(df, targets)
            return self.summary_fn(df, targets)
        except Exception:
            return None

    def write_scenario_params(self, params: dict) -> None:
        """Mutate row 0 of SimulatorScenarios.csv with the given params.

        Columns not in `params` are left untouched. Columns in `params` but
        not in the CSV are silently ignored (defensive — calibrator's
        allowlist should already prevent this).
        """
        csv_path = self.scenario_csv_path
        if not csv_path.exists():
            return
        df = pd.read_csv(csv_path)
        for name, value in params.items():
            if name in df.columns:
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
