"""Phase Protocol + PipelineContext.

The orchestrator (`Pipeline`) walks a list of `Phase` instances, calling
each one's `should_run(ctx)` predicate and `run(ctx)` body in order.
Phases mutate the shared `PipelineContext` to communicate (e.g., the
ModeDetector phase sets `ctx.spec`; downstream phases read it).

This module owns the two abstractions; `phases/` contains the concrete
adapters; `pipeline.py` is the orchestrator.

Why mutable ctx (not immutable): every phase today mutates Pipeline
state in the original god method. Preserving that semantic with the
minimum boilerplate (rather than threading `replace(ctx, ...)` returns)
keeps this refactor's risk profile low — shape changes, semantics don't.

Why LoopedPhase: today's Phase 4-6 runs inside an outer iteration loop.
Rather than have each phase read `ctx.iteration` and self-skip, the loop
is its own structural element — explicit in the phase list, with
convergence-driven early stop encapsulated in one place.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Protocol

if TYPE_CHECKING:
    from abm_auto.agents.mode_detector import ResearchSpec
    from abm_auto.memory.store import ExperimentMemory
    from abm_auto.runner.executor import Executor
    from abm_auto.runner.workspace import Workspace


@dataclass
class PipelineContext:
    """Shared state passed phase-to-phase. Mutable by design (see module docstring)."""

    # ── Construction-time deps (immutable after __init__) ──
    workspace: "Workspace"
    executor: "Executor"
    memory: "ExperimentMemory"
    story_path: Path

    # ── Pipeline-level flags (immutable after __init__) ──
    iterations: int = 3
    max_retries: int = 3
    peer_review: bool = False
    lang: str = "zh"
    seed: Optional[int] = None
    fetch_citations: bool = False
    baseline_path: Optional[Path] = None
    auto_lit_review: bool = True
    mode_override: Optional[str] = None
    external_model_path: Optional[str] = None
    observed_path: Optional[str] = None
    sensitivity_method: Optional[str] = None
    sensitivity_samples: int = 10

    # ── Phase-mutated state ──
    spec: Optional["ResearchSpec"] = None
    using_external_model: bool = False
    iteration: int = 0
    converged_at: Optional[int] = None
    all_insights: list[str] = field(default_factory=list)
    used_bayesian_calibration: bool = False
    citations_text: Optional[str] = None
    comparison_text: Optional[str] = None

    # Halt flag — any phase setting this short-circuits the orchestrator
    pipeline_halted: bool = False
    halt_reason: str = ""


class Phase(Protocol):
    """Smallest unit of pipeline work. Implementations live in `phases/`."""

    name: str

    def should_run(self, ctx: PipelineContext) -> bool:
        """Activation predicate. Return False to skip this phase."""
        ...

    def run(self, ctx: PipelineContext) -> None:
        """Do the work. Mutates ctx with phase outputs."""
        ...


class LoopedPhase:
    """Wraps a sub-list of phases in an outer iteration loop.

    On each iteration, sets `ctx.iteration = i`, then runs every inner
    phase whose `should_run(ctx)` returns True. Stops early if
    `ctx.converged_at` becomes non-None inside an iteration.

    Designed for today's Phase 4-6 cycle (simulate → analyze → optimize).
    """

    def __init__(self, name: str, inner: list[Phase]):
        self.name = name
        self.inner = inner

    def should_run(self, ctx: PipelineContext) -> bool:
        # Run the loop if at least one inner phase would, on at least
        # iteration 1, want to run. Cheap heuristic: assume the iteration
        # loop is meaningful whenever iterations >= 1.
        return ctx.iterations >= 1

    def run(self, ctx: PipelineContext) -> None:
        for i in range(1, ctx.iterations + 1):
            if ctx.pipeline_halted:
                return
            ctx.iteration = i
            for phase in self.inner:
                if ctx.pipeline_halted:
                    return
                if not phase.should_run(ctx):
                    continue
                phase.run(ctx)
            if ctx.converged_at is not None:
                return
