"""MIR — the Model Intermediate Representation (v0, open core).

The shared semantic contract between the open forward side (abm-auto / GIS) and
the closed inverse side (gaese). This package is the OPEN core only: it never
imports or interprets the closed extensions — those attach through the opaque
`MIR.extensions` field (the data-contract seam, strategic ADR-013).

See docs/superpowers/specs/2026-06-23-mir-v0-forward-design.md.
"""
from abm_auto.mir._schema import (
    MIR,
    MIRFidelity,
    MIRMetadata,
    MIRProcess,
    MIRRun,
    MIRSpace,
)
from abm_auto.mir._netlogo_adapter import (
    netlogo_controls_to_mir,
    netlogo_model_to_mir,
)

__all__ = [
    "MIR",
    "MIRMetadata",
    "MIRSpace",
    "MIRProcess",
    "MIRRun",
    "MIRFidelity",
    "netlogo_model_to_mir",
    "netlogo_controls_to_mir",
]
