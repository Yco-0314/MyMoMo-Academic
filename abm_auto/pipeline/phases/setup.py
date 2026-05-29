"""Setup phases — run once at pipeline start, before any model work.

Order: ModeDetector → ExternalModelDeclaration → InjectObservedData → LitReview → Hypothesis.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

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


class InjectObservedDataPhase:
    """Copy observed.csv into workspace/data/ so calibration can find it.

    Without this, calibration_data_path is interpreted relative to the
    auto-named workspace (which is empty), `_should_calibrate()` returns
    False, and Phase 6 silently falls through to the OptimizerAgent.
    The user wrote a story claiming empirical data exists; they expect
    Bayesian calibration; they get heuristic hand-tuning instead.

    Resolution order (first match wins):
      1. `ctx.observed_path` — from `--observed PATH` CLI flag
      2. `ctx.story_path.parent / ctx.spec.calibration_data_path` — relative to story
      3. `ctx.workspace.path / "data" / "observed.csv"` — already-injected
         (benchmark harnesses do this manually; idempotent skip)

    When the spec declares calibration data but no source is found, raises
    a HIGH audit issue so the failure isn't silent. OptimizeOrCalibratePhase
    surfaces the same condition with a loud stdout warning at Phase 6 time.
    """

    name = "Inject observed data"

    def should_run(self, ctx: PipelineContext) -> bool:
        if ctx.spec is None or not ctx.spec.has_calibration_data:
            return False
        # Already present (idempotent — benchmark harness path)
        existing = ctx.workspace.path / "data" / "observed.csv"
        return not existing.exists()

    def run(self, ctx: PipelineContext) -> None:
        src = self._resolve_source(ctx)
        if src is None:
            search = self._search_summary(ctx)
            console.print(
                f"  [yellow]⚠ spec declares calibration data "
                f"(`{ctx.spec.calibration_data_path}`) but no file found at:[/yellow]"
            )
            for line in search:
                console.print(f"      [yellow]· {line}[/yellow]")
            console.print(
                "  [yellow]Pipeline will fall back to OptimizerAgent at Phase 6 "
                "(heuristic, not Bayesian). Pass --observed PATH or place "
                "observed.csv next to your story.[/yellow]"
            )
            try:
                ctx.workspace.audit.raise_issue(
                    phase="Inject observed data",
                    severity="HIGH",
                    text=(
                        f"Spec declares calibration data "
                        f"(`{ctx.spec.calibration_data_path}`) but no file located. "
                        f"Searched: {search}. Pipeline will fall back to "
                        f"OptimizerAgent at Phase 6."
                    ),
                    actor="Pipeline",
                )
            except Exception:
                pass
            return

        dest_dir = ctx.workspace.path / "data"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "observed.csv"
        shutil.copy(src, dest)
        console.print(
            f"  [green]✓ Observed data injected: {src} → {dest.relative_to(ctx.workspace.path)}[/green]"
        )
        try:
            ctx.workspace.audit.info(
                phase="Inject observed data",
                text=f"Observed data injected from {src}",
                actor="Pipeline",
                structured={"source": str(src), "dest": str(dest)},
            )
        except Exception:
            pass

    def _resolve_source(self, ctx: PipelineContext) -> Optional[Path]:
        # 1. CLI flag wins
        if ctx.observed_path:
            p = Path(ctx.observed_path).expanduser().resolve()
            if p.exists():
                return p
        # 2. Resolve spec path relative to story directory
        if ctx.spec and ctx.spec.calibration_data_path:
            story_dir = ctx.story_path.parent
            candidate = (story_dir / ctx.spec.calibration_data_path).resolve()
            if candidate.exists():
                return candidate
            # Also try absolute (rare but legal)
            absolute = Path(ctx.spec.calibration_data_path).expanduser().resolve()
            if absolute.exists():
                return absolute
        return None

    def _search_summary(self, ctx: PipelineContext) -> list[str]:
        out: list[str] = []
        if ctx.observed_path:
            out.append(f"--observed: {ctx.observed_path}")
        if ctx.spec and ctx.spec.calibration_data_path:
            story_dir = ctx.story_path.parent
            out.append(f"story-dir relative: {(story_dir / ctx.spec.calibration_data_path).resolve()}")
            out.append(f"absolute path: {Path(ctx.spec.calibration_data_path).expanduser().resolve()}")
        return out


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
