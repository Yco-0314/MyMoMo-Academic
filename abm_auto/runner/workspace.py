from __future__ import annotations
import uuid
import json
import shutil
from pathlib import Path
from datetime import datetime

from abm_auto.config import WORKSPACE_DIR


class Workspace:
    """Manages the per-session working directory."""

    def __init__(self, path: Path):
        self.path = path
        self.story_path = path / "STORY.md"
        self.lit_notes_path = path / "lit_notes.md"
        self.design_path = path / "DESIGN.md"
        self.model_dir = path / "model"
        self.results_dir = path / "results"
        self.report_path = path / "report.md"
        self.params_history_path = path / "params_history.json"

    @classmethod
    def create(cls, name: str | None = None) -> "Workspace":
        session_id = name or f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        path = WORKSPACE_DIR / session_id
        path.mkdir(parents=True, exist_ok=True)
        (path / "results").mkdir(exist_ok=True)
        return cls(path)

    @classmethod
    def load(cls, path: Path | str) -> "Workspace":
        return cls(Path(path))

    # --- Story / Design ---

    def write_story(self, content: str) -> None:
        self.story_path.write_text(content, encoding="utf-8")

    def read_story(self) -> str:
        return self.story_path.read_text(encoding="utf-8") if self.story_path.exists() else ""

    def write_lit_notes(self, content: str) -> None:
        self.lit_notes_path.write_text(content, encoding="utf-8")

    def read_lit_notes(self) -> str:
        return self.lit_notes_path.read_text(encoding="utf-8") if self.lit_notes_path.exists() else ""

    def write_design(self, content: str) -> None:
        self.design_path.write_text(content, encoding="utf-8")

    def read_design(self) -> str:
        return self.design_path.read_text(encoding="utf-8") if self.design_path.exists() else ""

    # --- Model code files ---

    def write_model_files(self, files: dict[str, str]) -> None:
        """Write generated Python files to the model directory."""
        self.model_dir.mkdir(parents=True, exist_ok=True)
        for rel_path, content in files.items():
            target = self.model_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def read_model_files(self) -> dict[str, str]:
        """Read all text files under model_dir as {rel_path: content}."""
        if not self.model_dir.exists():
            return {}
        skip_suffixes = {".pyc", ".pyo", ".so", ".dll", ".dylib", ".db", ".sqlite"}
        skip_dirs = {"__pycache__", ".git"}
        result = {}
        for f in self.model_dir.rglob("*"):
            if f.is_file() and f.suffix not in skip_suffixes and not any(d in f.parts for d in skip_dirs):
                rel = str(f.relative_to(self.model_dir))
                try:
                    result[rel] = f.read_text(encoding="utf-8")
                except (UnicodeDecodeError, ValueError):
                    continue
        return result

    # --- Results ---

    def results_for_run(self, run_number: int) -> Path:
        p = self.results_dir / f"run_{run_number:02d}"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def list_result_csvs(self, run_number: int) -> list[Path]:
        run_dir = self.results_dir / f"run_{run_number:02d}"
        if not run_dir.exists():
            return []
        return list(run_dir.glob("*.csv"))

    # --- Params history ---

    def append_params_history(self, run: int, params: dict, hypothesis: str = "") -> None:
        history = []
        if self.params_history_path.exists():
            history = json.loads(self.params_history_path.read_text())
        history.append({"run": run, "params": params, "hypothesis": hypothesis})
        self.params_history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False))

    def read_params_history(self) -> list[dict]:
        if not self.params_history_path.exists():
            return []
        return json.loads(self.params_history_path.read_text())

    # --- Dropped scenarios (v2) ---

    def append_dropped_scenario(self, run: int, params: dict, reason: str, action: str = "") -> None:
        """Record a scenario that was tried and discarded, with the reason why.

        Written as a Markdown table row to dropped_scenarios.md for human readability.
        """
        dropped_path = self.path / "dropped_scenarios.md"

        # Write header if file is new
        if not dropped_path.exists():
            dropped_path.write_text(
                "# Dropped Scenarios\n\n"
                "Scenarios that were run but discarded during optimisation, "
                "with the reason each was abandoned.\n\n"
                "| Run | Params | Reason | Action taken |\n"
                "|-----|--------|--------|--------------|\n",
                encoding="utf-8",
            )

        params_str = ", ".join(f"{k}={v}" for k, v in params.items())
        # Truncate long param strings
        if len(params_str) > 80:
            params_str = params_str[:77] + "..."

        with dropped_path.open("a", encoding="utf-8") as f:
            f.write(f"| {run} | {params_str} | {reason} | {action} |\n")

    # --- Report ---

    def write_report(self, content: str) -> None:
        self.report_path.write_text(content, encoding="utf-8")

    # --- ARS Integration: research-output/ package ---

    def package_for_ars(self) -> Path:
        """Package abm-auto outputs into a standardised research-output/ directory
        that ARS academic-paper can consume directly.

        Produces:
          research-output/
            manuscript-context.md  ← report.md + ODD.md (IMRaD body material)
            data-summary.md        ← sensitivity analysis + convergence summary
            simulation-log.md      ← parameter history + iteration insights
            figures/               ← symlink or copy of figures/
        """
        out_dir = self.path / "research-output"
        out_dir.mkdir(exist_ok=True)

        # 1. manuscript-context.md
        parts = []
        if self.report_path.exists():
            parts.append(self.report_path.read_text(encoding="utf-8"))
        odd_path = self.path / "ODD.md"
        if odd_path.exists():
            parts.append("\n\n---\n\n## ODD Protocol\n\n" + odd_path.read_text(encoding="utf-8"))
        if parts:
            (out_dir / "manuscript-context.md").write_text("\n\n".join(parts), encoding="utf-8")

        # 2. data-summary.md
        data_parts = ["# Data Summary\n"]
        for method in ("morris", "sobol"):
            for suffix in ("_interpretation.md", ".json"):
                p = self.path / f"sensitivity_{method}{suffix}"
                if p.exists():
                    data_parts.append(f"## Sensitivity Analysis ({method})\n\n" + p.read_text(encoding="utf-8")[:3000])
                    break
        history = self.read_params_history()
        if history:
            import json as _json
            data_parts.append("## Parameter Evolution\n\n```json\n" + _json.dumps(history, indent=2, ensure_ascii=False) + "\n```")
        if len(data_parts) > 1:
            (out_dir / "data-summary.md").write_text("\n\n".join(data_parts), encoding="utf-8")

        # 3. simulation-log.md
        log_parts = ["# Simulation Log\n"]
        for run_dir in sorted(self.results_dir.glob("run_*")):
            insights_file = run_dir / "insights.md"
            if insights_file.exists():
                log_parts.append(f"## {run_dir.name}\n\n" + insights_file.read_text(encoding="utf-8"))
        if len(log_parts) > 1:
            (out_dir / "simulation-log.md").write_text("\n\n".join(log_parts), encoding="utf-8")

        # 4. figures/ — copy reference (not symlink for portability)
        figures_src = self.path / "figures"
        if figures_src.exists():
            figures_dst = out_dir / "figures"
            figures_dst.mkdir(exist_ok=True)
            import shutil
            for fig in figures_src.glob("*.png"):
                shutil.copy2(fig, figures_dst / fig.name)
            for fig in figures_src.glob("*.pdf"):
                shutil.copy2(fig, figures_dst / fig.name)

        return out_dir

    def __repr__(self) -> str:
        return f"Workspace({self.path})"
