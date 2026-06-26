"""``abm-auto gis ...`` — CLI parity for GIS mode (the spatial ABM layer).

Mirrors the main pipeline's story → spec → code → run flow for geo-referenced
models, so GIS is drivable from the command line instead of Python-only. Mounted
as a sub-app on the main CLI. GIS / LLM dependencies are imported lazily inside
each command, so importing this module is safe even without the ``[gis]`` extra
(the commands that need it call ``require_gis()`` first).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

gis_app = typer.Typer(
    name="gis",
    help="GIS spatial ABM commands (geo-referenced models): capabilities, extract, render, run.",
    add_completion=False,
)
console = Console()


def _make_client():
    """Build an LLMClient for the active provider from .env (mirrors the agents)."""
    from abm_auto import config
    from abm_auto.llm import make_client

    key = config.get_api_key()
    if not key:
        raise typer.BadParameter(
            f"{config.LLM_PROVIDER.upper()}_API_KEY is empty — set it in .env to use the LLM."
        )
    return make_client(
        provider=config.LLM_PROVIDER, api_key=key, base_url=config.get_base_url()
    )


@gis_app.command()
def capabilities() -> None:
    """List the GIS capabilities codegen can render, with their declared params."""
    from abm_auto.gis._capabilities import renderable_capabilities

    for cap in renderable_capabilities():
        params = ", ".join(
            f"{p.name}:{p.type.__name__}={p.default!r}" + (f" {p.unit}" if p.unit else "")
            for p in cap.params
        ) or "(none)"
        console.print(
            f"[bold cyan]{cap.key}[/bold cyan] "
            f"(spatial_type={cap.spatial_type}, mechanism={cap.mechanism})"
        )
        console.print(f"  params: {params}")


@gis_app.command()
def extract(
    story: Path = typer.Argument(..., help="Path to a GIS story.md", exists=True),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Write the spec JSON here (default: stdout)."),
    model: Optional[str] = typer.Option(None, "--model", help="LLM model (default: the provider default)."),
) -> None:
    """Extract a GISModelSpec from a story via the LLM (writes JSON)."""
    from abm_auto import config
    from abm_auto.gis import require_gis
    from abm_auto.gis._extractor import extract_gis_spec

    require_gis()
    spec = extract_gis_spec(
        story.read_text(encoding="utf-8"), _make_client(), model or config.DEFAULT_MODEL
    )
    payload = json.dumps(spec.to_dict(), indent=2, ensure_ascii=False)
    if out:
        out.write_text(payload + "\n", encoding="utf-8")
        console.print(f"[green]✓ spec written: {out}[/green]")
    else:
        console.print(payload)


@gis_app.command()
def render(
    spec_json: Path = typer.Argument(..., help="Path to a GISModelSpec JSON", exists=True),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Write main.py here (default: stdout)."),
) -> None:
    """Render a spec to runnable GIS model code — deterministic, no LLM."""
    from abm_auto.gis import require_gis
    from abm_auto.gis._model_spec import GISModelSpec
    from abm_auto.gis._templates import render as render_spec

    require_gis()
    spec = GISModelSpec.from_dict(json.loads(spec_json.read_text(encoding="utf-8")))
    code = render_spec(spec)["main.py"]
    if out:
        out.write_text(code, encoding="utf-8")
        console.print(f"[green]✓ main.py written: {out}[/green]")
    else:
        console.print(code)


@gis_app.command()
def run(
    source: Path = typer.Argument(..., help="A GIS story.md (LLM-extracted) or a spec .json", exists=True),
    out: Path = typer.Option(Path("gis_out"), "--out", "-o", help="Output directory for the generated model."),
    model: Optional[str] = typer.Option(None, "--model", help="LLM model for extraction (story input only)."),
) -> None:
    """Drive a GIS model end-to-end: (story→)spec→code→execute."""
    from abm_auto import config
    from abm_auto.gis import require_gis
    from abm_auto.gis._model_spec import GISModelSpec
    from abm_auto.gis._templates import render as render_spec

    require_gis()

    if source.suffix.lower() == ".json":
        spec = GISModelSpec.from_dict(json.loads(source.read_text(encoding="utf-8")))
    else:
        from abm_auto.gis._extractor import extract_gis_spec

        console.print("[cyan]Extracting spec from story via LLM...[/cyan]")
        spec = extract_gis_spec(
            source.read_text(encoding="utf-8"), _make_client(), model or config.DEFAULT_MODEL
        )

    out.mkdir(parents=True, exist_ok=True)
    main_py = out / "main.py"
    main_py.write_text(render_spec(spec)["main.py"], encoding="utf-8")
    console.print(f"[dim]model rendered → {main_py}[/dim]")

    console.print("[cyan]Running model...[/cyan]")
    # Make abm_auto importable in the model subprocess (it may be path-based, not
    # pip-installed) by passing the parent's import paths through PYTHONPATH.
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}
    result = subprocess.run(
        [sys.executable, str(main_py)],
        capture_output=True, text=True, timeout=config.DEFAULT_TIMEOUT, env=env,
    )
    if result.stdout:
        console.print(result.stdout)
    if result.returncode != 0:
        console.print(f"[red]model exited {result.returncode}[/red]")
        if result.stderr:
            console.print(result.stderr)
        raise typer.Exit(result.returncode)
    console.print("[green]✓ done[/green]")
