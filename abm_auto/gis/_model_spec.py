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
        self._validate_params(cap)

    def _validate_params(self, cap) -> None:
        """Check params against the capability's declared schema: reject unknown
        names (the LLM-guessed / misspelled params the render branches used to drop
        silently), then coerce + range-check the declared ones. Only enforced for
        renderable capabilities — params are consumed only by render(). `seed` is
        authoritative on the spec and accepted (ignored) if duplicated into params.
        """
        if not cap.renderable:
            return
        schema = {p.name: p for p in cap.params}
        for name, value in self.params.items():
            if name == "seed":
                continue
            spec = schema.get(name)
            if spec is None:
                allowed = ", ".join(sorted(schema)) or "(none)"
                raise ValueError(
                    f"unknown param {name!r} for capability {cap.key!r}; allowed: {allowed}"
                )
            try:
                coerced = spec.type(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"param {name!r} for {cap.key!r} must be {spec.type.__name__}, got {value!r}"
                ) from exc
            if isinstance(coerced, (int, float)) and not isinstance(coerced, bool):
                if spec.min is not None and coerced < spec.min:
                    raise ValueError(
                        f"param {name!r} for {cap.key!r} must be >= {spec.min}, got {coerced}"
                    )
                if spec.max is not None and coerced > spec.max:
                    raise ValueError(
                        f"param {name!r} for {cap.key!r} must be <= {spec.max}, got {coerced}"
                    )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "GISModelSpec":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
