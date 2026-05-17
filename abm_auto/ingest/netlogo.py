"""
NetLogo .nlogo / .nlogox → story.md converter.

Supports both formats:
- .nlogo  — legacy text format (sections separated by @#$#@#$#@)
- .nlogox — NetLogo 7+ XML format

Parses Info tab and Code tab to extract:
- Model description and purpose
- Agent types (breeds) and their properties
- Global parameters (sliders)
- Spatial structure
- Update rules
- Output metrics

Then generates a story.md suitable for the abm-auto pipeline.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class NetLogoModel:
    """Parsed representation of a .nlogo model."""
    name: str = ""
    info_text: str = ""
    code_text: str = ""
    breeds: list[dict] = field(default_factory=list)       # [{name, plural, owns}]
    globals: list[str] = field(default_factory=list)
    sliders: list[dict] = field(default_factory=list)       # [{name, min, max, default, step}]
    plots: list[str] = field(default_factory=list)
    has_patches: bool = False
    world_width: int = 0
    world_height: int = 0
    is_wrapping: bool = True


def parse_nlogo(path: Path) -> NetLogoModel:
    """Parse a .nlogo or .nlogox file into structured components."""
    if path.suffix == ".nlogox":
        return _parse_nlogox(path)
    return _parse_nlogo_text(path)


def _parse_nlogo_text(path: Path) -> NetLogoModel:
    """Parse legacy .nlogo text format."""
    text = path.read_text(encoding="utf-8", errors="replace")
    model = NetLogoModel(name=path.stem)

    # .nlogo sections are separated by @#$#@#$#@
    sections = text.split("@#$#@#$#@")

    if len(sections) >= 1:
        model.code_text = sections[0].strip()
    if len(sections) >= 3:
        model.info_text = sections[2].strip()

    # Parse code section
    _parse_code(model)

    # Parse interface section for sliders & world dimensions
    if len(sections) >= 2:
        _parse_interface(model, sections[1])

    return model


def _parse_nlogox(path: Path) -> NetLogoModel:
    """Parse NetLogo 7+ .nlogox XML format."""
    tree = ET.parse(path)
    root = tree.getroot()
    model = NetLogoModel(name=path.stem)

    # Code
    code_el = root.find("code")
    if code_el is not None and code_el.text:
        model.code_text = code_el.text.strip()
        _parse_code(model)

    # Info
    info_el = root.find("info")
    if info_el is not None and info_el.text:
        model.info_text = info_el.text.strip()

    # Widgets — sliders, plots, view
    widgets_el = root.find("widgets")
    if widgets_el is not None:
        for slider in widgets_el.findall("slider"):
            attrs = slider.attrib
            name = attrs.get("variable", "")
            if name:
                model.sliders.append({
                    "name": name,
                    "min": _safe_float(attrs.get("min", "0")),
                    "max": _safe_float(attrs.get("max", "0")),
                    "default": _safe_float(attrs.get("default", "0")),
                    "step": _safe_float(attrs.get("step", "1")),
                })

        for plot in widgets_el.findall("plot"):
            display = plot.attrib.get("display", "")
            if display:
                model.plots.append(display)

        # World dimensions from view
        view = widgets_el.find("view")
        if view is not None:
            attrs = view.attrib
            min_px = int(attrs.get("minPxcor", "0"))
            max_px = int(attrs.get("maxPxcor", "0"))
            min_py = int(attrs.get("minPycor", "0"))
            max_py = int(attrs.get("maxPycor", "0"))
            model.world_width = max_px - min_px + 1
            model.world_height = max_py - min_py + 1
            model.is_wrapping = (
                attrs.get("wrappingAllowedX", "true").lower() == "true"
                and attrs.get("wrappingAllowedY", "true").lower() == "true"
            )

    return model


def _strip_nlogo_comments(text: str) -> str:
    """Remove NetLogo comments (;; ...) from text."""
    return re.sub(r";[^\n]*", "", text)


def _extract_nlogo_vars(block_text: str) -> list[str]:
    """Extract variable names from a NetLogo own/globals block, ignoring comments."""
    clean = _strip_nlogo_comments(block_text)
    return re.findall(r"[\w][\w?-]*", clean)


def _parse_code(model: NetLogoModel) -> None:
    """Extract breeds, globals, and structural info from code."""
    code = model.code_text

    # Globals
    globals_match = re.search(r"globals\s*\[(.*?)\]", code, re.DOTALL)
    if globals_match:
        model.globals = _extract_nlogo_vars(globals_match.group(1))

    # Breeds
    for match in re.finditer(r"breed\s*\[\s*([\w-]+)\s+([\w-]+)\s*\]", code):
        plural, singular = match.group(1), match.group(2)
        # Find <breed>-own block
        owns_match = re.search(
            rf"{plural}-own\s*\[(.*?)\]", code, re.DOTALL
        )
        owns = _extract_nlogo_vars(owns_match.group(1)) if owns_match else []
        model.breeds.append({"singular": singular, "plural": plural, "owns": owns})

    # Turtles-own (default breed)
    turtles_own = re.search(r"turtles-own\s*\[(.*?)\]", code, re.DOTALL)
    if turtles_own and not model.breeds:
        owns = _extract_nlogo_vars(turtles_own.group(1))
        model.breeds.append({"singular": "turtle", "plural": "turtles", "owns": owns})

    # Patches
    patches_own = re.search(r"patches-own\s*\[(.*?)\]", code, re.DOTALL)
    if patches_own:
        model.has_patches = True


def _parse_interface(model: NetLogoModel, interface_text: str) -> None:
    """Extract sliders and world config from interface section."""
    lines = interface_text.strip().split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Slider: type "SLIDER" followed by metadata lines
        if line == "SLIDER":
            slider = _parse_slider_block(lines, i)
            if slider:
                model.sliders.append(slider)

        # Plot names
        if line == "PLOT":
            # Plot name is typically a few lines after PLOT
            if i + 5 < len(lines):
                plot_name = lines[i + 5].strip() if lines[i + 5].strip() else ""
                if plot_name and not plot_name.replace(".", "").isdigit():
                    model.plots.append(plot_name)

        # World dimensions
        # Look for world-wrap and dimensions in GRAPHICS-WINDOW block
        if line == "GRAPHICS-WINDOW":
            _parse_world_block(model, lines, i)

        i += 1


def _parse_slider_block(lines: list[str], start: int) -> dict | None:
    """Parse a SLIDER widget block."""
    try:
        # Standard .nlogo slider layout:
        # SLIDER, x1, y1, x2, y2, variable_name, variable_name, min, max, default, step, ...
        if start + 10 < len(lines):
            var_name = lines[start + 5].strip()
            var_name2 = lines[start + 6].strip()
            min_val = lines[start + 7].strip()
            max_val = lines[start + 8].strip()
            default_val = lines[start + 9].strip()
            step_val = lines[start + 10].strip()

            # Validate — var_name should be a word
            if re.match(r"^[\w-]+$", var_name):
                return {
                    "name": var_name,
                    "min": _safe_float(min_val),
                    "max": _safe_float(max_val),
                    "default": _safe_float(default_val),
                    "step": _safe_float(step_val),
                }
    except (IndexError, ValueError):
        pass
    return None


def _parse_world_block(model: NetLogoModel, lines: list[str], start: int) -> None:
    """Parse GRAPHICS-WINDOW block for world dimensions."""
    try:
        # Standard layout has min-pxcor, max-pxcor, min-pycor, max-pycor
        # at specific offsets in the block
        for offset in range(start, min(start + 30, len(lines))):
            line = lines[offset].strip()
            # World wrap settings
            if line in ("1", "0") and offset > start + 15:
                # These are typically the wrapping booleans
                pass
    except (IndexError, ValueError):
        pass


def _safe_float(s: str) -> float:
    """Try to parse a float, return 0.0 on failure."""
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def to_story_md(model: NetLogoModel) -> str:
    """Convert a parsed NetLogo model to story.md format."""
    parts = []

    title = model.name.replace("-", " ").replace("_", " ").title()
    parts.append(f"# Story: {title}")
    parts.append("")

    # Research Motivation (from info text)
    parts.append("## Research Motivation")
    parts.append("")
    info_summary = _extract_purpose(model.info_text)
    if info_summary:
        parts.append(info_summary)
    else:
        parts.append(f"Replicate and analyze the {title} model from the NetLogo models library.")
    parts.append("")

    # Research Goal
    parts.append("## Research Goal")
    parts.append("")
    goal = _extract_goal(model.info_text)
    if goal:
        parts.append(goal)
    else:
        parts.append(
            f"Simulate the {title} model and observe emergent dynamics. "
            "Identify key parameters driving system behavior through parameter sweeps."
        )
    parts.append("")

    # Agent Description
    parts.append("## Agent Description")
    parts.append("")
    if model.breeds:
        for breed in model.breeds:
            name = breed["singular"].title()
            owns = breed["owns"]
            parts.append(f"**{name}** agent with properties:")
            for prop in owns:
                parts.append(f"- `{prop}`")
            parts.append("")
    else:
        parts.append("Agents are turtles on a grid.")
        parts.append("")

    # Spatial Structure
    parts.append("## Spatial Structure")
    parts.append("")
    if model.has_patches:
        parts.append("Patch-based grid model. Each patch holds local state variables.")
    else:
        parts.append("Grid-based model with mobile agents.")
    if model.world_width and model.world_height:
        wrap = "toroidal (wrapping)" if model.is_wrapping else "bounded"
        parts.append(f"World size: {model.world_width}×{model.world_height}, {wrap} boundaries.")
    parts.append("")

    # Dynamics (from info text)
    parts.append("## Dynamics")
    parts.append("")
    dynamics = _extract_dynamics(model.info_text)
    if dynamics:
        parts.append(dynamics)
    else:
        parts.append("Each time step, agents execute their behavioral rules and interact with neighbors.")
    parts.append("")

    # Parameters of Interest
    parts.append("## Parameters of Interest")
    parts.append("")
    if model.sliders:
        for s in model.sliders:
            parts.append(
                f"- `{s['name']}`: range [{s['min']}, {s['max']}], "
                f"default={s['default']}, step={s['step']}"
            )
    else:
        # Fall back to globals
        for g in model.globals[:10]:
            parts.append(f"- `{g}`")
    parts.append("")

    # Output of Interest
    parts.append("## Output of Interest")
    parts.append("")
    if model.plots:
        for p in model.plots:
            parts.append(f"- {p}")
    else:
        parts.append("- Time series of key aggregate metrics")
        parts.append("- Emergent spatial patterns")
    parts.append("")

    # Mode
    parts.append("## Mode")
    parts.append("")
    parts.append("Simulator (no calibration needed)")
    parts.append("")

    # Source attribution
    parts.append("## Source")
    parts.append("")
    parts.append(f"Converted from NetLogo Models Library: `{model.name}.nlogo`")
    parts.append("")

    return "\n".join(parts)


def _extract_purpose(info: str) -> str:
    """Extract WHAT IS IT? section from NetLogo info tab."""
    # NetLogo info tabs often have ## WHAT IS IT? sections
    patterns = [
        r"##\s*WHAT IS IT\??\s*\n+(.*?)(?=\n##|\Z)",
        r"##\s*PURPOSE\s*\n+(.*?)(?=\n##|\Z)",
        r"##\s*OVERVIEW\s*\n+(.*?)(?=\n##|\Z)",
    ]
    for pat in patterns:
        match = re.search(pat, info, re.IGNORECASE | re.DOTALL)
        if match:
            text = match.group(1).strip()
            # Take first 3 paragraphs max
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            return "\n\n".join(paragraphs[:3])
    # Fallback: first 500 chars
    if info:
        return info[:500].strip()
    return ""


def _extract_goal(info: str) -> str:
    """Extract HOW IT WORKS or research goal from info tab."""
    patterns = [
        r"##\s*HOW IT WORKS\s*\n+(.*?)(?=\n##|\Z)",
        r"##\s*HOW DOES IT WORK\s*\n+(.*?)(?=\n##|\Z)",
    ]
    for pat in patterns:
        match = re.search(pat, info, re.IGNORECASE | re.DOTALL)
        if match:
            text = match.group(1).strip()
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            return "\n\n".join(paragraphs[:2])
    return ""


def _extract_dynamics(info: str) -> str:
    """Extract behavioral rules from info tab."""
    patterns = [
        r"##\s*HOW TO USE IT\s*\n+(.*?)(?=\n##|\Z)",
        r"##\s*THINGS TO NOTICE\s*\n+(.*?)(?=\n##|\Z)",
    ]
    for pat in patterns:
        match = re.search(pat, info, re.IGNORECASE | re.DOTALL)
        if match:
            text = match.group(1).strip()
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            return "\n\n".join(paragraphs[:2])
    return ""


# ── CLI entry point ──────────────────────────────────────────────────────────

def convert_nlogo_to_story(nlogo_path: Path, output_path: Path | None = None) -> Path:
    """Convert a .nlogo file to story.md. Returns path to output."""
    model = parse_nlogo(nlogo_path)
    story = to_story_md(model)

    if output_path is None:
        output_path = nlogo_path.parent / "story.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(story, encoding="utf-8")
    return output_path
