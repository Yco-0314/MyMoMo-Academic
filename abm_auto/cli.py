from __future__ import annotations
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from abm_auto import config

app = typer.Typer(
    name="abm-auto",
    help="Autonomous Agent-Based Modeling research pipeline",
    add_completion=False,
)
console = Console()


@app.command()
def run(
    story: Path = typer.Argument(..., help="Path to STORY.md", exists=True),
    iterations: int = typer.Option(config.DEFAULT_ITERATIONS, "--iterations", "-n", help="Number of run→analyze→optimize cycles"),
    model: str = typer.Option(config.DEFAULT_MODEL, "--model", help="Claude model for standard agents"),
    strong_model: str = typer.Option(config.STRONG_MODEL, "--strong-model", help="Claude model for design/code/report agents"),
    max_retries: int = typer.Option(config.DEFAULT_MAX_RETRIES, "--max-retries", help="Max error-fix attempts"),
    timeout: int = typer.Option(config.DEFAULT_TIMEOUT, "--timeout", help="Global simulation timeout in seconds (can be overridden per phase)"),
    timeout_simulation: Optional[int] = typer.Option(None, "--timeout-simulation", help="Simulation phase timeout (overrides --timeout)"),
    timeout_sa: Optional[int] = typer.Option(None, "--timeout-sa", help="Sensitivity analysis timeout"),
    timeout_llm: Optional[int] = typer.Option(None, "--timeout-llm", help="LLM API call timeout"),
    lit_notes: Optional[Path] = typer.Option(None, "--lit-notes", help="Path to literature notes (lit_notes.md) for additional research context"),
    workspace_name: Optional[str] = typer.Option(None, "--workspace", help="Custom workspace name (default: timestamp)"),
    sensitivity: Optional[str] = typer.Option(None, "--sensitivity", help="Run SALib sensitivity analysis after iterations: morris or sobol"),
    sensitivity_samples: int = typer.Option(10, "--sa-samples", help="Number of SA trajectories/base samples"),
    peer_review: bool = typer.Option(False, "--review", help="Run automated peer review after pipeline completes"),
    lang: str = typer.Option("zh", "--lang", help="Output language: en (English paper) or zh (Chinese report)"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed for reproducibility"),
    fetch_citations: bool = typer.Option(False, "--fetch-citations", help="Fetch real citations from Semantic Scholar (requires API key)"),
    baseline: Optional[Path] = typer.Option(None, "--baseline", help="Path to baseline CSV for comparison (time,metric1,metric2,...)"),
    no_lit_review: bool = typer.Option(False, "--no-lit-review", help="Skip Phase 0 automatic literature search"),
    mode: Optional[str] = typer.Option(None, "--mode", help="Force research mode: 'reproduce' or 'originate'. Default: auto-detect from story.md (LLM)."),
    external_model: Optional[str] = typer.Option(None, "--external-model", help="Path to prebuilt Python model dir (main.py + core/). When set, Phase 1d / 2 / 3 are skipped — dir is copied into workspace/model/ and Phase 4+ runs against it. Useful for reproducing established models without LLM codegen drift."),
    observed: Optional[Path] = typer.Option(None, "--observed", help="Path to observed.csv for calibration. Copied into workspace/data/ before Phase 4. Without this (or a data/observed.csv next to STORY.md), Phase 6 silently falls back from BayesianCalibrator to heuristic OptimizerAgent."),
):
    """
    Run the full autonomous ABM pipeline from a story description.

    Examples:\n
        abm-auto run examples/sir_epidemic/story.md\n
        abm-auto run story.md --lang en --review  # English paper with peer review\n
        abm-auto run story.md --iterations 5 --strong-model claude-opus-4-6\n
        abm-auto run story.md --sensitivity morris --sa-samples 10 --review\n
        abm-auto run story.md --seed 42  # Reproducible run\n
        abm-auto run story.md --iterations 10 --sa-samples 100 --fetch-citations --baseline data/original_results.csv  # Publication mode
    """
    from abm_auto.pipeline import Pipeline

    # Build phase-specific timeouts dict
    phase_timeouts = {}
    if timeout_simulation is not None:
        phase_timeouts["simulation"] = timeout_simulation
    if timeout_sa is not None:
        phase_timeouts["sensitivity_analysis"] = timeout_sa
    if timeout_llm is not None:
        phase_timeouts["llm"] = timeout_llm

    pipeline = Pipeline(
        story_path=story,
        iterations=iterations,
        model=model,
        strong_model=strong_model,
        max_retries=max_retries,
        timeout=timeout,
        phase_timeouts=phase_timeouts if phase_timeouts else None,
        workspace_name=workspace_name,
        lit_notes_path=lit_notes,
        sensitivity_method=sensitivity,
        sensitivity_samples=sensitivity_samples,
        peer_review=peer_review,
        lang=lang,
        seed=seed,
        fetch_citations=fetch_citations,
        baseline_path=baseline,
        auto_lit_review=not no_lit_review,
        mode_override=mode,
        external_model_path=external_model,
        observed_path=str(observed) if observed else None,
    )
    workspace_path = pipeline.run()
    console.print(f"\n[bold]Output directory:[/bold] {workspace_path}")


@app.command()
def optimize(
    workspace: Path = typer.Argument(..., help="Path to an existing workspace directory"),
    iterations: int = typer.Option(3, "--iterations", "-n"),
    model: str = typer.Option(config.DEFAULT_MODEL, "--model"),
):
    """Re-run the analyze→optimize loop on an existing workspace."""
    from abm_auto.runner.workspace import Workspace
    from abm_auto.runner.executor import Executor
    from abm_auto.agents.analyzer import AnalyzerAgent
    from abm_auto.agents.optimizer import OptimizerAgent
    from abm_auto.agents.coder import CoderAgent
    from abm_auto.agents.reporter import ReporterAgent
    from abm_auto.llm import make_client

    ws = Workspace.load(workspace)
    client = make_client(provider=config.LLM_PROVIDER, api_key=config.get_api_key(), base_url=config.get_base_url(), timeout=300.0)
    executor = Executor(ws)
    analyzer = AnalyzerAgent(client, ws, model=model)
    optimizer = OptimizerAgent(client, ws, model=model)
    coder = CoderAgent(client, ws, model=model)
    reporter = ReporterAgent(client, ws, model=model)

    existing_runs = len(ws.read_params_history())
    all_insights: list[str] = []

    for i in range(existing_runs + 1, existing_runs + iterations + 1):
        console.print(f"\n[bold]--- Iteration {i} ---[/bold]")
        success, output = executor.run(i)
        if not success:
            console.print(f"  [red]✗ {output[:200]}[/red]")
            continue
        insights = analyzer.run(executor, i)
        all_insights.append(insights)
        if i < existing_runs + iterations:
            optimizer.run(i, insights, coder)

    if all_insights:
        reporter.run(all_insights)


@app.command()
def sensitivity(
    workspace: Path = typer.Argument(..., help="Path to an existing workspace with working model code"),
    method: str = typer.Option("morris", "--method", "-m", help="SALib method: morris or sobol"),
    n_samples: int = typer.Option(10, "--samples", "-N", help="Number of trajectories (Morris) or base samples (Sobol)"),
    metric_column: Optional[str] = typer.Option(None, "--metric-col", help="Output CSV column to use as response variable (auto-detected if omitted)"),
    metric_file: Optional[str] = typer.Option(None, "--metric-file", help="Output CSV filename to read metric from (auto-detected if omitted)"),
    model: str = typer.Option(config.DEFAULT_MODEL, "--model"),
    timeout: int = typer.Option(config.DEFAULT_TIMEOUT, "--timeout"),
    lang: str = typer.Option("zh", "--lang", help="Output language: en or zh"),
):
    """
    Run SALib sensitivity analysis on an existing workspace.

    The workspace must already contain working model code (i.e., the pipeline
    ran at least through the verify phase). This command:

    1. Reads parameter bounds from SimulatorScenarios.csv (±50% of current values)
    2. Generates sample points via Morris or Sobol
    3. Runs the simulation for each sample
    4. Computes sensitivity indices
    5. Uses LLM to interpret results

    Examples:\n
        abm-auto sensitivity workspace/20260401_120000_abc123 --method morris -N 10\n
        abm-auto sensitivity workspace/my_run --method sobol -N 64 --metric-col infected_count
    """
    from abm_auto.runner.workspace import Workspace
    from abm_auto.runner.executor import Executor
    from abm_auto.agents.salib_optimizer import SensitivityAnalyzer
    from abm_auto.llm import make_client

    if method not in ("morris", "sobol"):
        console.print("[red]Method must be 'morris' or 'sobol'[/red]")
        raise typer.Exit(1)

    ws = Workspace.load(workspace)
    client = make_client(provider=config.LLM_PROVIDER, api_key=config.get_api_key(), base_url=config.get_base_url(), timeout=300.0)
    executor = Executor(ws, timeout=timeout)
    analyzer = SensitivityAnalyzer(client, ws, model=model, lang=lang)

    result = analyzer.run(
        executor,
        method=method,
        n_trajectories=n_samples,
        metric_column=metric_column,
        metric_file=metric_file,
    )

    if result:
        console.print(f"\n[bold green]Sensitivity analysis complete![/bold green]")
        console.print(f"Results: {ws.path}")
    else:
        console.print("[yellow]Sensitivity analysis did not produce results.[/yellow]")


@app.command()
def trajectories(
    workspace: Path = typer.Argument(..., help="Path to an existing workspace with ≥3 completed runs"),
    metric_column: Optional[str] = typer.Option(None, "--metric-col", help="Output CSV column (auto-detected if omitted)"),
    metric_file: Optional[str] = typer.Option(None, "--metric-file", help="Output CSV filename (auto-detected if omitted)"),
):
    """
    Run trajectory analysis on completed simulation runs.

    Clusters runs by output trajectory shape, finds critical divergence
    timesteps, and computes parameter-outcome correlations.

    Requires at least 3 completed runs in the workspace.

    Examples:\n
        abm-auto trajectories workspace/20260401_120000_abc123\n
        abm-auto trajectories workspace/my_run --metric-col infected_count
    """
    from abm_auto.analysis.trajectory_analyzer import TrajectoryAnalyzer

    ta = TrajectoryAnalyzer(Path(workspace))
    result = ta.analyze(metric_column=metric_column, metric_file=metric_file)

    if result:
        console.print(result.to_summary())
        console.print(f"\n[bold green]Trajectory analysis complete![/bold green]")
        console.print(f"Results: {workspace}/trajectory_analysis.md")
    else:
        console.print("[yellow]Insufficient data for trajectory analysis (need ≥3 runs).[/yellow]")


@app.command()
def memory(
    workspace: Path = typer.Argument(..., help="Path to an existing workspace"),
    tier: str = typer.Option("all", "--tier", "-t", help="Memory tier: working, episodic, semantic, or all"),
):
    """
    Inspect experiment memory for a workspace.

    Shows the accumulated knowledge across simulation runs,
    including working state, episodic run history, and semantic knowledge.

    Examples:\n
        abm-auto memory workspace/20260401_120000_abc123\n
        abm-auto memory workspace/my_run --tier semantic
    """
    from abm_auto.memory.store import ExperimentMemory

    mem = ExperimentMemory(Path(workspace) / "memory")

    if tier in ("all", "working"):
        entries = mem.working.all()
        console.print(f"\n[bold]Working Memory[/bold] ({len(entries)} entries)")
        for e in entries:
            console.print(f"  [{e.key}] (p={e.priority:.1f}): {e.value}")

    if tier in ("all", "episodic"):
        entries = mem.episodic.all()
        console.print(f"\n[bold]Episodic Memory[/bold] ({len(entries)} runs)")
        for e in entries:
            console.print(
                f"  Run {e.run_id} ({e.outcome}): "
                f"metrics={e.metrics}, hypothesis=\"{e.hypothesis}\""
            )
        stats = mem.episodic.summary_stats()
        if stats:
            console.print("  [dim]Summary stats:[/dim]")
            for k, v in stats.items():
                console.print(f"    {k}: mean={v['mean']:.3f} ± {v['std']:.3f} [{v['min']:.3f}, {v['max']:.3f}]")

    if tier in ("all", "semantic"):
        entries = mem.semantic.all()
        console.print(f"\n[bold]Semantic Memory[/bold] ({len(entries)} entries)")
        for e in entries:
            console.print(f"  [{e.category}] {e.key} (conf={e.confidence:.2f}): {e.knowledge}")

    if not any(
        [mem.working.all(), mem.episodic.all(), mem.semantic.all()]
    ):
        console.print("[yellow]No memory data found in this workspace.[/yellow]")


@app.command()
def review(
    workspace: Path = typer.Argument(..., help="Path to an existing workspace to review"),
    mode: str = typer.Option("panel", "--mode", "-m", help="Review mode: panel (5 reviewers + editor) or quick (single pass)"),
    model: str = typer.Option(config.STRONG_MODEL, "--model", help="Claude model (recommend strong model for rigorous review)"),
    lang: str = typer.Option("zh", "--lang", help="Review language: en or zh"),
):
    """
    Run automated peer review on a completed workspace.

    Panel mode (default): 5 specialized reviewers + Editor-in-Chief.\n
      R1 Theory Contribution — theoretical gaps, concept construction\n
      R2 Methodology — ODD transparency, V&V, parameter calibration\n
      R3 Literature — pseudo-innovation detection, research gap validation\n
      R4 Logic Structure — argument chain, logical fallacies\n
      EiC Editor-in-Chief — desk reject screening, final verdict\n

    Quick mode: Single-pass consolidated review (faster, less detailed).

    Examples:\n
        abm-auto review workspace/my_run\n
        abm-auto review workspace/my_run --lang en\n
        abm-auto review workspace/my_run --mode quick
    """
    from abm_auto.runner.workspace import Workspace
    from abm_auto.agents.reviewer import ReviewerAgent
    from abm_auto.llm import make_client

    if mode not in ("panel", "quick"):
        console.print("[red]Mode must be 'panel' or 'quick'[/red]")
        raise typer.Exit(1)

    ws = Workspace.load(workspace)
    client = make_client(provider=config.LLM_PROVIDER, api_key=config.get_api_key(), base_url=config.get_base_url(), timeout=300.0)
    reviewer = ReviewerAgent(client, ws, model=model, lang=lang)
    reviewer.run(mode=mode)


@app.command()
def ingest_netlogo(
    nlogo_path: Path = typer.Argument(..., help="Path to .nlogo file", exists=True),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output story.md path"),
):
    """
    Convert a NetLogo .nlogo model to story.md for the pipeline.

    Examples:\n
        abm-auto ingest-netlogo ~/models/Virus.nlogo\n
        abm-auto ingest-netlogo Fire.nlogo -o examples/fire/story.md
    """
    from abm_auto.ingest.netlogo import convert_nlogo_to_story

    out = convert_nlogo_to_story(nlogo_path, output)
    console.print(f"[green]✓ Converted to {out}[/green]")


@app.command()
def ingest_comses(
    query: str = typer.Argument(..., help="Search query (e.g., 'conflict', 'epidemic', 'cooperation')"),
    output_dir: Path = typer.Option(Path("examples"), "--output-dir", "-o", help="Output directory for generated story.md files"),
    max_models: int = typer.Option(5, "--max", "-n", help="Maximum number of models to fetch"),
):
    """
    Fetch models from CoMSES Computational Model Library and convert to story.md.

    Examples:\n
        abm-auto ingest-comses conflict\n
        abm-auto ingest-comses "epidemic spread" -n 10\n
        abm-auto ingest-comses cooperation -o examples/comses/
    """
    from abm_auto.ingest.comses import fetch_and_convert

    paths = fetch_and_convert(query, output_dir, max_models=max_models)
    if paths:
        console.print(f"[green]✓ Created {len(paths)} story.md files:[/green]")
        for p in paths:
            console.print(f"  {p}")
    else:
        console.print("[yellow]No models found for query.[/yellow]")


@app.command()
def batch(
    glob_pattern: str = typer.Argument(..., help='Glob pattern for story.md files, e.g. "examples/batch_2026_04/*/story.md"'),
    workers: int = typer.Option(6, "--workers", "-w", help="Number of parallel workers"),
    lang: str = typer.Option("en", "--lang", help="Output language: en or zh"),
    iterations: int = typer.Option(3, "--iterations", "-n", help="Iterations per story"),
    sensitivity: Optional[str] = typer.Option("morris", "--sensitivity", help="Sensitivity method: morris, sobol, or none"),
    no_review: bool = typer.Option(False, "--no-review", help="Skip peer review phase"),
    timeout: int = typer.Option(300, "--timeout", help="Simulation timeout per run (seconds)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="List matching stories without running"),
    label: str = typer.Option("batch", "--label", help="Label for summary CSV filename"),
):
    """
    Run multiple story.md files in parallel.

    Writes a summary CSV to workspace/<label>_summary.csv.
    Each failed story gets one automatic retry at --iterations 1 --no-review.

    Examples:\n
        abm-auto batch "examples/batch_2026_04/*/story.md" --workers 6\n
        abm-auto batch "examples/*/story.md" --workers 4 --lang zh --no-review\n
        abm-auto batch "examples/batch_2026_04/*/story.md" --dry-run
    """
    import glob as globmod
    from abm_auto.batch import run_batch

    paths = sorted(Path(p) for p in globmod.glob(glob_pattern, recursive=True))
    stories = [p for p in paths if p.is_file()]

    if not stories:
        console.print(f"[red]No stories found matching: {glob_pattern}[/red]")
        raise typer.Exit(1)

    sa = None if (not sensitivity or sensitivity.lower() == "none") else sensitivity

    run_batch(
        stories=stories,
        workers=workers,
        lang=lang,
        iterations=iterations,
        review=not no_review,
        sensitivity=sa,
        timeout_per_sim=timeout,
        dry_run=dry_run,
        batch_label=label,
    )


if __name__ == "__main__":
    app()
