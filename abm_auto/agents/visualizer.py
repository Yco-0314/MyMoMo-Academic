"""
Visualization agent: generates publication-quality figures from simulation results.

Produces:
1. Time-series plot of key metrics across simulation steps
2. Multi-run trajectory comparison (if multiple runs)
3. Parameter sensitivity tornado diagram (if SALib indices available)
4. Agent state distribution heatmap (for grid-based models)
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from rich.console import Console

console = Console()


class VisualizerAgent:
    """Generates figures from simulation results. No LLM calls — pure data visualization.

    Accepts ``lang`` to produce language-appropriate axis labels and titles.
    Does not extend ``BaseAgent`` (no LLM client needed), but follows the same
    ``__init__(workspace_path, lang=...)`` call signature used in pipeline.py.
    """

    # Localised label strings — add more langs as needed
    _LABELS: dict[str, dict[str, str]] = {
        "en": {
            "step": "Step",
            "value": "Value",
            "run": "Run",
            "time_series": "Time-series: {col}",
            "trajectories": "Multi-run trajectories: {col}",
            "sensitivity": "Sensitivity Analysis (Morris μ*)",
            "parameter": "Parameter",
            "mu_star": "μ* (mean abs. elementary effect)",
        },
        "zh": {
            "step": "步骤",
            "value": "值",
            "run": "运行",
            "time_series": "时间序列：{col}",
            "trajectories": "多轮轨迹对比：{col}",
            "sensitivity": "Morris 敏感性分析（μ*）",
            "parameter": "参数",
            "mu_star": "μ*（均值绝对基本效应）",
        },
    }

    def __init__(self, workspace_path: Path, lang: str = "zh"):
        self.workspace = workspace_path
        self.lang = lang if lang in self._LABELS else "en"
        self.figures_dir = workspace_path / "figures"
        self.figures_dir.mkdir(exist_ok=True)

    def _label(self, key: str, **fmt) -> str:
        """Return a localised label string, with optional .format() kwargs."""
        tmpl = self._LABELS[self.lang].get(key, self._LABELS["en"][key])
        return tmpl.format(**fmt) if fmt else tmpl

    def _setup_style(self) -> None:
        """Apply publication-quality style + CJK font fallback for lang='zh'.

        Without the CJK font setup, every Chinese glyph in axis labels /
        titles renders as a placeholder box and matplotlib emits a
        UserWarning per glyph (observed: ~14 warnings per run in the
        2026-05-29 dogfood test).
        """
        import matplotlib.pyplot as plt
        try:
            import seaborn as sns
            sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
        except ImportError:
            plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "ggplot")

        if self.lang == "zh":
            # Probe matplotlib's font registry at runtime — the static list of
            # CJK font NAMES used to be hard-coded but didn't always match
            # what's actually installed (`PingFang SC` on macOS appears as
            # `PingFang HK` or `Hannotate SC`; Linux ships `Noto Sans CJK SC`
            # but only when fonts-noto-cjk is installed). The 2026-05-29
            # dogfoods all still emitted ~14 CJK glyph warnings because none
            # of the listed names matched the system. This probe picks the
            # first font matplotlib actually sees from a broader candidate
            # set covering macOS / Linux / Windows defaults.
            from matplotlib import font_manager
            installed = {f.name for f in font_manager.fontManager.ttflist}
            candidates = [
                # macOS (verified via font_manager listing)
                "PingFang SC", "PingFang HK", "Hiragino Sans GB",
                "Hannotate SC", "Songti SC", "Heiti TC", "STHeiti",
                # Linux
                "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Zen Hei",
                # Windows
                "Microsoft YaHei", "SimHei",
            ]
            chosen = [c for c in candidates if c in installed]
            if chosen:
                current = plt.rcParams.get("font.sans-serif", [])
                plt.rcParams["font.sans-serif"] = chosen + list(current)
            # Some CJK fonts lack a minus glyph; turn off the unicode minus
            # so axes don't render a placeholder for negative numbers.
            plt.rcParams["axes.unicode_minus"] = False

    @staticmethod
    def _save(fig, path: Path) -> None:
        """Save figure as both PNG (screen) and PDF (print/journal submission)."""
        import matplotlib.pyplot as plt
        fig.savefig(path, dpi=150, bbox_inches="tight")
        fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
        plt.close(fig)

    def run(self) -> list[Path]:
        """Generate all applicable figures. Returns list of generated file paths."""
        try:
            import matplotlib
            matplotlib.use("Agg")  # non-interactive backend
            import matplotlib.pyplot as plt
            self._setup_style()
        except ImportError:
            console.print("  [yellow]⚠ matplotlib not available, skipping visualization[/yellow]")
            return []

        generated: list[Path] = []

        # Collect all run CSVs
        results_dir = self.workspace / "results"
        run_dirs = sorted(results_dir.glob("run_*")) if results_dir.exists() else []

        if not run_dirs:
            console.print("  [yellow]⚠ No run results found, skipping visualization[/yellow]")
            return generated

        # 1. Time-series plot from first run
        fig_path = self._plot_timeseries(run_dirs)
        if fig_path:
            generated.append(fig_path)

        # 2. Multi-run trajectory comparison
        if len(run_dirs) >= 2:
            fig_path = self._plot_trajectories(run_dirs)
            if fig_path:
                generated.append(fig_path)

        # 3. Sensitivity tornado (if available)
        sa_path = self.workspace / "sensitivity_indices.json"
        if sa_path.exists():
            fig_path = self._plot_sensitivity(sa_path)
            if fig_path:
                generated.append(fig_path)

        # 4. Final state distribution
        fig_path = self._plot_final_distribution(run_dirs[-1])
        if fig_path:
            generated.append(fig_path)

        if generated:
            console.print(f"  [green]✓ {len(generated)} figures generated in figures/[/green]")

        # Audit (works around the fact that VisualizerAgent takes a Path, not Workspace)
        try:
            from abm_auto.audit import AuditLedger
            AuditLedger(self.workspace).info(
                phase="Phase 7b",
                text=f"Generated {len(generated)} figures",
                actor="VisualizerAgent",
                structured={
                    "n_figures": len(generated),
                    "figure_names": [p.stem for p in generated],
                },
            )
        except Exception:
            pass

        return generated

    def _plot_timeseries(self, run_dirs: list[Path]) -> Path | None:
        """Plot key metrics over simulation steps; shaded CI when multiple runs available."""
        import matplotlib.pyplot as plt  # backend already set to Agg in run()
        import numpy as np

        csvs = list(run_dirs[0].glob("*.csv"))
        if not csvs:
            return None

        # Prefer environment CSV (aggregated metrics), fall back to first CSV
        env_csv = None
        for c in csvs:
            if "environment" in c.name.lower() or "env" in c.name.lower():
                env_csv = c
                break
        target = env_csv or csvs[0]

        try:
            df = pd.read_csv(target)
        except Exception:
            return None

        # Find time column
        time_col = None
        for candidate in ["period", "step", "t", "time", "tick"]:
            if candidate in df.columns:
                time_col = candidate
                break
        if time_col is None and "period" not in df.columns:
            # Use index as time
            df["_step"] = range(len(df))
            time_col = "_step"

        # Select numeric columns (skip metadata)
        skip = {"id", "id_scenario", "id_run", "run_num", "agent_id", "_step"}
        metrics = [
            c for c in df.columns
            if c != time_col
            and c.lower() not in skip
            and pd.api.types.is_numeric_dtype(df[c])
            and df[c].nunique() > 1
        ]

        if not metrics:
            return None

        # Plot up to 6 metrics
        metrics = metrics[:6]
        fig, axes = plt.subplots(
            len(metrics), 1,
            figsize=(10, 3 * len(metrics)),
            sharex=True,
            squeeze=False,
        )

        # Try to stack all runs for CI shading
        all_dfs: list[pd.DataFrame] = []
        for rd in run_dirs:
            csvs_rd = list(rd.glob("*.csv"))
            target_rd = None
            for c in csvs_rd:
                if "environment" in c.name.lower() or "env" in c.name.lower():
                    target_rd = c
                    break
            if target_rd is None and csvs_rd:
                target_rd = csvs_rd[0]
            if target_rd and target_rd.name == target.name:
                try:
                    all_dfs.append(pd.read_csv(target_rd))
                except Exception:
                    pass

        for i, col in enumerate(metrics):
            ax = axes[i, 0]
            if len(all_dfs) >= 2 and time_col:
                # Plot mean ± 1σ confidence band across all runs
                try:
                    arrays = [d.set_index(time_col)[col].values for d in all_dfs
                               if time_col in d.columns and col in d.columns]
                    min_len = min(len(a) for a in arrays)
                    mat = np.array([a[:min_len] for a in arrays])
                    t_axis = all_dfs[0][time_col].values[:min_len]
                    mean = mat.mean(axis=0)
                    std = mat.std(axis=0)
                    ax.plot(t_axis, mean, linewidth=1.8, label="Mean")
                    ax.fill_between(t_axis, mean - std, mean + std, alpha=0.25, label="±1σ")
                    ax.legend(fontsize=8, loc="upper right")
                except Exception:
                    ax.plot(df[time_col], df[col], linewidth=1.5)
            else:
                ax.plot(df[time_col], df[col], linewidth=1.5)
            ax.set_ylabel(col, fontsize=10)

        axes[-1, 0].set_xlabel(self._label("step"), fontsize=10)
        fig.suptitle(self._label("time_series", col="Run 1"), fontsize=13, fontweight="bold")
        plt.tight_layout()

        out = self.figures_dir / "timeseries.png"
        self._save(fig, out)
        return out

    def _plot_trajectories(self, run_dirs: list[Path]) -> Path | None:
        """Mean ± 1σ CI trajectories across all runs (individual traces as faint lines)."""
        import matplotlib.pyplot as plt  # backend already set to Agg in run()
        import numpy as np

        # Find a common CSV name across runs
        first_csvs = {c.name for c in run_dirs[0].glob("*.csv")}
        if not first_csvs:
            return None

        # Prefer environment CSV
        target_name = None
        for name in first_csvs:
            if "environment" in name.lower() or "env" in name.lower():
                target_name = name
                break
        if not target_name:
            target_name = sorted(first_csvs)[0]

        # Load all runs
        dfs = []
        for rd in run_dirs:
            csv_path = rd / target_name
            if csv_path.exists():
                try:
                    dfs.append(pd.read_csv(csv_path))
                except Exception:
                    continue

        if len(dfs) < 2:
            return None

        # Find time column and metric columns
        time_col = None
        for c in ["period", "step", "t", "time"]:
            if c in dfs[0].columns:
                time_col = c
                break

        skip = {"id", "id_scenario", "id_run", "run_num", "agent_id", "period", "step", "t", "time"}
        metric_cols = [
            c for c in dfs[0].columns
            if c.lower() not in skip
            and pd.api.types.is_numeric_dtype(dfs[0][c])
            and dfs[0][c].nunique() > 1
        ]

        if not metric_cols or not time_col:
            return None

        # Plot up to 4 metrics
        metric_cols = metric_cols[:4]
        fig, axes = plt.subplots(
            len(metric_cols), 1,
            figsize=(10, 3 * len(metric_cols)),
            sharex=True,
            squeeze=False,
        )

        palette = plt.cm.tab10.colors
        for i, col in enumerate(metric_cols):
            ax = axes[i, 0]

            # Stack arrays for CI
            try:
                arrays = [df.set_index(time_col)[col].values for df in dfs
                           if time_col in df.columns and col in df.columns]
                min_len = min(len(a) for a in arrays)
                mat = np.array([a[:min_len] for a in arrays])
                t_axis = dfs[0][time_col].values[:min_len]

                # Faint individual runs
                for j, row in enumerate(mat):
                    ax.plot(t_axis, row, linewidth=0.8, alpha=0.35,
                            color=palette[j % len(palette)])

                # Bold mean + CI band
                mean = mat.mean(axis=0)
                std = mat.std(axis=0)
                ax.plot(t_axis, mean, linewidth=2.0, color="black", label="Mean", zorder=5)
                ax.fill_between(t_axis, mean - std, mean + std,
                                alpha=0.20, color="steelblue", label="±1σ")
            except Exception:
                # Fallback: individual coloured lines
                for j, df in enumerate(dfs):
                    if col in df.columns and time_col in df.columns:
                        ax.plot(df[time_col], df[col], linewidth=1.2, alpha=0.7,
                                color=palette[j % len(palette)], label=f"Run {j + 1}")

            ax.set_ylabel(col, fontsize=10)
            if i == 0:
                ax.legend(fontsize=8, loc="upper right")

        axes[-1, 0].set_xlabel(time_col, fontsize=10)
        fig.suptitle("Multi-Run Trajectory Comparison", fontsize=13, fontweight="bold")
        plt.tight_layout()

        out = self.figures_dir / "trajectories.png"
        self._save(fig, out)
        return out

    def _plot_sensitivity(self, sa_path: Path) -> Path | None:
        """Tornado diagram from SALib sensitivity indices."""
        import matplotlib.pyplot as plt  # backend already set to Agg in run()

        try:
            data = json.loads(sa_path.read_text())
        except Exception:
            return None

        params = data.get("params", [])
        s1 = data.get("S1") or data.get("mu_star")
        if not params or not s1:
            return None

        # Sort by absolute sensitivity
        pairs = sorted(zip(params, s1), key=lambda x: abs(x[1]), reverse=True)
        names, values = zip(*pairs)

        fig, ax = plt.subplots(figsize=(8, max(4, len(names) * 0.4)))
        bars = ax.barh(range(len(names)), values, color="#4A90D9", edgecolor="white")
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=10)
        ax.set_xlabel("Sensitivity Index", fontsize=11)
        ax.set_title("Parameter Sensitivity (Tornado)", fontsize=13, fontweight="bold")
        ax.invert_yaxis()
        ax.grid(True, axis="x", alpha=0.3)
        plt.tight_layout()

        out = self.figures_dir / "sensitivity_tornado.png"
        self._save(fig, out)
        return out

    def _plot_final_distribution(self, last_run_dir: Path) -> Path | None:
        """Distribution of agent states at the final timestep."""
        import matplotlib.pyplot as plt  # backend already set to Agg in run()

        # Find agent CSV
        agent_csv = None
        for c in last_run_dir.glob("*.csv"):
            if "agent" in c.name.lower():
                agent_csv = c
                break
        if not agent_csv:
            return None

        try:
            df = pd.read_csv(agent_csv)
        except Exception:
            return None

        if "period" not in df.columns:
            return None

        # Get last period
        last_period = df["period"].max()
        final = df[df["period"] == last_period]

        # Find categorical or state column
        state_col = None
        for candidate in ["state", "status", "category", "type", "strategy"]:
            if candidate in final.columns:
                state_col = candidate
                break

        if not state_col:
            return None

        fig, ax = plt.subplots(figsize=(8, 5))
        counts = final[state_col].value_counts()
        counts.plot(kind="bar", ax=ax, color="#4A90D9", edgecolor="white")
        ax.set_xlabel(state_col, fontsize=11)
        ax.set_ylabel("Count", fontsize=11)
        ax.set_title(f"Agent {state_col.title()} Distribution (Final Step)", fontsize=13, fontweight="bold")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        out = self.figures_dir / "final_distribution.png"
        self._save(fig, out)
        return out
