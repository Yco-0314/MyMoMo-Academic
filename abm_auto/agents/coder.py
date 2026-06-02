from __future__ import annotations
import re

from rich.console import Console

from abm_auto.agents.base import BaseAgent
from abm_auto.agents.code_manager import parse_code_blocks as _parse_code_blocks
from abm_auto.codegen.fixups import apply_fixup_pipeline, make_default_pipeline
from abm_auto.config import TEMPLATES_DIR

console = Console()


def _load_templates_context() -> str:
    """Load simulator template files as reference context."""
    parts = []
    for template_name in ("simulator", "simulator_grid"):
        template_dir = TEMPLATES_DIR / template_name
        if not template_dir.exists():
            continue
        for f in sorted(template_dir.rglob("*.py")):
            rel = f.relative_to(template_dir)
            parts.append(f"=== TEMPLATE ({template_name}): {rel} ===\n{f.read_text()}")
    return "\n\n".join(parts)


class CoderAgent(BaseAgent):
    """Converts DESIGN.md → executable Python files."""

    def run(
        self,
        extra_feedback: str | None = None,
        memory_context: str = "",
    ) -> dict[str, str]:
        """Generate Python files from DESIGN.md.

        Args:
            extra_feedback: Optional refinement feedback from a previous failed
                            codegen attempt (used by the CoderVerifier GVR loop
                            when schema-contract violations or runtime errors
                            require re-generation).
            memory_context: Optional formatted markdown of semantic + episodic
                            memory (anti-patterns observed in past runs,
                            successful patterns). When non-empty, prepended to
                            the prompt as a "lessons from past runs" block.
                            Mirrors OptimizerAgent's existing memory_context
                            wiring — closes the read side of the memory
                            feedback loop (ADR-006 OQ#4).
        """
        console.print("[bold cyan]Phase 2: Generating Python code...[/bold cyan]")

        design = self.workspace.read_design()
        if not design:
            raise ValueError("DESIGN.md is empty or missing.")

        templates_ctx = _load_templates_context()
        knowledge_ctx = self._load_knowledge_context()
        prompt = self.load_prompt("phase2_code")
        contract_block = self._build_calibration_contract_block()

        system = (
            "You are an expert ABM Engineer. "
            "Generate all required Python files for an ABM simulation using the ABM Auto Runtime. "
            "All imports MUST use `from abm_auto.runtime import ...` — never `from Melodie import ...`. "
            "Output each file using the format:\n"
            "=== FILE: <relative_path> ===\n<content>\n\n"
            "Required files: core/agent.py, core/model.py, core/environment.py, "
            "core/scenario.py, core/data_collector.py, main.py, "
            "data/input/SimulatorScenarios.csv\n\n"
            "CRITICAL: In main.py Config(), ALWAYS use exactly "
            'input_folder="data/input" and output_folder="data/output". '
            "Do NOT use any other paths like 'input', 'output', 'config', or 'input_data'."
        )
        # GVR refinement feedback (only on retry attempts) — placed at top
        # so LLM reads "fix these schema/runtime issues" before the brief.
        feedback_block = ""
        if extra_feedback:
            feedback_block = (
                "## ⚠ Refinement Feedback (from previous codegen attempt)\n\n"
                "Your previous code was rejected. Address ALL of these issues:\n\n"
                f"{extra_feedback}\n\n"
                "---\n\n"
            )
            console.print("  [yellow]Using GVR feedback from previous attempt[/yellow]")

        # Cross-session memory context (semantic anti-patterns + episodic
        # lessons accumulated by ExperimentMemory across past runs). Mirror
        # of OptimizerAgent's memory_context wiring. The Pipeline passes
        # `ctx.memory.retrieve_context()` so the CoderAgent finally LEARNS
        # from prior codegen failures across runs — instead of repeating
        # the same hallucination patterns each session (ADR-006 OQ#4).
        memory_block = ""
        if memory_context.strip():
            memory_block = (
                "## Cross-session memory — lessons from past runs\n\n"
                "Patterns and anti-patterns the system has accumulated. Treat\n"
                "as informational — apply only when relevant to this design.\n\n"
                f"{memory_context}\n\n"
                "---\n\n"
            )

        # Mechanism Spec — the HARD CONTRACT from Phase 1d (if present).
        # Placed ABOVE DESIGN.md in the prompt so the LLM reads "implement
        # THIS pseudocode" before reading the free-form English design.
        # If both disagree, the spec wins (it was extracted FROM design to
        # remove ambiguity).
        mechanism_spec = self.workspace.read_mechanism_spec()
        spec_block = ""
        if mechanism_spec:
            spec_block = (
                "---\n\n"
                "## ⚠ MECHANISM SPECIFICATION — HARD CONTRACT ⚠\n\n"
                "Implement the algorithm below LITERALLY. This pseudocode was "
                "extracted from DESIGN.md specifically to remove implementation "
                "ambiguity. If anything in DESIGN.md (further below) appears to "
                "contradict this spec, **the spec wins** — DESIGN.md is for "
                "context and architecture, the spec is for algorithm.\n\n"
                f"{mechanism_spec}\n\n"
            )

        # Templated targets — when Layer 3 ran, the DataCollector was emitted
        # by TemplateGenerator and registers a specific set of environment
        # attributes (from `mechanism_spec.json[targets]`). The LLM-written
        # environment.py MUST set those exact attribute names each tick or
        # DataCollector collects zeros silently.
        #
        # Without this block: the 2026-05-29 dogfood saw LLM pick
        # `targets: [count_s, count_i, count_r]` in Stage-2 JSON but separately
        # write env.py using `self.susceptible / .infected / .resistant`.
        # Mismatch → DataCollector reads count_* (doesn't exist) → all zeros →
        # sanity-check fired → 4 GVR retries → pipeline exited 1.
        targets_block = self._build_templated_targets_block()

        user = (
            f"{feedback_block}"
            f"{memory_block}"
            f"{prompt}\n\n"
            f"{contract_block}"
            f"{targets_block}"
            f"{spec_block}"
            f"---\n\n## DESIGN.md\n\n{design}\n\n"
            f"---\n\n## Template Reference\n\n{templates_ctx}\n\n"
            f"---\n\n## Runtime Knowledge Reference\n\n{knowledge_ctx}"
        )

        # Estimate complexity: count agent types and attributes in design
        max_tokens = self._estimate_code_tokens(design)
        raw = self.call_llm(system, user, max_tokens=max_tokens)
        files = _parse_code_blocks(raw)

        if not files:
            # Fallback: try to extract any python blocks
            console.print("  [yellow]⚠ Could not parse file blocks, attempting raw extraction[/yellow]")
            files = self._extract_fallback(raw)

        # Post-generation fixups — each is an independent CodegenFixup adapter
        # in abm_auto.codegen.fixups. Order matters (e.g. CSV placement fixes
        # the filesystem layout before subsequent fixups depend on it).
        # The stateful CompletenessCheckFixup (last in the pipeline) needs
        # workspace + LLM access to re-call the model if agent.py is missing
        # attributes declared in DESIGN.md.
        pipeline = make_default_pipeline(
            workspace=self.workspace,
            llm_caller=self.call_llm,
        )
        files = apply_fixup_pipeline(files, fixups=pipeline)

        self.workspace.write_model_files(files)
        console.print(f"  [green]✓ {len(files)} files generated[/green]")

        # Audit: log generated file inventory
        try:
            total_lines = sum(len(c.splitlines()) for c in files.values())
            self.workspace.audit.info(
                phase="Phase 2",
                text=f"Generated {len(files)} files ({total_lines} lines total)",
                actor="CoderAgent",
                structured={
                    "n_files": len(files),
                    "total_lines": total_lines,
                    "file_names": list(files.keys()),
                },
            )
        except Exception:
            pass

        return files

    def _build_templated_targets_block(self) -> str:
        """Force LLM env.py to match the targets the templated DataCollector
        registers.

        When Layer 3 fires, TemplateGenerator emits a `data_collector.py` that
        registers exactly `mechanism_spec.json[targets]` as environment
        properties. Returns a hard-contract prompt block listing those names.
        The LLM's env.py MUST set `self.<name> = ...` on each tick for each
        target — otherwise DataCollector reads None/0 and downstream calibration
        gets a zero-trajectory.

        Without this block, the LLM picks attribute names independently of the
        Stage-2 JSON and silently mismatches (see 2026-05-29 dogfood log
        commit fd61d70).

        Returns empty string when mechanism_spec.json is absent (legacy
        whole-file codegen path; CoderAgent owns DataCollector and naming is
        self-consistent by construction).
        """
        import json
        spec_path = self.workspace.path / "mechanism_spec.json"
        if not spec_path.exists():
            return ""
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except Exception:
            return ""
        targets: list = spec.get("targets") or []
        if not targets:
            return ""
        env_class = spec.get("environment_class_name", "Environment")
        lines = "\n".join(f"        self.{t} = ...    # YOUR per-tick calculation here" for t in targets)
        return (
            "---\n\n"
            "## ⚠ TEMPLATED DATA COLLECTOR — ENVIRONMENT ATTRIBUTE CONTRACT ⚠\n\n"
            "The DataCollector is template-generated and registers EXACTLY these "
            f"environment attributes: `{', '.join(targets)}`.\n\n"
            f"Your `{env_class}.step(agents, network, scenario)` method MUST set "
            f"`self.<name>` for EVERY target listed above, on EVERY tick. Use these "
            "EXACT attribute names — no aliases (`infected` ≠ `count_i`), no "
            "alternate spellings. The DataCollector reads these by name and writes "
            "them to the output CSV; missing or misnamed → zeros in output → "
            "downstream calibration receives garbage.\n\n"
            f"Inside `{env_class}.step()` you must end with assignments equivalent to:\n\n"
            "```python\n"
            f"    def step(self, agents, network, scenario):\n"
            "        # ... your mechanism logic ...\n"
            "        # Required updates (data_collector reads these):\n"
            f"{lines}\n"
            "```\n\n"
        )

    def _build_calibration_contract_block(self) -> str:
        """Read calibration param SPECS from research_spec.json and render as a hard contract.

        Includes name + range + unit so the LLM uses the right scale.
        Without unit info, the LLM tends to convert "4.4 percent" → 0.044
        (probability) and the calibrator's prior bounds end up 100× off truth.
        """
        import json
        spec_path = self.workspace.path / "research_spec.json"
        if not spec_path.exists():
            return ""
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except Exception:
            return ""
        param_specs: list = spec.get("calibration_param_specs") or []
        params: list = spec.get("calibration_params") or []
        if not param_specs and not params:
            return ""

        # Build the contract table. Prefer rich specs; fall back to name-only.
        if param_specs:
            rows = []
            for s in param_specs:
                name = s.get("name", "?")
                lo = s.get("min", "?")
                hi = s.get("max", "?")
                unit = s.get("unit", "(unspecified)")
                rows.append(f"| `{name}` | {lo} – {hi} | {unit} |")
            contract_table = (
                "| Param name (EXACT) | Range | Unit (CRITICAL — use this scale verbatim) |\n"
                "|---|---|---|\n"
                + "\n".join(rows)
            )
            unit_warning = (
                "\n\n**UNIT DISCIPLINE — DO NOT CONVERT SCALES**:\n"
                "- If unit is `percent`, store the value as the PERCENTAGE (e.g. 4.4 for 4.4%), "
                "  NOT as probability 0.044. Inside agent code, divide by 100 only at the moment "
                "  of use: `if random.random() < self.scenario.virus_spread_chance / 100.0: ...`\n"
                "- If unit is `probability` or `rate`, store as the raw probability (0.0–1.0).\n"
                "- Default value in SimulatorScenarios.csv MUST be in the declared range and unit, "
                "  not auto-converted to a different scale.\n"
                "- The downstream BayesianCalibrator uses the declared `min`/`max` to build priors. "
                "  If your CSV value is on a different scale than declared, calibration will "
                "  estimate values in the WRONG scale and the pipeline will report nonsense."
            )
        else:
            # Legacy fallback when LLM didn't provide structured specs
            contract_table = "\n".join(f"  - `{p}`" for p in params)
            unit_warning = ""

        return (
            "---\n\n"
            "## ⚠⚠⚠ CALIBRATION CONTRACT (HARD CONSTRAINT) ⚠⚠⚠\n\n"
            "The downstream BayesianCalibrator will tune these parameters. "
            "Your generated code MUST expose them with the EXACT names, ranges, AND units below:\n\n"
            f"{contract_table}"
            f"{unit_warning}\n\n"
            "**Required to satisfy this contract**:\n"
            "1. `data/input/SimulatorScenarios.csv` MUST contain a column with each EXACT name above, "
            "with a default value IN the declared range and unit.\n"
            "2. `core/scenario.py` `Scenario.setup()` MUST declare each as an attribute with the same name.\n"
            "3. Each agent / environment method that uses these parameters MUST read them as "
            "`self.scenario.<name>` using the EXACT name above.\n"
            "4. You MAY add additional structural parameters (e.g. `agent_num`, `periods`, `seed`). "
            "Those are NOT calibration params — keep them separate.\n\n"
            "If you violate this contract:\n"
            "- Wrong NAME → BayesianCalibrator reports `missing` for that param.\n"
            "- Wrong SCALE/UNIT → BayesianCalibrator returns estimates in the wrong scale (silent failure).\n\n"
        )

    def _load_knowledge_context(self) -> str:
        """Inject MyMoMo Knowledge Base files into LLM context for code generation.

        Loads the API canon + the anti-patterns catalogue. The API canon
        tells the LLM what classes/methods exist; the anti-patterns
        catalogue directly addresses the most-frequent codegen mistakes
        observed during the SIR-on-network calibration benchmark runs.
        """
        parts = []
        for name in ("01-runtime-api", "05-anti-patterns"):
            try:
                content = self.load_knowledge(name)
                parts.append(f"=== MyMoMo Knowledge: {name}.md ===\n{content}")
            except FileNotFoundError:
                pass
        return "\n\n".join(parts)

    def apply_params(self, new_params: dict) -> None:
        """Update SimulatorScenarios.csv with new parameter values, preserving int types."""
        import pandas as pd
        import numpy as np

        csv_path = self.workspace.model_dir / "data" / "input" / "SimulatorScenarios.csv"
        if not csv_path.exists():
            console.print("  [yellow]⚠ SimulatorScenarios.csv not found, skipping param update[/yellow]")
            return

        df = pd.read_csv(csv_path)
        for key, value in new_params.items():
            if key in df.columns:
                # Preserve int types: if original column is int, cast value to int
                if pd.api.types.is_integer_dtype(df[key]):
                    df[key] = int(round(value))
                else:
                    df[key] = value
        df.to_csv(csv_path, index=False)
        console.print(f"  [green]✓ Parameters updated: {new_params}[/green]")

    @staticmethod
    def _estimate_code_tokens(design: str) -> int:
        """Estimate max_tokens needed based on model complexity."""
        # Count agent types (## Agent sections)
        agent_sections = len(re.findall(r"(?i)#+\s+.*agent", design))
        # Count attribute lines (- **attr** or - attr:)
        attribute_lines = len(re.findall(r"^\s*[-*]\s+\*{0,2}\w+\*{0,2}\s*(?:\(|:)", design, re.MULTILINE))
        # Heuristic: base 8192 + 1024 per extra agent type + 128 per extra attribute (beyond 10)
        estimate = 8192
        if agent_sections > 2:
            estimate += (agent_sections - 2) * 1024
        if attribute_lines > 10:
            estimate += (attribute_lines - 10) * 128
        # Cap at 16384
        return min(estimate, 16384)

    def _extract_fallback(self, text: str) -> dict[str, str]:
        """Try to salvage any python code block as main.py."""
        match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
        if match:
            return {"main.py": match.group(1)}
        return {}
