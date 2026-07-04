"""MIR v0 core schema (OPEN).

Dataclasses (matching the house style of `abm_auto/gis/_model_spec.py`:
dataclass + to_dict/from_dict/validate), so the open semantic core carries no
pydantic dependency. The 11 open clusters from the convergence analysis plus the
`extensions` seam.

A thin forward GIS spec populates `space` + `processes` + `run` + `fidelity` and
leaves `entities/state/relations/layers/metrics` empty; those empty clusters
exist so the closed inverse side (Blueprint, Half B) can fill them, and must
survive serialisation as empty. `extensions` is the data-contract seam
(ADR-013): the closed overlay (search_space / audiences / memory) attaches here,
and the OPEN side never interprets it.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class MIRMetadata:
    name: str = ""
    description: str = ""
    domain: str = "custom"
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MIRSpace:
    """Geographic / spatial dialect. GIS contributes this — Blueprint has none."""
    spatial_type: str = ""        # raster | network | point | polygon | coupled | ...
    crs: str = ""
    data_path: str = ""


@dataclass
class MIRProcess:
    """A mechanism / dynamic process."""
    mechanism: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MIRRun:
    seed: int = 0
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MIRFidelity:
    """The codegen-fidelity contract. GIS contributes this — Blueprint has none.
    Carried by MIR core so ANY MIR model is codegen-able and gateable."""
    capability: str = ""
    required_tokens: Tuple[str, ...] = ()
    gate: str = ""
    wrong_space_tokens: Tuple[str, ...] = ()


@dataclass
class MIR:
    """MIR v0 core (open). The shared semantic contract."""
    metadata: MIRMetadata = field(default_factory=MIRMetadata)
    entities: List[dict] = field(default_factory=list)      # agents (empty for thin GIS spec)
    state: List[dict] = field(default_factory=list)         # environment variables
    space: MIRSpace = field(default_factory=MIRSpace)
    relations: List[dict] = field(default_factory=list)     # causal links / coupling
    processes: List[MIRProcess] = field(default_factory=list)
    layers: List[dict] = field(default_factory=list)        # multi-scale hierarchy
    metrics: List[dict] = field(default_factory=list)       # goal metrics (measurement)
    run: MIRRun = field(default_factory=MIRRun)
    fidelity: MIRFidelity = field(default_factory=MIRFidelity)
    trace: Dict[str, Any] = field(default_factory=dict)
    # ── the seam: closed extensions attach here; the OPEN side never reads it ──
    extensions: Dict[str, Any] = field(default_factory=dict)

    # ── (de)serialisation ─────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, d: dict) -> "MIR":
        d = dict(d)
        meta = d.get("metadata") or {}
        space = d.get("space") or {}
        run = d.get("run") or {}
        fid = d.get("fidelity") or {}
        procs = d.get("processes") or []
        return cls(
            metadata=MIRMetadata(**{k: v for k, v in meta.items()
                                    if k in MIRMetadata.__dataclass_fields__}),
            entities=list(d.get("entities", [])),
            state=list(d.get("state", [])),
            space=MIRSpace(**{k: v for k, v in space.items()
                              if k in MIRSpace.__dataclass_fields__}),
            relations=list(d.get("relations", [])),
            processes=[MIRProcess(
                mechanism=p.get("mechanism", ""),
                params=dict(p.get("params", {})),
            ) for p in procs],
            layers=list(d.get("layers", [])),
            metrics=list(d.get("metrics", [])),
            run=MIRRun(seed=int(run.get("seed", 0)), params=dict(run.get("params", {}))),
            fidelity=MIRFidelity(
                capability=fid.get("capability", ""),
                required_tokens=tuple(fid.get("required_tokens", ()) or ()),
                gate=fid.get("gate", ""),
                wrong_space_tokens=tuple(fid.get("wrong_space_tokens", ()) or ()),
            ),
            trace=dict(d.get("trace", {})),
            extensions=dict(d.get("extensions", {})),
        )

    @classmethod
    def from_json(cls, s: str) -> "MIR":
        return cls.from_dict(json.loads(s))

    def validate(self) -> None:
        if not isinstance(self.metadata, MIRMetadata):
            raise ValueError("metadata must be a MIRMetadata")
        if not isinstance(self.space, MIRSpace):
            raise ValueError("space must be a MIRSpace")
        if not isinstance(self.run, MIRRun):
            raise ValueError("run must be a MIRRun")
        if not isinstance(self.fidelity, MIRFidelity):
            raise ValueError("fidelity must be a MIRFidelity")
        if not all(isinstance(p, MIRProcess) for p in self.processes):
            raise ValueError("processes must be MIRProcess instances")
        if not isinstance(self.extensions, dict):
            raise ValueError("extensions must be a dict (the closed-overlay seam)")
