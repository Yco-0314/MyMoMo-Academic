"""Phase 2 + 3: TemplateGenerator + CoderAgent + VerifierAgent.

Two-stage codegen (Layer 3 architectural change):

  Stage A — TemplateGenerator (deterministic, no LLM)
      If mechanism_spec.json exists from Phase 1d, emit 5 boilerplate
      files (model.py, scenario.py, data_collector.py, main.py,
      SimulatorScenarios.csv). These files are guaranteed correct by
      construction — no LLM-side errors possible.

  Stage B — CoderAgent + GVR (LLM)
      Generate the remaining files (agent.py, environment.py). The
      anti_pattern / dry_run / contract / fidelity validator chain
      retries via refine() on failure.

When mechanism_spec.json is absent or invalid, the pipeline falls back
to legacy whole-file codegen (CoderAgent writes all 7 files).

When `using_external_model` is True, BOTH stages are no-ops — the
user's prebuilt model lives in workspace/model/ untouched.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from rich.console import Console

from abm_auto.codegen.mechanism_spec import MechanismSpec
from abm_auto.codegen.template_generator import (
    TEMPLATE_FILES,
    generate_all,
    is_template_file,
)
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
        # Stage A: TemplateGenerator (deterministic). Runs only when a
        # valid mechanism_spec.json was produced in Phase 1d.
        template_used = _try_run_template_generator(ctx)

        # Phase 2: code generation (single-shot — verify drives any retry).
        # When templates ran, CoderAgent's output is post-processed to
        # revert any LLM edits to template-owned files.
        # Memory feedback: pass accumulated semantic + episodic knowledge
        # so CoderAgent learns from prior codegen failures (Item 4 / ADR-006 OQ#4).
        memory_context = ""
        try:
            memory_context = ctx.memory.retrieve_context()
        except Exception:
            pass
        self.coder.run(memory_context=memory_context)
        if template_used:
            _revert_template_files(ctx)

        # Phase 3: verify with composed validators
        def _gen(feedback):
            if feedback is not None:
                self.verifier.fix(feedback)
            return None

        def _structural_fidelity_validator(_ignored) -> ValidationOutcome:
            """Deterministic structural checks against mechanism_spec.json.

            Complements `_fidelity_validator` (LLM-judge, expensive & noisy)
            with cheap regex-based gates that catch the most common
            spec-vs-code drift:

              - scenario_params declared in JSON spec but missing from
                scenario.py `self.X` declarations
              - agent_state_vars declared in JSON spec but missing from
                agent.py `self.X` references

            Doesn't try to validate behavioral fidelity (that's the LLM
            judge's job) — just that the structural surface matches.

            Why this fires BEFORE `_fidelity_validator`: structural drift
            cascades into runtime errors (`AttributeError: 'Scenario' has
            no attribute 'X'`). Catching it via cheap regex saves an LLM
            call AND gives the GVR loop a more specific repair message.
            """
            import json
            import re as _re

            spec_path = ctx.workspace.path / "mechanism_spec.json"
            if not spec_path.exists():
                return ValidationOutcome(ok=True)
            try:
                spec = json.loads(spec_path.read_text(encoding="utf-8"))
            except Exception:
                return ValidationOutcome(ok=True)

            code_files = ctx.workspace.read_model_files()
            issues: list[str] = []

            # scenario.py: every scenario_param must be declared as self.X
            scenario_src = code_files.get("core/scenario.py", "")
            if scenario_src.strip():
                for p in spec.get("scenario_params", []) or []:
                    name = p.get("name", "")
                    if not name:
                        continue
                    if not _re.search(rf"\bself\.{_re.escape(name)}\b", scenario_src):
                        issues.append(
                            f"scenario.py: missing declaration `self.{name}`. "
                            f"mechanism_spec.json declares it as a scenario_param "
                            f"(unit={p.get('unit', '?')}, default={p.get('default', '?')}); "
                            f"add `self.{name} = <default>` in Scenario.setup()."
                        )

            # agent.py: every agent_state_var must appear as self.X
            agent_src = code_files.get("core/agent.py", "")
            if agent_src.strip():
                for v in spec.get("agent_state_vars", []) or []:
                    name = v.get("name", "")
                    if not name:
                        continue
                    if not _re.search(rf"\bself\.{_re.escape(name)}\b", agent_src):
                        issues.append(
                            f"agent.py: missing state variable `self.{name}`. "
                            f"mechanism_spec.json declares it as an agent_state_var "
                            f"(type={v.get('type', '?')}, init={v.get('init', '?')!r}); "
                            f"initialize it in Agent.setup()."
                        )

            # Grid/Network contradiction check — surfaced by 2026-05-30 originate
            # dogfood. When mechanism_spec.json's `topology` is non-null,
            # TemplateGenerator emits model.py with `self.network = create_network()`
            # + `setup_agent_connections(topology=...)`. If agent.py inherits
            # GridAgent, Network.setup_agent_connections raises
            # `AssertionError: isinstance(agent, NetworkAgent)` at sim time.
            # Catch this before Phase 4 with an explicit fix message that
            # routes the LLM back to mechanism_spec.json (set topology=null).
            model_src = code_files.get("core/model.py", "")
            spec_topology = spec.get("topology")
            agent_inherits_grid = bool(
                agent_src and _re.search(r"class\s+\w+\(\s*GridAgent\s*\)", agent_src)
            )
            model_uses_network = bool(
                model_src and (
                    "setup_agent_connections" in model_src
                    or "create_network" in model_src
                )
            )
            if agent_inherits_grid and model_uses_network:
                spec_topo_type = (
                    spec_topology.get("type")
                    if isinstance(spec_topology, dict) else None
                )
                issues.append(
                    f"Grid/Network contradiction: agent.py inherits GridAgent but "
                    f"model.py wires a Network topology "
                    f"(`{spec_topo_type or 'unknown'}`). The Network's add_agent "
                    f"asserts `isinstance(agent, NetworkAgent)`, which will "
                    f"crash at Phase 4. **Fix in mechanism_spec.json**: set "
                    f"`\"topology\": null` for Grid / spatial / no-topology "
                    f"models. TemplateGenerator will then emit a model.py "
                    f"without Network setup, and CoderAgent owns Grid "
                    f"placement inside agent.py / environment.py."
                )

            if not issues:
                return ValidationOutcome(ok=True)
            return ValidationOutcome(
                ok=False,
                reasons=issues,
                severity="fatal",   # structural mismatches cause runtime AttributeError
                structured={"issue_count": len(issues)},
            )

        def _targets_alignment_validator(_ignored) -> ValidationOutcome:
            """Verify LLM env.py sets every templated DataCollector attribute.

            When Layer 3 fires, mechanism_spec.json declares `targets` and
            TemplateGenerator emits a DataCollector that registers them as
            environment properties. The LLM-written environment.py MUST
            set `self.<target>` each tick or DataCollector reads None/0
            and downstream calibration silently receives zeros.

            Without this gate, the 2026-05-29 dogfood hit exactly that:
            spec said `count_s/i/r`, env.py used `susceptible/infected/
            resistant`, sanity-check fired "constant column", 4 GVR
            cycles tried to repair, pipeline exited 1.

            Scan is simple: regex for `self.<target>` assignment patterns
            in core/environment.py. Misses (e.g. tuple unpacking) are
            acceptable false negatives — dry_run + downstream sanity
            checks still backstop. Goal: catch the obvious
            spec-vs-implementation drift up front with a clear reason.
            """
            import json
            import re as _re

            spec_path = ctx.workspace.path / "mechanism_spec.json"
            if not spec_path.exists():
                return ValidationOutcome(ok=True)
            try:
                spec = json.loads(spec_path.read_text(encoding="utf-8"))
            except Exception:
                return ValidationOutcome(ok=True)
            targets: list = spec.get("targets") or []
            if not targets:
                return ValidationOutcome(ok=True)

            code_files = ctx.workspace.read_model_files()
            env_src = code_files.get("core/environment.py", "")
            if not env_src.strip():
                return ValidationOutcome(ok=True)

            missing = []
            for target in targets:
                # Match either `self.<target> =` or `self.<target>:` (typed)
                pattern = _re.compile(rf"\bself\.{_re.escape(target)}\s*[:=]")
                if not pattern.search(env_src):
                    missing.append(target)

            if not missing:
                return ValidationOutcome(ok=True)
            reasons = [
                f"core/environment.py does not assign `self.{name}` anywhere. "
                f"The templated DataCollector registers `{name}` as an "
                f"environment property and reads it each tick — without the "
                f"assignment, DataCollector writes empty / zero values to the "
                f"output CSV. Add `self.{name} = ...` updates inside the env "
                f"step() method."
                for name in missing
            ]
            return ValidationOutcome(
                ok=False,
                reasons=reasons,
                severity="fatal",   # silent zero-trajectory is worse than a halt
                structured={"missing_targets": missing},
            )

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
            ("anti_pattern", _anti_pattern_validator),               # static regex, cheap
            ("structural_fidelity", _structural_fidelity_validator),  # spec vs scenario.py / agent.py
            ("targets_alignment", _targets_alignment_validator),     # spec vs environment.py
            ("dry_run", _dry_run_validator),
            ("contract", _contract_validator),
            ("fidelity", _fidelity_validator),                       # LLM-judge, last
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


def _try_run_template_generator(ctx: PipelineContext) -> bool:
    """Emit the 5 template files when mechanism_spec.json is available + valid.

    Returns True when templates were written (=> CoderAgent's outputs for
    these files should be reverted after Stage B). Returns False when no
    JSON spec exists or it's invalid (=> legacy whole-file codegen).
    """
    json_path = ctx.workspace.path / "mechanism_spec.json"
    if not json_path.exists():
        return False
    try:
        spec = MechanismSpec.from_json(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        console.print(
            f"  [yellow]⚠ mechanism_spec.json failed to load ({e}); "
            f"falling back to legacy codegen[/yellow]"
        )
        return False

    errors = spec.validate()
    if errors:
        console.print(
            f"  [yellow]⚠ mechanism_spec.json invalid ({len(errors)} errors); "
            f"falling back to legacy codegen[/yellow]"
        )
        for e in errors[:5]:
            console.print(f"      [yellow]· {e}[/yellow]")
        return False

    files = generate_all(spec)
    model_dir = ctx.workspace.model_dir
    for rel, content in files.items():
        target = model_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    console.print(
        f"  [green]✓ TemplateGenerator wrote {len(files)} files "
        f"(LLM does NOT touch these): {', '.join(TEMPLATE_FILES)}[/green]"
    )
    # Audit
    try:
        ctx.workspace.audit.info(
            phase="Phase 2 (TemplateGenerator)",
            text=f"TemplateGenerator emitted {len(files)} boilerplate files from mechanism_spec.json",
            actor="TemplateGenerator",
            structured={"files": list(files.keys())},
        )
    except Exception:
        pass
    return True


def _revert_template_files(ctx: PipelineContext) -> None:
    """Re-emit template files after CoderAgent runs.

    CoderAgent may have edited / rewritten the template-owned files
    even when told not to (LLMs ignore directives sometimes). Running
    the generator again is idempotent — restores the deterministic
    contents. Cheap (~milliseconds; all string ops).
    """
    json_path = ctx.workspace.path / "mechanism_spec.json"
    if not json_path.exists():
        return
    try:
        spec = MechanismSpec.from_json(json_path.read_text(encoding="utf-8"))
    except Exception:
        return
    files = generate_all(spec)
    model_dir = ctx.workspace.model_dir
    overwrote = 0
    for rel, content in files.items():
        target = model_dir / rel
        if target.exists():
            existing = target.read_text(encoding="utf-8")
            if existing != content:
                overwrote += 1
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    if overwrote:
        console.print(
            f"  [dim]TemplateGenerator restored {overwrote} file(s) that "
            f"CoderAgent had edited[/dim]"
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
