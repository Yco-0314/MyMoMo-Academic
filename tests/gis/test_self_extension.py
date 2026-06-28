from abm_auto.gis._model_spec import GISModelSpec
from abm_auto.gis._self_extension import (
    gis_codegen_preflight,
    gis_codegen_scaffold,
    gis_self_extension_gap_gate,
    gis_self_extension_scaffold_gate,
)


def test_preflight_classifies_renderable_flood_spec():
    spec = GISModelSpec(
        spatial_type="network",
        mechanism="flood_evacuation",
        capability="flood_evacuation",
    )

    report = gis_codegen_preflight(spec)

    assert report["ok"] is True
    assert report["status"] == "renderable"
    assert report["action"] == "render"
    assert report["capability"] == "flood_evacuation"
    assert report["renderable"] is True
    assert report["layers"] == ("GeoNetwork", "RasterSpace")
    assert report["coupling"] == "raster_network_flood"
    assert report["gate"] == "flood_gate"
    assert "run_flood_evacuation" in report["required_tokens"]


def test_preflight_classifies_mechanism_contagion_as_renderable():
    spec = GISModelSpec(
        spatial_type="mechanism",
        mechanism="contagion",
        capability="mechanism_contagion",
    )

    report = gis_codegen_preflight(spec)

    assert report["ok"] is True
    assert report["status"] == "renderable"
    assert report["action"] == "render"
    assert report["capability"] == "mechanism_contagion"
    assert report["renderable"] is True
    assert report["gate"] == "mechanism_contagion_gate"


def test_scaffold_mechanism_contagion_refuses_after_gap_closure():
    spec = GISModelSpec(
        spatial_type="mechanism",
        mechanism="contagion",
        capability="mechanism_contagion",
    )

    report = gis_codegen_scaffold(spec)

    assert report["ok"] is False
    assert report["status"] == "renderable"
    assert report["action"] == "render"
    assert report["capability"] == "mechanism_contagion"
    assert "already renderable" in report["reason"]


def test_scaffold_renderable_capability_refuses_and_points_to_render():
    spec = GISModelSpec(
        spatial_type="network",
        mechanism="flood_evacuation",
        capability="flood_evacuation",
    )

    report = gis_codegen_scaffold(spec)

    assert report["ok"] is False
    assert report["status"] == "renderable"
    assert report["action"] == "render"
    assert report["capability"] == "flood_evacuation"
    assert "already renderable" in report["reason"]


def test_scaffold_unknown_capability_still_halts():
    spec = GISModelSpec(
        spatial_type="network",
        mechanism="missing",
        capability="missing_cell",
    )

    report = gis_codegen_scaffold(spec)

    assert report["ok"] is False
    assert report["status"] == "unknown_gap"
    assert report["action"] == "halt"
    assert report["capability"] == "missing_cell"


def test_preflight_classifies_social_spatial_as_renderable():
    spec = GISModelSpec(
        spatial_type="coupled",
        mechanism="social_spatial_contagion",
        capability="social_spatial_contagion",
    )

    report = gis_codegen_preflight(spec)

    assert report["ok"] is True
    assert report["status"] == "renderable"
    assert report["action"] == "render"
    assert report["capability"] == "social_spatial_contagion"
    assert report["coupling"] == "spatial_social"
    assert report["gate"] == "social_lift_gate"


def test_preflight_classifies_point_network_risk_as_renderable():
    spec = GISModelSpec(
        spatial_type="point",
        mechanism="point_network_risk",
        capability="point_network_risk",
    )

    report = gis_codegen_preflight(spec)

    assert report["ok"] is True
    assert report["status"] == "renderable"
    assert report["action"] == "render"
    assert report["capability"] == "point_network_risk"
    assert report["coupling"] == "point_network"
    assert report["gate"] == "point_network_risk_gate"


def test_preflight_classifies_polygon_point_zoning_as_renderable():
    spec = GISModelSpec(
        spatial_type="polygon",
        mechanism="polygon_point_zoning",
        capability="polygon_point_zoning",
    )

    report = gis_codegen_preflight(spec)

    assert report["ok"] is True
    assert report["status"] == "renderable"
    assert report["action"] == "render"
    assert report["capability"] == "polygon_point_zoning"
    assert report["coupling"] == "polygon_point"
    assert report["gate"] == "polygon_point_zoning_gate"


def test_preflight_classifies_raster_spatial_validation_as_renderable():
    spec = GISModelSpec(
        spatial_type="validation",
        mechanism="raster_spatial_validation",
        capability="raster_spatial_validation",
    )

    report = gis_codegen_preflight(spec)

    assert report["ok"] is True
    assert report["status"] == "renderable"
    assert report["action"] == "render"
    assert report["capability"] == "raster_spatial_validation"
    assert report["gate"] == "raster_validation_gate"


def test_preflight_classifies_raster_spatial_calibration_as_renderable():
    spec = GISModelSpec(
        spatial_type="calibration",
        mechanism="raster_spatial_calibration",
        capability="raster_spatial_calibration",
    )

    report = gis_codegen_preflight(spec)

    assert report["ok"] is True
    assert report["status"] == "renderable"
    assert report["action"] == "render"
    assert report["capability"] == "raster_spatial_calibration"
    assert report["gate"] == "raster_spatial_calibration_gate"


def test_preflight_classifies_mechanism_threshold_adoption_as_renderable():
    spec = GISModelSpec(
        spatial_type="mechanism",
        mechanism="threshold_adoption",
        capability="mechanism_threshold_adoption",
    )

    report = gis_codegen_preflight(spec)

    assert report["ok"] is True
    assert report["status"] == "renderable"
    assert report["action"] == "render"
    assert report["capability"] == "mechanism_threshold_adoption"
    assert report["gate"] == "mechanism_space_gate"


def test_preflight_classifies_temporal_flood_as_renderable():
    spec = GISModelSpec(
        spatial_type="temporal",
        mechanism="temporal_flood_evacuation",
        capability="temporal_flood_evacuation",
    )

    report = gis_codegen_preflight(spec)

    assert report["ok"] is True
    assert report["status"] == "renderable"
    assert report["action"] == "render"
    assert report["temporal"] is True
    assert report["dynamic"] is False


def test_preflight_classifies_dynamic_flood_as_renderable():
    spec = GISModelSpec(
        spatial_type="network",
        mechanism="dynamic_flood_evacuation",
        capability="dynamic_flood_evacuation",
    )

    report = gis_codegen_preflight(spec)

    assert report["ok"] is True
    assert report["status"] == "renderable"
    assert report["action"] == "render"
    assert report["temporal"] is True
    assert report["dynamic"] is True


def test_preflight_classifies_dynamic_congestion_as_renderable():
    spec = GISModelSpec(
        spatial_type="network",
        mechanism="dynamic_congestion_routing",
        capability="dynamic_congestion_routing",
    )

    report = gis_codegen_preflight(spec)

    assert report["ok"] is True
    assert report["status"] == "renderable"
    assert report["action"] == "render"
    assert report["temporal"] is False
    assert report["dynamic"] is True
    assert report["gate"] == "dynamic_congestion_reroute_gate"


def test_preflight_classifies_unknown_explicit_capability():
    spec = GISModelSpec(
        spatial_type="network",
        mechanism="missing",
        capability="missing_cell",
    )

    report = gis_codegen_preflight(spec)

    assert report["ok"] is False
    assert report["status"] == "unknown_gap"
    assert report["action"] == "halt"
    assert report["capability"] == "missing_cell"
    assert "unknown capability" in report["reason"]


def test_preflight_classifies_capability_mismatch_as_invalid_spec():
    spec = GISModelSpec(
        spatial_type="raster",
        mechanism="sir",
        capability="flood_evacuation",
    )

    report = gis_codegen_preflight(spec)

    assert report["ok"] is False
    assert report["status"] == "invalid_spec"
    assert report["action"] == "halt"
    assert report["capability"] == "flood_evacuation"
    assert "does not match" in report["reason"]


def test_preflight_classifies_invalid_implicit_spec():
    spec = GISModelSpec(spatial_type="network", mechanism="social_spatial_contagion")

    report = gis_codegen_preflight(spec)

    assert report["ok"] is False
    assert report["status"] == "invalid_spec"
    assert report["action"] == "halt"
    assert report["capability"] == ""
    assert "mechanism" in report["reason"]


def test_self_extension_gap_gate_passes_and_states_limitation():
    ok, desc = gis_self_extension_gap_gate()

    assert ok, desc
    assert "deterministic gap/halt" in desc
    assert "not self-generating" in desc


def test_self_extension_scaffold_gate_passes_and_states_boundary():
    ok, desc = gis_self_extension_scaffold_gate()

    assert ok, desc
    assert "scaffold" in desc
    assert "FIRES on a real registered gap" in desc
    assert "refuses renderable" in desc
    assert "generates no code" in desc


# ── the self-extension loop, exercised on a REAL registered gap ──

def test_preflight_classifies_spatial_method_transfer_as_registered_gap():
    """The method-transfer capability is registered in the runtime registry but
    not renderable — a genuine standing gap, so the loop's gap path is real, not
    vacuous."""
    spec = GISModelSpec(
        spatial_type="method_transfer",
        mechanism="ricci_curvature",
        capability="spatial_method_transfer",
    )
    report = gis_codegen_preflight(spec)
    assert report["ok"] is False
    assert report["status"] == "registered_gap"
    assert report["action"] == "halt"
    assert report["renderable"] is False


def test_scaffold_fires_on_registered_gap_and_halts_to_human():
    spec = GISModelSpec(
        spatial_type="method_transfer",
        mechanism="ricci_curvature",
        capability="spatial_method_transfer",
    )
    report = gis_codegen_scaffold(spec)
    assert report["ok"] is True
    assert report["status"] == "scaffold_ready"
    assert report["action"] == "scaffold"
    assert report["required_human_review"] is True
    assert report["generates_code"] is False
    assert report["gate"] == "spatial_method_transfer_gate"
    assert report["steps"]                       # a bounded work-surface, not code


def test_gap_to_renderable_transition_fires_once():
    """The auto-fill transition the loop is meant to perform, demonstrated once:
    a registered gap -> scaffold -> (implement + gate) -> renderable. Done via a
    fixture capability injected into the registry so the real one stays an honest gap."""
    from dataclasses import replace
    import pytest
    from abm_auto.gis import _capabilities as caps

    fixture = caps.GISCapability(
        key="_fixture_gap", spatial_type="_fx", mechanism="_fx",
        layers=("RasterSpace",), renderable=False,
        required_tokens=("foo", "foo_gate"), gate="foo_gate",
    )
    patched = dict(caps.CAPABILITIES)
    patched["_fixture_gap"] = fixture
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(caps, "CAPABILITIES", patched)
        spec = GISModelSpec(spatial_type="_fx", mechanism="_fx", capability="_fixture_gap")
        # BEFORE: a registered gap that scaffolds + halts
        assert gis_codegen_preflight(spec)["status"] == "registered_gap"
        assert gis_codegen_scaffold(spec)["status"] == "scaffold_ready"
        # the loop FILLS it: implementation + gate pass -> mark renderable
        patched["_fixture_gap"] = replace(fixture, renderable=True)
        # AFTER: the same request now renders (gap closed end-to-end)
        after = gis_codegen_preflight(spec)
        assert after["status"] == "renderable"
        assert after["action"] == "render"
