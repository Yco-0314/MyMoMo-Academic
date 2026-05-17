"""
Parallel batch runner for abm-auto.

Runs multiple story.md files concurrently, writes a summary CSV.
Each worker directly instantiates Pipeline (no subprocess chain), so
the executor's model subprocess is the only subprocess layer.

This gives phase-level failure diagnostics in the CSV and avoids
the previous 3-layer hierarchy:
  OLD: ProcessPool → subprocess cli run → subprocess python main.py
  NEW: ProcessPool → Pipeline.run() → subprocess python main.py
"""
from __future__ import annotations

import csv
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from abm_auto.config import WORKSPACE_DIR

console = Console()


def _run_one(
    story: Path,
    lang: str,
    iterations: int,
    review: bool,
    sensitivity: str | None,
    timeout_per_sim: int,
) -> dict:
    """Run a single story through Pipeline directly. Returns a result dict.

    Runs in a worker process — imports are local to avoid pickling issues.
    Worker stdout/stderr is redirected to a per-story log file so that
    Rich output from 6 concurrent workers doesn't interleave in the terminal.
    """
    import sys as _sys
    import io

    t0 = time.time()

    # Redirect worker output to a story-specific log file
    story_slug = Path(story).parent.name[:40]
    log_dir = Path(story).parent
    log_path = log_dir / "pipeline.log"
    _log_fh = open(log_path, "w", encoding="utf-8", buffering=1)
    _orig_stdout, _orig_stderr = _sys.stdout, _sys.stderr
    _sys.stdout = _log_fh
    _sys.stderr = _log_fh

    try:
        # Local import inside worker process — avoids pickling the Pipeline object
        from abm_auto.pipeline import Pipeline

        pipeline = Pipeline(
            story_path=story,
            iterations=iterations,
            lang=lang,
            sensitivity_method=sensitivity,
            sensitivity_samples=10,
            peer_review=review,
            timeout=timeout_per_sim,
        )
        workspace_path = pipeline.run()
        elapsed = time.time() - t0

        # Count how many result CSVs exist to infer completed iterations
        result_dirs = sorted(workspace_path.glob("results/run_*"))
        iters_done = sum(
            1 for d in result_dirs if any(d.glob("*.csv"))
        )

        return {
            "story": str(story),
            "workspace": str(workspace_path),
            "status": "OK",
            "iters_completed": iters_done,
            "failed_phase": "",
            "wall_seconds": round(elapsed),
            "notes": "",
        }

    except Exception as exc:
        elapsed = time.time() - t0
        tb = traceback.format_exc()
        failed_phase = _detect_failed_phase(tb)
        return {
            "story": str(story),
            "workspace": "",
            "status": "FAIL",
            "iters_completed": 0,
            "failed_phase": failed_phase,
            "wall_seconds": round(elapsed),
            "notes": (str(exc) + "\n" + tb[-300:]).strip(),
        }

    finally:
        # Restore stdout/stderr and close log file
        _sys.stdout = _orig_stdout
        _sys.stderr = _orig_stderr
        _log_fh.close()


def _retry_one(story: Path, timeout_per_sim: int) -> dict:
    """Fast retry: 1 iteration, no review, no sensitivity — diagnostic pass."""
    import sys as _sys

    t0 = time.time()
    log_path = Path(story).parent / "pipeline_retry.log"
    _log_fh = open(log_path, "w", encoding="utf-8", buffering=1)
    _orig_stdout, _orig_stderr = _sys.stdout, _sys.stderr
    _sys.stdout = _log_fh
    _sys.stderr = _log_fh

    try:
        from abm_auto.pipeline import Pipeline

        pipeline = Pipeline(
            story_path=story,
            iterations=1,
            lang="en",
            sensitivity_method=None,
            peer_review=False,
            timeout=timeout_per_sim,
        )
        workspace_path = pipeline.run()
        elapsed = time.time() - t0
        result_dirs = sorted(workspace_path.glob("results/run_*"))
        iters_done = sum(1 for d in result_dirs if any(d.glob("*.csv")))
        return {
            "story": str(story),
            "workspace": str(workspace_path),
            "status": "OK(retry1)",
            "iters_completed": iters_done,
            "failed_phase": "",
            "wall_seconds": round(elapsed),
            "notes": "retry succeeded",
        }
    except Exception as exc:
        tb = traceback.format_exc()
        return {
            "story": str(story),
            "workspace": "",
            "status": "FAIL",
            "iters_completed": 0,
            "failed_phase": _detect_failed_phase(tb),
            "wall_seconds": round(time.time() - t0),
            "notes": (str(exc) + "\n" + tb[-300:]).strip(),
        }
    finally:
        _sys.stdout = _orig_stdout
        _sys.stderr = _orig_stderr
        _log_fh.close()


def _detect_failed_phase(tb: str) -> str:
    """Scan a traceback string and return the pipeline phase that failed."""
    phase_markers = [
        ("designer.py", "Phase1:Design"),
        ("odd_writer.py", "Phase1b:ODD"),
        ("coder.py", "Phase2:Code"),
        ("verifier.py", "Phase3:Verify"),
        ("analyzer.py", "Phase4:Analyze"),
        ("optimizer.py", "Phase5:Optimize"),
        ("salib_optimizer.py", "Phase6b:Sensitivity"),
        ("reporter.py", "Phase7:Report"),
        ("reviewer.py", "Phase8:Review"),
        ("executor.py", "Executor"),
    ]
    for marker, label in phase_markers:
        if marker in tb:
            return label
    return "Unknown"


def run_batch(
    stories: list[Path],
    workers: int = 6,
    lang: str = "en",
    iterations: int = 3,
    review: bool = True,
    sensitivity: str | None = "morris",
    timeout_per_sim: int = 300,
    dry_run: bool = False,
    batch_label: str = "batch",
) -> Path:
    """Run all stories in parallel. Returns path to summary CSV."""
    if not stories:
        console.print("[yellow]No stories found.[/yellow]")
        return WORKSPACE_DIR / f"{batch_label}_summary.csv"

    console.print(f"\n[bold cyan]ABM Batch Run[/bold cyan]")
    console.print(f"  Stories : {len(stories)}")
    console.print(f"  Workers : {workers}")
    console.print(f"  Lang    : {lang}  Iterations: {iterations}  Review: {review}")
    console.print(f"  Sensitivity: {sensitivity or 'none'}")

    if dry_run:
        console.print("\n[bold yellow]DRY RUN — listing stories only:[/bold yellow]")
        for s in stories:
            console.print(f"  {s}")
        return WORKSPACE_DIR / f"{batch_label}_summary.csv"

    results: list[dict] = []
    summary_path = WORKSPACE_DIR / f"{batch_label}_summary.csv"
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        overall = progress.add_task(
            f"[cyan]Running {len(stories)} stories…", total=len(stories)
        )

        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _run_one, s, lang, iterations, review, sensitivity, timeout_per_sim
                ): s
                for s in stories
            }

            for future in as_completed(futures):
                story = futures[future]
                res = future.result()

                if res["status"] == "FAIL":
                    # One retry at minimal settings
                    console.print(
                        f"  [yellow]Retrying {story.name}… "
                        f"(failed at {res['failed_phase']})[/yellow]"
                    )
                    res = _retry_one(story, timeout_per_sim)

                results.append(res)
                status_color = "green" if res["status"].startswith("OK") else "red"
                phase_info = f" [{res['failed_phase']}]" if res.get("failed_phase") else ""
                console.print(
                    f"  [{status_color}]{res['status']}[/{status_color}]"
                    f"{phase_info} {story.name} ({res['wall_seconds']}s)"
                )
                progress.advance(overall)

    # Write summary CSV (added failed_phase column)
    fieldnames = [
        "story", "workspace", "status", "iters_completed",
        "failed_phase", "wall_seconds", "notes",
    ]
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    ok = sum(1 for r in results if r["status"].startswith("OK"))
    fail = len(results) - ok
    console.print(f"\n[bold]Batch complete:[/bold] {ok}/{len(results)} OK, {fail} FAIL")
    console.print(f"Summary: {summary_path}")
    return summary_path
