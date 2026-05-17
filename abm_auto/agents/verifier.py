from __future__ import annotations
import re

from rich.console import Console

from abm_auto.agents.base import BaseAgent
from abm_auto.agents.code_manager import parse_code_blocks as _parse_code_blocks
from abm_auto.runner.executor import Executor
from abm_auto.config import DEFAULT_MAX_RETRIES

console = Console()


class VerifierAgent(BaseAgent):
    """Runs model code, catches errors, and asks LLM to fix them."""

    def run(self, executor: Executor, max_retries: int = DEFAULT_MAX_RETRIES) -> bool:
        """Phase 3: import-check loop. Returns True when code imports cleanly."""
        console.print("[bold cyan]Phase 3: Verifying & fixing code...[/bold cyan]")

        for attempt in range(1, max_retries + 1):
            error = executor.dry_run()
            if error is None:
                console.print(f"  [green]✓ Code verified (attempt {attempt})[/green]")
                return True

            console.print(f"  [yellow]✗ Error on attempt {attempt}/{max_retries}:[/yellow] {error[:200]}")

            if attempt == max_retries:
                console.print("  [red]✗ Max retries reached. Could not fix code.[/red]")
                return False

            self.fix(error)

        return False

    def fix_and_rerun(
        self,
        executor: Executor,
        error: str,
        run_number: int,
        max_retries: int = DEFAULT_MAX_RETRIES,
        label: str = "fix",
    ) -> tuple[bool, str]:
        """Public seam: fix the code for a given error then re-run the simulation.

        Replaces the scattered ``self.verifier._fix(err); executor.run(i)`` patterns
        in pipeline.py.  Returns (success, output_or_error).
        """
        for attempt in range(1, max_retries + 1):
            console.print(
                f"  [yellow]✗ {label} attempt {attempt}/{max_retries}:[/yellow] "
                f"{error[:200]}"
            )
            self.fix(error)
            success, output = executor.run(run_number)
            if success:
                return True, output
            error = output  # feed new error into next attempt

        console.print(f"  [red]✗ Could not fix after {max_retries} attempts.[/red]")
        return False, error

    def fix(self, error: str) -> None:
        """Apply one LLM-assisted fix pass to the current model files.

        Previously named ``_fix`` — now public so pipeline can call it
        without breaking encapsulation.
        """
        files = self.workspace.read_model_files()
        # Exclude large data files (e.g., AgentParams.csv with 63K rows) to stay under API limits
        MAX_FILE_SIZE = 5000  # chars
        files_text_parts = []
        for rel, content in files.items():
            if len(content) > MAX_FILE_SIZE:
                # Include only header + truncation note for large files
                lines = content.split("\n")
                truncated = "\n".join(lines[:5]) + f"\n... ({len(lines)} lines total, truncated)"
                files_text_parts.append(f"=== FILE: {rel} ===\n{truncated}")
            else:
                files_text_parts.append(f"=== FILE: {rel} ===\n{content}")
        files_text = "\n\n".join(files_text_parts)

        prompt_template = self.load_prompt("verify_fix")
        prompt = prompt_template.replace("{{ error }}", error).replace("{{ code_files }}", files_text)

        system = (
            "You are an expert Python debugger for ABM simulations using the ABM Auto Runtime. "
            "All imports MUST use `from abm_auto.runtime import ...` — NEVER `from Melodie import ...`. "
            "Return ONLY the fixed files using:\n=== FILE: <path> ===\n<content>\n"
            "Include only files that need changes."
        )

        raw = self.call_llm(system, prompt, max_tokens=6144)
        fixed_files = _parse_code_blocks(raw)

        if fixed_files:
            self.workspace.write_model_files(fixed_files)
            console.print(f"  [dim]Applied fixes to: {list(fixed_files.keys())}[/dim]")

        # Extract and print the FIX explanation (appears before file blocks)
        fix_match = re.search(r"FIX:\s*(.+?)(?:\n|$)", raw)
        if fix_match:
            console.print(f"  [dim]Fix: {fix_match.group(1).strip()}[/dim]")
