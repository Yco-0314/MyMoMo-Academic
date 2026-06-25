"""Codegen registry wiring of NetLogo gis-extension parity (Phase 1/2/3).

For each of the 3 new capabilities — topology_clip, raster_focal, raster_coverage —
verify:
  1. registry: cap is in CAPABILITIES, renderable, with the right required_tokens;
  2. render: render(spec) produces code that contains every required_token;
  3. fidelity gate: gis_codegen_gate(files, spec) PASSES on the real render;
  4. execution: the rendered code runs end-to-end and its associated gate prints PASS;
  5. fault injection: a rendered file with a required token removed FAILS the gate.

Wraps render → subprocess execute. PYTHONPATH = repo root so the
subprocess can import abm_auto.gis.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from abm_auto.gis._capabilities import CAPABILITIES, resolve_capability
from abm_auto.gis._codegen_gate import gis_codegen_gate
from abm_auto.gis._model_spec import GISModelSpec
from abm_auto.gis._templates import render


REPO_ROOT = str(Path(__file__).resolve().parents[2])

_CASES = [
    ("topology_clip", "topology", "line_polygon_clip", "PASS: line×polygon clip"),
    ("raster_focal", "raster", "focal_smoothing", "PASS: focal ops OK"),
    ("raster_coverage", "raster", "areal_coverage", "PASS: coverage OK"),
]


# ── 1. registry ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("key,spatial_type,mechanism,_", _CASES)
def test_capability_registered_and_resolves(key, spatial_type, mechanism, _):
    assert key in CAPABILITIES, f"{key} not in CAPABILITIES"
    cap = CAPABILITIES[key]
    assert cap.renderable is True
    assert cap.spatial_type == spatial_type
    assert cap.mechanism == mechanism
    assert cap.required_tokens, f"{key} has no required_tokens"
    # implicit resolution also finds it
    resolved = resolve_capability(spatial_type, mechanism)
    assert resolved.key == key


# ── 2. render contains required tokens ───────────────────────────────────────

@pytest.mark.parametrize("key,spatial_type,mechanism,_", _CASES)
def test_render_contains_every_required_token(key, spatial_type, mechanism, _):
    spec = GISModelSpec(spatial_type=spatial_type, mechanism=mechanism)
    code = render(spec)["main.py"]
    cap = CAPABILITIES[key]
    for tok in cap.required_tokens:
        assert tok in code, f"{key} render missing required token {tok!r}"
    assert "from abm_auto.gis" in code


# ── 3. fidelity gate PASS on real render ─────────────────────────────────────

@pytest.mark.parametrize("key,spatial_type,mechanism,_", _CASES)
def test_fidelity_gate_passes_on_clean_render(key, spatial_type, mechanism, _):
    spec = GISModelSpec(spatial_type=spatial_type, mechanism=mechanism)
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


# ── 4. execute the generated model end-to-end → its inner gate prints PASS ──

@pytest.mark.parametrize("key,spatial_type,mechanism,expected_prefix", _CASES)
def test_render_executes_and_inner_gate_passes(tmp_path, key, spatial_type, mechanism, expected_prefix):
    spec = GISModelSpec(spatial_type=spatial_type, mechanism=mechanism)
    main = tmp_path / "main.py"
    main.write_text(render(spec)["main.py"])
    env = {**os.environ, "PYTHONPATH": REPO_ROOT}
    out = subprocess.run([sys.executable, str(main)], capture_output=True,
                         text=True, timeout=120, env=env)
    assert out.returncode == 0, f"stderr:\n{out.stderr}"
    assert out.stdout.startswith(expected_prefix), \
        f"unexpected stdout for {key}:\n{out.stdout}"


# ── 5. fault injection: removing a required token must FAIL the gate ────────

@pytest.mark.parametrize("key,spatial_type,mechanism,_", _CASES)
def test_fidelity_gate_fails_when_required_token_is_stripped(key, spatial_type, mechanism, _):
    spec = GISModelSpec(spatial_type=spatial_type, mechanism=mechanism)
    files = render(spec)
    cap = CAPABILITIES[key]
    # pick the first required token and corrupt it in the generated source
    victim = cap.required_tokens[0]
    files["main.py"] = files["main.py"].replace(victim, "__broken__")
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok, f"{key}: gate did not catch missing {victim!r}"
    assert any(victim in r for r in reasons), \
        f"{key}: gate reasons {reasons} did not mention missing token {victim!r}"


# ── 5b. wrong-space leak must FAIL the gate ────────────────────────────────

@pytest.mark.parametrize("key,spatial_type,mechanism,_", _CASES)
def test_fidelity_gate_fails_on_wrong_space_token(key, spatial_type, mechanism, _):
    spec = GISModelSpec(spatial_type=spatial_type, mechanism=mechanism)
    cap = CAPABILITIES[key]
    if not cap.wrong_space_tokens:
        pytest.skip(f"{key} has no wrong_space_tokens to inject")
    files = render(spec)
    leak = cap.wrong_space_tokens[0]
    files["main.py"] += f"\n# leak: {leak}\n"
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok, f"{key}: gate did not catch leaked {leak!r}"
    assert any(leak in r for r in reasons)
