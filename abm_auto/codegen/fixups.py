"""Codegen post-LLM fixups — file-level corrections applied to raw LLM output.

CoderAgent's `run()` used to inline 4+ post-hoc fixup methods between the
LLM call and the workspace write. That made CoderAgent a god class: each
new failure mode observed in dogfoods added another inline method, with
no test surface per fixup and no way to reuse fixups outside CoderAgent.

This module restructures the fixups as the same Phase-adapter pattern
Pipeline uses (commit 6d195c1):

    files = coder.generate_raw()   # LLM call returns dict[path, content]
    for fixup in DEFAULT_FIXUPS:
        if fixup.should_run(files):
            files = fixup.run(files)
    workspace.write_model_files(files)

Each fixup is a pure function over `dict[path, content]`: deterministic,
no LLM, no workspace state, independently testable. Adding a fixup =
one new class here + one line in `DEFAULT_FIXUPS`.

Fixups that ARE NOT here (and why):
  - `_extract_fallback` — runs only when the file-parser returns empty;
    not a transformation, an alternate parse path. Stays on CoderAgent.
  - `_check_attribute_completeness` + `_complete_missing_attributes` —
    requires `design` (workspace state) AND a follow-up LLM call. Stays
    on CoderAgent.
  - `_validate_syntax` — soft check that only LOGS, doesn't transform.
    Stays as a CoderAgent post-step (it's not really a fixup).
"""
from __future__ import annotations

import re
from typing import Protocol

from rich.console import Console

console = Console()


class CodegenFixup(Protocol):
    """One post-LLM transformation over the generated file map.

    Mirrors `Phase` (abm_auto.pipeline.phase) — same shape, different scope.
    """

    name: str

    def should_run(self, files: dict[str, str]) -> bool:
        """True if this fixup applies to the current file set."""
        ...

    def run(self, files: dict[str, str]) -> dict[str, str]:
        """Return a (possibly modified) file map."""
        ...


class ConfigPathsFixup:
    """Force main.py's Config(input_folder=..., output_folder=...) to the
    canonical `data/input` / `data/output` paths.

    LLM frequently writes non-standard paths (`input`, `output`, `config`,
    `input_data`). Executor expects standardized layout to find scenario
    CSV + write result CSV.
    """

    name = "config_paths"

    def should_run(self, files: dict[str, str]) -> bool:
        return "main.py" in files

    def run(self, files: dict[str, str]) -> dict[str, str]:
        main = files["main.py"]
        # Fix non-standard input_folder paths
        main = re.sub(
            r'input_folder\s*=\s*["\'](?!data/input)[^"\']+["\']',
            'input_folder="data/input"',
            main,
        )
        # Fix non-standard output_folder paths
        main = re.sub(
            r'output_folder\s*=\s*["\'](?!data/output)[^"\']+["\']',
            'output_folder="data/output"',
            main,
        )
        files["main.py"] = main
        return files


class CsvLocationFixup:
    """Move SimulatorScenarios.csv into the canonical `data/input/` location.

    LLM sometimes places it under `input/`, `scenarios/`, or directly at
    the top-level. Executor reads from `data/input/` — move it there.
    """

    name = "csv_location"

    def should_run(self, files: dict[str, str]) -> bool:
        return any(
            key.endswith("SimulatorScenarios.csv")
            and key != "data/input/SimulatorScenarios.csv"
            for key in files
        )

    def run(self, files: dict[str, str]) -> dict[str, str]:
        wrong_key = next(
            (k for k in list(files.keys())
             if k.endswith("SimulatorScenarios.csv")
             and k != "data/input/SimulatorScenarios.csv"),
            None,
        )
        if wrong_key is not None:
            files["data/input/SimulatorScenarios.csv"] = files.pop(wrong_key)
            console.print(
                f"  [yellow]⚠ Moved {wrong_key} → data/input/SimulatorScenarios.csv[/yellow]"
            )
        return files


class GridCategoryInjectionFixup:
    """Inject `set_category(self)` into every GridAgent subclass that lacks it.

    MyMoMo Runtime's GridAgent raises NotImplementedError if `set_category()`
    is absent. LLM frequently forgets. Detect class definition pattern + inject
    a minimal `self.category = 0` implementation right before the first
    `def setup(self):` in the class body.
    """

    name = "grid_category_injection"

    def should_run(self, files: dict[str, str]) -> bool:
        return any(
            "GridAgent" in content
            and re.search(r"class\s+\w+\(GridAgent\)", content)
            and "set_category" not in content
            for path, content in files.items()
            if path.endswith(".py")
        )

    def run(self, files: dict[str, str]) -> dict[str, str]:
        for path, content in list(files.items()):
            if not path.endswith(".py"):
                continue
            if "GridAgent" not in content:
                continue
            if not re.search(r"class\s+\w+\(GridAgent\)", content):
                continue
            if "set_category" in content:
                continue
            lines = content.split("\n")
            new_lines: list[str] = []
            injected = False
            for i, line in enumerate(lines):
                new_lines.append(line)
                # Inject right before first `def setup(self):` so subclass
                # has the required method co-located with its other lifecycle.
                if not injected and "def setup(self):" in line and i > 0:
                    indent = len(line) - len(line.lstrip())
                    ind = " " * indent
                    new_lines.insert(-1, f"{ind}def set_category(self):")
                    new_lines.insert(-1, f"{ind}    self.category = 0")
                    new_lines.insert(-1, "")
                    injected = True
            if injected:
                files[path] = "\n".join(new_lines)
                console.print(f"  [dim]Auto-injected set_category() into {path}[/dim]")
        return files


class SyntaxValidationFixup:
    """Soft check — log Python files that don't parse, return files unchanged.

    Not a transformation in the strict sense; this is the post-fixup hook
    that surfaces parse errors before they bite at dry_run time. Kept here
    for symmetry with the rest of the fixup pipeline (a "linting" step in
    the same protocol shape).
    """

    name = "syntax_validation"

    def should_run(self, files: dict[str, str]) -> bool:
        return bool(files)

    def run(self, files: dict[str, str]) -> dict[str, str]:
        from abm_auto.agents.code_manager import validate_syntax as _validate
        for err in _validate(files):
            console.print(f"  [yellow]⚠ {err}[/yellow]")
        return files


# ── Default pipeline ─────────────────────────────────────────────────────


DEFAULT_FIXUPS: list[CodegenFixup] = [
    ConfigPathsFixup(),
    CsvLocationFixup(),
    GridCategoryInjectionFixup(),
    SyntaxValidationFixup(),
]


# ── Stateful fixups (need workspace + LLM) ──────────────────────────────


class CompletenessCheckFixup:
    """Re-call the LLM to complete agent.py if attributes from DESIGN.md are missing.

    Closes the second half of CoderAgent's god-class decomposition.
    Unlike the four pure fixups above, this one needs the design document
    (workspace state) and the LLM (to re-generate). Constructed at codegen
    time via `make_completeness_fixup(workspace, llm_caller)`.

    The check is a regex scan over DESIGN.md for agent-attribute mentions,
    cross-checked against agent.py contents. Missing attrs trigger a
    focused single-file regeneration prompt that asks the LLM to emit
    the COMPLETE corrected file.

    Heuristic, conservative: false positives (claiming an attr is missing
    when it isn't) are OK — the LLM is asked to "emit the complete file
    with all attrs initialized" and will preserve what's already there.
    False negatives (missing an actual missing attr) are also OK — the
    downstream dry_run / contract / fidelity validators backstop.
    """

    name = "completeness_check"

    def __init__(self, workspace, llm_caller):
        """
        Args:
            workspace: provides read_design()
            llm_caller: callable matching `BaseAgent.call_llm(system, user, max_tokens)`
                — typically `coder_agent.call_llm` bound method.
        """
        self.workspace = workspace
        self.llm_caller = llm_caller

    def should_run(self, files: dict[str, str]) -> bool:
        design = self.workspace.read_design()
        if not design:
            return False
        agent_file = self._agent_file_key(files)
        if agent_file is None:
            return False
        return bool(self._detect_missing(files[agent_file], design))

    def run(self, files: dict[str, str]) -> dict[str, str]:
        import ast
        from rich.console import Console as _Console
        _console = _Console()

        design = self.workspace.read_design()
        agent_file = self._agent_file_key(files)
        if agent_file is None:
            return files
        missing = self._detect_missing(files[agent_file], design)
        if not missing:
            return files

        _console.print(
            f"  [yellow]⚠ Missing attributes in {agent_file}: {missing}[/yellow]"
        )
        system = (
            "You are an expert Python developer. The following agent code is "
            "INCOMPLETE — it is missing attributes that were specified in the "
            "design document. Output the COMPLETE, corrected file. Output ONLY "
            "the Python code, no explanation."
        )
        user = (
            f"## Design Document (relevant section)\n\n{design[:3000]}\n\n"
            f"## Current {agent_file} (INCOMPLETE)\n\n```python\n{files[agent_file]}\n```\n\n"
            f"## Missing attributes\n\nThe following attributes are missing: {missing}\n\n"
            f"Generate the COMPLETE corrected {agent_file} with ALL attributes initialized "
            f"in setup(). Use getattr(self, 'attr', default) pattern for CSV-loaded attributes."
        )
        try:
            raw = self.llm_caller(system, user, max_tokens=4096)
            code = raw.strip()
            if code.startswith("```"):
                code = code.split("\n", 1)[-1].rsplit("```", 1)[0]
            ast.parse(code)   # validate it parses before swap
            files[agent_file] = code
            _console.print(f"  [green]✓ {agent_file} completed with missing attributes[/green]")
        except (SyntaxError, Exception) as e:
            _console.print(f"  [red]✗ Could not complete {agent_file}: {e}[/red]")
        return files

    @staticmethod
    def _agent_file_key(files: dict[str, str]) -> str | None:
        for key in files:
            if "agent.py" in key:
                return key
        return None

    @staticmethod
    def _detect_missing(agent_code: str, design: str) -> list[str]:
        """Regex-scan DESIGN.md for agent-attribute mentions; return any
        absent from agent_code.

        Logic moved verbatim from CoderAgent._check_attribute_completeness
        (commit 22c5298 and earlier). Heuristic — false positives expected;
        the LLM's "emit complete file" prompt handles them gracefully.
        """
        attr_pattern = re.compile(
            r"[-*]\s+\*{0,2}(\w+)\*{0,2}\s*(?:\(|:|\s*—|\s*–|\s*-)",
        )
        design_attrs: set[str] = set()
        in_agent_section = False
        for line in design.split("\n"):
            lower = line.lower().strip()
            if "agent" in lower and ("attribute" in lower or "propert" in lower or "state" in lower):
                in_agent_section = True
                continue
            if in_agent_section and line.startswith("#"):
                in_agent_section = False
            if in_agent_section:
                m = attr_pattern.match(line.strip())
                if m:
                    attr = m.group(1)
                    if attr not in {"the", "each", "all", "type", "int", "float",
                                    "str", "bool", "list", "dict", "note"}:
                        design_attrs.add(attr)
        return [a for a in design_attrs if a not in agent_code]


def make_default_pipeline(workspace=None, llm_caller=None) -> list[CodegenFixup]:
    """Construct the standard fixup pipeline.

    When `workspace + llm_caller` provided, includes the stateful
    `CompletenessCheckFixup` at the end. When omitted, returns only the
    pure fixups — useful for tests + external consumers that don't have
    LLM access.
    """
    pipeline: list[CodegenFixup] = list(DEFAULT_FIXUPS)
    if workspace is not None and llm_caller is not None:
        pipeline.append(CompletenessCheckFixup(workspace, llm_caller))
    return pipeline


def apply_fixup_pipeline(
    files: dict[str, str],
    fixups: list[CodegenFixup] = DEFAULT_FIXUPS,
) -> dict[str, str]:
    """Walk fixups in order. Each runs only if should_run returns True."""
    for fixup in fixups:
        if fixup.should_run(files):
            files = fixup.run(files)
    return files


__all__ = [
    "CodegenFixup",
    "ConfigPathsFixup",
    "CsvLocationFixup",
    "GridCategoryInjectionFixup",
    "SyntaxValidationFixup",
    "CompletenessCheckFixup",
    "DEFAULT_FIXUPS",
    "make_default_pipeline",
    "apply_fixup_pipeline",
]
