"""Deterministic GIS codegen self-extension preflight.

This module reports registry gaps. It does not generate code.
"""
from __future__ import annotations

from abm_auto.gis._capabilities import (
    GISCapability,
    get_capability,
    resolve_capability,
)
from abm_auto.gis._model_spec import GISModelSpec


_SCAFFOLD_FILES = (
    "abm_auto/gis/_capabilities.py",
    "abm_auto/gis/_templates.py",
    "tests/gis/test_capabilities.py",
    "tests/gis/test_codegen.py",
    "tests/gis/test_codegen_gate.py",
    "tests/gis/test_extractor.py",
    "tests/gis/test_self_extension.py",
    "docs/reproduce/coupled-seam/STATUS.md",
)

_SCAFFOLD_TEST_TARGETS = (
    "tests/gis/test_capabilities.py",
    "tests/gis/test_codegen.py",
    "tests/gis/test_codegen_gate.py",
    "tests/gis/test_extractor.py",
    "tests/gis/test_self_extension.py",
)


def _capability_report(
    cap: GISCapability,
    *,
    ok: bool,
    status: str,
    action: str,
    reason: str,
) -> dict:
    return {
        "ok": ok,
        "status": status,
        "action": action,
        "capability": cap.key,
        "spatial_type": cap.spatial_type,
        "mechanism": cap.mechanism,
        "renderable": cap.renderable,
        "layers": cap.layers,
        "coupling": cap.coupling,
        "temporal": cap.temporal,
        "dynamic": cap.dynamic,
        "gate": cap.gate,
        "required_tokens": cap.required_tokens,
        "reason": reason,
    }


def _halt_report(status: str, capability: str, reason: str) -> dict:
    return {
        "ok": False,
        "status": status,
        "action": "halt",
        "capability": capability,
        "reason": reason,
    }


def gis_codegen_preflight(spec) -> dict:
    """Classify a GIS codegen request before rendering or halting."""
    capability = getattr(spec, "capability", "") or ""
    try:
        cap = resolve_capability(spec.spatial_type, spec.mechanism, capability)
    except ValueError as exc:
        reason = str(exc)
        if capability:
            try:
                get_capability(capability)
            except ValueError:
                return _halt_report("unknown_gap", capability, reason)
        return _halt_report("invalid_spec", capability, reason)

    if cap.renderable:
        return _capability_report(
            cap,
            ok=True,
            status="renderable",
            action="render",
            reason="",
        )

    return _capability_report(
        cap,
        ok=False,
        status="registered_gap",
        action="halt",
        reason=f"capability {cap.key!r} is registered but not codegen-renderable",
    )


def gis_codegen_scaffold(spec) -> dict:
    """Return a structured scaffold package for registered codegen gaps.

    This does not generate code. It names the deterministic work surface that a
    later implementation phase must fill and gate.
    """
    preflight = gis_codegen_preflight(spec)
    if preflight["status"] == "registered_gap":
        return {
            "ok": True,
            "status": "scaffold_ready",
            "action": "scaffold",
            "capability": preflight["capability"],
            "spatial_type": preflight["spatial_type"],
            "mechanism": preflight["mechanism"],
            "layers": preflight["layers"],
            "coupling": preflight["coupling"],
            "gate": preflight["gate"],
            "required_tokens": preflight["required_tokens"],
            "source_status": preflight["status"],
            "source_reason": preflight["reason"],
            "required_human_review": True,
            "generates_code": False,
            "files": _SCAFFOLD_FILES,
            "test_targets": _SCAFFOLD_TEST_TARGETS,
            "steps": (
                "write failing capability, render, fidelity, extractor, and preflight tests",
                "add or strengthen a deterministic gate before making the capability renderable",
                "implement the smallest template that calls existing GIS runtime functions",
                "run GIS and base-engine zero-change verification before merge",
            ),
            "reason": (
                f"capability {preflight['capability']!r} is registered but "
                "not codegen-renderable; scaffold requires human review and "
                "does not generate code"
            ),
        }

    if preflight["status"] == "renderable":
        report = dict(preflight)
        report["ok"] = False
        report["reason"] = (
            f"capability {preflight['capability']!r} is already renderable; "
            "call render instead of scaffold"
        )
        return report

    return preflight


def gis_self_extension_gap_gate() -> tuple[bool, str]:
    """Gate for deterministic gap/halt classification, not code generation."""
    checks = {
        "flood_renderable": gis_codegen_preflight(GISModelSpec(
            spatial_type="network",
            mechanism="flood_evacuation",
            capability="flood_evacuation",
        )),
        "mechanism_renderable": gis_codegen_preflight(GISModelSpec(
            spatial_type="mechanism",
            mechanism="contagion",
            capability="mechanism_contagion",
        )),
        # A REAL registered gap (ADR-019 layer E): runtime/gate exists, but the
        # runnable codegen template is not built yet. The loop must DETECT it and
        # halt to human instead of pretending it can render.
        "registered_gap": gis_codegen_preflight(GISModelSpec(
            spatial_type="method_transfer",
            mechanism="ricci_curvature",
            capability="spatial_method_transfer",
        )),
        "unknown_gap": gis_codegen_preflight(GISModelSpec(
            spatial_type="network",
            mechanism="missing",
            capability="missing_cell",
        )),
        "invalid_spec": gis_codegen_preflight(GISModelSpec(
            spatial_type="raster",
            mechanism="sir",
            capability="flood_evacuation",
        )),
    }
    expected = {
        "flood_renderable": (True, "renderable", "render"),
        "mechanism_renderable": (True, "renderable", "render"),
        "registered_gap": (False, "registered_gap", "halt"),
        "unknown_gap": (False, "unknown_gap", "halt"),
        "invalid_spec": (False, "invalid_spec", "halt"),
    }

    for label, report in checks.items():
        ok, status, action = expected[label]
        observed = (report["ok"], report["status"], report["action"])
        if observed != (ok, status, action):
            return False, f"{label} preflight mismatch: {report}"

    return (
        True,
        "deterministic gap/halt reporting distinguishes renderable, registered-gap, "
        "unknown, and invalid GIS codegen requests; a REAL codegen-template gap "
        "(spatial_method_transfer, ADR-019 layer E) is detected and halts to human "
        "even though its runtime gate exists — the loop is exercised, and this is "
        "not self-generating GIS capabilities",
    )


def gis_self_extension_scaffold_gate() -> tuple[bool, str]:
    """Gate for bounded scaffold reporting, not code generation."""
    # The scaffold path FIRES on a real registered codegen-template gap
    # (ADR-019 layer E).
    gap = gis_codegen_scaffold(GISModelSpec(
        spatial_type="method_transfer",
        mechanism="ricci_curvature",
        capability="spatial_method_transfer",
    ))
    mechanism = gis_codegen_scaffold(GISModelSpec(
        spatial_type="mechanism",
        mechanism="contagion",
        capability="mechanism_contagion",
    ))
    renderable = gis_codegen_scaffold(GISModelSpec(
        spatial_type="network",
        mechanism="flood_evacuation",
        capability="flood_evacuation",
    ))
    unknown = gis_codegen_scaffold(GISModelSpec(
        spatial_type="network",
        mechanism="missing",
        capability="missing_cell",
    ))

    if (gap["ok"], gap["status"], gap["action"]) != (True, "scaffold_ready", "scaffold"):
        return False, f"registered-gap scaffold did not fire: {gap}"
    if not (gap.get("required_human_review") and not gap.get("generates_code")):
        return False, f"scaffold must require human review and generate no code: {gap}"
    if (mechanism["ok"], mechanism["status"], mechanism["action"]) != (
        False,
        "renderable",
        "render",
    ):
        return False, f"mechanism scaffold refusal mismatch: {mechanism}"
    if (renderable["ok"], renderable["status"], renderable["action"]) != (
        False,
        "renderable",
        "render",
    ):
        return False, f"renderable scaffold mismatch: {renderable}"
    if (unknown["ok"], unknown["status"], unknown["action"]) != (
        False,
        "unknown_gap",
        "halt",
    ):
        return False, f"unknown scaffold mismatch: {unknown}"

    return (
        True,
        "self-extension scaffold FIRES on a real registered codegen-template gap "
        "(spatial_method_transfer): a bounded work-surface that requires human review "
        "and generates no code; it still refuses renderable capabilities and halts "
        "unknown requests",
    )
