from __future__ import annotations

import json
from pathlib import Path

from abm_auto.mir import MIR
from abm_auto.netlogo_migration import (
    SCHEMA,
    load_netlogo_migration_spec,
    netlogo_semantic_migration_gate,
    netlogo_semantic_migration_to_mir,
    run_netlogo_semantic_migration,
    validate_netlogo_migration_spec,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_SPEC = REPO_ROOT / "docs/reproduce/netlogo-semantic-migration/example-spec.json"


def _valid_spec() -> dict:
    return {
        "schema": SCHEMA,
        "model_id": "wolf-sheep-mini-migration-v1",
        "title": "Wolf Sheep Mini Migration",
        "world": {
            "seed": 0,
            "schedule": "sequential",
            "patches": {
                "min_pxcor": 0,
                "max_pxcor": 1,
                "min_pycor": 0,
                "max_pycor": 0,
                "state": {"grass": 1},
            },
            "globals": {"energy_cost": 1},
        },
        "turtles": [
            {
                "breed": "sheep",
                "count": 2,
                "state": {"energy": 3},
                "positions": [[0, 0], [1, 0]],
            },
            {
                "breed": "wolf",
                "count": 1,
                "state": {"energy": 5},
                "positions": [[0, 0]],
            },
        ],
        "links": [
            {"end1": 0, "end2": 1, "breed": "social-links", "directed": False}
        ],
        "ticks": 2,
        "monitors": [
            {"name": "count_turtles", "reporter": "count turtles"},
            {"name": "count_sheep", "reporter": "count breed sheep"},
            {"name": "count_links", "reporter": "count links"},
        ],
        "expected": {
            "ticks": 2,
            "turtle_count": 3,
            "patch_count": 2,
            "link_count": 1,
            "breeds": {"sheep": 2, "wolf": 1},
            "monitor_records": 2,
        },
        "boundary_note": "Manifest migration only; not NetLogo parser or procedure execution.",
    }


def test_valid_spec_validates_runs_and_exports_mir():
    spec = _valid_spec()

    validation = validate_netlogo_migration_spec(spec)
    result = run_netlogo_semantic_migration(spec)
    mir = netlogo_semantic_migration_to_mir(spec)
    restored = MIR.from_json(mir.to_json())

    assert validation == {
        "ok": True,
        "issues": [],
        "model_id": "wolf-sheep-mini-migration-v1",
        "turtle_count": 3,
        "patch_count": 2,
        "link_count": 1,
        "monitor_count": 3,
    }
    assert result["ok"], result["issues"]
    assert result["ticks"] == 2
    assert result["turtle_count"] == 3
    assert result["patch_count"] == 2
    assert result["link_count"] == 1
    assert result["breeds"] == {"sheep": 2, "wolf": 1}
    assert len(result["monitor_records"]) == 2
    assert result["monitor_records"][0]["count_sheep"] == 2
    assert result["monitor_records"][1]["t"] == 2
    assert mir.metadata.domain == "netlogo"
    assert mir.processes[0].mechanism == "netlogo_semantic_migration"
    assert mir.run.params["ticks"] == 2
    assert mir.trace["source_format"] == "netlogo_semantic_migration_manifest"
    assert restored.to_dict() == mir.to_dict()


def test_validation_rejects_schema_schedule_bounds_positions_links_and_reporters():
    spec = _valid_spec()
    spec["schema"] = "wrong"
    spec["world"]["schedule"] = "forever"
    spec["world"]["patches"]["min_pxcor"] = 2
    spec["turtles"][0]["positions"] = [[0, 0]]
    spec["turtles"][1]["positions"] = [[4, 4]]
    spec["links"][0]["end2"] = 99
    spec["monitors"].append({"name": "bad", "reporter": "mean [energy] of turtles"})

    result = validate_netlogo_migration_spec(spec)

    assert not result["ok"]
    assert "schema must be 'abm-auto/netlogo-semantic-migration/v1'" in result["issues"]
    assert "world.schedule must be sequential or random_order" in result["issues"]
    assert "world.patches min/max bounds are not ordered" in result["issues"]
    assert "turtles[0].positions length must equal count" in result["issues"]
    assert "turtles[1].positions[0] is outside patch grid" in result["issues"]
    assert "links[0].end2 references missing turtle id 99" in result["issues"]
    assert "monitors[3].reporter is unsupported" in result["issues"]


def test_validation_rejects_missing_expected_fields():
    spec = _valid_spec()
    del spec["expected"]["monitor_records"]

    result = validate_netlogo_migration_spec(spec)

    assert not result["ok"]
    assert "expected.monitor_records is required" in result["issues"]


def test_gate_fails_when_runtime_does_not_match_expected():
    spec = _valid_spec()
    spec["expected"]["turtle_count"] = 99

    ok, desc = netlogo_semantic_migration_gate(spec)

    assert ok is False
    assert "expected turtle_count=99, got 3" in desc


def test_committed_example_spec_gates_with_boundary_message():
    spec = load_netlogo_migration_spec(SEED_SPEC)

    ok, desc = netlogo_semantic_migration_gate(spec)
    result = run_netlogo_semantic_migration(spec)

    assert ok, desc
    assert result["model_id"] == "wolf-sheep-mini-migration-v1"
    assert "not a NetLogo parser" in desc
    assert "not NetLogo procedure execution" in desc


def test_committed_example_spec_is_stable_json():
    loaded = json.loads(SEED_SPEC.read_text(encoding="utf-8"))

    assert loaded["schema"] == SCHEMA
    assert loaded["expected"]["breeds"] == {"sheep": 2, "wolf": 1}
