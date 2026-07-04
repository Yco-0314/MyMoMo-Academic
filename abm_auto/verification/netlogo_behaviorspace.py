"""BehaviorSpace manifest bridge for NetLogo oracle runs.

This module packages NetLogo BehaviorSpace experiments as auditable manifests.
It does not execute NetLogo; `netlogo_oracle.run_experiment` remains the only
external runner.
"""
from __future__ import annotations

import json
import re
import shlex
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from abm_auto.verification import netlogo_oracle


@dataclass(frozen=True)
class BehaviorSpaceExperiment:
    name: str
    setup: str = ""
    go: str = ""
    repetitions: int = 1
    run_metrics_every_step: bool = False
    time_limit_steps: int | None = None
    metrics: tuple[str, ...] = ()
    enumerated_values: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "setup": self.setup,
            "go": self.go,
            "repetitions": self.repetitions,
            "run_metrics_every_step": self.run_metrics_every_step,
            "time_limit_steps": self.time_limit_steps,
            "metrics": list(self.metrics),
            "enumerated_values": {
                key: list(values)
                for key, values in sorted(self.enumerated_values.items())
            },
        }


def extract_behaviorspace_experiments(model_path: Path | str) -> list[BehaviorSpaceExperiment]:
    """Extract BehaviorSpace experiments from a `.nlogo` or `.nlogox` file."""
    path = Path(model_path)
    text = path.read_text(encoding="utf-8", errors="replace")
    block = _extract_experiments_block(text)
    if not block:
        return []
    root = ET.fromstring(block)
    return [_experiment_from_xml(el) for el in root.findall("experiment")]


def find_behaviorspace_experiment(
    model_path: Path | str,
    experiment_name: str,
) -> BehaviorSpaceExperiment:
    for experiment in extract_behaviorspace_experiments(model_path):
        if experiment.name == experiment_name:
            return experiment
    raise ValueError(f"BehaviorSpace experiment not found: {experiment_name!r}")


def summarize_behaviorspace_output(
    table_path: Path | str,
    *,
    metrics: Iterable[str] | None = None,
    max_tick: int | None = None,
    require_metrics: bool = False,
) -> dict:
    """Reduce a NetLogo BehaviorSpace table into stable scalar summaries."""
    df = netlogo_oracle.parse_table(table_path)
    if max_tick is not None:
        df = df[df["[step]"] <= max_tick]

    metric_names = list(metrics) if metrics is not None else _default_metric_columns(df)
    missing_metrics = [
        metric for metric in metric_names
        if metric not in df.columns
    ]
    if require_metrics and missing_metrics:
        missing = ", ".join(missing_metrics)
        raise ValueError(f"Missing BehaviorSpace metric columns: {missing}")

    metric_summaries: dict[str, dict[str, float]] = {}
    for metric in metric_names:
        if metric not in df.columns:
            continue
        by_tick = df.groupby("[step]")[metric].mean()
        if by_tick.empty:
            continue
        metric_summaries[metric] = {
            "final_mean": float(by_tick.iloc[-1]),
            "max_mean": float(by_tick.max()),
        }

    return {
        "row_count": int(len(df)),
        "run_count": int(df["[run number]"].nunique()) if "[run number]" in df.columns else 0,
        "max_step": int(df["[step]"].max()) if "[step]" in df.columns and len(df) else None,
        "metrics": metric_summaries,
        "missing_metrics": missing_metrics,
    }


def build_behaviorspace_manifest(
    model_path: Path | str,
    experiment_name: str,
    output_table_path: Path | str,
    *,
    manifest_path: Path | str | None = None,
    require_metrics: bool = False,
) -> dict:
    """Build a JSON-serializable audit manifest for a BehaviorSpace output."""
    model = Path(model_path)
    output = Path(output_table_path)
    experiment = find_behaviorspace_experiment(model, experiment_name)
    headless = netlogo_oracle.netlogo_dir() / "netlogo-headless.sh"
    manifest = {
        "schema": "netlogo-behaviorspace-manifest/v1",
        "model_path": str(model),
        "experiment_name": experiment_name,
        "output_table_path": str(output),
        "command": [
            str(headless),
            "--model",
            str(model),
            "--experiment",
            experiment_name,
            "--table",
            str(output),
        ],
        "tool": {
            "netlogo_dir": str(netlogo_oracle.netlogo_dir()),
            "java_home": netlogo_oracle.java_home(),
            "available": bool(netlogo_oracle.is_available()),
        },
        "experiment": experiment.to_dict(),
        "reduction": summarize_behaviorspace_output(
            output,
            metrics=experiment.metrics,
            require_metrics=require_metrics,
        ),
    }
    if manifest_path is not None:
        manifest["manifest_path"] = str(Path(manifest_path))
    return manifest


def write_behaviorspace_manifest(manifest: dict[str, Any], path: Path | str) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out


def write_behaviorspace_repro_pack(
    model_path: Path | str,
    experiment_name: str,
    output_table_path: Path | str,
    out_dir: Path | str,
) -> dict[str, Any]:
    """Write a reviewer-facing repro pack for an existing BehaviorSpace table."""
    manifest_path = Path(out_dir) / "manifest.json"
    readme_path = Path(out_dir) / "MANIFEST.md"
    manifest = build_behaviorspace_manifest(
        model_path,
        experiment_name,
        output_table_path,
        manifest_path=manifest_path,
        require_metrics=True,
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_behaviorspace_manifest(manifest, manifest_path)
    readme_path.write_text(
        _render_behaviorspace_pack_readme(manifest),
        encoding="utf-8",
    )
    return {
        "manifest": manifest,
        "manifest_path": str(manifest_path),
        "readme_path": str(readme_path),
    }


def _render_behaviorspace_pack_readme(manifest: dict[str, Any]) -> str:
    reduction = manifest["reduction"]
    metrics = sorted(reduction["metrics"])
    command = shlex.join(manifest["command"])
    lines = [
        "# NetLogo BehaviorSpace Repro Pack",
        "",
        "This pack does not execute NetLogo. It records the external oracle command shape and summarizes an existing BehaviorSpace output table.",
        "",
        "## Inputs",
        "",
        f"- Model: `{manifest['model_path']}`",
        f"- Experiment: `{manifest['experiment_name']}`",
        f"- Output table: `{manifest['output_table_path']}`",
        f"- NetLogo available: `{manifest['tool']['available']}`",
        "",
        "## Oracle Command Shape",
        "",
        "```text",
        command,
        "```",
        "",
        "## Reduction",
        "",
        f"- Rows: `{reduction['row_count']}`",
        f"- Runs: `{reduction['run_count']}`",
        f"- Max step: `{reduction['max_step']}`",
        f"- Metrics: `{', '.join(metrics)}`",
        "",
        "## Boundary",
        "",
        "This is oracle evidence packaging only. It does not imply native MyMoMo execution of NetLogo procedures or BehaviorSpace experiments.",
        "",
    ]
    return "\n".join(lines)


def _extract_experiments_block(text: str) -> str:
    match = re.search(r"<experiments>.*?</experiments>", text, flags=re.DOTALL)
    return match.group(0) if match else ""


def _experiment_from_xml(el: ET.Element) -> BehaviorSpaceExperiment:
    time_limit = el.find("timeLimit")
    time_limit_steps = None
    if time_limit is not None and time_limit.attrib.get("steps") is not None:
        time_limit_steps = int(float(time_limit.attrib["steps"]))

    values: dict[str, tuple[str, ...]] = {}
    for value_set in el.findall("enumeratedValueSet"):
        variable = value_set.attrib.get("variable", "")
        if not variable:
            continue
        values[variable] = tuple(
            value.attrib.get("value", "")
            for value in value_set.findall("value")
        )

    return BehaviorSpaceExperiment(
        name=el.attrib.get("name", ""),
        setup=_child_text(el, "setup"),
        go=_child_text(el, "go"),
        repetitions=int(float(el.attrib.get("repetitions", "1"))),
        run_metrics_every_step=_boolish(el.attrib.get("runMetricsEveryStep", "")),
        time_limit_steps=time_limit_steps,
        metrics=tuple(
            metric.text.strip()
            for metric in el.findall("metric")
            if metric.text and metric.text.strip()
        ),
        enumerated_values=values,
    )


def _child_text(el: ET.Element, name: str) -> str:
    child = el.find(name)
    return child.text.strip() if child is not None and child.text else ""


def _boolish(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "t", "yes", "on"}


def _default_metric_columns(df: pd.DataFrame) -> list[str]:
    skip = {
        "[run number]",
        "[step]",
        "number-of-nodes",
        "average-node-degree",
        "initial-outbreak-size",
        "virus-check-frequency",
        "virus-spread-chance",
        "recovery-chance",
        "gain-resistance-chance",
    }
    return [
        col for col in df.columns
        if col not in skip and pd.api.types.is_numeric_dtype(df[col])
    ]
