"""Phase 4-6 inner-loop phases — wrapped by LoopedPhase in the orchestrator.

Three phases run per outer iteration:
  SimulatePhase           — Phase 4: run sim, GVR-fix on failure, sanity-check on iter 1
  AnalyzePhase            — Phase 5: insights + memory ingestion + convergence check
  OptimizeOrCalibratePhase — Phase 6: BayesianCalibrator (once) OR OptimizerAgent (every iter)
"""
from __future__ import annotations

from rich.console import Console

from abm_auto.agents.sanity_checker import SanityChecker
from abm_auto.analysis.results_reader import convergence_cv
from abm_auto.pipeline.phase import PipelineContext
from abm_auto.refinement import ValidationOutcome, refine

console = Console()


class SimulatePhase:
    """Phase 4: Execute model.run() with GVR-driven fix loop on failure.

    On iter==1, additionally run SanityChecker over the result CSV and
    GVR-fix if degenerate output detected (e.g., zero infections).
    """

    name = "Phase 4 (Simulate)"

    def __init__(self, executor, verifier, max_retries: int):
        self.executor = executor
        self.verifier = verifier
        self.max_retries = max_retries

    def should_run(self, ctx: PipelineContext) -> bool:
        return True   # always within the loop

    def run(self, ctx: PipelineContext) -> None:
        i = ctx.iteration
        console.print(f"\n[bold]--- Iteration {i}/{ctx.iterations} ---[/bold]")

        success, output = self.executor.run(i)
        if not success:
            success, output = self._fix_and_rerun(ctx, output, i, "Simulation fix")
        if not success:
            console.print("  [red]Skipping this iteration.[/red]")
            ctx.iteration_failed = True   # ad-hoc flag; AnalyzePhase reads it
            return
        ctx.iteration_failed = False

        # Iter-1 only: deeper sanity check on output structure
        if i == 1:
            csvs = ctx.workspace.list_result_csvs(i)
            design = ctx.workspace.read_design()
            sanity_warnings = SanityChecker.check_run(csvs, design)
            if sanity_warnings:
                sanity_issue_ids = []
                for w in sanity_warnings:
                    console.print(f"  [bold red]{w}[/bold red]")
                    iid = ctx.workspace.audit.raise_issue(
                        phase="Phase 4 post-run",
                        severity="HIGH",
                        text=w,
                        actor="SanityChecker",
                    )
                    sanity_issue_ids.append(iid)
                error_msg = SanityChecker.format_warnings(sanity_warnings)
                fix_success, _ = self._fix_and_rerun(ctx, error_msg, i, "Sanity fix")
                if fix_success:
                    new_warnings = SanityChecker.check_run(
                        ctx.workspace.list_result_csvs(i), design
                    )
                    if not new_warnings:
                        console.print("  [green]✓ Sanity check passed after fix[/green]")
                        for iid in sanity_issue_ids:
                            ctx.workspace.audit.resolve(
                                iid, note="Fixed by Verifier", actor="VerifierAgent",
                            )
                    else:
                        console.print("  [red]⚠ Sanity issues persist — continuing anyway[/red]")
                        ctx.workspace.audit.raise_issue(
                            phase="Phase 4 post-fix",
                            severity="HIGH",
                            text="Sanity issues persist after Verifier fix attempt",
                            actor="Pipeline",
                        )
                else:
                    console.print("  [red]⚠ Sanity fix failed — continuing anyway[/red]")
                    ctx.workspace.audit.raise_issue(
                        phase="Phase 4 post-fix",
                        severity="HIGH",
                        text="Verifier could not fix sanity issues",
                        actor="Pipeline",
                    )

    def _fix_and_rerun(self, ctx, initial_error: str, run_number: int, label: str):
        """GVR-driven version of VerifierAgent.fix_and_rerun. Returns (success, output)."""
        last_output_capture = {"value": ""}

        def _gen(feedback):
            err_to_fix = feedback if feedback is not None else initial_error
            self.verifier.fix(err_to_fix)
            return None

        def _val(_ignored) -> ValidationOutcome:
            success, output = self.executor.run(run_number)
            last_output_capture["value"] = output
            if success:
                return ValidationOutcome(ok=True, structured={"output_preview": output[:300]})
            return ValidationOutcome(
                ok=False, reasons=[output[:1000]], severity="soft",
                structured={"error_preview": output[:500]},
            )

        gvr = refine(
            generator=_gen,
            validator=_val,
            max_iters=self.max_retries,
            on_exhaust="halt",
            audit=ctx.workspace.audit,
            actor=f"CoderVerifier-{label.replace(' ', '_')}",
            phase=f"Phase 4-6 ({label})",
        )
        if gvr.accepted:
            return True, last_output_capture["value"]
        last_reason = (
            gvr.attempts[-1].outcome.reasons[0]
            if gvr.attempts[-1].outcome.reasons else "exhausted"
        )
        return False, last_reason


class AnalyzePhase:
    """Phase 5: Analyzer + memory ingestion + early-stop convergence check.

    On convergence detection (CV across runs < threshold), sets
    ctx.converged_at so LoopedPhase short-circuits the remaining iterations.
    """

    name = "Phase 5 (Analyze)"

    def __init__(self, analyzer, cv_threshold: float = 0.05):
        self.analyzer = analyzer
        self.cv_threshold = cv_threshold

    def should_run(self, ctx: PipelineContext) -> bool:
        return not getattr(ctx, "iteration_failed", False)

    def run(self, ctx: PipelineContext) -> None:
        i = ctx.iteration
        insights = self.analyzer.run(ctx.executor, i)
        ctx.all_insights.append(insights)

        _ingest_to_memory(ctx, i, insights, self.analyzer)

        # Adaptive early-stop after ≥2 successful iterations
        if 2 <= i < ctx.iterations:
            run_ids = list(range(1, i + 1))
            converged, cv_by_metric = convergence_cv(
                ctx.workspace, run_ids, cv_threshold=self.cv_threshold
            )
            if cv_by_metric:
                console.print(
                    "  [dim]Convergence CV: "
                    + ", ".join(f"{k}={v:.3f}" for k, v in cv_by_metric.items())
                    + "[/dim]"
                )
            if converged:
                console.print(
                    f"  [bold green]✓ Converged after {i} iterations — stopping early.[/bold green]"
                )
                ctx.converged_at = i


class OptimizeOrCalibratePhase:
    """Phase 6: Bayesian calibration (once) OR heuristic optimizer (every iter).

    Calibrator runs on the FIRST opportunity (and only once, because it fits
    posterior in a single batch). Optimizer runs every iteration (except the
    last and after convergence) when calibration isn't applicable.
    """

    name = "Phase 6 (Optimize or Calibrate)"

    def __init__(self, calibrator, optimizer, coder):
        self.calibrator = calibrator
        self.optimizer = optimizer
        self.coder = coder

    def should_run(self, ctx: PipelineContext) -> bool:
        if getattr(ctx, "iteration_failed", False):
            return False
        # Skip Phase 6 on last iter and after convergence
        if ctx.iteration >= ctx.iterations:
            return False
        if ctx.converged_at is not None:
            return False
        return True

    def run(self, ctx: PipelineContext) -> None:
        i = ctx.iteration
        insights = ctx.all_insights[-1] if ctx.all_insights else ""

        if _should_calibrate(ctx) and not ctx.used_bayesian_calibration:
            cal_result = self.calibrator.run(ctx.executor, spec=ctx.spec)
            ctx.used_bayesian_calibration = True
            if cal_result.ok:
                console.print(
                    f"  [green]✓ Calibrated {len(cal_result.best_params)} params "
                    f"via {cal_result.backend}[/green]"
                )
            else:
                console.print(
                    f"  [yellow]Calibration skipped ({cal_result.reason}) — "
                    f"falling back to heuristic optimizer[/yellow]"
                )
                self.optimizer.run(
                    i, insights, self.coder,
                    memory_context=ctx.memory.retrieve_context(),
                )
        else:
            self.optimizer.run(
                i, insights, self.coder,
                memory_context=ctx.memory.retrieve_context(),
            )
        _print_memory_summary(ctx, i)


# ── Module-local helpers (lifted from the legacy god method) ──────────────


def _should_calibrate(ctx: PipelineContext) -> bool:
    """True iff BayesianCalibrator should replace OptimizerAgent for ctx.spec."""
    if ctx.spec is None or not ctx.spec.has_calibration_data:
        return False
    if ctx.spec.calibration_data_path:
        from pathlib import Path
        p = ctx.workspace.path / ctx.spec.calibration_data_path
        if p.exists():
            return True
        p_abs = Path(ctx.spec.calibration_data_path)
        if p_abs.exists():
            return True
    return (ctx.workspace.path / "data" / "observed.csv").exists()


def _ingest_to_memory(ctx: PipelineContext, run_id: int, insights: str, analyzer) -> None:
    """Episodic record + (≥2 runs) semantic knowledge extraction via LLM."""
    import json
    import pandas as pd

    from abm_auto import config

    params_history = ctx.workspace.read_params_history()
    current_params = next(
        (h["params"] for h in params_history if h["run"] == run_id), {}
    )
    hypothesis = next(
        (h.get("hypothesis", "") for h in params_history if h["run"] == run_id), ""
    )

    # Extract metrics from CSV
    metrics: dict = {}
    csvs = ctx.workspace.list_result_csvs(run_id)
    if csvs:
        try:
            df = pd.read_csv(csvs[0])
            skip = {"id", "step", "period", "run_num", "scenario_id", "agent_id"}
            for col in df.columns:
                if col.lower() not in skip and pd.api.types.is_numeric_dtype(df[col]):
                    metrics[col] = float(df[col].iloc[-1])
        except Exception:
            pass

    ctx.memory.ingest_run(
        run_id=run_id,
        params=current_params,
        metrics=metrics,
        hypothesis=hypothesis,
        insights=insights[:500],
        outcome="success",
        importance=0.7,
    )

    # Semantic knowledge extraction kicks in after 2+ runs
    if run_id >= 2:
        prompt_path = config.PROMPTS_DIR / "extract_knowledge.md"
        if not prompt_path.exists():
            return
        template = prompt_path.read_text(encoding="utf-8")
        existing = ctx.memory.semantic.to_context(max_tokens=800)
        prompt = analyzer.render_prompt(
            template,
            run_id=str(run_id),
            hypothesis=hypothesis or "无",
            params=json.dumps(current_params, ensure_ascii=False),
            metrics=json.dumps(metrics, ensure_ascii=False),
            insights=insights[:1000],
            existing_knowledge=existing or "（空）",
        )
        system = "You are an ABM research assistant. Output ONLY a JSON array. No other text."
        try:
            raw = analyzer.call_llm(system, prompt, max_tokens=512).strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
            entries = json.loads(raw)
            for e in entries[:5]:
                ctx.memory.add_knowledge(
                    key=e["key"],
                    knowledge=e["knowledge"],
                    confidence=e.get("confidence", 0.5),
                    source_runs=[run_id],
                    category=e.get("category", "pattern"),
                )
                console.print(f"  [dim]📝 Knowledge: {e['key']}[/dim]")
        except (json.JSONDecodeError, KeyError, TypeError):
            pass


def _print_memory_summary(ctx: PipelineContext, after_iteration: int) -> None:
    episodic_entries = ctx.memory.episodic.all()
    semantic_entries = getattr(ctx.memory.semantic, "_entries", {})
    n_episodic = len(episodic_entries)
    n_semantic = len(semantic_entries)
    parts = [f"[dim]Memory after iter {after_iteration}: {n_episodic} run(s) recorded"]
    if n_semantic:
        keys = list(semantic_entries.keys())[:3]
        keys_str = ", ".join(f'"{k}"' for k in keys)
        suffix = f" +{n_semantic - 3} more" if n_semantic > 3 else ""
        parts.append(f", {n_semantic} semantic insight(s): {keys_str}{suffix}")
    parts.append("[/dim]")
    console.print("  " + "".join(parts))
