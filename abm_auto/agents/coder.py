from __future__ import annotations
import ast
import re

from rich.console import Console

from abm_auto.agents.base import BaseAgent
from abm_auto.agents.code_manager import parse_code_blocks as _parse_code_blocks, validate_syntax as _cm_validate_syntax
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

    def run(self) -> dict[str, str]:
        console.print("[bold cyan]Phase 2: Generating Python code...[/bold cyan]")

        design = self.workspace.read_design()
        if not design:
            raise ValueError("DESIGN.md is empty or missing.")

        templates_ctx = _load_templates_context()
        knowledge_ctx = self._load_knowledge_context()
        prompt = self.load_prompt("phase2_code")

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
        user = (
            f"{prompt}\n\n"
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

        # Post-generation fixes
        files = self._fix_config_paths(files)
        files = self._ensure_output_dirs(files)
        files = self._fix_grid_agent_category(files)
        files = self._validate_syntax(files)

        # Completeness check: verify all DESIGN.md agent attributes present
        missing = self._check_attribute_completeness(files, design)
        if missing:
            console.print(f"  [yellow]⚠ Missing attributes detected, requesting completion...[/yellow]")
            files = self._complete_missing_attributes(files, design, missing)

        self.workspace.write_model_files(files)
        console.print(f"  [green]✓ {len(files)} files generated[/green]")
        return files

    def _load_knowledge_context(self) -> str:
        """Inject runtime knowledge files into LLM context for code generation."""
        parts = []
        for name in ("runtime-quickref", "runtime-framework"):
            try:
                content = self.load_knowledge(name)
                parts.append(f"=== KNOWLEDGE: {name}.md ===\n{content}")
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

    def _check_attribute_completeness(
        self, files: dict[str, str], design: str
    ) -> dict[str, list[str]]:
        """Check if generated agent code contains all attributes from DESIGN.md.

        Returns dict mapping file path → list of missing attribute names.
        """
        # Extract attributes from DESIGN.md: lines like "- **attr_name**" or "- attr_name:"
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
                    # Skip common non-attribute words
                    if attr not in {"the", "each", "all", "type", "int", "float", "str", "bool", "list", "dict", "note"}:
                        design_attrs.add(attr)

        if not design_attrs:
            return {}

        # Check agent.py for these attributes
        missing: dict[str, list[str]] = {}
        agent_file = None
        for key in files:
            if "agent.py" in key:
                agent_file = key
                break

        if agent_file:
            agent_code = files[agent_file]
            absent = [a for a in design_attrs if a not in agent_code]
            if absent:
                missing[agent_file] = absent

        return missing

    def _complete_missing_attributes(
        self, files: dict[str, str], design: str, missing: dict[str, list[str]]
    ) -> dict[str, str]:
        """Re-generate files with missing attributes."""
        for filepath, attrs in missing.items():
            console.print(f"  [yellow]  Missing in {filepath}: {attrs}[/yellow]")

            existing_code = files.get(filepath, "")
            system = (
                "You are an expert Python developer. "
                "The following agent code is INCOMPLETE — it is missing attributes "
                "that were specified in the design document. "
                "Output the COMPLETE, corrected file. "
                "Output ONLY the Python code, no explanation."
            )
            user = (
                f"## Design Document (relevant section)\n\n{design[:3000]}\n\n"
                f"## Current {filepath} (INCOMPLETE)\n\n```python\n{existing_code}\n```\n\n"
                f"## Missing attributes\n\nThe following attributes are missing: {attrs}\n\n"
                f"Generate the COMPLETE corrected {filepath} with ALL attributes initialized "
                f"in setup(). Use getattr(self, 'attr', default) pattern for CSV-loaded attributes."
            )
            try:
                raw = self.call_llm(system, user, max_tokens=4096)
                # Extract code from response
                code = raw.strip()
                if code.startswith("```"):
                    code = code.split("\n", 1)[-1].rsplit("```", 1)[0]
                # Validate it parses
                ast.parse(code)
                files[filepath] = code
                console.print(f"  [green]✓ {filepath} completed with missing attributes[/green]")
            except (SyntaxError, Exception) as e:
                console.print(f"  [red]✗ Could not complete {filepath}: {e}[/red]")

        return files

    def _fix_config_paths(self, files: dict[str, str]) -> dict[str, str]:
        """Ensure main.py uses standardized Config paths."""
        if "main.py" not in files:
            return files

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

    def _ensure_output_dirs(self, files: dict[str, str]) -> dict[str, str]:
        """Ensure data/input and data/output directories will exist.

        If SimulatorScenarios.csv was placed under a non-standard key,
        move it to data/input/SimulatorScenarios.csv.
        """
        csv_key = None
        for key in list(files.keys()):
            if key.endswith("SimulatorScenarios.csv"):
                csv_key = key
                break

        if csv_key and csv_key != "data/input/SimulatorScenarios.csv":
            files["data/input/SimulatorScenarios.csv"] = files.pop(csv_key)
            console.print(f"  [yellow]⚠ Moved {csv_key} → data/input/SimulatorScenarios.csv[/yellow]")

        return files

    def _validate_syntax(self, files: dict[str, str]) -> dict[str, str]:
        """Validate Python files parse correctly."""
        for err in _cm_validate_syntax(files):
            console.print(f"  [yellow]⚠ {err}[/yellow]")
        return files

    def _fix_grid_agent_category(self, files: dict[str, str]) -> dict[str, str]:
        """Ensure every GridAgent subclass implements set_category().

        Melodie raises NotImplementedError if set_category() is absent.
        Insert a minimal implementation right after class definition.
        """
        for path, content in files.items():
            if not path.endswith(".py"):
                continue
            if "GridAgent" not in content:
                continue
            # Check if any class inherits GridAgent but lacks set_category
            has_grid_subclass = re.search(r"class\s+\w+\(GridAgent\)", content)
            if not has_grid_subclass:
                continue
            if "set_category" in content:
                continue  # already present
            # Inject set_category into setup() or right after class header
            # Strategy: insert after "def setup(self):" line if it exists
            lines = content.split("\n")
            new_lines = []
            injected = False
            for i, line in enumerate(lines):
                new_lines.append(line)
                # Inject right before first `def setup(self):` in a GridAgent class
                if not injected and "def setup(self):" in line and i > 0:
                    indent = len(line) - len(line.lstrip())
                    ind = " " * indent
                    new_lines.insert(-1, f"{ind}def set_category(self):")
                    new_lines.insert(-1, f"{ind}    self.category = 0")
                    new_lines.insert(-1, f"")
                    injected = True
            if injected:
                files[path] = "\n".join(new_lines)
                console.print(f"  [dim]Auto-injected set_category() into {path}[/dim]")
        return files

    def _extract_fallback(self, text: str) -> dict[str, str]:
        """Try to salvage any python code block as main.py."""
        match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
        if match:
            return {"main.py": match.group(1)}
        return {}
