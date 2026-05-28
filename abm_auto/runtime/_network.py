"""
ABM Auto Runtime — Network wrapper.

Fixes over raw MyMoMo Runtime Network:
  1. get_neighbors() returns Agent objects by default, not (category, id) tuples.
  2. _agent_list_ref is injected by Model.create_network() (Candidate 3) so
     get_neighbors() needs no agent_list parameter at the call site.
  3. setup_agent_connections(topology=...) accepts a Topology callable instead
     of Melodie's string `network_type`. The callable owns graph construction;
     this method only handles agent-category registration and edge insertion.
     Determinism flows through the injected `_rng`.
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any, List, Optional

from Melodie import Network as _Network

if TYPE_CHECKING:
    from abm_auto.runtime._agent import NetworkAgent
    from abm_auto.runtime._topologies import Topology


class Network(_Network):
    """Social/spatial network for ABM Auto simulations.

    Drop-in replacement for MyMoMo Runtime's Network with a cleaner neighbor API
    and a pluggable topology seam.

    Topology usage::

        from abm_auto.runtime.topologies import netlogo_spatially_clustered

        self.network.setup_agent_connections(
            agent_lists=[self.agents],
            topology=netlogo_spatially_clustered(avg_degree=6),
        )

    Preferred neighbor lookup (with ABM Auto Model auto-injection)::

        for agent in self.agents:
            for neighbor in self.network.get_neighbors(agent):
                ...
    """

    # Injected by Model.create_network() — allows zero-arg neighbor lookup
    _agent_list_ref: Optional[Any] = None
    # Injected by Model.create_network() — owned seeded RNG for topology construction
    _rng: Optional[random.Random] = None

    def setup_agent_connections(
        self,
        agent_lists: List[Any],
        topology: "Topology",
    ) -> None:
        """Build the network from a Topology callable.

        Replaces Melodie's `(network_type: str, network_params: dict)` API
        with a single callable slot. To use a networkx-named graph, wrap it
        with `melodie_named("random_geometric_graph", radius=0.113)`.

        :param agent_lists: One AgentList per agent category to place on the network.
        :param topology: A `Topology` callable: ``(n, rng) -> nx.Graph``.
        """
        assert isinstance(agent_lists, list)

        # 1. Register agents into categories and build the contiguous node-id map.
        node_id = 0
        node_id_to_node_type: dict[int, tuple[int, int]] = {}
        for agent_list in agent_lists:
            if len(agent_list) > 0:
                agent_list[0].set_category()
                self.agent_categories[agent_list[0].category] = agent_list
            for agent in agent_list:
                self.add_agent(agent)
                agent._set_network(self)
                node_id_to_node_type[node_id] = (agent.category, agent.id)
                node_id += 1

        # 2. Construct the graph via the supplied topology.
        rng = self._rng if self._rng is not None else random.Random()
        g = topology(len(self.nodes), rng)

        # 3. Translate networkx edges into Melodie edge objects.
        for edge in g.edges:
            src = node_id_to_node_type[edge[0]]
            dst = node_id_to_node_type[edge[1]]
            edge_obj = self.edge_cls(src[0], src[1], dst[0], dst[1], {})
            self.add_edge(src, dst, edge_obj)
        self._nx_edges = list(g.edges)

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
                # MyMoMo Runtime's network stores agents by category
                if hasattr(self, "agent_categories") and category in self.agent_categories:
                    result.append(self.agent_categories[category].get_agent(agent_id))
                else:
                    result.append(effective_list[agent_id])
            else:
                result.append(item)
        return result
