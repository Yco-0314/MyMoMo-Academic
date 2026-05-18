from __future__ import annotations
from pathlib import Path

import anthropic
from rich.console import Console
from rich.panel import Panel

from abm_auto import config
from abm_auto.agents.base import SECTION_LABELS
from abm_auto.runner.workspace import Workspace
from abm_auto.runner.executor import Executor
from abm_auto.agents.designer import DesignAgent
from abm_auto.agents.coder import CoderAgent
from abm_auto.agents.verifier import VerifierAgent
from abm_auto.agents.analyzer import AnalyzerAgent
from abm_auto.agents.optimizer import OptimizerAgent
from abm_auto.agents.reporter import ReporterAgent
from abm_auto.agents.odd_writer import OddWriter
from abm_auto.agents.salib_optimizer import SensitivityAnalyzer
from abm_auto.agents.reviewer import ReviewerAgent
from abm_auto.agents.sanity_checker import SanityChecker
from abm_auto.agents.viability_checker import ViabilityChecker
from abm_auto.agents.lit_reviewer import LitReviewAgent
from abm_auto.agents.visualizer import VisualizerAgent
from abm_auto.analysis.trajectory_analyzer import TrajectoryAnalyzer
from abm_auto.analysis.results_reader import convergence_cv
from abm_auto.memory.store import ExperimentMemory

console = Console()


class Pipeline:
    """
    Orchestrates the full autonomous ABM research pipeline:
    STORY.md → Design → Code → Verify → [Run → Analyze → Optimize] × N → Report
    """

    def __init__(
        self,
        story_path: Path,
        iterations: int = config.DEFAULT_ITERATIONS,
        model: str = config.DEFAULT_MODEL,
        strong_model: str = config.STRONG_MODEL,
        max_retries: int = config.DEFAULT_MAX_RETRIES,
        timeout: int | None = None,
        phase_timeouts: dict[str, int] | None = None,
        workspace_name: str | None = None,
        lit_notes_path: Path | None = None,
        sensitivity_method: str | None = None,
        sensitivity_samples: int = 10,
        peer_review: bool = False,
        lang: str = "zh",
        seed: int | None = None,
        fetch_citations: bool = False,
        baseline_path: Path | None = None,
        auto_lit_review: bool = True,
    ):
        self.story_path = Path(story_path)
        self.iterations = iterations
        self.max_retries = max_retries

        # Phase-specific timeouts (fallback to global timeout or defaults)
        self.phase_timeouts = phase_timeouts or {}
        global_timeout = timeout or config.DEFAULT_TIMEOUT
        self.timeout_simulation = self.phase_timeouts.get("simulation",
            config.PHASE_TIMEOUTS.get("simulation", global_timeout))
        self.timeout_llm = self.phase_timeouts.get("llm",
            config.PHASE_TIMEOUTS.get("llm", 300))
        self.timeout_sa = self.phase_timeouts.get("sensitivity_analysis",
            config.PHASE_TIMEOUTS.get("sensitivity_analysis", 1800))
        self.sensitivity_method = sensitivity_method
        self.sensitivity_samples = sensitivity_samples
        self.peer_review = peer_review
        self.lang = lang
        self.seed = seed
        self.fetch_citations = fetch_citations
        self.baseline_path = Path(baseline_path) if baseline_path else None
        self.auto_lit_review = auto_lit_review

        if not config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set. Add it to .env or environment.")

        self.client = anthropic.Anthropic(
            api_key=config.ANTHROPIC_API_KEY,
            base_url=config.ANTHROPIC_BASE_URL,
            timeout=self.timeout_llm
        )

        # Workspace
        self.workspace = Workspace.create(workspace_name)
        console.print(f"[dim]Workspace: {self.workspace.path}[/dim]")

        # Copy story
        self.workspace.write_story(self.story_path.read_text(encoding="utf-8"))

        # Copy lit_notes if provided
        if lit_notes_path and Path(lit_notes_path).exists():
            self.workspace.write_lit_notes(Path(lit_notes_path).read_text(encoding="utf-8"))

        # Agents (all receive lang parameter)
        agent_kw = {"lang": lang}
        self.designer = DesignAgent(self.client, self.workspace, model=strong_model, **agent_kw)
        self.coder = CoderAgent(self.client, self.workspace, model=strong_model, **agent_kw)
        self.verifier = VerifierAgent(self.client, self.workspace, model=model, **agent_kw)
        self.analyzer = AnalyzerAgent(self.client, self.workspace, model=model, **agent_kw)
        self.optimizer = OptimizerAgent(self.client, self.workspace, model=model, **agent_kw)
        self.reporter = ReporterAgent(self.client, self.workspace, model=strong_model, **agent_kw)
        self.odd_writer = OddWriter(self.client, self.workspace, model=model, **agent_kw)
        self.sensitivity_analyzer = SensitivityAnalyzer(self.client, self.workspace, model=model, **agent_kw)
        self.reviewer = ReviewerAgent(self.client, self.workspace, model=strong_model, **agent_kw)
        self.viability_checker = ViabilityChecker(self.client, self.workspace, model=model, **agent_kw)
        self.lit_reviewer = LitReviewAgent(self.client, self.workspace, model=model, **agent_kw)

        self.executor = Executor(self.workspace, timeout=self.timeout_simulation)

        # Experiment memory (3-tier)
        self.memory = ExperimentMemory(self.workspace.path / "memory")

    def run(self) -> Path:
        """Execute the full pipeline. Returns path to the final report."""
        console.print(Panel.fit(
            f"[bold]ABM Auto Pipeline[/bold]\n"
            f"Story: {self.story_path.name}\n"
            f"Iterations: {self.iterations}",
            border_style="blue",
        ))

        # Phase 0: Automatic literature review (before design)
        if self.auto_lit_review:
            self.lit_reviewer.run()

        # Phase 1: Design
        self.designer.run()

        # Phase 1c: Viability Gate — stop early if design is too weak
        viability = self.viability_checker.check(
            self.workspace.design_path,
            self.story_path,
        )
        if not viability.ok:
            console.print(Panel.fit(
                "[bold red]Pipeline halted: Viability Gate failed.[/bold red]\n"
                f"See: {self.workspace.path / 'kill_memo.md'}",
                border_style="red",
            ))
            return self.workspace.path

        # Phase 1b: ODD Protocol
        self.odd_writer.run()

        # Phase 2: Code generation
        self.coder.run()

        # Phase 3: Verify & fix
        ok = self.verifier.run(self.executor, max_retries=self.max_retries)
        if not ok:
            console.print("[red]Pipeline halted: could not produce working code.[/red]")
            return self.workspace.path

        # Inject random seed if specified
        if self.seed is not None:
            self._inject_seed(self.seed)

        # Pre-run sanity check (agent_num, CSV paths, grid consistency)
        pre_warnings = SanityChecker.check_pre_run(
            self.workspace.model_dir,
            self.workspace.read_design(),
        )
        for w in pre_warnings:
            console.print(f"  [bold yellow]{w}[/bold yellow]")

        # Record initial params
        self._record_initial_params()

        # Phases 4-6: Run → Analyze → Optimize loop
        all_insights: list[str] = []
        # converged_at tracks which iteration early-stop was triggered (None = ran all)
        converged_at: int | None = None
        for i in range(1, self.iterations + 1):
            console.print(f"\n[bold]--- Iteration {i}/{self.iterations} ---[/bold]")

            # Phase 4+5: Run simulation + analyze (with fix-retry loop)
            success, output = self.executor.run(i)
            if not success:
                success, output = self.verifier.fix_and_rerun(
                    self.executor, output, i,
                    max_retries=self.max_retries,
                    label="Simulation fix",
                )
            if not success:
                console.print("  [red]Skipping this iteration.[/red]")
                continue

            # Sanity check: detect degenerate output (e.g., zero infections)
            if i == 1:
                csvs = self.workspace.list_result_csvs(i)
                design = self.workspace.read_design()
                sanity_warnings = SanityChecker.check_run(csvs, design)
                if sanity_warnings:
                    for w in sanity_warnings:
                        console.print(f"  [bold red]{w}[/bold red]")
                    error_msg = SanityChecker.format_warnings(sanity_warnings)
                    success, output = self.verifier.fix_and_rerun(
                        self.executor, error_msg, i,
                        max_retries=self.max_retries,
                        label="Sanity fix",
                    )
                    if success:
                        new_warnings = SanityChecker.check_run(
                            self.workspace.list_result_csvs(i), design
                        )
                        if not new_warnings:
                            console.print("  [green]✓ Sanity check passed after fix[/green]")
                        else:
                            console.print("  [red]⚠ Sanity issues persist — continuing anyway[/red]")
                    else:
                        console.print("  [red]⚠ Sanity fix failed — continuing anyway[/red]")

            insights = self.analyzer.run(self.executor, i)
            all_insights.append(insights)

            # Ingest into experiment memory
            self._ingest_to_memory(i, insights)

            # Adaptive early-stop: check convergence after ≥2 successful iterations
            if i >= 2 and i < self.iterations:
                if self._has_converged(completed_runs=i):
                    console.print(
                        f"  [bold green]✓ Converged after {i} iterations — stopping early.[/bold green]"
                    )
                    converged_at = i
                    break

            # Phase 6: Optimize (not after last iteration, not after convergence)
            if i < self.iterations and converged_at is None:
                self.optimizer.run(i, insights, self.coder, memory_context=self.memory.retrieve_context())
                self._print_memory_summary(i)

        # Phase 6b: Sensitivity analysis (optional)
        if self.sensitivity_method and all_insights:
            sa_result = self.sensitivity_analyzer.run(
                self.executor,
                method=self.sensitivity_method,
                n_trajectories=self.sensitivity_samples,
            )
            if sa_result and sa_result.get("interpretation"):
                section_hdr = SECTION_LABELS.get(self.lang, SECTION_LABELS["zh"])[
                    "sensitivity"
                ].format(method=self.sensitivity_method.upper())
                all_insights.append(f"{section_hdr}\n\n" + sa_result["interpretation"])

        # Phase 6c: Trajectory analysis (when ≥3 runs available)
        if len(all_insights) >= 3:
            ta = TrajectoryAnalyzer(self.workspace.path)
            ta_result = ta.analyze()
            if ta_result:
                console.print("[bold cyan]Trajectory analysis complete[/bold cyan]")
                # LLM interpretation
                ta_interp = self._interpret_trajectories(ta_result)
                if ta_interp:
                    traj_hdr = SECTION_LABELS.get(self.lang, SECTION_LABELS["zh"])["trajectory"]
                    all_insights.append(f"{traj_hdr}\n\n{ta_interp}")

        # Phase 6d: Statistical analysis (when ≥2 runs)
        if len(all_insights) >= 2:
            from abm_auto.analysis.statistics import analyze_runs
            try:
                stat_report = analyze_runs(self.workspace.path)
                if stat_report.summaries:
                    console.print("[bold cyan]Statistical analysis complete[/bold cyan]")
                    all_insights.append(stat_report.to_markdown())
                    # Save standalone
                    stat_path = self.workspace.path / "statistical_analysis.md"
                    stat_path.write_text(stat_report.to_markdown(), encoding="utf-8")
            except Exception as e:
                console.print(f"  [yellow]⚠ Statistical analysis failed: {e}[/yellow]")

        # Phase 6e: Citation fetching (optional)
        citations_text = None
        if self.fetch_citations:
            console.print("[bold cyan]Phase 6e: Fetching citations...[/bold cyan]")
            from abm_auto.agents.citation_fetcher import CitationFetcher
            from abm_auto.agents.formatting_utils import format_citations_for_report
            try:
                fetcher = CitationFetcher(self.workspace.path)
                story_text = self.workspace.read_story()
                citations = fetcher.fetch_citations(story_text)
                if citations:
                    citations_text = format_citations_for_report(citations)
                    console.print(f"  [green]✓ Fetched {len(citations.get('references', []))} citations[/green]")
            except Exception as e:
                console.print(f"  [yellow]⚠ Citation fetching failed: {e}[/yellow]")

        # Phase 6f: Baseline comparison (optional)
        comparison_text = None
        if self.baseline_path and self.baseline_path.exists():
            console.print("[bold cyan]Phase 6f: Comparing with baseline...[/bold cyan]")
            from abm_auto.agents.benchmark_comparator import BenchmarkComparator
            from abm_auto.agents.formatting_utils import format_baseline_comparison_for_report
            try:
                comparator = BenchmarkComparator(self.workspace.path)
                comparison = comparator.compare(self.baseline_path)
                if comparison:
                    comparison_text = format_baseline_comparison_for_report(comparison)
                    console.print(f"  [green]✓ Baseline comparison complete[/green]")
            except Exception as e:
                console.print(f"  [yellow]⚠ Baseline comparison failed: {e}[/yellow]")

        # Phase 7: Final report
        if all_insights:
            self.reporter.run(all_insights, citations=citations_text, baseline_comparison=comparison_text)
        else:
            console.print("[yellow]No successful runs — skipping report.[/yellow]")

        # Phase 7b: Visualization
        console.print("[bold cyan]Phase 7b: Generating figures...[/bold cyan]")
        viz = VisualizerAgent(self.workspace.path, lang=self.lang)
        figures = viz.run()
        if figures:
            # Append figure references to report
            report_path = self.workspace.report_path
            if report_path.exists():
                fig_section = "\n\n## Figures\n\n"
                for fig in figures:
                    fig_section += f"![{fig.stem}](figures/{fig.name})\n\n"
                report_path.write_text(
                    report_path.read_text(encoding="utf-8") + fig_section,
                    encoding="utf-8",
                )

        # Phase 8: Peer review (optional)
        if self.peer_review:
            self.reviewer.run()
            self._process_resolution_ledger()

        # Package outputs for ARS academic-paper integration
        ars_out = self.workspace.package_for_ars()
        console.print(f"  [dim]ARS package: {ars_out.relative_to(self.workspace.path.parent)}[/dim]")

        console.print(Panel.fit(
            f"[bold green]Pipeline complete![/bold green]\n"
            f"Results: {self.workspace.path}\n"
            f"ARS input: {ars_out}",
            border_style="green",
        ))
        return self.workspace.path

    def _interpret_trajectories(self, ta_result) -> str:
        """Use LLM to interpret trajectory analysis results."""
        from abm_auto.analysis.trajectory_analyzer import TrajectoryAnalysisResult

        story = self.workspace.read_story()
        design = self.workspace.read_design()

        prompt_path = config.PROMPTS_DIR / "trajectory.md"
        if not prompt_path.exists():
            return ""
        template = prompt_path.read_text(encoding="utf-8")

        # Build cluster summary
        clusters_lines = []
        for c in ta_result.clusters:
            params_str = ", ".join(f"{k}={v:.3f}" for k, v in c.distinguishing_params.items())
            clusters_lines.append(
                f"- Cluster {c.cluster_id}: {c.size} runs, "
                f"final={c.avg_final_value:.4f}±{c.std_final_value:.4f}, params: {params_str}"
            )

        # Build critical timesteps summary
        ct_lines = []
        for ct in ta_result.critical_timesteps[:10]:
            means_str = ", ".join(f"C{k}={v:.4f}" for k, v in ct.cluster_means.items())
            ct_lines.append(f"- t={ct.timestep}: divergence={ct.divergence_score:.4f} ({means_str})")

        # Build correlation summary
        corr_lines = []
        for pc in ta_result.param_correlations:
            corr_lines.append(f"- {pc.parameter}: r={pc.correlation:.3f}, p={pc.p_value:.4f}, {pc.direction}")

        prompt = self.analyzer.render_prompt(
            template,
            total_runs=str(ta_result.total_runs),
            metric_column=ta_result.metric_column,
            story_summary=story[:800],
            design_summary=design[:800],
            clusters_summary="\n".join(clusters_lines) or "无聚类结果",
            critical_timesteps="\n".join(ct_lines) or "无显著分叉点",
            param_correlations="\n".join(corr_lines) or "无显著相关性",
        )

        system = SECTION_LABELS.get(self.lang, SECTION_LABELS["zh"])["trajectory_system"]
        interpretation = self.analyzer.call_llm(system, prompt, max_tokens=2048)

        interp_path = self.workspace.path / "trajectory_interpretation.md"
        interp_path.write_text(interpretation, encoding="utf-8")
        return interpretation

    def _ingest_to_memory(self, run_id: int, insights: str) -> None:
        """Ingest run results into experiment memory + extract semantic knowledge."""
        import json

        params_history = self.workspace.read_params_history()
        current_params = next(
            (h["params"] for h in params_history if h["run"] == run_id), {}
        )
        hypothesis = next(
            (h.get("hypothesis", "") for h in params_history if h["run"] == run_id), ""
        )

        # Extract metrics from CSV
        metrics = {}
        csvs = self.workspace.list_result_csvs(run_id)
        if csvs:
            try:
                import pandas as pd
                df = pd.read_csv(csvs[0])
                skip = {"id", "step", "period", "run_num", "scenario_id", "agent_id"}
                for col in df.columns:
                    if col.lower() not in skip and pd.api.types.is_numeric_dtype(df[col]):
                        metrics[col] = float(df[col].iloc[-1])
            except Exception:
                pass

        # Episodic: record this run
        self.memory.ingest_run(
            run_id=run_id,
            params=current_params,
            metrics=metrics,
            hypothesis=hypothesis,
            insights=insights[:500],
            outcome="success",
            importance=0.7,
        )

        # Semantic: LLM-based knowledge extraction (after ≥2 runs)
        if run_id >= 2:
            self._extract_knowledge(run_id, current_params, metrics, hypothesis, insights)

    def _extract_knowledge(
        self, run_id: int, params: dict, metrics: dict, hypothesis: str, insights: str,
    ) -> None:
        """Use LLM to extract reusable knowledge from this run."""
        import json

        prompt_path = config.PROMPTS_DIR / "extract_knowledge.md"
        if not prompt_path.exists():
            return

        template = prompt_path.read_text(encoding="utf-8")
        existing = self.memory.semantic.to_context(max_tokens=800)

        prompt = self.analyzer.render_prompt(
            template,
            run_id=str(run_id),
            hypothesis=hypothesis or "无",
            params=json.dumps(params, ensure_ascii=False),
            metrics=json.dumps(metrics, ensure_ascii=False),
            insights=insights[:1000],
            existing_knowledge=existing or "（空）",
        )

        system = "You are an ABM research assistant. Output ONLY a JSON array. No other text."
        try:
            raw = self.analyzer.call_llm(system, prompt, max_tokens=512)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
            entries = json.loads(raw)
            for e in entries[:5]:
                self.memory.add_knowledge(
                    key=e["key"],
                    knowledge=e["knowledge"],
                    confidence=e.get("confidence", 0.5),
                    source_runs=[run_id],
                    category=e.get("category", "pattern"),
                )
                console.print(f"  [dim]📝 Knowledge: {e['key']}[/dim]")
        except (json.JSONDecodeError, KeyError, TypeError):
            pass  # knowledge extraction is best-effort

    def _inject_seed(self, seed: int) -> None:
        """Inject random seed into generated main.py for reproducibility."""
        main_py = self.workspace.model_dir / "main.py"
        if not main_py.exists():
            return

        content = main_py.read_text(encoding="utf-8")
        seed_block = (
            f"\n# Reproducibility: fixed random seed\n"
            f"import random, numpy as np\n"
            f"random.seed({seed})\n"
            f"np.random.seed({seed})\n"
        )

        # Insert after imports but before if __name__
        if "if __name__" in content:
            content = content.replace(
                'if __name__',
                f'{seed_block}\nif __name__',
            )
        else:
            content = seed_block + content

        main_py.write_text(content, encoding="utf-8")

        # Record seed in workspace metadata
        import json
        meta_path = self.workspace.path / "metadata.json"
        meta = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
        meta["seed"] = seed
        meta_path.write_text(json.dumps(meta, indent=2))
        console.print(f"  [green]✓ Random seed {seed} injected[/green]")

    def _print_memory_summary(self, after_iteration: int) -> None:
        """Print a brief readable summary of what experiment memory has accumulated."""
        episodic_entries = self.memory.episodic.all()
        semantic_entries = getattr(self.memory.semantic, "_entries", {})
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

    def _has_converged(
        self,
        completed_runs: int,
        cv_threshold: float = 0.05,
    ) -> bool:
        """Return True if metrics have converged across completed simulation runs.

        Delegates to ResultsReader.convergence_cv() — single source of truth for
        CSV column filtering and convergence logic.
        """
        run_ids = list(range(1, completed_runs + 1))
        converged, cv_by_metric = convergence_cv(
            self.workspace, run_ids, cv_threshold=cv_threshold
        )
        if cv_by_metric:
            console.print(
                f"  [dim]Convergence CV: "
                + ", ".join(f"{k}={v:.3f}" for k, v in cv_by_metric.items())
                + "[/dim]"
            )
        return converged

    def _process_resolution_ledger(self) -> None:
        """Read the Resolution Ledger from peer_review.md and display routing summary.

        In v2 this surfaces the action buckets so the researcher can decide next steps.
        Future: auto-trigger NEW_ANALYSIS re-runs and FIX code revisions.
        """
        peer_review_path = self.workspace.path / "peer_review.md"
        if not peer_review_path.exists():
            return

        review_text = peer_review_path.read_text(encoding="utf-8")
        if "Resolution Ledger" not in review_text:
            return

        actions = self.reviewer.parse_ledger(review_text)

        # Write machine-readable ledger summary
        import json as _json
        ledger_summary_path = self.workspace.path / "resolution_ledger.json"
        ledger_summary_path.write_text(
            _json.dumps(actions, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Display routing summary
        total = sum(len(v) for v in actions.values())
        if total == 0:
            return

        console.print("\n[bold magenta]Resolution Ledger summary:[/bold magenta]")
        colors = {"FIX": "red", "NEW_ANALYSIS": "yellow", "DOWNGRADE": "cyan", "DROP": "dim"}
        for action, issues in actions.items():
            if issues:
                color = colors.get(action, "white")
                console.print(f"  [{color}]{action}[/{color}] ({len(issues)}): "
                               + "; ".join(i[:60] for i in issues[:3])
                               + ("…" if len(issues) > 3 else ""))

        console.print(f"  [dim]Full ledger: {ledger_summary_path.name}[/dim]")

    def _record_initial_params(self) -> None:
        """Read SimulatorScenarios.csv and record initial params in history."""
        import pandas as pd

        csv_path = self.workspace.model_dir / "data" / "input" / "SimulatorScenarios.csv"
        if not csv_path.exists():
            return
        try:
            df = pd.read_csv(csv_path)
            if not df.empty:
                row = df.iloc[0].to_dict()
                # Remove metadata columns
                for col in ["id", "run_num"]:
                    row.pop(col, None)
                self.workspace.append_params_history(run=1, params=row, hypothesis="Initial parameters")
        except Exception:
            pass
