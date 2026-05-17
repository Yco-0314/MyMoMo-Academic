"""
ABM Auto Runtime — Agent base classes.

Wraps Melodie's Agent/GridAgent/NetworkAgent and fixes known gotchas:
  - Agent: adds _safe_attr() to prevent setup() from overwriting CSV-loaded values
  - GridAgent: provides default set_category() so subclasses don't need to override
    unless they have multiple agent types on the same grid
  - NetworkAgent: same default set_category() as GridAgent
"""
from __future__ import annotations

from typing import Any

from Melodie import Agent as _Agent
from Melodie import GridAgent as _GridAgent
from Melodie import NetworkAgent as _NetworkAgent


class Agent(_Agent):
    """Base agent class for ABM Auto simulations.

    Key addition over raw Melodie Agent:
      Use ``self._safe_attr(name, default)`` inside ``setup()`` for any attribute
      that may be pre-loaded from AgentParams.csv.  This preserves the CSV value
      instead of overwriting it with the default.

    Example::

        def setup(self):
            # state may come from AgentParams.csv — preserve it
            self.state: int = self._safe_attr("state", 0)
            # infection_prob is never in CSV — plain assignment is fine
            self.infection_prob: float = 0.0
    """

    def _safe_attr(self, name: str, default: Any) -> Any:
        """Return the current value of *name* if already set, else *default*.

        Use inside ``setup()`` for attributes that are loaded from CSV before
        ``setup()`` is called by the Melodie runtime.
        """
        return getattr(self, name, default)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={getattr(self, 'id', '?')}>"


class GridAgent(_GridAgent):
    """Grid-aware agent with a safe default category.

    Melodie's GridAgent raises ``NotImplementedError`` if ``set_category()``
    is not overridden.  ABM Auto's GridAgent defaults to category 0, which is
    correct for models with a single agent type.  Override only when you have
    multiple agent types sharing the same grid.

    Also inherits ``_safe_attr()`` from Agent for CSV-loading safety.
    """

    def _safe_attr(self, name: str, default: Any) -> Any:
        return getattr(self, name, default)

    def set_category(self) -> None:
        """Default category for single-type grid models.  Override when needed."""
        self.category = 0

    def __repr__(self) -> str:
        x = getattr(self, "x", "?")
        y = getattr(self, "y", "?")
        return f"<{self.__class__.__name__} id={getattr(self, 'id', '?')} pos=({x},{y})>"


class NetworkAgent(_NetworkAgent):
    """Network-aware agent with a safe default category.

    Same rationale as GridAgent: defaults to category 0 for single-type networks.
    """

    def _safe_attr(self, name: str, default: Any) -> Any:
        return getattr(self, name, default)

    def set_category(self) -> None:
        """Default category for single-type network models.  Override when needed."""
        self.category = 0

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={getattr(self, 'id', '?')}>"
