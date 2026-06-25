"""Phase 1 + 1c: Design + Viability Gate, wired through the GVR refine loop.

Generate-Validate-Refine: DesignAgent produces DESIGN.md, ViabilityChecker
audits it. On failure (excessive AI-ASSUMPTION tags, missing required
elements, or LLM viability judgement), refine() feeds the failure reasons
back into DesignAgent and retries.

On exhaustion with `on_exhaust="continue_best"`, the best-so-far design
stays in the workspace; pipeline continues with a HIGH audit issue.
Hard halt only when best-so-far still has ≥4 unresolved reasons (broken
design too broken to continue).
"""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from abm_auto.pipeline.phase import PipelineContext
from abm_auto.refinement import ValidationOutcome, refine

console = Console()


class DesignViabilityPhase:
    """Phase 1 + 1c via GVR (first non-Verifier adapter of the pattern)."""

    name = "Phase 1+1c (Design + Viability)"

    def __init__(self, designer, viability):
        self.designer = designer
        self.viability = viability

    def should_run(self, ctx: PipelineContext) -> bool:
        return True

    def checkpoint_artefacts(self, ctx: PipelineContext) -> list:
        # ADR-021 D2: DESIGN.md is the cost-anchor artefact this phase produces.
        return [ctx.workspace.design_path]

    def run(self, ctx: PipelineContext) -> None:
        def _design_gen(feedback):
            return self.designer.run(extra_feedback=feedback)

        def _viability_val(_design_text) -> ValidationOutcome:
            # ViabilityChecker reads DESIGN.md from workspace, not from arg.
            # The artifact through refine() is `design_text` only for symmetry;
            # the validator uses the workspace state.
            result = self.viability.check(
                ctx.workspace.design_path, ctx.story_path, spec=ctx.spec,
            )
            return ValidationOutcome(
                ok=result.ok,
                reasons=result.reasons,
                severity="soft",   # let the phase decide halt vs continue
                structured={
                    "assumption_count": result.assumption_count,
                    "missing_elements": list(result.missing_elements),
                    "llm_verdict": result.llm_verdict,
                },
            )

        gvr = refine(
            generator=_design_gen,
            validator=_viability_val,
            max_iters=3,
            on_exhaust="continue_best",
            audit=ctx.workspace.audit,
            actor="DesignerViability",
            phase="Phase 1+1c",
        )

        if gvr.accepted:
            return

        # Exhausted. Best-so-far DESIGN.md is in workspace; HIGH audit issue open.
        console.print(
            Panel.fit(
                "[bold yellow]Viability not accepted after refinement; "
                "continuing with best-so-far design.[/bold yellow]\n"
                f"See: {ctx.workspace.path / 'audit_ledger.md'}",
                border_style="yellow",
            )
        )

        # Hard-halt override #1: an EMPTY / unusable DESIGN.md must halt.
        # The GVR refine loop can leave a 0-byte DESIGN.md when the LLM
        # returns nothing on its final attempt (a transient failure). An
        # empty design has few "reasons" so it slips past the reasons>=4
        # gate below, then crashes Phase 1d/1b downstream (ODD writer:
        # "DESIGN.md is missing"). Catch it here and halt cleanly instead.
        design_now = ctx.workspace.read_design()
        if len(design_now.strip()) < 200:   # a real design is thousands of chars
            console.print(
                Panel.fit(
                    "[bold red]Pipeline halted: DESIGN.md is empty or unusable "
                    "after refinement.[/bold red]\n"
                    "The design phase produced no usable design (likely a "
                    "transient LLM failure on the final attempt). Re-run, or "
                    "simplify the story.\n"
                    f"See: {ctx.workspace.path / 'kill_memo.md'}",
                    border_style="red",
                )
            )
            ctx.pipeline_halted = True
            ctx.halt_reason = "DESIGN.md empty/unusable after refinement"
            return

        # Hard-halt override #2: if best attempt is REALLY broken (≥4 reasons),
        # halt — proceeding produces garbage downstream.
        best_outcome = gvr.attempts[-1].outcome
        if len(best_outcome.reasons) >= 4:
            console.print(
                Panel.fit(
                    "[bold red]Pipeline halted: best-so-far design too broken.[/bold red]\n"
                    f"See: {ctx.workspace.path / 'kill_memo.md'}",
                    border_style="red",
                )
            )
            ctx.pipeline_halted = True
            ctx.halt_reason = "DESIGN.md too broken to continue"
