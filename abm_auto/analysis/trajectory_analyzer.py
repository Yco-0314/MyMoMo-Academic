"""
Trajectory analysis for ABM simulation runs.

Adapted from a prior internal tool's path_analyzer.py for the abm-auto context:
- Clusters runs by output trajectory shape (KMeans on time-series vectors)
- Detects critical timesteps where trajectories diverge
- Correlates parameter values with outcome clusters

Pure analytics — no LLM calls, no simulation state mutations.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class TrajectoryCluster:
    cluster_id: int
    label: str
    member_runs: list[int]
    avg_final_value: float
    std_final_value: float
    size: int
    distinguishing_params: dict[str, float]  # param_name → avg value in cluster


@dataclass
class CriticalTimestep:
    timestep: int
    column: str
    divergence_score: float  # absolute difference between cluster means
    cluster_means: dict[int, float]  # cluster_id → mean value at this timestep


@dataclass
class ParameterCorrelation:
    parameter: str
    metric_column: str
    correlation: float  # Pearson r
    p_value: float
    direction: str  # "positive", "negative", "weak"


@dataclass
class TrajectoryAnalysisResult:
    total_runs: int
    metric_column: str
    metric_file: str
    clusters: list[TrajectoryCluster]
    critical_timesteps: list[CriticalTimestep]
    param_correlations: list[ParameterCorrelation]

    def to_summary(self) -> str:
        lines = [
            f"# 轨迹分析报告",
            f"",
            f"- 总运行次数: {self.total_runs}",
            f"- 分析指标: {self.metric_file}:{self.metric_column}",
            f"",
            f"## 轨迹聚类 ({len(self.clusters)} 类)",
        ]
        for c in self.clusters:
            lines.append(f"### Cluster {c.cluster_id}: {c.label}")
            lines.append(f"- 成员: runs {c.member_runs}")
            lines.append(f"- 终值: {c.avg_final_value:.4f} ± {c.std_final_value:.4f}")
            if c.distinguishing_params:
                params_str = ", ".join(f"{k}={v:.3f}" for k, v in c.distinguishing_params.items())
                lines.append(f"- 特征参数: {params_str}")
            lines.append("")

        if self.critical_timesteps:
            lines.append(f"## 关键分叉点 (top {len(self.critical_timesteps)})")
            for ct in self.critical_timesteps[:10]:
                means_str = ", ".join(f"C{k}={v:.4f}" for k, v in ct.cluster_means.items())
                lines.append(f"- t={ct.timestep}: divergence={ct.divergence_score:.4f} ({means_str})")
            lines.append("")

        if self.param_correlations:
            lines.append(f"## 参数-结果相关性")
            for pc in self.param_correlations:
                lines.append(f"- {pc.parameter}: r={pc.correlation:.3f} (p={pc.p_value:.4f}, {pc.direction})")
            lines.append("")

        return "\n".join(lines)


class TrajectoryAnalyzer:
    """Analyzes ABM output trajectories across multiple runs."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.results_dir = workspace_path / "results"
        self.params_history_path = workspace_path / "params_history.json"

    def analyze(
        self,
        metric_column: str | None = None,
        metric_file: str | None = None,
    ) -> TrajectoryAnalysisResult | None:
        """
        Run full trajectory analysis across all completed runs.

        Args:
            metric_column: CSV column to track. Auto-detected if None.
            metric_file: Which CSV file. Auto-detected if None.

        Returns:
            TrajectoryAnalysisResult or None if insufficient data.
        """
        # 1. Load trajectories from all runs
        trajectories, run_ids, resolved_col, resolved_file = self._load_trajectories(
            metric_column, metric_file
        )
        if len(trajectories) < 3:
            return None  # need at least 3 runs

        # 2. Load parameter history
        params_by_run = self._load_params()

        # 3. Cluster trajectories
        clusters, labels = self._cluster_trajectories(trajectories, run_ids, params_by_run)

        # 4. Find critical timesteps
        critical = self._find_critical_timesteps(trajectories, labels, resolved_col)

        # 5. Parameter-outcome correlations
        correlations = self._compute_correlations(trajectories, run_ids, params_by_run, resolved_col)

        result = TrajectoryAnalysisResult(
            total_runs=len(run_ids),
            metric_column=resolved_col,
            metric_file=resolved_file,
            clusters=clusters,
            critical_timesteps=critical,
            param_correlations=correlations,
        )

        # Save results
        self._save(result)
        return result

    def _load_trajectories(
        self,
        metric_column: str | None,
        metric_file: str | None,
    ) -> tuple[list[np.ndarray], list[int], str, str]:
        """Load time-series data from all run directories."""
        trajectories = []
        run_ids = []
        resolved_col = metric_column
        resolved_file = metric_file

        # Find all run directories
        run_dirs = sorted(self.results_dir.glob("run_*"))
        # Filter out SA runs (run_9xxx)
        run_dirs = [d for d in run_dirs if int(d.name.split("_")[1]) < 9000]

        for run_dir in run_dirs:
            run_num = int(run_dir.name.split("_")[1])
            csvs = list(run_dir.glob("*.csv"))
            if not csvs:
                continue

            # Pick target CSV
            target = None
            if resolved_file:
                target = next((c for c in csvs if c.name == resolved_file), None)
            if target is None:
                target = csvs[0]
                resolved_file = target.name

            try:
                df = pd.read_csv(target)
            except Exception:
                continue

            # Pick target column
            if resolved_col and resolved_col in df.columns:
                col = resolved_col
            else:
                skip = {"id", "step", "period", "run_num", "scenario_id", "agent_id"}
                col = None
                for c in df.columns:
                    if c.lower() in skip:
                        continue
                    if pd.api.types.is_numeric_dtype(df[c]):
                        col = c
                        break
                if col is None:
                    continue
                resolved_col = col

            # Aggregate by step if agent-level data
            if "step" in df.columns or "period" in df.columns:
                step_col = "step" if "step" in df.columns else "period"
                series = df.groupby(step_col)[col].mean().values
            else:
                series = df[col].values

            trajectories.append(series.astype(float))
            run_ids.append(run_num)

        return trajectories, run_ids, resolved_col or "", resolved_file or ""

    def _load_params(self) -> dict[int, dict]:
        """Load params_history.json → {run_id: params_dict}."""
        if not self.params_history_path.exists():
            return {}
        history = json.loads(self.params_history_path.read_text())
        return {h["run"]: h.get("params", {}) for h in history}

    def _cluster_trajectories(
        self,
        trajectories: list[np.ndarray],
        run_ids: list[int],
        params_by_run: dict[int, dict],
    ) -> tuple[list[TrajectoryCluster], np.ndarray]:
        """Cluster runs by trajectory shape using KMeans."""
        # Normalize to same length (pad with final value)
        max_len = max(len(t) for t in trajectories)
        matrix = np.zeros((len(trajectories), max_len))
        for i, t in enumerate(trajectories):
            matrix[i, :len(t)] = t
            if len(t) < max_len:
                matrix[i, len(t):] = t[-1]

        # Determine n_clusters
        n = len(trajectories)
        n_clusters = min(max(2, n // 3), 6)

        try:
            from sklearn.cluster import KMeans
            km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = km.fit_predict(matrix)
        except ImportError:
            # Fallback: split by final value median
            finals = matrix[:, -1]
            median = np.median(finals)
            labels = np.array([0 if v <= median else 1 for v in finals])

        # Build cluster objects
        clusters = []
        all_params = set()
        for rid in run_ids:
            all_params.update(params_by_run.get(rid, {}).keys())

        for cid in sorted(set(labels)):
            mask = labels == cid
            member_runs = [run_ids[i] for i in range(len(run_ids)) if mask[i]]
            finals = matrix[mask, -1]

            # Compute distinguishing params (avg in this cluster)
            distinguishing = {}
            for param in all_params:
                vals = [
                    float(params_by_run.get(rid, {}).get(param, 0))
                    for rid in member_runs
                    if param in params_by_run.get(rid, {})
                ]
                if vals:
                    distinguishing[param] = np.mean(vals)

            clusters.append(TrajectoryCluster(
                cluster_id=int(cid),
                label=f"Cluster {cid} (n={len(member_runs)})",
                member_runs=member_runs,
                avg_final_value=float(np.mean(finals)),
                std_final_value=float(np.std(finals)),
                size=len(member_runs),
                distinguishing_params=distinguishing,
            ))

        return clusters, labels

    def _find_critical_timesteps(
        self,
        trajectories: list[np.ndarray],
        labels: np.ndarray,
        column: str,
    ) -> list[CriticalTimestep]:
        """Find timesteps where cluster trajectories diverge most."""
        if len(set(labels)) < 2:
            return []

        max_len = max(len(t) for t in trajectories)
        matrix = np.zeros((len(trajectories), max_len))
        for i, t in enumerate(trajectories):
            matrix[i, :len(t)] = t
            if len(t) < max_len:
                matrix[i, len(t):] = t[-1]

        critical = []
        unique_labels = sorted(set(labels))

        for t in range(max_len):
            cluster_means = {}
            for cid in unique_labels:
                mask = labels == cid
                cluster_means[int(cid)] = float(np.mean(matrix[mask, t]))

            # Divergence = max difference between any two clusters
            values = list(cluster_means.values())
            divergence = max(values) - min(values)

            if divergence > 0.01:  # threshold
                critical.append(CriticalTimestep(
                    timestep=t,
                    column=column,
                    divergence_score=divergence,
                    cluster_means=cluster_means,
                ))

        # Sort by divergence, return top 20
        critical.sort(key=lambda x: x.divergence_score, reverse=True)
        return critical[:20]

    def _compute_correlations(
        self,
        trajectories: list[np.ndarray],
        run_ids: list[int],
        params_by_run: dict[int, dict],
        column: str,
    ) -> list[ParameterCorrelation]:
        """Compute Pearson correlation between each parameter and final metric value."""
        from scipy import stats

        finals = np.array([t[-1] for t in trajectories])

        # Collect all parameter names
        all_params = set()
        for rid in run_ids:
            all_params.update(params_by_run.get(rid, {}).keys())

        correlations = []
        for param in sorted(all_params):
            values = []
            valid_finals = []
            for i, rid in enumerate(run_ids):
                p = params_by_run.get(rid, {})
                if param in p:
                    try:
                        values.append(float(p[param]))
                        valid_finals.append(finals[i])
                    except (ValueError, TypeError):
                        continue

            if len(values) < 3:
                continue

            x = np.array(values)
            y = np.array(valid_finals)

            # Skip if no variance
            if np.std(x) < 1e-10 or np.std(y) < 1e-10:
                continue

            r, p_val = stats.pearsonr(x, y)

            if abs(r) > 0.3:
                direction = "positive" if r > 0 else "negative"
            else:
                direction = "weak"

            correlations.append(ParameterCorrelation(
                parameter=param,
                metric_column=column,
                correlation=float(r),
                p_value=float(p_val),
                direction=direction,
            ))

        correlations.sort(key=lambda x: abs(x.correlation), reverse=True)
        return correlations

    def _save(self, result: TrajectoryAnalysisResult) -> None:
        """Save analysis results to workspace."""
        # Save summary markdown
        summary_path = self.workspace_path / "trajectory_analysis.md"
        summary_path.write_text(result.to_summary(), encoding="utf-8")

        # Save structured JSON
        json_path = self.workspace_path / "trajectory_analysis.json"
        data = {
            "total_runs": result.total_runs,
            "metric_column": result.metric_column,
            "metric_file": result.metric_file,
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "label": c.label,
                    "member_runs": c.member_runs,
                    "avg_final_value": c.avg_final_value,
                    "std_final_value": c.std_final_value,
                    "size": c.size,
                    "distinguishing_params": c.distinguishing_params,
                }
                for c in result.clusters
            ],
            "critical_timesteps": [
                {
                    "timestep": ct.timestep,
                    "column": ct.column,
                    "divergence_score": ct.divergence_score,
                    "cluster_means": ct.cluster_means,
                }
                for ct in result.critical_timesteps
            ],
            "param_correlations": [
                {
                    "parameter": pc.parameter,
                    "metric_column": pc.metric_column,
                    "correlation": pc.correlation,
                    "p_value": pc.p_value,
                    "direction": pc.direction,
                }
                for pc in result.param_correlations
            ],
        }
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
