"""MIR v0 Half A — forward round-trip (open).

Proves a real GIS model survives GISModelSpec -> MIR -> (json) -> MIR ->
GISModelSpec -> render -> run with no fidelity token lost and its science gate
still passing. The `extensions` seam stays empty for GIS and is ignored by the
open side. Predictions locked in docs/reproduce/mir-v0/PREDICTIONS-locked.md.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from abm_auto.gis._capabilities import resolve_capability
from abm_auto.gis._codegen_gate import gis_codegen_gate
from abm_auto.gis._model_spec import GISModelSpec
from abm_auto.gis._templates import render
from abm_auto.mir import MIR
from abm_auto.mir._gis_adapter import gis_spec_to_mir, mir_to_gis_spec

REPO = str(Path(__file__).resolve().parents[2])

# (spatial_type, mechanism) — diverse renderable capabilities, all on `main` and
# executable on synthetic data. Includes the NetLogo-parity caps (topology_clip /
# raster_focal / raster_coverage), merged into main, so MIR v0 now round-trips the
# full codegen baseline.
CASES = [
    ("raster", "sir"),
    ("network", "flood_evacuation"),
    ("coupled", "social_spatial_contagion"),
    ("mechanism", "threshold_adoption"),
    ("polygon", "polygon_point_zoning"),
    ("topology", "line_polygon_clip"),   # NetLogo parity (DE-9IM)
    ("raster", "focal_smoothing"),       # NetLogo parity (focal)
    ("raster", "areal_coverage"),        # NetLogo parity (coverage)
]


# ── A1 schema ────────────────────────────────────────────────────────────────

def test_empty_mir_roundtrips_dict_and_json():
    m = MIR()
    assert MIR.from_dict(m.to_dict()).to_dict() == m.to_dict()
    assert MIR.from_json(m.to_json()).to_json() == m.to_json()
    m.validate()


def test_validate_rejects_non_dict_extensions():
    m = MIR()
    m.extensions = ["not", "a", "dict"]  # type: ignore[assignment]
    with pytest.raises(ValueError, match="extensions"):
        m.validate()


# ── P1 field-identity ────────────────────────────────────────────────────────

@pytest.mark.parametrize("st,mech", CASES)
def test_spec_mir_spec_field_identity(st, mech):
    # params carries the spec-level "seed" key (accepted on every capability) so
    # this identity check exercises a non-empty params dict across all CASES — the
    # per-capability render params differ, but seed validates everywhere.
    spec = GISModelSpec(spatial_type=st, mechanism=mech, seed=3, params={"seed": 12})
    back = mir_to_gis_spec(gis_spec_to_mir(spec))
    assert back.spatial_type == spec.spatial_type
    assert back.mechanism == spec.mechanism
    assert back.data_path == spec.data_path
    assert back.seed == spec.seed
    assert back.params == spec.params
    assert resolve_capability(back.spatial_type, back.mechanism, back.capability).key == \
           resolve_capability(st, mech).key


# ── P2 fidelity tokens survive ───────────────────────────────────────────────

@pytest.mark.parametrize("st,mech", CASES)
def test_fidelity_tokens_survive(st, mech):
    cap = resolve_capability(st, mech)
    mir = gis_spec_to_mir(GISModelSpec(spatial_type=st, mechanism=mech))
    assert mir.fidelity.required_tokens == tuple(cap.required_tokens)
    assert mir.fidelity.gate == cap.gate
    assert mir.fidelity.wrong_space_tokens == tuple(cap.wrong_space_tokens)
    # survive json round-trip too
    assert MIR.from_json(mir.to_json()).fidelity.required_tokens == tuple(cap.required_tokens)


# ── P3 byte-identical render after spec->MIR->json->MIR->spec ────────────────

@pytest.mark.parametrize("st,mech", CASES)
def test_render_byte_identical_after_roundtrip(st, mech):
    spec = GISModelSpec(spatial_type=st, mechanism=mech)
    rt = mir_to_gis_spec(MIR.from_json(gis_spec_to_mir(spec).to_json()))
    assert render(rt)["main.py"] == render(spec)["main.py"]


# ── P4 gate + execute survive ────────────────────────────────────────────────

@pytest.mark.parametrize("st,mech", CASES)
def test_roundtripped_spec_passes_gate_and_executes(tmp_path, st, mech):
    spec = GISModelSpec(spatial_type=st, mechanism=mech)
    rt = mir_to_gis_spec(MIR.from_json(gis_spec_to_mir(spec).to_json()))
    files = render(rt)
    ok, reasons = gis_codegen_gate(files, rt)
    assert ok, reasons
    main = tmp_path / "main.py"
    main.write_text(files["main.py"])
    out = subprocess.run([sys.executable, str(main)], capture_output=True, text=True,
                         timeout=120, env={**os.environ, "PYTHONPATH": REPO})
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("PASS"), out.stdout


# ── P5 extensions seam ───────────────────────────────────────────────────────

def test_extensions_empty_for_gis_and_ignored_by_open_side():
    spec = GISModelSpec(spatial_type="raster", mechanism="sir")
    mir = gis_spec_to_mir(spec)
    assert mir.extensions == {}
    # inject an arbitrary closed overlay -> open render must be byte-identical
    mir.extensions = {"search_space": {"dimensions": [1, 2, 3]}, "audiences": ["policy"]}
    rt = mir_to_gis_spec(mir)
    assert render(rt)["main.py"] == render(spec)["main.py"]


# ── P6 empty clusters survive ────────────────────────────────────────────────

def test_empty_clusters_survive_roundtrip():
    spec = GISModelSpec(spatial_type="raster", mechanism="sir")
    mir = MIR.from_json(gis_spec_to_mir(spec).to_json())
    assert mir.entities == []
    assert mir.state == []
    assert mir.relations == []
    assert mir.layers == []
    assert mir.metrics == []
