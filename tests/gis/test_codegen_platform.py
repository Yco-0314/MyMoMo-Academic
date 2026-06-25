"""Codegen emits a full platform ABM: the gis_abm_platform
capability renders a GISAgent/GISModel/DataCollector ABM that runs end-to-end and
passes the codegen-fidelity gate; fault injection still fails the gate."""
import os
import subprocess
import sys
from pathlib import Path

from abm_auto.gis._capabilities import CAPABILITIES, resolve_capability
from abm_auto.gis._codegen_gate import gis_codegen_gate
from abm_auto.gis._model_spec import GISModelSpec
from abm_auto.gis._templates import render

REPO = str(Path(__file__).resolve().parents[2])


def _spec():
    return GISModelSpec(spatial_type="platform", mechanism="diffusion")


def test_capability_registered():
    cap = CAPABILITIES["gis_abm_platform"]
    assert cap.renderable
    assert resolve_capability("platform", "diffusion").key == "gis_abm_platform"
    for tok in ("GISAgent", "GISModel", "DataCollector", "step"):
        assert tok in cap.required_tokens


def test_render_contains_platform_tokens():
    code = render(_spec())["main.py"]
    for tok in ("GISAgent", "GISModel", "DataCollector", "step", "run"):
        assert tok in code
    assert "from abm_auto.gis" in code


def test_fidelity_gate_passes_on_clean_render():
    spec = _spec()
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


def test_render_executes_full_abm_and_passes():
    spec = _spec()
    code = render(spec)["main.py"]
    # sanity: it really emits subclasses (codegen writes the ABM, not a call)
    assert "class DiffuseAgent(GISAgent)" in code
    assert "class DiffuseModel(GISModel)" in code
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         timeout=60, env={**os.environ, "PYTHONPATH": REPO})
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("PASS"), out.stdout


def test_fidelity_gate_fails_when_required_token_stripped():
    spec = _spec()
    files = render(spec)
    files["main.py"] = files["main.py"].replace("DataCollector", "__broken__")
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok
    assert any("DataCollector" in r for r in reasons)
