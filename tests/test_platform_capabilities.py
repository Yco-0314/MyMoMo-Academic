from __future__ import annotations

from pathlib import Path

from abm_auto.platform_capabilities import (
    list_platform_capabilities,
    load_platform_capability_registry,
    validate_platform_capability_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "docs/reproduce/platform-capabilities/registry.json"


def _entry(**overrides):
    entry = {
        "key": "gama_species",
        "domain": "gama",
        "concept": "species",
        "disposition": "native",
        "evidence_level": "E0",
        "source": "docs/reproduce/gama-semantic-coverage/STATUS.md",
        "next_action": "reuse as semantic pressure in MIR and platform docs",
        "boundary_note": "does not imply GAML compatibility",
    }
    entry.update(overrides)
    return entry


def _registry(**overrides):
    registry = {
        "schema": "abm-auto/platform-capability-registry/v1",
        "title": "MyMoMo Platform Capability Disposition Registry",
        "entries": [_entry()],
    }
    registry.update(overrides)
    return registry


def test_valid_registry_passes():
    result = validate_platform_capability_registry(_registry())

    assert result == {"ok": True, "issues": [], "entry_count": 1}


def test_duplicate_keys_fail():
    registry = _registry()
    registry["entries"].append(dict(registry["entries"][0]))

    result = validate_platform_capability_registry(registry)

    assert result["ok"] is False
    assert "duplicate capability key gama_species" in result["issues"]


def test_invalid_disposition_and_evidence_level_fail():
    registry = _registry(entries=[
        _entry(disposition="maybe", evidence_level="E9"),
    ])

    result = validate_platform_capability_registry(registry)

    assert result["ok"] is False
    assert (
        "entries[0].disposition must be one of audit_baseline, bridge, native, out_of_scope"
        in result["issues"]
    )
    assert "entries[0].evidence_level must be E0-E6" in result["issues"]


def test_list_platform_capabilities_filters_in_registry_order():
    registry = _registry(entries=[
        _entry(key="gama_species", domain="gama", disposition="native"),
        _entry(
            key="transport_sumo_matsim_bridge",
            domain="transport",
            concept="SUMO/MATSim bridge",
            disposition="bridge",
            evidence_level="E1",
            next_action="define bridge manifest",
            boundary_note="does not prove traffic-flow validity",
        ),
    ])

    result = list_platform_capabilities(registry, disposition="bridge")

    assert [entry["key"] for entry in result] == ["transport_sumo_matsim_bridge"]


def test_committed_registry_validates_and_loads():
    registry = load_platform_capability_registry(REGISTRY_PATH)

    result = validate_platform_capability_registry(registry)

    assert result["ok"] is True
    assert result["entry_count"] >= 7
    bridge_entries = list_platform_capabilities(registry, domain="platform", disposition="bridge")
    assert [entry["key"] for entry in bridge_entries] == [
        "unified_abm_bridge_contract",
        "terrain_bridge_manifest",
    ]
    assert "not a unified simulator" in bridge_entries[0]["boundary_note"]
    assert "not a 3D engine" in bridge_entries[1]["boundary_note"]
