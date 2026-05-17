"""
ABM Auto Runtime — Grid wrapper.

Fixes over raw Melodie Grid:
  1. get_neighbors() returns Agent objects by default, not (category, id) tuples.
     Pass return_agents=False to get the original tuple list if needed.
  2. width and height are public properties (Melodie uses _width/_height).
  3. Clearer error messages with "ABM Auto" prefix.
  4. _agent_list_ref is injected by Model.create_grid() (Candidate 3) so
     get_neighbors() needs no agent_list parameter at the call site.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from Melodie import Grid as _Grid

if TYPE_CHECKING:
    from abm_auto.runtime._agent import GridAgent


class Grid(_Grid):
    """Spatial grid for ABM Auto simulations.

    Drop-in replacement for Melodie's Grid with a cleaner neighbor API.

    Preferred usage when using ABM Auto's Model (agent_list auto-injected)::

        # In Model.run():
        for agent in self.agents:
            neighbors = self.grid.get_neighbors(agent)
            for neighbor in neighbors:
                if neighbor.state == 1:
                    agent.expose()

    Explicit agent_list still accepted for backwards compatibility::

        neighbors = self.grid.get_neighbors(agent, agent_list=self.agents)

    Original tuple API still available via ``return_agents=False``::

        for category, agent_id in self.grid.get_neighbors(agent, return_agents=False):
            ...
    """

    # Injected by Model.create_grid() — allows zero-arg neighbor lookup
    _agent_list_ref: Optional[Any] = None

    @property
    def width(self) -> int:
        """Public width property (Melodie uses private _width)."""
        return self._width

    @property
    def height(self) -> int:
        """Public height property (Melodie uses private _height)."""
        return self._height

    def get_neighbors(
        self,
        agent: "GridAgent",
        radius: int = 1,
        moore: bool = True,
        except_self: bool = True,
        agent_list: Any = None,
        return_agents: bool = True,
    ):
        """Return neighbors of *agent*.

        Parameters
        ----------
        agent:
            The agent whose neighbours to find.
        radius:
            Chebyshev radius (Moore) or Manhattan radius (von Neumann).
        moore:
            True → Moore neighbourhood; False → von Neumann.
        except_self:
            Exclude the agent's own cell (default True).
        agent_list:
            AgentList from the model (``self.agents``).  Required when
            ``return_agents=True`` (the default).
        return_agents:
            If True (default) return GridAgent objects.
            If False return raw ``(category, agent_id)`` tuples — same as
            original Melodie behaviour.

        Returns
        -------
        list[GridAgent] when return_agents=True, else list[tuple[str, int]].
        """
        raw: list = super().get_neighbors(agent, radius, moore, except_self)

        if not return_agents:
            return raw

        # Prefer injected ref (set by Model.create_grid()), fallback to explicit arg
        effective_list = agent_list if agent_list is not None else self._agent_list_ref

        if effective_list is None:
            raise ValueError(
                "ABM Auto Grid.get_neighbors(): no agent_list available.\n"
                "Either use 'from abm_auto.runtime import Model' (auto-injects), or\n"
                "pass agent_list=self.agents explicitly."
            )

        result = []
        for item in raw:
            # Melodie returns (category_str, agent_id_int) tuples
            if isinstance(item, tuple):
                _, agent_id = item
                result.append(effective_list[agent_id])
            else:
                # Future-proof: already an agent object
                result.append(item)
        return result
