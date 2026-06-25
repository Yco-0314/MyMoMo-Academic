"""GIS codegen-fidelity gate — deterministic structural checks on generated code.

The fidelity principle: trust deterministic checks, never the generator's word.
Confirms the generated model uses the right space + gate
for its spatial_type, imports only from the runtime, and contains no unsafe patterns.
"""
from __future__ import annotations

from typing import List, Tuple

from abm_auto.gis._capabilities import resolve_capability

_FORBIDDEN = ("import Melodie", "from Melodie", "os.system", "subprocess",
              "eval(", "exec(", "__import__")


def gis_codegen_gate(files: dict, spec) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    code = files.get("main.py", "")
    if not code.strip():
        return False, ["main.py missing or empty"]

    for bad in _FORBIDDEN:
        if bad in code:
            reasons.append(f"forbidden pattern: {bad}")

    if "from abm_auto.gis" not in code:
        reasons.append("does not import from abm_auto.gis (wrong runtime entry)")

    cap = resolve_capability(spec.spatial_type, spec.mechanism,
                             getattr(spec, "capability", ""))
    if not cap.renderable:
        reasons.append(f"capability '{cap.key}' is registered but not codegen-renderable")

    for token in cap.required_tokens:
        if token not in code:
            reasons.append(f"{cap.key} model missing required call: {token}")

    for wrong in cap.wrong_space_tokens:
        if wrong in code:
            reasons.append(f"{cap.key} model wrongly uses {wrong}")

    return (not reasons), reasons
