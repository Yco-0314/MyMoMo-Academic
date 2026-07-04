"""GISModelSpec <-> MIR core adapter (Half A, forward / open).

A thin forward GIS spec maps onto MIR core's space + processes + run + fidelity
clusters; the entities/state/relations/layers/metrics clusters stay empty (they
exist for the closed Blueprint side to fill in Half B). The fidelity contract
(capability + required_tokens + gate) is carried through MIR so the regenerated
model is still gateable.
"""
from __future__ import annotations

from abm_auto.gis._capabilities import resolve_capability
from abm_auto.gis._model_spec import GISModelSpec
from abm_auto.mir._schema import MIR, MIRFidelity, MIRMetadata, MIRProcess, MIRRun, MIRSpace


def gis_spec_to_mir(spec: GISModelSpec) -> MIR:
    """Serialise a GISModelSpec into MIR core. Carries the fidelity contract so
    the regenerated model stays codegen-gateable."""
    spec.validate()
    cap = resolve_capability(spec.spatial_type, spec.mechanism, spec.capability)
    return MIR(
        metadata=MIRMetadata(name=cap.key, domain="gis"),
        space=MIRSpace(spatial_type=spec.spatial_type, data_path=spec.data_path),
        processes=[MIRProcess(mechanism=spec.mechanism, params=dict(spec.params))],
        run=MIRRun(seed=spec.seed, params=dict(spec.params)),
        fidelity=MIRFidelity(
            capability=cap.key,
            required_tokens=tuple(cap.required_tokens),
            gate=cap.gate,
            wrong_space_tokens=tuple(cap.wrong_space_tokens),
        ),
    )


def mir_to_gis_spec(mir: MIR) -> GISModelSpec:
    """Reconstruct a GISModelSpec from MIR core. Uses only the open core — the
    `extensions` seam is never read here (it is the closed overlay)."""
    mir.validate()
    proc = mir.processes[0] if mir.processes else MIRProcess()
    spec = GISModelSpec(
        spatial_type=mir.space.spatial_type,
        mechanism=proc.mechanism,
        data_path=mir.space.data_path,
        params=dict(mir.run.params),
        seed=mir.run.seed,
        capability=mir.fidelity.capability,
    )
    spec.validate()
    return spec
