"""B4 — story -> GISModelSpec extraction (the LLM half of autonomous GIS codegen).

The LLM reads a GIS-flagged story and emits the typed GISModelSpec that the
deterministic templates render to runnable code. Output is validated, so a bad
extraction fails at parse time, not at run time.
"""
from __future__ import annotations

import json

from abm_auto.gis._capabilities import renderable_capabilities, resolve_capability
from abm_auto.gis._model_spec import GISModelSpec

_SYSTEM = ("You configure a GIS agent-based model from a description. "
           "Output ONLY valid JSON, no prose, no code fences.")


def _format_param(p) -> str:
    """Render one ParamSpec for the prompt: name(type=default unit, lo..hi)."""
    out = f"{p.name}({p.type.__name__}={p.default!r}"
    if p.unit:
        out += f" {p.unit}"
    if p.min is not None or p.max is not None:
        lo = "" if p.min is None else p.min
        hi = "" if p.max is None else p.max
        out += f", {lo}..{hi}"
    return out + ")"


def _renderable_capability_table() -> str:
    lines = []
    for cap in renderable_capabilities():
        layers = ", ".join(cap.layers)
        line = (
            f'- capability="{cap.key}": spatial_type="{cap.spatial_type}", '
            f'mechanism="{cap.mechanism}", layers="{layers}"'
        )
        if cap.params:
            line += "; params: " + ", ".join(_format_param(p) for p in cap.params)
        lines.append(line)
    return "\n".join(lines)

_PROMPT = """Story:
{story}

Produce a GIS model spec as JSON.
- Choose one renderable capability from this table when clear:
{renderable_table}
- "capability": use the selected capability key when clear. Omit it for legacy output.
- "spatial_type" and "mechanism" must match the selected capability. For legacy
  output without "capability", use one of the legacy renderable pairs above.
- "data_path": the input data file path if the story names one, else "".
- "params": optional dict. Use ONLY the params listed for the chosen capability
  above (match the types); unknown or misspelled params are rejected. Omit to take defaults.

Return exactly: {{"capability": "...", "spatial_type": "...", "mechanism": "...", "data_path": "...", "params": {{}}}}"""


def _parse(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    return json.loads(raw)


def extract_gis_spec(story: str, client, model: str = "default") -> GISModelSpec:
    """Call the LLM to turn a story into a validated GISModelSpec. ``model`` is
    passed through to ``client.create``; pass the model id your client expects
    (the default is a provider-neutral placeholder)."""
    raw = client.create(model=model, max_tokens=300,
                        system=_SYSTEM,
                        user=_PROMPT.format(
                            story=story,
                            renderable_table=_renderable_capability_table(),
                        ))
    parsed = _parse(raw)
    spec = GISModelSpec(
        spatial_type=parsed.get("spatial_type", ""),
        mechanism=parsed.get("mechanism", ""),
        data_path=parsed.get("data_path", "") or "",
        params=parsed.get("params", {}) or {},
        capability=parsed.get("capability", "") or "",
    )
    spec.validate()
    cap = resolve_capability(spec.spatial_type, spec.mechanism, spec.capability)
    if not cap.renderable:
        raise ValueError(
            f"capability {cap.key!r} is registered but not codegen-renderable"
        )
    return spec
