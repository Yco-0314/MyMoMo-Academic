"""ABM Auto Runtime — standalone ``Network`` + ``Edge`` (ADR-009 Phase 4, Stage C).

Faithful, dependency-free reimplementation of Melodie's ``Network`` / ``Edge``
(``Melodie/network.py``) — no Melodie import. Same node/edge data structures
(``nodes`` set, ``edges`` adjacency dict, ``(category, id)`` node tuples) and
neighbour semantics. The graph-construction seam is ABM Auto's:
``setup_agent_connections`` takes a ``Topology`` callable ``(n, rng) -> nx.Graph``
(replacing Melodie's ``(network_type: str, params)`` API) and determinism flows
through the injected ``_rng``. ``get_neighbors`` resolves raw ``(category, id)``
tuples to NetworkAgent objects. The visualizer layout helpers are kept (lazy
networkx imports) but are unused on the non-visual run path.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set, Tuple, Type

from abm_auto.runtime._agent import NetworkAgent

NodeType = Tuple[int, int]


class Edge:
    """An edge linking two agents ``(category, id)``; may carry properties."""

    def __init__(self, category_1: int, agent_1_id: int, category_2: int,
                 agent_2_id: int, edge_properties: Dict[str, Any]) -> None:
        self.category_1 = category_1
        self.agent_1_id = agent_1_id
        self.category_2 = category_2
        self.agent_2_id = agent_2_id
        self.properties: Dict[str, Any] = edge_properties
        self.setup()
        self.post_setup()

    def setup(self) -> None:
        pass

    def post_setup(self) -> None:
        for prop_name, prop_value in self.properties.items():
            setattr(self, prop_name, prop_value)

    def __repr__(self) -> str:
        return (f"<{self.__class__.__name__} {(self.category_1, self.agent_1_id)} "
                f"--> {(self.category_2, self.agent_2_id)}>")


class Network:
    """Graph linking agents. Nodes are ``(category, id)`` tuples; ``edges`` is an
    adjacency dict of dicts holding ``Edge`` objects."""

    def __init__(self, model=None, edge_cls: Optional[Type[Edge]] = None,
                 directed: bool = False, name: str = "network") -> None:
        self.model = model
        self.simple = True
        self.directed = directed
        self.nodes: Set[NodeType] = set()
        self.edges: Dict[NodeType, Dict[NodeType, Edge]] = {}
        self.edge_cls: Type[Edge] = edge_cls if edge_cls is not None else Edge
        self.agent_categories: Dict[int, Any] = {}
        self.layout_file = os.path.join(model.config.visualizer_tmpdir, name + "_layout.gexf")
        self.layout: dict = {}
        self._layout_creator = lambda G: __import__("networkx").spring_layout(G)
        # ABM Auto: injected by Model.create_network()
        self._agent_list_ref: Optional[Any] = None
        self._rng = None
        self.setup()

    def _setup(self) -> None:
        self.setup()

    def setup(self) -> None:
        pass

    # ── edges ────────────────────────────────────────────────────────────────

    def add_edge(self, source_id: NodeType, target_id: NodeType, edge: Edge) -> None:
        if source_id not in self.edges:
            self.edges[source_id] = {}
        self.edges[source_id][target_id] = edge
        if not self.directed:
            if target_id not in self.edges:
                self.edges[target_id] = {}
            self.edges[target_id][source_id] = edge

    def get_edge(self, source_id: NodeType, target_id: NodeType) -> Edge:
        return self.edges[source_id][target_id]

    def remove_edge(self, source_id: NodeType, target_id: NodeType) -> None:
        self.edges[source_id].pop(target_id)
        if not self.directed:
            self.edges[target_id].pop(source_id)

    # ── neighbours ───────────────────────────────────────────────────────────

    def _get_neighbor_positions(self, agent_id: int, category: int) -> List[NodeType]:
        neighbor_ids = self.edges.get((category, agent_id))
        if neighbor_ids is None:
            return []
        return list(neighbor_ids.keys())

    # ── agents ───────────────────────────────────────────────────────────────

    def _add_agent(self, category: int, agent_id: int) -> None:
        self.nodes.add((category, agent_id))

    def _remove_agent(self, category: int, agent_id: int) -> None:
        agent_tuple = (category, agent_id)
        self.nodes.remove(agent_tuple)
        target_edges = self.edges.pop(agent_tuple)
        if not self.directed:
            for target_node, edge in target_edges.items():
                self.edges[target_node].pop(agent_tuple)

    def remove_agent(self, agent) -> None:
        assert hasattr(agent, "category")
        self._remove_agent(agent.category, agent.id)

    def add_agent(self, agent) -> None:
        assert isinstance(agent, NetworkAgent)
        agent.set_category()
        agent._set_network(self)
        self._add_agent(agent.category, agent.id)

    def create_edge(self, agent_1_id: int, category_1: int, agent_2_id: int,
                    category_2: int, **edge_properties) -> None:
        edge = self.edge_cls(category_1, agent_1_id, category_2, agent_2_id, edge_properties)
        src_pos = (category_1, agent_1_id)
        dst_pos = (category_2, agent_2_id)
        assert src_pos in self.nodes
        assert dst_pos in self.nodes
        self.add_edge(src_pos, dst_pos, edge)

    def all_agents(self) -> Set[NodeType]:
        return self.nodes

    def get_node_edges(self, agent) -> List[Edge]:
        assert isinstance(agent, NetworkAgent)
        return list(self.edges[(agent.category, agent.id)].values())

    # ── layout (visualization only; unused on the non-visual path) ────────────

    def setup_layout_creator(self, layout_creator) -> None:
        self._layout_creator = layout_creator

    def update_layout(self) -> None:
        import ast

        import networkx as nx
        import numpy as np

        if os.path.exists(self.layout_file):
            try:
                G = nx.read_gexf(self.layout_file, node_type=ast.literal_eval)
                self.layout = {n: np.array([G.nodes[n]["viz"]["position"]["x"],
                                            G.nodes[n]["viz"]["position"]["y"]]) for n in G.nodes}
                return
            except Exception:
                pass
        g = nx.DiGraph()
        for start_node in self.edges.keys():
            for end_node in self.edges[start_node].keys():
                g.add_edge(start_node, end_node)
        layout = self._layout_creator(g)
        for node, pos in layout.items():
            g.nodes[node]["viz"] = {"position": {"x": pos[0], "y": pos[1], "z": 0}}
        nx.write_gexf(g, self.layout_file)
        self.layout = layout

    def get_position(self, agent_category: int, agent_id: int):
        if (agent_category, agent_id) not in self.layout:
            self.update_layout()
        return self.layout[(agent_category, agent_id)] * 1000

    # ── ABM Auto graph-construction seam + neighbour resolution ───────────────

    def setup_agent_connections(self, agent_lists: List[Any], topology) -> None:
        """Build the network from a Topology callable ``(n, rng) -> nx.Graph``."""
        assert isinstance(agent_lists, list)
        import random as _random

        node_id = 0
        node_id_to_node_type: Dict[int, NodeType] = {}
        for agent_list in agent_lists:
            if len(agent_list) > 0:
                agent_list[0].set_category()
                self.agent_categories[agent_list[0].category] = agent_list
            for agent in agent_list:
                self.add_agent(agent)
                agent._set_network(self)
                node_id_to_node_type[node_id] = (agent.category, agent.id)
                node_id += 1

        rng = self._rng if self._rng is not None else _random.Random()
        g = topology(len(self.nodes), rng)
        for edge in g.edges:
            src = node_id_to_node_type[edge[0]]
            dst = node_id_to_node_type[edge[1]]
            self.add_edge(src, dst, self.edge_cls(src[0], src[1], dst[0], dst[1], {}))
        self._nx_edges = list(g.edges)

    def get_neighbors(self, agent, agent_list: Any = None, return_agents: bool = True):
        """Neighbours of *agent*: NetworkAgent objects by default, or raw
        ``(category, id)`` tuples with ``return_agents=False``."""
        assert hasattr(agent, "category")
        raw = self._get_neighbor_positions(agent.id, agent.category)
        if not return_agents:
            return raw
        effective_list = agent_list if agent_list is not None else self._agent_list_ref
        if effective_list is None:
            raise ValueError(
                "ABM Auto Network.get_neighbors(): no agent_list available. Use "
                "'from abm_auto.runtime import Model' (auto-injects), or pass "
                "agent_list=self.agents."
            )
        result = []
        for item in raw:
            if isinstance(item, tuple):
                category, agent_id = item
                if category in self.agent_categories:
                    result.append(self.agent_categories[category].get_agent(agent_id))
                else:
                    result.append(effective_list[agent_id])
            else:
                result.append(item)
        return result


__all__ = ["Network", "Edge"]
