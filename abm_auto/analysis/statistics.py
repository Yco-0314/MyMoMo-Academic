"""
Statistical analysis module for ABM simulation results.

Provides hypothesis testing, effect sizes, confidence intervals,
and model selection criteria for comparing parameter configurations
across multiple simulation runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from abm_auto.analysis.results_reader import final_metrics


@dataclass
class ComparisonResult:
    """Result of comparing two parameter configurations."""
    metric: str
    group_a_label: str
    group_b_label: str
    mean_a: float
    mean_b: float
    std_a: float
    std_b: float
    n_a: int
    n_b: int
    test_name: str
    statistic: float
    p_value: float
    effect_size: float  # Cohen's d
    effect_label: str   # small/medium/large
    ci_diff_low: float  # 95% CI of difference
    ci_diff_high: float
    significant: bool


@dataclass
class MetricSummary:
    """Summary statistics for a single metric across runs."""
    metric: str
    n: int
    mean: float
    std: float
    median: float
    ci_low: float   # 95% CI via bootstrap
    ci_high: float
    iqr: float


@dataclass
class StatisticalReport:
    """Full statistical analysis report."""
    summaries: list[MetricSummary] = field(default_factory=list)
    comparisons: list[ComparisonResult] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Render as markdown for inclusion in report."""
        lines = ["## Statistical Analysis\n"]

        if self.summaries:
            lines.append("### Metric Summaries\n")
            lines.append("| Metric | N | Mean | Std | Median | 95% CI |")
            lines.append("|--------|---|------|-----|--------|--------|")
            for s in self.summaries:
                lines.append(
                    f"| {s.metric} | {s.n} | {s.mean:.4f} | {s.std:.4f} | "
                    f"{s.median:.4f} | [{s.ci_low:.4f}, {s.ci_high:.4f}] |"
                )
            lines.append("")

        if self.comparisons:
            lines.append("### Parameter Configuration Comparisons\n")
            for c in self.comparisons:
                sig = "**significant**" if c.significant else "not significant"
                lines.append(
                    f"**{c.metric}**: {c.group_a_label} (μ={c.mean_a:.4f}) vs "
                    f"{c.group_b_label} (μ={c.mean_b:.4f})\n"
                    f"- {c.test_name}: stat={c.statistic:.4f}, p={c.p_value:.4f} ({sig})\n"
                    f"- Cohen's d = {c.effect_size:.3f} ({c.effect_label})\n"
                    f"- 95% CI of difference: [{c.ci_diff_low:.4f}, {c.ci_diff_high:.4f}]\n"
                )

        return "\n".join(lines)


def bootstrap_ci(data: np.ndarray, n_bootstrap: int = 1000, alpha: float = 0.05) -> tuple[float, float]:
    """Compute bootstrap confidence interval for the mean."""
    if len(data) < 2:
        return (float(data[0]), float(data[0])) if len(data) == 1 else (0.0, 0.0)

    rng = np.random.default_rng(42)
    boot_means = np.array([
        rng.choice(data, size=len(data), replace=True).mean()
        for _ in range(n_bootstrap)
    ])
    low = float(np.percentile(boot_means, 100 * alpha / 2))
    high = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    return low, high


def cohens_d(a: np.ndarray, b: np.ndarray) -> tuple[float, str]:
    """Compute Cohen's d effect size and label."""
    n_a, n_b = len(a), len(b)
    if n_a < 2 or n_b < 2:
        return 0.0, "insufficient_data"

    pooled_std = np.sqrt(
        ((n_a - 1) * a.std(ddof=1) ** 2 + (n_b - 1) * b.std(ddof=1) ** 2)
        / (n_a + n_b - 2)
    )
    # Treat variance that is negligible relative to the group means as zero. An
    # exact "== 0" check let a tiny-but-nonzero pooled_std (e.g. ~1e-14 of float
    # noise) through, and the division below then blew d up into a spurious "large".
    scale = max(abs(float(a.mean())), abs(float(b.mean())), 1.0)
    if pooled_std < 1e-9 * scale:
        return 0.0, "zero_variance"

    d = abs(float(a.mean() - b.mean())) / pooled_std

    if d < 0.2:
        label = "negligible"
    elif d < 0.5:
        label = "small"
    elif d < 0.8:
        label = "medium"
    else:
        label = "large"

    return float(d), label


def summarize_metric(values: np.ndarray, name: str) -> MetricSummary:
    """Compute summary statistics for a metric."""
    ci_low, ci_high = bootstrap_ci(values)
    q1, q3 = np.percentile(values, [25, 75])
    return MetricSummary(
        metric=name,
        n=len(values),
        mean=float(values.mean()),
        std=float(values.std(ddof=1)) if len(values) > 1 else 0.0,
        median=float(np.median(values)),
        ci_low=ci_low,
        ci_high=ci_high,
        iqr=float(q3 - q1),
    )


def compare_groups(
    a: np.ndarray,
    b: np.ndarray,
    metric: str,
    label_a: str = "Config A",
    label_b: str = "Config B",
    alpha: float = 0.05,
) -> ComparisonResult:
    """Compare two groups using appropriate test (t-test or Mann-Whitney)."""
    # Choose test: if both groups have n >= 20 and approximately normal, use t-test
    # Otherwise use Mann-Whitney U (non-parametric)
    use_parametric = len(a) >= 8 and len(b) >= 8

    if use_parametric:
        # Check normality (Shapiro-Wilk, if n <= 50)
        if len(a) <= 50 and len(b) <= 50:
            _, p_norm_a = stats.shapiro(a)
            _, p_norm_b = stats.shapiro(b)
            use_parametric = p_norm_a > 0.05 and p_norm_b > 0.05

    if use_parametric:
        stat, p = stats.ttest_ind(a, b, equal_var=False)  # Welch's t-test
        test_name = "Welch's t-test"
    else:
        stat, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        test_name = "Mann-Whitney U"

    d, d_label = cohens_d(a, b)

    # CI of difference (bootstrap)
    diff = a.mean() - b.mean()
    rng = np.random.default_rng(42)
    boot_diffs = np.array([
        rng.choice(a, size=len(a), replace=True).mean()
        - rng.choice(b, size=len(b), replace=True).mean()
        for _ in range(1000)
    ])
    ci_low = float(np.percentile(boot_diffs, 2.5))
    ci_high = float(np.percentile(boot_diffs, 97.5))

    return ComparisonResult(
        metric=metric,
        group_a_label=label_a,
        group_b_label=label_b,
        mean_a=float(a.mean()),
        mean_b=float(b.mean()),
        std_a=float(a.std(ddof=1)) if len(a) > 1 else 0.0,
        std_b=float(b.std(ddof=1)) if len(b) > 1 else 0.0,
        n_a=len(a),
        n_b=len(b),
        test_name=test_name,
        statistic=float(stat),
        p_value=float(p),
        effect_size=d,
        effect_label=d_label,
        ci_diff_low=ci_low,
        ci_diff_high=ci_high,
        significant=p < alpha,
    )


def analyze_runs(workspace_path, metric_columns: list[str] | None = None) -> StatisticalReport:
    """
    Analyze all completed runs in a workspace.

    Computes per-metric summaries and, if parameter changes detected
    between runs, compares early vs late configurations.
    """
    from pathlib import Path
    import json

    workspace = Path(workspace_path)
    results_dir = workspace / "results"
    report = StatisticalReport()

    if not results_dir.exists():
        return report

    # Collect final-step metrics from each run
    run_metrics: list[dict[str, float]] = []
    run_dirs = sorted(results_dir.glob("run_*"))

    for rd in run_dirs:
        row = final_metrics(list(rd.glob("*.csv")))
        if row:
            run_metrics.append(row)

    if not run_metrics:
        return report

    # Determine metric columns
    all_cols = set()
    for rm in run_metrics:
        all_cols.update(rm.keys())

    if metric_columns:
        cols = [c for c in metric_columns if c in all_cols]
    else:
        cols = sorted(all_cols)

    # Summaries
    for col in cols:
        values = np.array([rm[col] for rm in run_metrics if col in rm])
        if len(values) >= 2:
            report.summaries.append(summarize_metric(values, col))

    # Comparisons: if we have ≥ 4 runs, compare first half vs second half
    # (representing initial vs optimized parameter configurations)
    n = len(run_metrics)
    if n >= 4:
        mid = n // 2
        for col in cols:
            early = np.array([rm[col] for rm in run_metrics[:mid] if col in rm])
            late = np.array([rm[col] for rm in run_metrics[mid:] if col in rm])
            if len(early) >= 2 and len(late) >= 2:
                report.comparisons.append(
                    compare_groups(
                        early, late, col,
                        label_a=f"Runs 1-{mid}",
                        label_b=f"Runs {mid + 1}-{n}",
                    )
                )

    return report
