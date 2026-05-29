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
    "DEFAULT_FIXUPS",
    "apply_fixup_pipeline",
]
