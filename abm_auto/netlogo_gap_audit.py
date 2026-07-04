"""Deterministic feature-family audit for parsed NetLogo fixtures.

This module is not a NetLogo parser or executor. It scans a parsed
``NetLogoModel`` for coarse semantic families so fixture pressure can drive the
next native cells without overclaiming arbitrary ``.nlogo`` support.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol


class ParsedNetLogoModel(Protocol):
    name: str
    code_text: str
    controls: object


@dataclass(frozen=True)
class NetLogoSemanticAudit:
    """Supported-vs-gap report for one parsed NetLogo model."""

    model_name: str
    supported: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    unclassified: tuple[str, ...] = ()
    evidence: dict[str, list[str]] = field(default_factory=dict)

    @property
    def can_run_natively(self) -> bool:
        return not self.gaps and not self.unclassified

    def to_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "can_run_natively": self.can_run_natively,
            "supported": list(self.supported),
            "gaps": list(self.gaps),
            "unclassified": list(self.unclassified),
            "evidence": {key: list(value) for key, value in sorted(self.evidence.items())},
        }


_SUPPORTED_PATTERNS: dict[str, tuple[str, ...]] = {
    "agentset_ask": (r"\bask\b",),
    "cardinal_movement_adjacent": (r"\bsetxy\b",),
    "controls_sliders": (),
    "link_agents": (r"\blinks?\b",),
    "link_neighbors": (r"\blink-neighbors\b",),
    "metric_count_turtles_with": (r"\bcount\s+turtles\s+with\b",),
    "network_generation_minimal": (r"\bcreate-link-with\b",),
    "random_selection": (r"\bn-of\b", r"\bone-of\b"),
    "ticks": (r"\btick\b", r"\breset-ticks\b"),
    "turtle_state": (r"\bturtles-own\b", r"\bset\s+[A-Za-z0-9_\-?]+\b"),
}

_GAP_PATTERNS: dict[str, tuple[str, ...]] = {
    "agentset_expression_parser": (
        r"\bother\s+turtles\s+with\b",
        r"\blink-neighbor\?\b",
        r"\bmy-links\b",
    ),
    "code_tab_procedure_execution": (r"(?m)^\s*to(?:-report)?\s+[A-Za-z0-9_\-?]+",),
    "control_flow_parser": (r"\bifelse\b", r"\bwhile\b", r"\brepeat\b", r"\bstop\b"),
    "network_generation": (r"\bmin-one-of\b", r"\bdistance\b"),
    "random_number_semantics": (r"\brandom(?:-float)?\b",),
    "visual_layout": (r"\blayout-spring\b", r"\bset-default-shape\b", r"\bset\s+color\b"),
}


def audit_netlogo_model(model: ParsedNetLogoModel) -> NetLogoSemanticAudit:
    """Return a deterministic semantic coverage audit for a parsed NetLogo model."""

    scan_text = _audit_text(model)
    unclassified = _unclassified_code(model)
    evidence: dict[str, list[str]] = {}
    supported: set[str] = set()
    gaps: set[str] = set()

    for key, patterns in _SUPPORTED_PATTERNS.items():
        hits = _pattern_hits(scan_text, patterns)
        if key == "controls_sliders" and _has_sliders(model):
            hits.append("Interface sliders")
        if hits:
            supported.add(key)
            evidence[key] = sorted(set(hits))

    for key, patterns in _GAP_PATTERNS.items():
        hits = _pattern_hits(scan_text, patterns)
        if hits:
            gaps.add(key)
            evidence[key] = sorted(set(hits))

    return NetLogoSemanticAudit(
        model_name=str(getattr(model, "name", "")),
        supported=tuple(sorted(supported)),
        gaps=tuple(sorted(gaps)),
        unclassified=tuple(sorted(unclassified)),
        evidence={key: evidence[key] for key in sorted(evidence)},
    )


def _pattern_hits(code: str, patterns: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, code):
            hits.append(_normalize_evidence(match.group(0)))
    return hits


def _audit_text(model: ParsedNetLogoModel) -> str:
    parts = [_sanitize_netlogo_text(getattr(model, "code_text", "") or "")]
    controls = getattr(model, "controls", None)
    if controls is None:
        return "\n".join(parts)

    for monitor in getattr(controls, "monitors", ()):
        reporter = getattr(monitor, "reporter", "") or ""
        if reporter:
            parts.append(_sanitize_netlogo_text(reporter))

    for plot in getattr(controls, "plots", ()):
        for pen in getattr(plot, "pens", ()):
            update_command = getattr(pen, "update_command", "") or ""
            if update_command:
                parts.append(_sanitize_netlogo_text(update_command))

    return "\n".join(parts)


def _unclassified_code(model: ParsedNetLogoModel) -> list[str]:
    code = _sanitize_netlogo_text(getattr(model, "code_text", "") or "")
    for line in code.splitlines():
        text = line.strip()
        if not text:
            continue
        return ["code_tab_text"]
    return []


def _sanitize_netlogo_text(text: str) -> str:
    return "\n".join(_strip_strings(_strip_comment(line)) for line in text.splitlines())


def _strip_comment(line: str) -> str:
    in_string = False
    escaped = False
    for index, char in enumerate(line):
        if char == '"' and not escaped:
            in_string = not in_string
        if char == ";" and not in_string:
            return line[:index]
        escaped = char == "\\" and not escaped
    return line


def _strip_strings(line: str) -> str:
    out: list[str] = []
    in_string = False
    escaped = False
    for char in line:
        if char == '"' and not escaped:
            in_string = not in_string
            out.append(" ")
        elif not in_string:
            out.append(char)
        else:
            out.append(" ")
        escaped = char == "\\" and not escaped
    return "".join(out)


def _normalize_evidence(value: str) -> str:
    return " ".join(value.strip().split())


def _has_sliders(model: ParsedNetLogoModel) -> bool:
    controls = getattr(model, "controls", None)
    if controls is None:
        return False
    return bool(getattr(controls, "sliders", None))
