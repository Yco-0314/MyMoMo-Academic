from __future__ import annotations

import json
import shlex
from pathlib import Path

from typer.testing import CliRunner

from abm_auto.cli import app
from abm_auto.verification.netlogo_behaviorspace import (
    write_behaviorspace_repro_pack,
)


MODEL = Path("tests/fixtures/netlogo/Virus_on_a_Network.nlogo")
SIR_TABLE = Path("tests/fixtures/netlogo/output/sir_trajectories.csv")


runner = CliRunner()


def test_write_behaviorspace_repro_pack_writes_json_and_markdown(tmp_path):
    result = write_behaviorspace_repro_pack(
        MODEL,
        "oracle_sir_network_GT",
        SIR_TABLE,
        tmp_path / "pack",
    )

    manifest_path = Path(result["manifest_path"])
    readme_path = Path(result["readme_path"])
    assert manifest_path.exists()
    assert readme_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == "netlogo-behaviorspace-manifest/v1"
    assert manifest["experiment_name"] == "oracle_sir_network_GT"
    assert manifest["manifest_path"] == str(manifest_path)
    assert manifest["reduction"]["row_count"] == 7530
    assert "count turtles with [infected?]" in manifest["reduction"]["metrics"]
    assert result["manifest"] == manifest


def test_behaviorspace_repro_pack_markdown_names_audit_boundary(tmp_path):
    result = write_behaviorspace_repro_pack(
        MODEL,
        "oracle_sir_network_GT",
        SIR_TABLE,
        tmp_path / "pack",
    )

    body = Path(result["readme_path"]).read_text(encoding="utf-8")
    assert "# NetLogo BehaviorSpace Repro Pack" in body
    assert "This pack does not execute NetLogo." in body
    assert f"- Model: `{MODEL}`" in body
    assert "- Experiment: `oracle_sir_network_GT`" in body
    assert f"- Output table: `{SIR_TABLE}`" in body
    assert "netlogo-headless.sh" in body
    assert "- Rows: `7530`" in body
    assert "- Runs: `30`" in body
    assert "- Max step: `250`" in body


def test_behaviorspace_repro_pack_quotes_command_paths_with_spaces(tmp_path):
    spaced_dir = tmp_path / "path with spaces"
    spaced_dir.mkdir()
    model = spaced_dir / "Virus Model.nlogo"
    table = spaced_dir / "sir output.csv"
    model.write_text(MODEL.read_text(encoding="utf-8"), encoding="utf-8")
    table.write_text(SIR_TABLE.read_text(encoding="utf-8"), encoding="utf-8")

    result = write_behaviorspace_repro_pack(
        model,
        "oracle_sir_network_GT",
        table,
        tmp_path / "pack",
    )

    body = Path(result["readme_path"]).read_text(encoding="utf-8")
    assert shlex.quote(str(model)) in body
    assert shlex.quote(str(table)) in body


def test_write_behaviorspace_repro_pack_rejects_missing_declared_metrics(tmp_path):
    out = tmp_path / "pack"

    result = runner.invoke(
        app,
        [
            "netlogo-behaviorspace-pack",
            str(MODEL),
            "oracle_sir_network_GT",
            "tests/fixtures/netlogo/output/network_topology.csv",
            "--out",
            str(out),
        ],
    )

    assert result.exit_code != 0
    assert "Missing BehaviorSpace metric columns" in result.output
    assert not out.exists()


def test_netlogo_behaviorspace_pack_cli_writes_pack(tmp_path):
    out = tmp_path / "pack"

    result = runner.invoke(
        app,
        [
            "netlogo-behaviorspace-pack",
            str(MODEL),
            "oracle_sir_network_GT",
            str(SIR_TABLE),
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (out / "manifest.json").exists()
    assert (out / "MANIFEST.md").exists()
    assert "manifest.json" in result.output
    assert "MANIFEST.md" in result.output


def test_netlogo_behaviorspace_pack_cli_rejects_unknown_experiment(tmp_path):
    out = tmp_path / "pack"

    result = runner.invoke(
        app,
        [
            "netlogo-behaviorspace-pack",
            str(MODEL),
            "missing_experiment",
            str(SIR_TABLE),
            "--out",
            str(out),
        ],
    )

    assert result.exit_code != 0
    assert "BehaviorSpace experiment not found" in result.output
    assert not out.exists()
