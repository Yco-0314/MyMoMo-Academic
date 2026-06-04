"""Phase 1e: the Coverage Gate (ADR-014).

After mechanism extraction, before codegen: verify the spec is BUILDABLE, not
just well-specified. The viability gate (Phase 1c) checks spec QUALITY; this
checks whether every declared mechanism maps to a provided operator (or
generatable code). A model that is perfectly specified but needs an operator
the runtime lacks (a conditional GAN) HALTS here — naming the missing
capability — instead of silently reaching codegen and being stubbed out.

This wires in the deterministic Coverage Gate core. Extraction is the
heuristic stub (1a); the LLM extraction (1b) is the accuracy upgrade, gated by
the same deterministic verdict.
"""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from abm_auto.codegen.coverage_gate import CoverageGate, extract_mechanisms_heuristic
from abm_auto.codegen.mechanism_spec import MechanismSpec
from abm_auto.pipeline.phase import PipelineContext

console = Console()


class CoverageGatePhase:
    """Halt on an unbuildable mechanism; pass otherwise (noting any tier-3
    build-and-verify mechanisms for the codegen self-test step)."""

    name = "Phase 1e (Coverage Gate)"

    def should_run(self, ctx: PipelineContext) -> bool:
        if getattr(ctx, "using_external_model", False):
            return False
        return (ctx.workspace.path / "mechanism_spec.json").exists()

    def run(self, ctx: PipelineContext) -> None:
        spec_path = ctx.workspace.path / "mechanism_spec.json"
        try:
            spec = MechanismSpec.from_json(spec_path.read_text(encoding="utf-8"))
        except Exception:
            spec = None
        prose = f"{ctx.workspace.read_design()}\n{ctx.workspace.read_mechanism_spec()}"

        mechs = extract_mechanisms_heuristic(spec, prose)
        verdict = CoverageGate().check(mechs)

        if verdict.passed:
            console.print(
                f"  [green]✓ Coverage Gate passed[/green] "
                f"[dim](build+verify: {verdict.build_and_verify or 'none'})[/dim]"
            )
            try:
                ctx.workspace.audit.info(
                    phase="Phase 1e",
                    text=f"Coverage Gate passed; tier-3 build+verify: {verdict.build_and_verify}",
                    actor="CoverageGate",
                    structured={"build_and_verify": verdict.build_and_verify},
                )
            except Exception:
                pass
            return

        # Uncovered → halt, naming the missing capability (demand-driven).
        uncovered_caps = sorted({m.capability for m in mechs if m.name in verdict.uncovered})
        reason = (
            f"Coverage Gate: no provided operator covers {uncovered_caps}. "
            f"The design is well-specified but UNBUILDABLE (codegen would stub it). "
            f"Add an operator for this capability, or simplify the mechanism. See ADR-014."
        )
        console.print(
            Panel.fit(
                "[bold red]Pipeline halted: Coverage Gate — unbuildable mechanism.[/bold red]\n"
                f"No operator covers: {uncovered_caps}\n"
                f"(spec passed viability but cannot be generated; this is the W2 wall "
                f"the gate exists to catch.)",
                border_style="red",
            )
        )
        ctx.pipeline_halted = True
        ctx.halt_reason = reason
        try:
            ctx.workspace.audit.raise_issue(
                phase="Phase 1e",
                severity="BLOCKING",
                text=reason,
                actor="CoverageGate",
                structured={"uncovered": verdict.uncovered, "capabilities": uncovered_caps},
            )
        except Exception:
            pass
