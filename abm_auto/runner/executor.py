from __future__ import annotations
import os
import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from abm_auto.runner.workspace import Workspace
from abm_auto.config import DEFAULT_TIMEOUT, PROJECT_ROOT

console = Console()


def _subprocess_env() -> dict:
    """Build subprocess environment with PROJECT_ROOT on PYTHONPATH so
    `from abm_auto.runtime import ...` works inside model subprocesses."""
    env = os.environ.copy()
    project_root_str = str(PROJECT_ROOT)
    existing = env.get("PYTHONPATH", "")
    if project_root_str not in existing.split(os.pathsep):
        env["PYTHONPATH"] = project_root_str + (os.pathsep + existing if existing else "")
    return env


class Executor:
    """Runs an ABM simulation in an isolated subprocess."""

    def __init__(self, workspace: Workspace, timeout: int = DEFAULT_TIMEOUT):
        self.workspace = workspace
        self.timeout = timeout

    def dry_run(self) -> str | None:
        """
        Try importing the model code without running the simulation.
        Returns error string if any, None on success.
        """
        model_dir = self.workspace.model_dir
        if not model_dir.exists():
            return "Model directory does not exist."

        check_script = """
import sys, importlib.util
sys.path.insert(0, '.')
try:
    import core.agent, core.model, core.environment, core.scenario, core.data_collector
    print("IMPORT_OK")
except Exception as e:
    print(f"IMPORT_ERROR: {e}")
"""
        result = subprocess.run(
            [sys.executable, "-c", check_script],
            cwd=str(model_dir),
            env=_subprocess_env(),
            capture_output=True,
            text=True,
            timeout=30,
        )
        combined = (result.stdout + result.stderr).strip()
        if "IMPORT_OK" in combined:
            return None
        return combined or "Unknown import error"

    def run(self, run_number: int) -> tuple[bool, str]:
        """
        Execute main.py in the model directory.
        Copies output CSV files to workspace/results/run_XX/.
        Returns (success, output_or_error).
        """
        model_dir = self.workspace.model_dir
        main_py = model_dir / "main.py"

        if not main_py.exists():
            return False, "main.py not found in model directory"

        console.print(f"  [dim]Running simulation (run #{run_number})...[/dim]")

        try:
            result = subprocess.run(
                [sys.executable, "main.py"],
                cwd=str(model_dir),
                env=_subprocess_env(),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return False, f"Simulation timed out after {self.timeout}s"

        if result.returncode != 0:
            error = (result.stderr or result.stdout or "Unknown error").strip()
            # Persist error log for diagnostics
            run_dir = self.workspace.results_for_run(run_number)
            (run_dir / "error.log").write_text(error, encoding="utf-8")
            return False, error

        # Even on returncode 0, capture stderr warnings for diagnostics
        if result.stderr and result.stderr.strip():
            run_dir = self.workspace.results_for_run(run_number)
            (run_dir / "stderr.log").write_text(result.stderr.strip(), encoding="utf-8")

        # Copy output CSVs to results/run_XX/
        run_dir = self.workspace.results_for_run(run_number)

        # Search multiple possible output locations (LLM sometimes generates
        # non-standard paths like "output/" instead of "data/output/")
        candidate_dirs = [
            model_dir / "data" / "output",
            model_dir / "output",
            model_dir / "data",
        ]

        copied = 0
        for output_dir in candidate_dirs:
            if output_dir.exists():
                for csv_file in output_dir.glob("*.csv"):
                    shutil.copy2(csv_file, run_dir / csv_file.name)
                    copied += 1
            if copied > 0:
                break

        stdout = result.stdout.strip()
        if copied == 0:
            console.print(f"  [yellow]⚠ Run #{run_number} complete but no CSV output found[/yellow]")
        else:
            console.print(f"  [green]✓ Run #{run_number} complete[/green] ({copied} CSV files)")
        return True, stdout

    def get_results_summary(self, run_number: int) -> str:
        """Return a text summary of CSV results for the given run."""
        from abm_auto.analysis.results_reader import describe
        return describe(self.workspace, run_number)
