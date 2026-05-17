"""
ABM Auto Runtime — Model wrapper.

Key fix (Candidate 3):
  create_grid() and create_network() default to our Grid/Network subclasses
  and inject self.agents into them so get_neighbors() needs no agent_list
  parameter at the call site.

  Before (Route A):
      neighbors = self.grid.get_neighbors(agent, agent_list=self.agents)

  After (Candidate 3, this file):
      neighbors = self.grid.get_neighbors(agent)
"""
from __future__ import annotations

from typing import Optional, Type

from Melodie import Model as _Model


class Model(_Model):
    """ABM Auto base model.

    Drop-in replacement for Melodie Model.  Overrides ``create_grid()`` and
    ``create_network()`` so the returned objects know about ``self.agents``
    and can resolve neighbour IDs without caller help.
    """

    def create_grid(
        self,
        grid_cls: Optional[Type] = None,
        spot_cls: Optional[Type] = None,
    ):
        """Create a Grid, defaulting to ABM Auto's Grid subclass.

        After creation the grid's ``_agent_list_ref`` is set to
        ``self.agents`` (available because ``create_agent_list()`` is always
        called first in the generated ``create()`` method).
        """
        # Import here to avoid circular imports at module load time
        from abm_auto.runtime._grid import Grid as _Grid

        grid = super().create_grid(grid_cls or _Grid, spot_cls)
        # Inject agent_list so Grid.get_neighbors() needs no extra arg
        if getattr(self, "agents", None) is not None:
            grid._agent_list_ref = self.agents
        return grid

    def create_network(
        self,
        network_cls: Optional[Type] = None,
        edge_cls: Optional[Type] = None,
    ):
        """Create a Network, defaulting to ABM Auto's Network subclass.

        Same agent_list injection pattern as ``create_grid()``.
        """
        from abm_auto.runtime._network import Network as _Network

        network = super().create_network(network_cls or _Network, edge_cls)
        if getattr(self, "agents", None) is not None:
            network._agent_list_ref = self.agents
        return network
