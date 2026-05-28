"""Phase 6b-6d: Optional post-iteration analyses.

  SensitivityPhase  — Phase 6b SALib (Morris/Sobol). Activated by sensitivity_method flag.
  TrajectoryPhase   — Phase 6c trajectory clustering. ≥3 runs required.
  StatisticalPhase  — Phase 6d summary stats. ≥2 runs required.
"""
from __future__ import annotations

from rich.console import Console

from abm_auto import config
from abm_auto.agents.base import SECTION_LABELS
from abm_auto.pipeline.phase import PipelineContext

console = Console()


class SensitivityPhase:
    """Phase 6b: SALib sensitivity analysis (Morris / Sobol / FAST)."""

    name = "Phase 6b (Sensitivity)"

    def __init__(self, sensitivity_analyzer):
        self.sa = sensitivity_analyzer

    def should_run(self, ctx: PipelineContext) -> bool:
        return bool(ctx.sensitivity_method and ctx.all_insights)

    def run(self, ctx: PipelineContext) -> None:
        sa_result = self.sa.run(
            ctx.executor,
            method=ctx.sensitivity_method,
            n_trajectories=ctx.sensitivity_samples,
        )
        if sa_result and sa_result.get("interpretation"):
            section_hdr = SECTION_LABELS.get(ctx.lang, SECTION_LABELS["zh"])[
                "sensitivity"
            ].format(method=ctx.sensitivity_method.upper())
            ctx.all_insights.append(f"{section_hdr}\n\n" + sa_result["interpretation"])


class TrajectoryPhase:
    """Phase 6c: Trajectory analysis (clustering + critical timesteps + correlations)."""

    name = "Phase 6c (Trajectory)"

    def __init__(self, analyzer):
        self.analyzer = analyzer

    def should_run(self, ctx: PipelineContext) -> bool:
        return len(ctx.all_insights) >= 3

    def run(self, ctx: PipelineContext) -> None:
        from abm_auto.analysis.trajectory_analyzer import TrajectoryAnalyzer

        ta = TrajectoryAnalyzer(ctx.workspace.path)
        ta_result = ta.analyze()
        if not ta_result:
            return
        console.print("[bold cyan]Trajectory analysis complete[/bold cyan]")
        ta_interp = _interpret_trajectories(ctx, ta_result, self.analyzer)
        if ta_interp:
            traj_hdr = SECTION_LABELS.get(ctx.lang, SECTION_LABELS["zh"])["trajectory"]
            ctx.all_insights.append(f"{traj_hdr}\n\n{ta_interp}")


class StatisticalPhase:
    """Phase 6d: Statistical summary across runs."""

    name = "Phase 6d (Statistical)"

    def should_run(self, ctx: PipelineContext) -> bool:
        return len(ctx.all_insights) >= 2

    def run(self, ctx: PipelineContext) -> None:
        from abm_auto.analysis.statistics import analyze_runs
        try:
            stat_report = analyze_runs(ctx.workspace.path)
            if stat_report.summaries:
                console.print("[bold cyan]Statistical analysis complete[/bold cyan]")
                ctx.all_insights.append(stat_report.to_markdown())
                stat_path = ctx.workspace.path / "statistical_analysis.md"
                stat_path.write_text(stat_report.to_markdown(), encoding="utf-8")
        except Exception as e:
            console.print(f"  [yellow]⚠ Statistical analysis failed: {e}[/yellow]")


def _interpret_trajectories(ctx: PipelineContext, ta_result, analyzer) -> str:
    """LLM interpretation of trajectory-analysis result."""
    story = ctx.workspace.read_story()
    design = ctx.workspace.read_design()
    prompt_path = config.PROMPTS_DIR / "trajectory.md"
    if not prompt_path.exists():
        return ""
    template = prompt_path.read_text(encoding="utf-8")

    clusters_lines = []
    for c in ta_result.clusters:
        params_str = ", ".join(
            f"{k}={v:.3f}" for k, v in c.distinguishing_params.items()
        )
        clusters_lines.append(
            f"- Cluster {c.cluster_id}: {c.size} runs, "
            f"final={c.avg_final_value:.4f}±{c.std_final_value:.4f}, params: {params_str}"
        )
    ct_lines = []
    for ct in ta_result.critical_timesteps[:10]:
        means_str = ", ".join(f"C{k}={v:.4f}" for k, v in ct.cluster_means.items())
        ct_lines.append(
            f"- t={ct.timestep}: divergence={ct.divergence_score:.4f} ({means_str})"
        )
    corr_lines = []
    for pc in ta_result.param_correlations:
        corr_lines.append(
            f"- {pc.parameter}: r={pc.correlation:.3f}, p={pc.p_value:.4f}, {pc.direction}"
        )

    prompt = analyzer.render_prompt(
        template,
        total_runs=str(ta_result.total_runs),
        metric_column=ta_result.metric_column,
        story_summary=story[:800],
        design_summary=design[:800],
        clusters_summary="\n".join(clusters_lines) or "无聚类结果",
        critical_timesteps="\n".join(ct_lines) or "无显著分叉点",
        param_correlations="\n".join(corr_lines) or "无显著相关性",
    )
    system = SECTION_LABELS.get(ctx.lang, SECTION_LABELS["zh"])["trajectory_system"]
    interpretation = analyzer.call_llm(system, prompt, max_tokens=2048)
    interp_path = ctx.workspace.path / "trajectory_interpretation.md"
    interp_path.write_text(interpretation, encoding="utf-8")
    return interpretation
