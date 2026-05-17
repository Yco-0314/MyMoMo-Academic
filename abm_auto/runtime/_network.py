"""
ABM Auto Runtime — Network wrapper.

Fixes over raw Melodie Network:
  1. get_neighbors() returns Agent objects by default, not (category, id) tuples.
  2. _agent_list_ref is injected by Model.create_network() (Candidate 3) so
     get_neighbors() needs no agent_list parameter at the call site.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from Melodie import Network as _Network

if TYPE_CHECKING:
    from abm_auto.runtime._agent import NetworkAgent


class Network(_Network):
    """Social/spatial network for ABM Auto simulations.

    Drop-in replacement for Melodie's Network with a cleaner neighbor API.

    Preferred usage when using ABM Auto's Model (agent_list auto-injected)::

        # In Model.run():
        for agent in self.agents:
            neighbors = self.network.get_neighbors(agent)
            for neighbor in neighbors:
                agent.update(neighbor.opinion)

    Explicit agent_list still accepted for backwards compatibility::

        neighbors = self.network.get_neighbors(agent, agent_list=self.agents)

    Original tuple API still available via ``return_agents=False``.
    """

    # Injected by Model.create_network() — allows zero-arg neighbor lookup
    _agent_list_ref: Optional[Any] = None

    def get_neighbors(
        self,
        agent: "NetworkAgent",
        agent_list: Any = None,
        return_agents: bool = True,
    ):
        """Return neighbours of *agent* in the network.

        Parameters
        ----------
        agent:
            The agent whose neighbours to find.
        agent_list:
            AgentList from the model (``self.agents``).  Required when
            ``return_agents=True`` (the default).
        return_agents:
            If True (default) return NetworkAgent objects.
            If False return raw ``(category, agent_id)`` tuples.
        """
        raw: list = super().get_neighbors(agent)

        if not return_agents:
            return raw

        # Prefer injected ref (set by Model.create_network()), fallback to explicit arg
        effective_list = agent_list if agent_list is not None else self._agent_list_ref

        if effective_list is None:
            raise ValueError(
                "ABM Auto Network.get_neighbors(): no agent_list available.\n"
                "Either use 'from abm_auto.runtime import Model' (auto-injects), or\n"
                "pass agent_list=self.agents explicitly."
            )

        result = []
        for item in raw:
            if isinstance(item, tuple):
                category, agent_id = item
                # Melodie's network stores agents by category
                if hasattr(self, "agent_categories") and category in self.agent_categories:
                    result.append(self.agent_categories[category].get_agent(agent_id))
                else:
                    result.append(effective_list[agent_id])
            else:
                result.append(item)
        return result
