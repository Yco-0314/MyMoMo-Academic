"""SimulatorWrapper — calibration's adapter over the workspace + executor.

Stateful (unlike priors/posterior helpers) because it owns:
  - the workspace path (to find scenario CSV + read result CSV)
  - the executor (to actually run a sim)
  - a monotonic run_id counter (every simulate() call gets a unique id)

Provides ONE public method, `simulate(params, targets) → np.ndarray | None`,
which the inference backends consume as a callable. Backends never touch
the executor or the workspace directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


class SimulatorWrapper:
    """Adapts (workspace, executor) into a simulate(params, targets) callable.

    Usage:
        sim = SimulatorWrapper(workspace, executor)
        stats = sim.simulate({"virus_spread_chance": 5.0, ...}, ["susceptible", "infected"])
        # → np.array([mean_s, std_s, last_s, mean_i, std_i, last_i]) or None on failure
    """

    def __init__(self, workspace, executor, base_run_id: int = 10000):
        """
        Args:
            workspace: abm_auto.runner.workspace.Workspace
            executor:  abm_auto.runner.executor.Executor
            base_run_id: starting run_id for calibration sims. Defaults to 10000
                         to leave room for normal pipeline runs (1, 2, 3, ...).
        """
        self.workspace = workspace
        self.executor = executor
        self._run_counter = base_run_id

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
            return summary_stats(df, targets)
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


def summary_stats(df: pd.DataFrame, targets: list[str]) -> np.ndarray:
    """Reduce a time-series CSV to a fixed-length summary vector.

    For each target column: [mean, std, last_value]. Missing columns
    contribute zeros so the vector length is always 3 × len(targets).

    Free function (not a method) so backends can call it on observed data
    too without constructing a SimulatorWrapper.
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


def infer_targets(observed: pd.DataFrame) -> list[str]:
    """Default calibration targets: all numeric columns minus obvious id cols.

    Used by orchestrator when spec.calibration_targets is empty.
    """
    skip = {"id", "step", "period", "run_num", "scenario_id", "agent_id"}
    return [
        c for c in observed.columns
        if pd.api.types.is_numeric_dtype(observed[c]) and c.lower() not in skip
    ]
