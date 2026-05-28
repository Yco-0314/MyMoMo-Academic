"""Pre-simulation phases: seed injection, sanity check, initial-params record."""
from __future__ import annotations

import json

from rich.console import Console

from abm_auto.agents.sanity_checker import SanityChecker
from abm_auto.pipeline.phase import PipelineContext

console = Console()


class SeedInjectionPhase:
    """Inject `random.seed(...)` + `np.random.seed(...)` into generated main.py."""

    name = "Pre-run: seed injection"

    def should_run(self, ctx: PipelineContext) -> bool:
        return ctx.seed is not None

    def run(self, ctx: PipelineContext) -> None:
        main_py = ctx.workspace.model_dir / "main.py"
        if not main_py.exists():
            return
        content = main_py.read_text(encoding="utf-8")
        seed_block = (
            f"\n# Reproducibility: fixed random seed\n"
            f"import random, numpy as np\n"
            f"random.seed({ctx.seed})\n"
            f"np.random.seed({ctx.seed})\n"
        )
        if "if __name__" in content:
            content = content.replace("if __name__", f"{seed_block}\nif __name__")
        else:
            content = seed_block + content
        main_py.write_text(content, encoding="utf-8")

        meta_path = ctx.workspace.path / "metadata.json"
        meta = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
        meta["seed"] = ctx.seed
        meta_path.write_text(json.dumps(meta, indent=2))
        console.print(f"  [green]✓ Random seed {ctx.seed} injected[/green]")


class PreRunSanityPhase:
    """Run SanityChecker on the model dir + DESIGN.md before any simulation."""

    name = "Pre-run: sanity check"

    def should_run(self, ctx: PipelineContext) -> bool:
        return True

    def run(self, ctx: PipelineContext) -> None:
        pre_warnings = SanityChecker.check_pre_run(
            ctx.workspace.model_dir,
            ctx.workspace.read_design(),
        )
        for w in pre_warnings:
            console.print(f"  [bold yellow]{w}[/bold yellow]")
            ctx.workspace.audit.raise_issue(
                phase="Phase 3 pre-run",
                severity="MEDIUM",
                text=w,
                actor="SanityChecker",
            )


class RecordInitialParamsPhase:
    """Capture run=1 baseline params from SimulatorScenarios.csv into params_history."""

    name = "Pre-run: record initial params"

    def should_run(self, ctx: PipelineContext) -> bool:
        return True

    def run(self, ctx: PipelineContext) -> None:
        import pandas as pd
        csv_path = ctx.workspace.model_dir / "data" / "input" / "SimulatorScenarios.csv"
        if not csv_path.exists():
            return
        try:
            df = pd.read_csv(csv_path)
            if not df.empty:
                row = df.iloc[0].to_dict()
                for col in ("id", "run_num"):
                    row.pop(col, None)
                ctx.workspace.append_params_history(
                    run=1, params=row, hypothesis="Initial parameters"
                )
        except Exception:
            pass
