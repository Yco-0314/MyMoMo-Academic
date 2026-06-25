"""GISModelSpec: the typed schema codegen renders to a runnable GIS model.

The deterministic contract between the (LLM) story->spec extractor and the
spec->code templates. Validate at parse time so bad specs fail before codegen.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict

from abm_auto.gis._capabilities import MECHANISMS, SPATIAL_TYPES, resolve_capability


@dataclass
class GISModelSpec:
    spatial_type: str                      # raster | network
    mechanism: str                         # per spatial_type (see MECHANISMS)
    data_path: str = ""                    # optional; raster falls back to synthetic
    params: Dict[str, Any] = field(default_factory=dict)
    seed: int = 0
    capability: str = ""                   # optional explicit registry key

    def validate(self) -> None:
        cap = resolve_capability(self.spatial_type, self.mechanism, self.capability)
        if cap.key == "network_routing_load" and not self.data_path:
            raise ValueError("network models require a data_path (road shapefile)")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "GISModelSpec":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
