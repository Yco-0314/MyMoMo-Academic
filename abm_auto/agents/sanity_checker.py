"""
Post-run sanity checker: detects degenerate simulations where
agent states never change (e.g., zero infections in an epidemic model).

This catches the class of bugs where code runs without errors but produces
meaningless output — typically caused by setup() overwriting CSV-loaded
initial states, or broken interaction logic.
"""
from __future__ import annotations

import re

import pandas as pd
from pathlib import Path
from rich.console import Console

from abm_auto.analysis.results_reader import METADATA_COLS, numeric_metrics

console = Console()


class SanityChecker:
    """Checks simulation output for degenerate patterns."""

    @staticmethod
    def check_pre_run(model_dir: Path, design_text: str = "") -> list[str]:
        """
        Pre-run checks before simulation execution.
        Validates agent_num consistency with grid dimensions, CSV existence, etc.
        Returns list of warning strings (empty = all OK).
        """
        warnings: list[str] = []

        csv_path = model_dir / "data" / "input" / "SimulatorScenarios.csv"
        if not csv_path.exists():
            warnings.append(
                f"⚠ SimulatorScenarios.csv not found at {csv_path}. "
                "Check that main.py uses input_folder='data/input'."
            )
            return warnings

        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            warnings.append(f"⚠ Cannot read SimulatorScenarios.csv: {e}")
            return warnings

        if df.empty:
            warnings.append("⚠ SimulatorScenarios.csv is empty (no rows).")
            return warnings

        row = df.iloc[0]

        # Check: grid models must have agent_num = grid_width * grid_height
        is_grid = "grid_width" in df.columns and "grid_height" in df.columns
        if not is_grid and design_text:
            is_grid = bool(re.search(r"grid|Grid|GridAgent|grid_width", design_text))

        if is_grid and "grid_width" in df.columns and "grid_height" in df.columns:
            gw = int(row.get("grid_width", 0))
            gh = int(row.get("grid_height", 0))
            agent_num = int(row.get("agent_num", 0))
            expected = gw * gh

            if expected > 0 and agent_num != expected:
                warnings.append(
                    f"⚠ agent_num={agent_num} but grid is {gw}×{gh}={expected}. "
                    f"Auto-fixing agent_num to {expected}."
                )
                df.at[0, "agent_num"] = expected
                df.to_csv(csv_path, index=False)
                console.print(f"  [green]✓ Auto-fixed agent_num: {agent_num} → {expected}[/green]")

        # Check: agent_num should be > 0
        if "agent_num" in df.columns and int(row.get("agent_num", 0)) == 0:
            warnings.append(
                "⚠ agent_num=0 in SimulatorScenarios.csv — "
                "simulation will create no agents."
            )

        # Check: periods should be > 0
        if "periods" in df.columns and int(row.get("periods", 0)) == 0:
            warnings.append("⚠ periods=0 — simulation will run for 0 steps.")

        return warnings

    @staticmethod
    def check_run(result_csvs: list[Path], design_text: str = "") -> list[str]:
        """
        Analyze output CSVs for suspicious patterns.
        Returns list of warning strings (empty = all OK).
        """
        warnings: list[str] = []

        for csv_path in result_csvs:
            try:
                df = pd.read_csv(csv_path)
            except Exception:
                continue

            # Skip small files
            if len(df) < 2:
                continue

            # --- Check 1: Constant columns that should vary ---
            # Environment-level CSVs with aggregates
            numeric_cols = numeric_metrics(df)
            constant_cols = [c for c in numeric_cols if df[c].nunique() <= 1]
            varying_cols = [c for c in numeric_cols if df[c].nunique() > 1]

            if numeric_cols and not varying_cols:
                warnings.append(
                    f"⚠ {csv_path.name}: ALL numeric columns are constant — "
                    f"no dynamics observed. Columns: {constant_cols[:5]}. "
                    f"Likely cause: agent initial states not set correctly "
                    f"(check if agent.setup() overwrites CSV-loaded attributes)."
                )

            # --- Check 2: State column never changes (agent CSV) ---
            if "state" in df.columns and "period" in df.columns:
                states_by_period = df.groupby("period")["state"].nunique()
                if (states_by_period <= 1).all() and len(states_by_period) > 5:
                    unique_state = df["state"].iloc[0]
                    warnings.append(
                        f"⚠ {csv_path.name}: agent 'state' is always {unique_state} "
                        f"across all periods — no state transitions occurred."
                    )

            # --- Check 3: Environment counters don't change ---
            if "environment" in csv_path.name.lower():
                for col in numeric_cols:
                    if col in constant_cols and "count" in col.lower():
                        val = df[col].iloc[0]
                        warnings.append(
                            f"⚠ {csv_path.name}: '{col}' is constant ({val}) "
                            f"throughout the simulation."
                        )

        return warnings

    @staticmethod
    def format_warnings(warnings: list[str]) -> str:
        """Format warnings for LLM consumption."""
        if not warnings:
            return ""
        header = (
            "SANITY CHECK FAILED — The simulation ran without errors but produced "
            "degenerate output. The most common cause is agent.setup() overwriting "
            "CSV-loaded initial states. Fix the initialization logic.\n\n"
        )
        return header + "\n".join(warnings)
