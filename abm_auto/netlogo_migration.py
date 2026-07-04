"""Manifest-driven NetLogo semantic migration gate.

This module migrates a small NetLogo-like semantic manifest into the existing
native ``NetLogoWorld`` cells and a MIR summary. It is not a NetLogo parser and
does not execute NetLogo procedures.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from abm_auto.mir._schema import MIR, MIRMetadata, MIRProcess, MIRRun
from abm_auto.netlogo_semantics import NetLogoWorld

SCHEMA = "abm-auto/netlogo-semantic-migration/v1"
SUPPORTED_SCHEDULES = frozenset({"sequential", "random_order"})
REQUIRED_EXPECTED_FIELDS = frozenset({
    "breeds",
    "link_count",
    "monitor_records",
    "patch_count",
    "ticks",
    "turtle_count",
})


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int)


def _is_non_negative_int(value: Any) -> bool:
    return _is_int(value) and value >= 0


def load_netlogo_migration_spec(path: Path) -> dict:
    """Load a NetLogo semantic migration JSON spec."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_netlogo_migration_spec(spec: dict) -> dict:
    """Validate the manifest shape before constructing a NetLogoWorld."""
    if not isinstance(spec, dict):
        return {
            "ok": False,
            "issues": ["spec must be a JSON object"],
            "model_id": None,
            "turtle_count": 0,
            "patch_count": 0,
            "link_count": 0,
            "monitor_count": 0,
        }

    issues: list[str] = []
    if spec.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA!r}")
    if not _is_nonempty_string(spec.get("model_id")):
        issues.append("model_id must be a non-empty string")
    if not _is_nonempty_string(spec.get("title")):
        issues.append("title must be a non-empty string")
    if not _is_nonempty_string(spec.get("boundary_note")):
        issues.append("boundary_note must be a non-empty string")

    world = spec.get("world")
    if not isinstance(world, dict):
        issues.append("world must be an object")
        world = {}
    schedule = world.get("schedule")
    if schedule not in SUPPORTED_SCHEDULES:
        issues.append("world.schedule must be sequential or random_order")
    if not _is_non_negative_int(world.get("seed")):
        issues.append("world.seed must be a non-negative integer")
    if "globals" in world and not isinstance(world["globals"], dict):
        issues.append("world.globals must be an object")

    patches = world.get("patches")
    if not isinstance(patches, dict):
        issues.append("world.patches must be an object")
        patches = {}
    bounds = {
        name: patches.get(name)
        for name in ("min_pxcor", "max_pxcor", "min_pycor", "max_pycor")
    }
    for name, value in bounds.items():
        if not _is_int(value):
            issues.append(f"world.patches.{name} must be an integer")
    bounds_are_ints = all(_is_int(value) for value in bounds.values())
    bounds_ordered = (
        bounds_are_ints
        and bounds["min_pxcor"] <= bounds["max_pxcor"]
        and bounds["min_pycor"] <= bounds["max_pycor"]
    )
    if bounds_are_ints and not bounds_ordered:
        issues.append("world.patches min/max bounds are not ordered")
    if "state" in patches and not isinstance(patches["state"], dict):
        issues.append("world.patches.state must be an object")

    turtles = spec.get("turtles")
    if not isinstance(turtles, list) or not turtles:
        issues.append("turtles must be a non-empty list")
        turtles = []
    migration_turtle_count = 0
    breed_counts: Counter[str] = Counter()
    for idx, group in enumerate(turtles):
        prefix = f"turtles[{idx}]"
        if not isinstance(group, dict):
            issues.append(f"{prefix} must be an object")
            continue
        breed = group.get("breed")
        if not _is_nonempty_string(breed):
            issues.append(f"{prefix}.breed must be a non-empty string")
            breed = ""
        count = group.get("count")
        if not (_is_int(count) and count > 0):
            issues.append(f"{prefix}.count must be a positive integer")
            count = 0
        if "state" in group and not isinstance(group["state"], dict):
            issues.append(f"{prefix}.state must be an object")
        positions = group.get("positions")
        if positions is not None:
            if not isinstance(positions, list):
                issues.append(f"{prefix}.positions must be a list")
                positions = []
            if count and len(positions) != count:
                issues.append(f"{prefix}.positions length must equal count")
            for pos_idx, position in enumerate(positions):
                pos_prefix = f"{prefix}.positions[{pos_idx}]"
                if (
                    not isinstance(position, list)
                    or len(position) != 2
                    or not all(_is_int(value) for value in position)
                ):
                    issues.append(f"{pos_prefix} must be [x, y] integers")
                    continue
                if bounds_are_ints and not (
                    bounds["min_pxcor"] <= position[0] <= bounds["max_pxcor"]
                    and bounds["min_pycor"] <= position[1] <= bounds["max_pycor"]
                ):
                    issues.append(f"{pos_prefix} is outside patch grid")
        migration_turtle_count += count
        if breed:
            breed_counts[str(breed)] += count

    links = spec.get("links", [])
    if not isinstance(links, list):
        issues.append("links must be a list")
        links = []
    for idx, link in enumerate(links):
        prefix = f"links[{idx}]"
        if not isinstance(link, dict):
            issues.append(f"{prefix} must be an object")
            continue
        for endpoint in ("end1", "end2"):
            value = link.get(endpoint)
            if not _is_int(value):
                issues.append(f"{prefix}.{endpoint} must be an integer")
            elif value < 0 or value >= migration_turtle_count:
                issues.append(f"{prefix}.{endpoint} references missing turtle id {value}")
        if not _is_nonempty_string(link.get("breed", "links")):
            issues.append(f"{prefix}.breed must be a non-empty string")
        if "directed" in link and not isinstance(link["directed"], bool):
            issues.append(f"{prefix}.directed must be boolean")

    ticks = spec.get("ticks")
    if not _is_non_negative_int(ticks):
        issues.append("ticks must be a non-negative integer")

    monitors = spec.get("monitors")
    if not isinstance(monitors, list) or not monitors:
        issues.append("monitors must be a non-empty list")
        monitors = []
    for idx, monitor in enumerate(monitors):
        prefix = f"monitors[{idx}]"
        if not isinstance(monitor, dict):
            issues.append(f"{prefix} must be an object")
            continue
        if not _is_nonempty_string(monitor.get("name")):
            issues.append(f"{prefix}.name must be a non-empty string")
        reporter = monitor.get("reporter")
        if not _is_supported_reporter(reporter):
            issues.append(f"{prefix}.reporter is unsupported")

    expected = spec.get("expected")
    if not isinstance(expected, dict):
        issues.append("expected must be an object")
        expected = {}
    for field in sorted(REQUIRED_EXPECTED_FIELDS):
        if field not in expected:
            issues.append(f"expected.{field} is required")

    patch_count = _patch_count(bounds) if bounds_ordered else 0
    return {
        "ok": not issues,
        "issues": issues,
        "model_id": spec.get("model_id"),
        "turtle_count": migration_turtle_count,
        "patch_count": patch_count,
        "link_count": len(links),
        "monitor_count": len(monitors),
    }


def run_netlogo_semantic_migration(spec: dict) -> dict:
    """Build a NetLogoWorld from a migration manifest and summarize it."""
    validation = validate_netlogo_migration_spec(spec)
    if not validation["ok"]:
        return {
            "ok": False,
            "issues": validation["issues"],
            "model_id": spec.get("model_id") if isinstance(spec, dict) else None,
            "ticks": 0,
            "turtle_count": 0,
            "patch_count": 0,
            "link_count": 0,
            "breeds": {},
            "monitor_records": [],
            "mir": {},
        }

    world = _build_world(spec)
    for monitor in spec["monitors"]:
        world.monitor(monitor["name"], _monitor_function(monitor["reporter"]))
    world.collect_monitors()
    if spec["ticks"] > 0:
        world.tick(spec["ticks"])
    world.collect_monitors()

    breeds = Counter(turtle.breed for turtle in world.turtles.ordered())
    mir = netlogo_semantic_migration_to_mir(spec)
    return {
        "ok": True,
        "issues": [],
        "model_id": spec["model_id"],
        "ticks": world.t,
        "turtle_count": len(world.turtles),
        "patch_count": len(world.patches),
        "link_count": len(world.links),
        "breeds": dict(sorted(breeds.items())),
        "monitor_records": list(world.monitor_records),
        "mir": mir.to_dict(),
    }


def netlogo_semantic_migration_to_mir(spec: dict) -> MIR:
    """Create a MIR summary for a validated NetLogo migration manifest."""
    validation = validate_netlogo_migration_spec(spec)
    if not validation["ok"]:
        first = "; ".join(validation["issues"][:3])
        raise ValueError(f"invalid NetLogo migration spec: {first}")
    world = spec["world"]
    patches = world["patches"]
    turtle_entities = [
        {
            "kind": "turtle_breed",
            "breed": group["breed"],
            "count": group["count"],
            "state_keys": sorted((group.get("state") or {}).keys()),
        }
        for group in spec["turtles"]
    ]
    link_entities = [
        {
            "kind": "link_breed",
            "breed": link.get("breed", "links"),
            "directed": bool(link.get("directed", False)),
        }
        for link in spec.get("links", [])
    ]
    entities = [
        {
            "kind": "patch_grid",
            "bounds": {
                "min_pxcor": patches["min_pxcor"],
                "max_pxcor": patches["max_pxcor"],
                "min_pycor": patches["min_pycor"],
                "max_pycor": patches["max_pycor"],
            },
            "state_keys": sorted((patches.get("state") or {}).keys()),
        },
        *turtle_entities,
        *link_entities,
    ]
    state = [
        {"scope": "global", "name": name, "value": value}
        for name, value in sorted((world.get("globals") or {}).items())
    ] + [
        {"scope": "patch", "name": name, "default": value}
        for name, value in sorted((patches.get("state") or {}).items())
    ]
    relations = [
        {
            "kind": "link",
            "end1": link["end1"],
            "end2": link["end2"],
            "breed": link.get("breed", "links"),
            "directed": bool(link.get("directed", False)),
        }
        for link in spec.get("links", [])
    ]
    return MIR(
        metadata=MIRMetadata(
            name=spec["model_id"],
            description=spec["title"],
            domain="netlogo",
            provenance={"source": "netlogo_semantic_migration_manifest"},
        ),
        entities=entities,
        state=state,
        relations=relations,
        processes=[MIRProcess(
            mechanism="netlogo_semantic_migration",
            params={"monitor_reporters": [m["reporter"] for m in spec["monitors"]]},
        )],
        metrics=[
            {"kind": "monitor", "name": m["name"], "reporter": m["reporter"]}
            for m in spec["monitors"]
        ],
        run=MIRRun(
            seed=world["seed"],
            params={"ticks": spec["ticks"], "schedule": world["schedule"]},
        ),
        trace={
            "source_format": "netlogo_semantic_migration_manifest",
            "boundary_note": spec["boundary_note"],
        },
    )


def netlogo_semantic_migration_gate(spec: dict) -> tuple[bool, str]:
    """Gate validation, runtime expected values, and MIR round-trip stability."""
    result = run_netlogo_semantic_migration(spec)
    if not result["ok"]:
        first = "; ".join(result["issues"][:3])
        return False, f"NetLogo semantic migration gate failed validation: {first}"

    expected = spec["expected"]
    for key in ("ticks", "turtle_count", "patch_count", "link_count", "breeds"):
        if result[key] != expected[key]:
            return False, f"expected {key}={expected[key]}, got {result[key]}"
    if len(result["monitor_records"]) != expected["monitor_records"]:
        return False, (
            f"expected monitor_records={expected['monitor_records']}, "
            f"got {len(result['monitor_records'])}"
        )
    mir = netlogo_semantic_migration_to_mir(spec)
    if MIR.from_json(mir.to_json()).to_dict() != mir.to_dict():
        return False, "MIR round-trip changed semantic migration summary"
    return (
        True,
        "NetLogo semantic migration gate passed "
        f"(model_id={spec['model_id']}, turtles={result['turtle_count']}, "
        f"patches={result['patch_count']}, links={result['link_count']}); "
        "manifest migration only, not a NetLogo parser and not NetLogo procedure execution",
    )


def _patch_count(bounds: dict[str, Any]) -> int:
    return (bounds["max_pxcor"] - bounds["min_pxcor"] + 1) * (
        bounds["max_pycor"] - bounds["min_pycor"] + 1
    )


def _build_world(spec: dict) -> NetLogoWorld:
    world_spec = spec["world"]
    patches = world_spec["patches"]
    world = NetLogoWorld(
        seed=world_spec["seed"],
        schedule=world_spec["schedule"],
        globals=world_spec.get("globals") or {},
    )
    world.create_patches(
        patches["min_pxcor"],
        patches["max_pxcor"],
        patches["min_pycor"],
        patches["max_pycor"],
        **(patches.get("state") or {}),
    )
    turtles = []
    for group in spec["turtles"]:
        created = world.create_turtles(
            group["count"],
            breed=group["breed"],
            **(group.get("state") or {}),
        ).ordered()
        for turtle, position in zip(created, group.get("positions") or [], strict=False):
            turtle.setxy(position[0], position[1])
        turtles.extend(created)
    for link in spec.get("links", []):
        world.create_link(
            turtles[link["end1"]],
            turtles[link["end2"]],
            directed=bool(link.get("directed", False)),
            breed=link.get("breed", "links"),
        )
    return world


def _is_supported_reporter(reporter: Any) -> bool:
    if reporter in {"count turtles", "count patches", "count links"}:
        return True
    return isinstance(reporter, str) and re.fullmatch(r"count breed [A-Za-z0-9_\-?]+", reporter) is not None


def _monitor_function(reporter: str) -> Callable[[NetLogoWorld], Any]:
    if reporter == "count turtles":
        return lambda world: len(world.turtles)
    if reporter == "count patches":
        return lambda world: len(world.patches)
    if reporter == "count links":
        return lambda world: len(world.links)
    match = re.fullmatch(r"count breed ([A-Za-z0-9_\-?]+)", reporter)
    if match:
        breed = match.group(1)
        return lambda world: len(world.turtles.with_breed(breed))
    raise ValueError(f"unsupported monitor reporter {reporter!r}")


__all__ = [
    "SCHEMA",
    "load_netlogo_migration_spec",
    "netlogo_semantic_migration_gate",
    "netlogo_semantic_migration_to_mir",
    "run_netlogo_semantic_migration",
    "validate_netlogo_migration_spec",
]
