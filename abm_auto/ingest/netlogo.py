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
import shlex
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class NetLogoControlValue:
    """Raw NetLogo control value plus parsed float when it is plainly numeric."""
    raw: str = ""
    number: float | None = None

    def to_dict(self) -> dict:
        return {"raw": self.raw, "number": self.number}


@dataclass
class NetLogoSlider:
    name: str
    label: str
    minimum: NetLogoControlValue
    maximum: NetLogoControlValue
    default: NetLogoControlValue
    step: NetLogoControlValue
    units: str = ""
    orientation: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "minimum": self.minimum.to_dict(),
            "maximum": self.maximum.to_dict(),
            "default": self.default.to_dict(),
            "step": self.step.to_dict(),
            "units": self.units,
            "orientation": self.orientation,
        }


@dataclass
class NetLogoSwitch:
    name: str
    label: str
    default: bool

    def to_dict(self) -> dict:
        return {"name": self.name, "label": self.label, "default": self.default}


@dataclass
class NetLogoChooser:
    name: str
    label: str
    choices: list[str] = field(default_factory=list)
    default: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "choices": list(self.choices),
            "default": self.default,
        }


@dataclass
class NetLogoInputBox:
    name: str
    label: str
    default: NetLogoControlValue
    multiline: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "default": self.default.to_dict(),
            "multiline": self.multiline,
        }


@dataclass
class NetLogoMonitor:
    name: str
    reporter: str

    def to_dict(self) -> dict:
        return {"name": self.name, "reporter": self.reporter}


@dataclass
class NetLogoPlotPen:
    name: str
    interval: NetLogoControlValue = field(default_factory=NetLogoControlValue)
    mode: str = ""
    color: str = ""
    update_command: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "interval": self.interval.to_dict(),
            "mode": self.mode,
            "color": self.color,
            "update_command": self.update_command,
        }


@dataclass
class NetLogoPlotSpec:
    name: str
    x_axis: str = ""
    y_axis: str = ""
    pens: list[NetLogoPlotPen] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "pens": [p.to_dict() for p in self.pens],
        }


@dataclass
class NetLogoControlsSpec:
    sliders: list[NetLogoSlider] = field(default_factory=list)
    switches: list[NetLogoSwitch] = field(default_factory=list)
    choosers: list[NetLogoChooser] = field(default_factory=list)
    input_boxes: list[NetLogoInputBox] = field(default_factory=list)
    monitors: list[NetLogoMonitor] = field(default_factory=list)
    plots: list[NetLogoPlotSpec] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "sliders": [s.to_dict() for s in self.sliders],
            "switches": [s.to_dict() for s in self.switches],
            "choosers": [c.to_dict() for c in self.choosers],
            "input_boxes": [i.to_dict() for i in self.input_boxes],
            "monitors": [m.to_dict() for m in self.monitors],
            "plots": [p.to_dict() for p in self.plots],
        }


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
    controls: NetLogoControlsSpec = field(default_factory=NetLogoControlsSpec)


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

    # Widgets — controls, plots, view
    widgets_el = root.find("widgets")
    if widgets_el is not None:
        _parse_xml_widgets(model, widgets_el)

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
            slider = _parse_slider_control(lines, i)
            if slider:
                _add_slider(model, slider)

        if line == "SWITCH":
            switch = _parse_switch_control(lines, i)
            if switch:
                model.controls.switches.append(switch)

        if line == "CHOOSER":
            chooser = _parse_chooser_control(lines, i)
            if chooser:
                model.controls.choosers.append(chooser)

        if line == "INPUTBOX":
            input_box = _parse_input_box_control(lines, i)
            if input_box:
                model.controls.input_boxes.append(input_box)

        if line == "MONITOR":
            monitor = _parse_monitor_control(lines, i)
            if monitor:
                model.controls.monitors.append(monitor)

        # Plot names
        if line == "PLOT":
            plot = _parse_plot_control(lines, i)
            if plot:
                _add_plot(model, plot)

        # World dimensions
        # Look for world-wrap and dimensions in GRAPHICS-WINDOW block
        if line == "GRAPHICS-WINDOW":
            _parse_world_block(model, lines, i)

        i += 1


def _parse_slider_control(lines: list[str], start: int) -> NetLogoSlider | None:
    """Parse a SLIDER widget block."""
    try:
        # Standard .nlogo slider layout:
        # SLIDER, x1, y1, x2, y2, variable_name, variable_name, min, max, default, step, ...
        if start + 10 < len(lines):
            var_name = lines[start + 5].strip()
            label = lines[start + 6].strip()
            min_val = lines[start + 7].strip()
            max_val = lines[start + 8].strip()
            default_val = lines[start + 9].strip()
            step_val = lines[start + 10].strip()
            units = lines[start + 12].strip() if start + 12 < len(lines) else ""
            orientation = lines[start + 13].strip() if start + 13 < len(lines) else ""

            # Validate — var_name should be a word
            if re.match(r"^[\w?-]+$", var_name):
                return NetLogoSlider(
                    name=var_name,
                    label=label,
                    minimum=_control_value(min_val),
                    maximum=_control_value(max_val),
                    default=_control_value(default_val),
                    step=_control_value(step_val),
                    units="" if units == "NIL" else units,
                    orientation=orientation,
                )
    except (IndexError, ValueError):
        pass
    return None


def _parse_switch_control(lines: list[str], start: int) -> NetLogoSwitch | None:
    """Parse a SWITCH widget block."""
    try:
        if start + 7 < len(lines):
            name = lines[start + 5].strip()
            label = lines[start + 6].strip()
            default = _boolish(lines[start + 7].strip())
            if name:
                return NetLogoSwitch(name=name, label=label, default=default)
    except (IndexError, ValueError):
        pass
    return None


def _parse_chooser_control(lines: list[str], start: int) -> NetLogoChooser | None:
    """Parse a CHOOSER widget block."""
    try:
        if start + 8 < len(lines):
            name = lines[start + 5].strip()
            label = lines[start + 6].strip()
            choices = _parse_choices(lines[start + 7].strip())
            default = _choice_default(choices, lines[start + 8].strip())
            if name:
                return NetLogoChooser(
                    name=name,
                    label=label,
                    choices=choices,
                    default=default,
                )
    except (IndexError, ValueError):
        pass
    return None


def _parse_input_box_control(lines: list[str], start: int) -> NetLogoInputBox | None:
    """Parse an INPUTBOX widget block."""
    try:
        if start + 6 < len(lines):
            name = lines[start + 5].strip()
            default = lines[start + 6].strip()
            multiline = _boolish(lines[start + 8].strip()) if start + 8 < len(lines) else False
            if name:
                return NetLogoInputBox(
                    name=name,
                    label=name,
                    default=_control_value(default),
                    multiline=multiline,
                )
    except (IndexError, ValueError):
        pass
    return None


def _parse_monitor_control(lines: list[str], start: int) -> NetLogoMonitor | None:
    """Parse a MONITOR widget block."""
    try:
        if start + 6 < len(lines):
            name = lines[start + 5].strip()
            reporter = lines[start + 6].strip()
            if name:
                return NetLogoMonitor(name=name, reporter=reporter)
    except (IndexError, ValueError):
        pass
    return None


def _parse_plot_control(lines: list[str], start: int) -> NetLogoPlotSpec | None:
    """Parse a PLOT widget block, including pen update commands when present."""
    try:
        if start + 7 >= len(lines):
            return None
        name = lines[start + 5].strip()
        x_axis = lines[start + 6].strip()
        y_axis = lines[start + 7].strip()
        if not name or name.replace(".", "").isdigit():
            return None
        pens: list[NetLogoPlotPen] = []
        for offset in range(start + 8, len(lines)):
            if lines[offset].strip() != "PENS":
                continue
            for pen_offset in range(offset + 1, len(lines)):
                pen_line = lines[pen_offset].strip()
                if not pen_line:
                    break
                if pen_line in _TEXT_WIDGET_MARKERS:
                    break
                pen = _parse_pen_line(pen_line)
                if pen:
                    pens.append(pen)
            break
        return NetLogoPlotSpec(name=name, x_axis=x_axis, y_axis=y_axis, pens=pens)
    except (IndexError, ValueError):
        return None


_TEXT_WIDGET_MARKERS = {
    "GRAPHICS-WINDOW",
    "SLIDER",
    "SWITCH",
    "CHOOSER",
    "INPUTBOX",
    "MONITOR",
    "PLOT",
    "BUTTON",
    "TEXTBOX",
    "OUTPUT",
}


def _control_value(raw: object) -> NetLogoControlValue:
    text = "" if raw is None else str(raw).strip()
    try:
        return NetLogoControlValue(raw=text, number=float(text))
    except (TypeError, ValueError):
        return NetLogoControlValue(raw=text, number=None)


def _legacy_float(value: NetLogoControlValue) -> float:
    return value.number if value.number is not None else 0.0


def _add_slider(model: NetLogoModel, slider: NetLogoSlider) -> None:
    model.controls.sliders.append(slider)
    model.sliders.append({
        "name": slider.name,
        "min": _legacy_float(slider.minimum),
        "max": _legacy_float(slider.maximum),
        "default": _legacy_float(slider.default),
        "step": _legacy_float(slider.step),
    })


def _add_plot(model: NetLogoModel, plot: NetLogoPlotSpec) -> None:
    model.controls.plots.append(plot)
    model.plots.append(plot.name)


def _boolish(raw: object) -> bool:
    text = "" if raw is None else str(raw).strip().lower()
    return text in {"1", "true", "t", "yes", "on"}


def _parse_choices(raw: object) -> list[str]:
    text = "" if raw is None else str(raw).strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    if not text:
        return []
    try:
        return [str(part) for part in shlex.split(text)]
    except ValueError:
        return [p for p in text.split() if p]


def _choice_default(choices: list[str], raw: object) -> str | None:
    text = "" if raw is None else str(raw).strip()
    if not text:
        return choices[0] if choices else None
    try:
        idx = int(float(text))
    except ValueError:
        return text.strip('"')
    if 0 <= idx < len(choices):
        return choices[idx]
    return None


def _parse_pen_line(line: str) -> NetLogoPlotPen | None:
    try:
        parts = shlex.split(line)
    except ValueError:
        return None
    if not parts:
        return None
    return NetLogoPlotPen(
        name=parts[0],
        interval=_control_value(parts[1] if len(parts) > 1 else ""),
        mode=parts[2] if len(parts) > 2 else "",
        color=parts[3] if len(parts) > 3 else "",
        update_command=parts[-1] if len(parts) > 1 else "",
    )


def _attr(el: ET.Element, *names: str, default: str = "") -> str:
    for name in names:
        value = el.attrib.get(name)
        if value is not None:
            return value
    return default


def _parse_xml_widgets(model: NetLogoModel, widgets_el: ET.Element) -> None:
    for widget in list(widgets_el):
        tag = widget.tag.lower().replace("-", "").replace("_", "")
        if tag == "slider":
            name = _attr(widget, "variable", "name")
            if name:
                _add_slider(model, NetLogoSlider(
                    name=name,
                    label=_attr(widget, "display", "label", default=name),
                    minimum=_control_value(_attr(widget, "min", "minimum", default="0")),
                    maximum=_control_value(_attr(widget, "max", "maximum", default="0")),
                    default=_control_value(_attr(widget, "default", "value", default="0")),
                    step=_control_value(_attr(widget, "step", default="1")),
                    units=_attr(widget, "units"),
                    orientation=_attr(widget, "direction", "orientation"),
                ))
            continue

        if tag == "switch":
            name = _attr(widget, "variable", "name")
            if name:
                model.controls.switches.append(NetLogoSwitch(
                    name=name,
                    label=_attr(widget, "display", "label", default=name),
                    default=_boolish(_attr(widget, "on", "default", "value")),
                ))
            continue

        if tag == "chooser":
            name = _attr(widget, "variable", "name")
            choices = _parse_choices(_attr(widget, "choices"))
            if name:
                default_raw = _attr(
                    widget,
                    "currentChoice",
                    "current",
                    "default",
                    "value",
                    "currentChoiceIndex",
                )
                model.controls.choosers.append(NetLogoChooser(
                    name=name,
                    label=_attr(widget, "display", "label", default=name),
                    choices=choices,
                    default=_choice_default(choices, default_raw),
                ))
            continue

        if tag == "inputbox":
            name = _attr(widget, "variable", "name")
            if name:
                model.controls.input_boxes.append(NetLogoInputBox(
                    name=name,
                    label=_attr(widget, "display", "label", default=name),
                    default=_control_value(_attr(widget, "default", "value")),
                    multiline=_boolish(_attr(widget, "multiline")),
                ))
            continue

        if tag == "monitor":
            display = _attr(widget, "display", "name")
            reporter = _attr(widget, "reporter", "source", "value")
            if display:
                model.controls.monitors.append(NetLogoMonitor(
                    name=display,
                    reporter=reporter,
                ))
            continue

        if tag == "plot":
            display = _attr(widget, "display", "name")
            if display:
                pens = []
                for pen in list(widget):
                    if pen.tag.lower() != "pen":
                        continue
                    pens.append(NetLogoPlotPen(
                        name=_attr(pen, "display", "name"),
                        interval=_control_value(_attr(pen, "interval")),
                        mode=_attr(pen, "mode"),
                        color=_attr(pen, "color"),
                        update_command=_attr(pen, "update", "updateCommand"),
                    ))
                _add_plot(model, NetLogoPlotSpec(
                    name=display,
                    x_axis=_attr(widget, "xAxis", "xaxis", "x_axis"),
                    y_axis=_attr(widget, "yAxis", "yaxis", "y_axis"),
                    pens=pens,
                ))


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
