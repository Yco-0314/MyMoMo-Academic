"""Phase 2 + 3: CoderAgent generates, VerifierAgent refines via GVR loop.

Three validators are AND-composed:
  - dry_run: import sanity check (fatal severity — pipeline halts on persistent failure)
  - contract: calibration_params actually appear as CSV columns (soft)
  - fidelity: LLM-judge generated code vs mechanism_spec.md (soft)

When `using_external_model` is True, the entire phase is a no-op (the
user's code is already in workspace/model/).
"""
from __future__ import annotations

from rich.console import Console

from abm_auto.pipeline.phase import PipelineContext
from abm_auto.refinement import ValidationOutcome, compose_validators, refine

console = Console()


class CodegenPhase:
    """Phase 2 + Phase 3 bundled — codegen is meaningless without verify."""

    name = "Phase 2+3 (Coder + Verifier)"

    def __init__(self, coder, verifier, executor, max_retries: int):
        self.coder = coder
        self.verifier = verifier
        self.executor = executor
        self.max_retries = max_retries

    def should_run(self, ctx: PipelineContext) -> bool:
        return not ctx.using_external_model

    def run(self, ctx: PipelineContext) -> None:
        # Phase 2: code generation (single-shot — verify drives any retry)
        self.coder.run()

        # Phase 3: verify with composed validators
        def _gen(feedback):
            if feedback is not None:
                self.verifier.fix(feedback)
            return None

        def _anti_pattern_validator(_ignored) -> ValidationOutcome:
            """Static scan for known-recurring codegen anti-patterns.

            Catches what dry_run sometimes lets slip: hallucinated names
            in branches not exercised at import time. Patterns sourced
            from mymomo_knowledge/05-anti-patterns.md §1-3. Sourced
            centrally from anti_patterns.scan() so the catalogue stays
            in one place.
            """
            from abm_auto.codegen.anti_patterns import scan as scan_anti_patterns

            code_files = ctx.workspace.read_model_files()
            if not code_files:
                return ValidationOutcome(ok=True)
            issues = scan_anti_patterns(code_files)
            if not issues:
                return ValidationOutcome(ok=True)
            return ValidationOutcome(
                ok=False,
                reasons=issues,
                severity="fatal",  # these patterns guarantee runtime failure
                structured={"issue_count": len(issues)},
            )

        def _dry_run_validator(_ignored) -> ValidationOutcome:
            error = self.executor.dry_run()
            if error is None:
                return ValidationOutcome(ok=True)
            return ValidationOutcome(
                ok=False,
                reasons=[error[:1000]],
                severity="fatal",
                structured={"error_preview": error[:500]},
            )

        def _contract_validator(_ignored) -> ValidationOutcome:
            violations = _check_calibration_contract(ctx)
            if not violations:
                return ValidationOutcome(ok=True)
            return ValidationOutcome(
                ok=False,
                reasons=violations,
                severity="soft",
                structured={"violation_count": len(violations)},
            )

        def _fidelity_validator(_ignored) -> ValidationOutcome:
            spec = ctx.workspace.read_mechanism_spec()
            if not spec or len(spec.strip()) < 200:
                return ValidationOutcome(ok=True)
            code_files = ctx.workspace.read_model_files()
            code_blob = "\n".join(
                f"--- {p} ---\n{code_files[p]}" for p in (
                    "core/agent.py", "core/model.py",
                    "core/environment.py", "core/data_collector.py",
                ) if p in code_files
            )
            if not code_blob.strip():
                return ValidationOutcome(ok=True)
            system = (
                "You are a strict algorithm-fidelity judge. Compare ABM "
                "pseudocode (the contract) against its Python implementation. "
                "Identify SEMANTIC deviations: different update order, "
                "different stochastic semantics, wrong unit handling, missed "
                "edge cases. Ignore stylistic differences and naming. "
                "Output ONLY valid JSON, no other text."
            )
            prompt = (
                "## Mechanism Spec (the contract)\n\n"
                f"{spec[:4000]}\n\n"
                "## Generated Python code\n\n"
                f"{code_blob[:6000]}\n\n"
                "Does the code IMPLEMENT the spec's algorithm faithfully?\n\n"
                "Return JSON:\n"
                "{\n"
                '  "matches": true/false,\n'
                '  "deviations": ["<specific deviation 1>", "..."],\n'
                '  "severity_assessment": "minor" | "moderate" | "critical"\n'
                "}"
            )
            try:
                import json as _json
                raw = self.coder.call_llm(system, prompt, max_tokens=600).strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
                parsed = _json.loads(raw)
                if parsed.get("matches", False):
                    return ValidationOutcome(ok=True)
                deviations = parsed.get("deviations") or ["(no specifics given)"]
                return ValidationOutcome(
                    ok=False,
                    reasons=[f"Spec deviation: {d}" for d in deviations[:5]],
                    severity="soft",
                    structured={
                        "assessment": parsed.get("severity_assessment", "unknown"),
                        "deviation_count": len(deviations),
                    },
                )
            except Exception:
                return ValidationOutcome(ok=True)

        _val = compose_validators([
            ("anti_pattern", _anti_pattern_validator),   # static, runs first — cheap
            ("dry_run", _dry_run_validator),
            ("contract", _contract_validator),
            ("fidelity", _fidelity_validator),
        ])

        gvr = refine(
            generator=_gen,
            validator=_val,
            max_iters=self.max_retries,
            on_exhaust="continue_best",
            audit=ctx.workspace.audit,
            actor="CoderVerifier",
            phase="Phase 3",
        )

        if gvr.accepted:
            return

        # Exhausted — halt only on persistent FATAL severity
        best = min(
            gvr.attempts,
            key=lambda a: (len(a.outcome.reasons), -a.iteration),
        )
        if best.outcome.severity == "fatal":
            console.print(
                "[red]Pipeline halted: could not produce working code "
                "(fatal errors remain after retries).[/red]"
            )
            ctx.pipeline_halted = True
            ctx.halt_reason = "Codegen produced unrunnable code after all retries"
            return
        console.print(
            "[yellow]Pipeline proceeding with best-so-far code "
            "despite soft validator failures (see audit_ledger).[/yellow]"
        )


def _check_calibration_contract(ctx: PipelineContext) -> list[str]:
    """Verify SimulatorScenarios.csv has every calibration_param as a column."""
    if ctx.spec is None or not ctx.spec.calibration_params:
        return []
    csv_path = ctx.workspace.model_dir / "data" / "input" / "SimulatorScenarios.csv"
    if not csv_path.exists():
        return [
            f"data/input/SimulatorScenarios.csv is missing — calibration cannot run. "
            f"Required calibration params: {ctx.spec.calibration_params}"
        ]
    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
    except Exception as e:
        return [f"Could not read SimulatorScenarios.csv: {e}"]
    existing_cols = set(c.lower() for c in df.columns)
    missing = [
        p for p in ctx.spec.calibration_params
        if p.lower() not in existing_cols
    ]
    if not missing:
        return []
    return [
        f"CALIBRATION CONTRACT VIOLATION: data/input/SimulatorScenarios.csv is missing "
        f"required column(s): {missing}. "
        f"BayesianCalibrator needs these EXACT column names to tune the requested params. "
        f"Current columns: {list(df.columns)}. "
        f"Fix: add the missing column(s) to SimulatorScenarios.csv with sensible default values, "
        f"AND ensure core/scenario.py declares them as attributes with the same names, "
        f"AND ensure agent/environment code reads them as self.scenario.<exact_name>."
    ]
