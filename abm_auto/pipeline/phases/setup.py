"""Setup phases — run once at pipeline start, before any model work.

Order: ModeDetector → ExternalModelDeclaration → LitReview → Hypothesis.
"""
from __future__ import annotations

import json

from rich.console import Console

from abm_auto.pipeline.phase import PipelineContext

console = Console()


class ModeDetectorPhase:
    """Phase -1: Detect research mode (reproduce vs originate) from story.md.

    Sets ctx.spec for every downstream phase. Mode override via CLI bypasses
    detection. Must run before any other phase that reads ctx.spec.
    """

    name = "Phase -1 (ModeDetector)"

    def __init__(self, agent):
        self.agent = agent

    def should_run(self, ctx: PipelineContext) -> bool:
        return True   # always

    def run(self, ctx: PipelineContext) -> None:
        ctx.spec = self.agent.run(mode_override=ctx.mode_override)


class ExternalModelDeclarationPhase:
    """Records `external_model_path` onto ctx.spec + persists research_spec.json.

    When the user passes --external-model, downstream phases (Phase 1d, 2, 3)
    use spec.external_model_path to short-circuit themselves. This phase
    just propagates the construction-time arg into the spec.
    """

    name = "External model declaration"

    def should_run(self, ctx: PipelineContext) -> bool:
        return bool(ctx.external_model_path)

    def run(self, ctx: PipelineContext) -> None:
        if ctx.spec is None:
            return
        ctx.spec.external_model_path = str(ctx.external_model_path)
        ctx.using_external_model = True
        try:
            spec_path = ctx.workspace.path / "research_spec.json"
            spec_path.write_text(
                json.dumps(ctx.spec.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass
        console.print(
            f"  [cyan]External model declared: {ctx.external_model_path} "
            f"→ Phase 1d / 2 / 3 will be skipped[/cyan]"
        )


class LitReviewPhase:
    """Phase 0: Automatic literature review (LitReviewAgent).

    Runs before Design so DesignAgent has lit_notes.md as context.
    Conditional on `auto_lit_review` flag.
    """

    name = "Phase 0 (LitReview)"

    def __init__(self, agent):
        self.agent = agent

    def should_run(self, ctx: PipelineContext) -> bool:
        return ctx.auto_lit_review

    def run(self, ctx: PipelineContext) -> None:
        self.agent.run()


class HypothesisPhase:
    """Phase 0.5: Hypothesis generation — originate mode only.

    Produces hypothesis.md with competing hypotheses + recommendation;
    DesignAgent reads it as its theoretical anchor. Without it, an
    originate-mode design has no mechanistic grounding and over-generalises.
    """

    name = "Phase 0.5 (Hypothesis)"

    def __init__(self, agent):
        self.agent = agent

    def should_run(self, ctx: PipelineContext) -> bool:
        return bool(ctx.spec and ctx.spec.mode == "originate")

    def run(self, ctx: PipelineContext) -> None:
        self.agent.run()
