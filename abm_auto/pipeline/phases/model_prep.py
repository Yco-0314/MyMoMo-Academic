"""Model-prep phases: between Design and Codegen.

Three phases — only ODD always runs; the others depend on whether the user
brought an external model:

  ExternalModelInjectionPhase   — copies user-supplied model dir if --external-model
  MechanismExtractorPhase       — Phase 1d, skipped when external model
  OddPhase                      — Phase 1b, runs in both branches
"""
from __future__ import annotations

import shutil
from pathlib import Path

from rich.console import Console

from abm_auto.pipeline.phase import PipelineContext

console = Console()


class ExternalModelInjectionPhase:
    """Copy the user-supplied external model directory into workspace.model_dir.

    Replaces Phase 2 (CoderAgent) when --external-model is given. The source
    directory must contain `main.py` plus core/ files arranged the same way
    CoderAgent's output would be. After this, Phase 4+ runs Executor.run()
    against the supplied model with zero LLM-mediated changes.
    """

    name = "External model injection"

    def should_run(self, ctx: PipelineContext) -> bool:
        return ctx.using_external_model

    def run(self, ctx: PipelineContext) -> None:
        source = ctx.spec.external_model_path if ctx.spec else None
        if not source:
            return
        src = Path(source).expanduser().resolve()
        if not src.exists():
            console.print(f"  [red]✗ external model path not found: {src}[/red]")
            ctx.pipeline_halted = True
            ctx.halt_reason = f"External model path not found: {src}"
            return
        if not src.is_dir():
            console.print(f"  [red]External model path must be a directory: {src}[/red]")
            ctx.pipeline_halted = True
            ctx.halt_reason = f"External model path is not a directory: {src}"
            return
        if not (src / "main.py").exists():
            console.print(
                f"  [yellow]⚠ external model dir missing main.py: {src}[/yellow]"
            )
        dest = ctx.workspace.model_dir
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest, dirs_exist_ok=True)
        console.print(f"  [green]✓ External model copied {src} → {dest}[/green]")
        try:
            ctx.workspace.audit.info(
                phase="Phase 2 (skipped — external)",
                text=f"External model injected from {src}",
                actor="Pipeline",
                structured={"source": str(src), "dest": str(dest)},
            )
        except Exception:
            pass


class MechanismExtractorPhase:
    """Phase 1d: Pseudocode pinning before codegen.

    Extracts a mechanism spec from DESIGN.md that CoderAgent reads as a hard
    contract (injected at TOP of its prompt, above DESIGN.md). Skipped when
    external model is supplied (the user's existing code IS the spec).
    """

    name = "Phase 1d (MechanismExtractor)"

    def __init__(self, agent):
        self.agent = agent

    def should_run(self, ctx: PipelineContext) -> bool:
        return not ctx.using_external_model

    def run(self, ctx: PipelineContext) -> None:
        self.agent.run()


class OddPhase:
    """Phase 1b: ODD Protocol generation.

    Runs in both branches — ODD.md is research documentation, useful
    regardless of whether the model was generated or supplied externally.
    """

    name = "Phase 1b (ODD)"

    def __init__(self, agent):
        self.agent = agent

    def should_run(self, ctx: PipelineContext) -> bool:
        return True

    def run(self, ctx: PipelineContext) -> None:
        self.agent.run()
