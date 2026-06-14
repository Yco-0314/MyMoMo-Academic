"""ABM Auto Runtime — Agent base classes.

The agent hierarchy: a serialization/param mixin (``_Element``), the base
``Agent`` (``id`` + scenario/model refs + a ``setup()`` hook), and the two
space-aware specializations — ``GridAgent`` (carries ``grid`` / ``x`` / ``y`` /
``category``) and ``NetworkAgent`` (carries ``category`` / ``network``).

Two conveniences worth knowing: ``_safe_attr(name, default)`` keeps a value that
was pre-loaded from CSV instead of overwriting it in ``setup()``, and
``set_category()`` defaults to 0 so single-type models need not override it.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class _Element:
    """Param/serialization mixin: ``set_params`` + ``to_dict`` / ``to_json``."""

    _unserializable_props_: tuple = ()

    def set_params(self, params: Dict[str, Any]) -> None:
        for name, value in params.items():
            if name in self.__dict__:
                setattr(self, name, value)

    def to_dict(self, properties: Optional[List[str]] = None) -> Dict:
        if properties is None:
            properties = self.__dict__.keys()
        return {p: self.__dict__[p] for p in properties}

    def to_json(self, properties: Optional[List[str]] = None) -> Dict:
        if properties is None:
            properties = self.__dict__.keys()
        return {
            p: self.__dict__[p]
            for p in properties
            if p not in self._unserializable_props_
        }


class Agent(_Element):
    """Base agent: ``id`` + scenario/model refs + a ``setup()`` hook.

    Use ``self._safe_attr(name, default)`` inside ``setup()`` for any attribute
    that may be pre-loaded from a CSV — it preserves the loaded value instead of
    overwriting it with the default.
    """

    _unserializable_props_ = ("model", "scenario")

    def __init__(self, agent_id: int) -> None:
        self.id = agent_id
        self.scenario = None
        self.model = None

    def setup(self) -> None:
        """Declare agent properties with initial values. Overridden per model."""
        pass

    def _safe_attr(self, name: str, default: Any) -> Any:
        return getattr(self, name, default)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={getattr(self, 'id', '?')}>"


class GridItem(Agent):
    _unserializable_props_ = ("model", "scenario", "grid")

    def __init__(self, agent_id: int, grid=None, x: int = 0, y: int = 0) -> None:
        super().__init__(agent_id)
        self.grid = grid
        self.x = x
        self.y = y


class GridAgent(GridItem):
    """Grid-aware agent. Defaults ``category`` to 0 (single-type grid); override
    ``set_category()`` when multiple agent types share a grid."""

    def __init__(self, agent_id: int, x: int = 0, y: int = 0, grid=None) -> None:
        super().__init__(agent_id, grid, x, y)
        self.category = -1
        self.set_category()
        assert self.category >= 0, "category should be >= 0"

    def set_category(self) -> None:
        """Default category for single-type grid models. Override when needed."""
        self.category = 0

    def rand_move_agent(self, x_range, y_range) -> None:
        if self.grid is None:
            raise ValueError("GridAgent has not been registered onto a grid")
        self.x, self.y = self.grid.rand_move_agent(self, self.category, x_range, y_range)

    def __repr__(self) -> str:
        x = getattr(self, "x", "?")
        y = getattr(self, "y", "?")
        return f"<{self.__class__.__name__} id={getattr(self, 'id', '?')} pos=({x},{y})>"


class NetworkAgent(Agent):
    """Network-aware agent. Defaults ``category`` to 0; override
    ``set_category()`` for multi-type networks."""

    def _set_network(self, network) -> None:
        self.network = network

    def set_category(self) -> None:
        """Default category for single-type network models. Override when needed."""
        self.category = 0

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={getattr(self, 'id', '?')}>"


__all__ = ["Agent", "GridItem", "GridAgent", "NetworkAgent"]
