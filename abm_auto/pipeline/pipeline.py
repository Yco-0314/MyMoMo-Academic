"""ABM Auto Pipeline orchestrator.

Walks a list of `Phase` instances over a shared `PipelineContext`. Each
phase decides for itself whether to run (`should_run`) and what to do
(`run`). Adding a new phase = one new file in `phases/` + one line in
`_build_phases()`.

External contract (unchanged from the pre-refactor god method):
  - `Pipeline(...).run() -> Path` returns workspace.path on completion
  - all constructor parameters preserved
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from abm_auto import config
from abm_auto.agents.bayesian_calibrator import BayesianCalibrator
from abm_auto.agents.coder import CoderAgent
from abm_auto.agents.designer import DesignAgent
from abm_auto.agents.hypothesis_agent import HypothesisAgent
from abm_auto.agents.lit_reviewer import LitReviewAgent
from abm_auto.agents.coverage_extractor import CoverageExtractor
from abm_auto.agents.coverage_synthesizer import OperatorSynthesizer
from abm_auto.codegen.synthesis_phase import SynthesisPhase
from abm_auto.agents.mechanism_extractor import MechanismExtractor
from abm_auto.agents.mode_detector import ModeDetector
from abm_auto.agents.analyzer import AnalyzerAgent
from abm_auto.agents.odd_writer import OddWriter
from abm_auto.agents.optimizer import OptimizerAgent
from abm_auto.agents.reporter import ReporterAgent
from abm_auto.agents.reviewer import ReviewerAgent
from abm_auto.agents.salib_optimizer import SensitivityAnalyzer
from abm_auto.agents.verifier import VerifierAgent
from abm_auto.agents.viability_checker import ViabilityChecker
from abm_auto.agents.what_if_oracle import WhatIfOracle
from abm_auto.llm import make_client
from abm_auto.memory.store import ExperimentMemory
from abm_auto.pipeline.phase import LoopedPhase, Phase, PipelineContext
from abm_auto.runner.executor import Executor
from abm_auto.runner.workspace import Workspace
from abm_auto.runner.checkpoint import CheckpointStore, plan_skips, run_phases

console = Console()


class Pipeline:
    """Orchestrates the autonomous ABM research pipeline.

    Constructor builds agents + context + phase list. `run()` walks the
    phase list with halt-on-flag semantics.
    """

    def __init__(
        self,
        story_path: Path,
        iterations: int = config.DEFAULT_ITERATIONS,
        model: str = config.DEFAULT_MODEL,
        strong_model: str = config.STRONG_MODEL,
        max_retries: int = config.DEFAULT_MAX_RETRIES,
        timeout: Optional[int] = None,
        phase_timeouts: Optional[dict[str, int]] = None,
        workspace_name: Optional[str] = None,
        lit_notes_path: Optional[Path] = None,
        sensitivity_method: Optional[str] = None,
        sensitivity_samples: int = 10,
        peer_review: bool = False,
        lang: str = "zh",
        seed: Optional[int] = None,
        fetch_citations: bool = False,
        baseline_path: Optional[Path] = None,
        auto_lit_review: bool = True,
        mode_override: Optional[str] = None,
        intent_override: Optional[str] = None,
        external_model_path: Optional[str] = None,
        observed_path: Optional[str] = None,
        resume_from: Optional[str] = None,
        enable_critics: bool = False,
        allow_critic_soft: bool = False,
        benchmark_archetype: Optional[str] = None,
    ):
        self.story_path = Path(story_path)
        self.max_retries = max_retries
        self.resume_from = resume_from

        # Phase-specific timeouts (fallback to global timeout or defaults)
        self.phase_timeouts = phase_timeouts or {}
        global_timeout = timeout or config.DEFAULT_TIMEOUT
        self.timeout_simulation = self.phase_timeouts.get(
            "simulation",
            config.PHASE_TIMEOUTS.get("simulation", global_timeout),
        )
        self.timeout_llm = self.phase_timeouts.get(
            "llm", config.PHASE_TIMEOUTS.get("llm", 300)
        )
        self.timeout_sa = self.phase_timeouts.get(
            "sensitivity_analysis",
            config.PHASE_TIMEOUTS.get("sensitivity_analysis", 1800),
        )

        # LLM client
        api_key = config.get_api_key()
        if not api_key:
            key_name = (
                "DEEPSEEK_API_KEY" if config.LLM_PROVIDER == "deepseek"
                else "ANTHROPIC_API_KEY"
            )
            raise ValueError(f"{key_name} is not set. Add it to .env or environment.")
        self.client = make_client(
            provider=config.LLM_PROVIDER,
            api_key=api_key,
            base_url=config.get_base_url(),
            timeout=self.timeout_llm,
        )
        console.print(f"[dim]LLM provider: {config.LLM_PROVIDER}, model: {model}[/dim]")

        # Workspace — resume reopens an existing one; default creates a fresh one
        if resume_from is not None:
            self.workspace = Workspace.load(resume_from)
        else:
            self.workspace = Workspace.create(workspace_name)
        console.print(f"[dim]Workspace: {self.workspace.path}[/dim]")
        # D2 Checkpoint store (ADR-021): per-phase resume ledger under workspace/checkpoints/
        self.checkpoint_store = CheckpointStore(self.workspace.path)

        # Copy story + optional lit_notes
        self.workspace.write_story(self.story_path.read_text(encoding="utf-8"))
        if lit_notes_path and Path(lit_notes_path).exists():
            self.workspace.write_lit_notes(
                Path(lit_notes_path).read_text(encoding="utf-8")
            )

        # Agents (constructed once, injected into phases)
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
        self.mode_detector = ModeDetector(self.client, self.workspace, model=model, **agent_kw)
        self.hypothesis_agent = HypothesisAgent(self.client, self.workspace, model=strong_model, **agent_kw)
        self.mechanism_extractor = MechanismExtractor(self.client, self.workspace, model=strong_model, **agent_kw)
        self.coverage_extractor = CoverageExtractor(self.client, self.workspace, model=model, **agent_kw)
        self.coverage_synthesizer = OperatorSynthesizer(self.client, self.workspace, model=model, **agent_kw)
        self.synthesis_phase = SynthesisPhase()
        self.what_if_oracle = WhatIfOracle(self.client, self.workspace, model=strong_model, **agent_kw)
        self.bayesian_calibrator = BayesianCalibrator(self.client, self.workspace, model=model, **agent_kw)

        # Executor + memory
        self.executor = Executor(self.workspace, timeout=self.timeout_simulation)
        self.memory = ExperimentMemory(self.workspace.path / "memory")

        # Shared mutable state
        self.ctx = PipelineContext(
            workspace=self.workspace,
            executor=self.executor,
            memory=self.memory,
            story_path=self.story_path,
            iterations=iterations,
            max_retries=max_retries,
            peer_review=peer_review,
            lang=lang,
            seed=seed,
            fetch_citations=fetch_citations,
            baseline_path=Path(baseline_path) if baseline_path else None,
            auto_lit_review=auto_lit_review,
            mode_override=mode_override,
            intent_override=intent_override,
            external_model_path=external_model_path,
            observed_path=observed_path,
            benchmark_archetype=benchmark_archetype,
            sensitivity_method=sensitivity_method,
            sensitivity_samples=sensitivity_samples,
        )

        # Phase list — order matters
        self.phases: list[Phase] = self._build_phases()

        # D4 (ADR-021): opt-in inline Critics (two adapters). Default off ⇒ the phase
        # list is byte-identical to today; enabled ⇒ a soft adversarial gate runs after
        # the Design and Mechanism phases.
        if enable_critics:
            from abm_auto.agents.critic import DesignCritic, MechanismCritic
            from abm_auto.pipeline.phases.critic_phase import insert_critics
            critics = [
                DesignCritic(self.client, self.workspace, model=strong_model, lang=lang),
                MechanismCritic(self.client, self.workspace, model=strong_model, lang=lang),
            ]
            self.phases = insert_critics(self.phases, critics, allow_soft=allow_critic_soft)

        # D3 (ADR-021): opt-in compose-time contract check. Default off ⇒ existing
        # runs are byte-identical; ABM_VALIDATE_CONTRACTS=1 fails fast on a phase
        # whose declared inputs no earlier phase produces.
        if os.environ.get("ABM_VALIDATE_CONTRACTS") == "1":
            from abm_auto.pipeline.contract import validate_pipeline
            validate_pipeline(self.phases)

    def _build_phases(self) -> list[Phase]:
        """Construct the ordered phase list with explicit agent injection."""
        # Import lazily to avoid circular imports at package load time
        from abm_auto.pipeline.phases.analyses import (
            SensitivityPhase,
            StatisticalPhase,
            TrajectoryPhase,
        )
        from abm_auto.pipeline.phases.codegen import CodegenPhase
        from abm_auto.pipeline.phases.coverage import CoverageGatePhase
        from abm_auto.pipeline.phases.design import DesignViabilityPhase
        from abm_auto.pipeline.phases.enrichment import (
            BaselinePhase,
            CitationsPhase,
            WhatIfPhase,
        )
        from abm_auto.pipeline.phases.iteration import (
            AnalyzePhase,
            OptimizeOrCalibratePhase,
            SimulatePhase,
        )
        from abm_auto.pipeline.phases.model_prep import (
            ExternalModelInjectionPhase,
            MechanismExtractorPhase,
            OddPhase,
        )
        from abm_auto.pipeline.phases.output import (
            PackageArsPhase,
            PeerReviewPhase,
            ReportPhase,
            VisualizerPhase,
        )
        from abm_auto.pipeline.phases.pre_run import (
            PreRunSanityPhase,
            RecordInitialParamsPhase,
            SeedInjectionPhase,
        )
        from abm_auto.pipeline.phases.benchmark_phase import BenchmarkPhase
        from abm_auto.pipeline.phases.setup import (
            ExternalModelDeclarationPhase,
            HypothesisPhase,
            InjectObservedDataPhase,
            LitReviewPhase,
            ModeDetectorPhase,
        )

        # Inner loop body: simulate → analyze → optimize-or-calibrate
        inner_loop = LoopedPhase(
            name="Phase 4-6 (run × iterations)",
            inner=[
                SimulatePhase(executor=self.executor, verifier=self.verifier, max_retries=self.max_retries),
                AnalyzePhase(analyzer=self.analyzer),
                OptimizeOrCalibratePhase(
                    calibrator=self.bayesian_calibrator,
                    optimizer=self.optimizer,
                    coder=self.coder,
                ),
            ],
        )

        return [
            ModeDetectorPhase(self.mode_detector),
            ExternalModelDeclarationPhase(),
            InjectObservedDataPhase(),
            LitReviewPhase(self.lit_reviewer),
            HypothesisPhase(self.hypothesis_agent),
            DesignViabilityPhase(designer=self.designer, viability=self.viability_checker),
            ExternalModelInjectionPhase(),
            MechanismExtractorPhase(self.mechanism_extractor),
            CoverageGatePhase(
                extractor=self.coverage_extractor,
                synthesizer=self.coverage_synthesizer,
                synthesis=self.synthesis_phase,
                # ADR-015 self-extension is OPT-IN (executes generated code,
                # sandboxed) — off unless ABM_ENABLE_SYNTHESIS=1.
                enable_synthesis=os.getenv("ABM_ENABLE_SYNTHESIS", "") == "1",
            ),
            OddPhase(self.odd_writer),
            CodegenPhase(coder=self.coder, verifier=self.verifier, executor=self.executor, max_retries=self.max_retries),
            SeedInjectionPhase(),
            PreRunSanityPhase(),
            RecordInitialParamsPhase(),
            inner_loop,
            SensitivityPhase(self.sensitivity_analyzer),
            TrajectoryPhase(self.analyzer),
            StatisticalPhase(),
            WhatIfPhase(self.what_if_oracle),
            CitationsPhase(),
            BaselinePhase(),
            BenchmarkPhase(),  # ADR-021 D5: runs only when --benchmark <archetype> is set
            ReportPhase(self.reporter),
            VisualizerPhase(),
            PeerReviewPhase(self.reviewer),
            PackageArsPhase(),
        ]

    def run(self) -> Path:
        """Walk the phase list, halting on pipeline_halted flag."""
        console.print(
            Panel.fit(
                f"[bold]ABM Auto Pipeline[/bold]\n"
                f"Story: {self.story_path.name}\n"
                f"Iterations: {self.ctx.iterations}",
                border_style="blue",
            )
        )

        # D2 Checkpoint (ADR-021): on resume, skip the valid-checkpoint prefix up to
        # resume_from; in all runs, write a checkpoint after each successful phase
        # (resume_from=None ⇒ skip set empty ⇒ behaviour identical to before).
        skip = plan_skips(self.phases, self.checkpoint_store, self.resume_from)
        run_phases(self.phases, self.ctx, store=self.checkpoint_store, skip=skip)
        if self.ctx.pipeline_halted:
            console.print(
                f"[yellow]Pipeline halted: {self.ctx.halt_reason}[/yellow]"
            )

        console.print(
            Panel.fit(
                f"[bold green]Pipeline complete![/bold green]\n"
                f"Results: {self.workspace.path}\n",
                border_style="green",
            )
        )
        return self.workspace.path
